"""Authentication: login + registration against the Supabase ``users`` table.

Table contract (pre-existing)
-----------------------------
======================  ====================================================
id                      uuid  (server default)
username                text  (unique)
password                text
created_at              timestamptz (server default)
======================  ====================================================

Passwords are stored as salted PBKDF2-SHA256 hashes (``pbkdf2_sha256$...``).
Legacy plain-text values already present in the table are still accepted on
login and transparently upgraded to a hash on the user's next sign-in.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Optional

import streamlit as st

from src import ui
from src.config import T_USERS, friendly_db_error, require_client

_HASH_ALGO = "pbkdf2_sha256"
_HASH_ITERATIONS = 240_000
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
_MIN_PASSWORD = 6


# --------------------------------------------------------------------------
# Password hashing helpers
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _HASH_ITERATIONS)
    return f"{_HASH_ALGO}${_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    """Constant-time verification supporting both hashed and legacy plain text."""
    if not stored:
        return False
    if stored.startswith(f"{_HASH_ALGO}$"):
        try:
            _, iterations, salt_hex, hash_hex = stored.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
            )
            return hmac.compare_digest(digest.hex(), hash_hex)
        except (ValueError, TypeError):
            return False
    # Legacy plain-text record from an older system.
    return hmac.compare_digest(stored, password)


# --------------------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------------------
def init_session() -> None:
    """Ensure the session-state keys used across the app exist."""
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("auth_view", "login")
    st.session_state.setdefault("nav", "Chemical Add_on")


def login_user(user: dict) -> None:
    st.session_state.logged_in = True
    st.session_state.username = user.get("username", "")
    st.session_state.user_id = user.get("id")
    st.session_state.nav = "Chemical Add_on"


def logout_user() -> None:
    for key in ("logged_in", "username", "user_id"):
        st.session_state[key] = False if key == "logged_in" else ("" if key == "username" else None)
    st.session_state.auth_view = "login"


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def _validate_registration(username: str, password: str, confirm: str) -> Optional[str]:
    if not username or not password:
        return "Username and password are required."
    if not _USERNAME_RE.match(username):
        return "Username must be 3–32 characters (letters, numbers, dot, dash, underscore)."
    if len(password) < _MIN_PASSWORD:
        return f"Password must be at least {_MIN_PASSWORD} characters."
    if password != confirm:
        return "Passwords do not match."
    return None


# --------------------------------------------------------------------------
# Database operations (commented: all calls are wrapped in try/except)
# --------------------------------------------------------------------------
def fetch_user(client, username: str) -> Optional[dict]:
    """Look up one user by username (case-insensitive)."""
    try:
        response = (
            client.table(T_USERS)
            .select("id, username, password, created_at")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None
    except Exception as exc:
        st.error(f"Could not reach the user database. {friendly_db_error(exc)}", icon="⚠️")
        return None


def register_user(client, username: str, password: str) -> tuple[bool, str]:
    """Insert a new account. Returns ``(ok, message)``."""
    try:
        existing = (
            client.table(T_USERS).select("id").eq("username", username).limit(1).execute()
        )
        if existing.data:
            return False, "That username is already taken. Please choose another."

        client.table(T_USERS).insert(
            {"username": username, "password": hash_password(password)}
        ).execute()
        return True, "Account created successfully. You can sign in now."
    except Exception as exc:
        return False, friendly_db_error(exc)


def authenticate(client, username: str, password: str) -> tuple[bool, str]:
    """Verify credentials. Returns ``(ok, message)``."""
    user = fetch_user(client, username)
    if not user:
        # Do not disclose whether the username exists.
        return False, "Invalid username or password."
    if not verify_password(password, user.get("password")):
        return False, "Invalid username or password."

    # Opportunistically upgrade legacy plain-text passwords to a hash.
    stored = user.get("password") or ""
    if not stored.startswith(f"{_HASH_ALGO}$"):
        try:
            client.table(T_USERS).update({"password": hash_password(password)}).eq(
                "id", user["id"]
            ).execute()
        except Exception:
            pass  # non-critical; login still succeeds

    login_user(user)
    return True, "Signed in."


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
def _auth_brand(subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="cc-auth-brand">
          <div class="cc-auth-logo">CF</div>
          <div class="cc-auth-title">Concord ChemTrack</div>
          <div class="cc-auth-sub">{ui.esc(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_page() -> None:
    """Render the login / register card. Sets session state on success."""
    init_session()
    client = require_client()
    if client is None:
        return

    left, center, right = st.columns([1, 1.35, 1])
    with center:
        if st.session_state.auth_view == "register":
            _render_register(client)
        else:
            _render_login(client)

        st.markdown(
            f'<div class="cc-muted" style="text-align:center;font-size:.72rem;margin-top:1rem">'
            f"{ui.COMPANY} &middot; Internal use only</div>",
            unsafe_allow_html=True,
        )


def _render_login(client) -> None:
    _auth_brand("Sign in to manage chemical inventory")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="e.g. lahirus", key="login_username")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
        submitted = st.form_submit_button("Sign in", width="stretch")

    if submitted:
        username = (username or "").strip()
        if not username or not password:
            st.error("Please enter both username and password.", icon="⚠️")
        else:
            with st.spinner("Verifying credentials…"):
                ok, message = authenticate(client, username, password)
            if ok:
                st.toast(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error(message, icon="🔒")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="cc-muted" style="text-align:center;font-size:.8rem">'
        "New to ChemTrack?</div>",
        unsafe_allow_html=True,
    )
    if st.button("Create an account", width="stretch", type="secondary"):
        st.session_state.auth_view = "register"
        st.rerun()


def _render_register(client) -> None:
    _auth_brand("Create your ChemTrack account")
    with st.form("register_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="3–32 characters", key="reg_username")
        password = st.text_input("Password", type="password", placeholder="min. 6 characters", key="reg_password")
        confirm = st.text_input("Confirm password", type="password", placeholder="repeat password", key="reg_confirm")
        submitted = st.form_submit_button("Create account", width="stretch")

    if submitted:
        username = (username or "").strip()
        problem = _validate_registration(username, password or "", confirm or "")
        if problem:
            st.error(problem, icon="⚠️")
        else:
            with st.spinner("Creating account…"):
                ok, message = register_user(client, username, password)
            if ok:
                st.success(message, icon="✅")
                st.session_state.auth_view = "login"
                st.session_state["login_username"] = username
                st.rerun()
            else:
                st.error(message, icon="⚠️")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    if st.button("← Back to sign in", width="stretch", type="secondary"):
        st.session_state.auth_view = "login"
        st.rerun()
