"""Application configuration, Supabase client factory and schema bootstrap.

Security notes
--------------
* Credentials are read **only** from ``st.secrets`` (or environment variables as a
  fallback for CI/containers). They are never hard-coded or written to source.
* If ``.streamlit/secrets.toml`` does not exist, a template is created with
  placeholder values and the app shows setup instructions instead of crashing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import streamlit as st
from supabase import Client, create_client

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = ROOT_DIR / ".streamlit"
SECRETS_FILE = SECRETS_DIR / "secrets.toml"

SECRETS_TEMPLATE = """\
# ============================================================
#  Concord ChemTrack - Supabase credentials  (DO NOT COMMIT)
# ============================================================
#  Supabase Dashboard -> Project Settings -> API
SUPABASE_URL = "https://YOUR-PROJECT-REF.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_OR_SERVICE_ROLE_KEY"
"""

# Tables used by the application
T_USERS = "users"                    # existing table: id, username, password, created_at
T_CATEGORIES = "chemical_categories" # optional grouping
T_ITEMS = "chemical_items"           # master chemical items
T_TRANSACTIONS = "stock_transactions"# stock in / out entries


# --------------------------------------------------------------------------
# Secrets bootstrap
# --------------------------------------------------------------------------
def ensure_secrets_template() -> bool:
    """Create ``.streamlit/secrets.toml`` from the template if missing.

    Returns ``True`` when a *new* template was created.
    """
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    if SECRETS_FILE.exists():
        return False
    SECRETS_FILE.write_text(SECRETS_TEMPLATE, encoding="utf-8")
    return True


def _secret(name: str) -> Optional[str]:
    """Read a single value from st.secrets, falling back to environment vars."""
    try:
        value = st.secrets.get(name)  # type: ignore[attr-defined]
        if value:
            return str(value).strip()
    except Exception:
        # st.secrets raises when the file is missing/malformed - fall through
        pass
    return (os.getenv(name) or "").strip() or None


def get_credentials() -> tuple[Optional[str], Optional[str]]:
    """Return ``(url, key)``; either may be ``None`` when not configured."""
    return _secret("SUPABASE_URL"), _secret("SUPABASE_KEY")


def credentials_look_valid(url: Optional[str], key: Optional[str]) -> bool:
    """Heuristic check so placeholders in the template are not treated as real."""
    if not url or not key:
        return False
    if "YOUR-PROJECT-REF" in url or "YOUR_SUPABASE" in key:
        return False
    return url.startswith("http") and len(key) > 20


def secrets_configured() -> bool:
    """True when usable Supabase credentials are present."""
    return credentials_look_valid(*get_credentials())


# --------------------------------------------------------------------------
# Supabase client
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Optional[Client]:
    """Create (and cache) the Supabase client.

    ``@st.cache_resource`` keeps a single connection pool across reruns, which
    keeps page navigation fast. Returns ``None`` when credentials are missing.
    """
    url, key = get_credentials()
    if not credentials_look_valid(url, key):
        return None
    try:
        return create_client(url, key)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - network / config failure
        st.session_state["_supabase_error"] = str(exc)
        return None


def require_client() -> Optional[Client]:
    """Return the client or render a friendly setup message and return None."""
    client = get_supabase_client()
    if client is None:
        render_setup_help()
    return client


def render_setup_help() -> None:
    """Show setup instructions when Supabase is not configured."""
    from src.ui import setup_card  # local import to avoid a cycle

    setup_card(
        error=st.session_state.get("_supabase_error"),
        secrets_path=SECRETS_FILE,
    )


# --------------------------------------------------------------------------
# Error handling helpers
# --------------------------------------------------------------------------
def friendly_db_error(exc: Any) -> str:
    """Translate common PostgREST / Supabase errors into user-readable text."""
    raw = str(exc) or exc.__class__.__name__
    low = raw.lower()

    if "duplicate key" in low or "23505" in low:
        return "That record already exists (duplicate value). Please use a unique name/code."
    if "invalid api key" in low or "jwt" in low or "401" in low:
        return "Authentication with Supabase failed. Check SUPABASE_KEY in .streamlit/secrets.toml."
    if "could not find the table" in low or "pgrst205" in low or "42p01" in low:
        return "A required table was not found in Supabase. Run the generated SQL (see Settings)."
    if "row-level security" in low or "42501" in low:
        return "Supabase blocked the request via Row Level Security. Use a service-role key or add an RLS policy."
    if "timeout" in low or "timed out" in low:
        return "The database request timed out. Please try again."
    if "getaddrinfo" in low or "name or service not known" in low or "connection" in low:
        return "Could not reach Supabase. Check your internet connection and SUPABASE_URL."
    return raw


# --------------------------------------------------------------------------
# Schema bootstrap
# --------------------------------------------------------------------------
SCHEMA_SQL = """\
-- Concord ChemTrack - required tables (run once in Supabase SQL editor)

-- users (expected to already exist)
create table if not exists public.users (
    id         uuid primary key default gen_random_uuid(),
    username   text not null unique,
    password   text not null,
    created_at timestamptz not null default now()
);
alter table public.users enable row level security;

create table if not exists public.chemical_categories (
    id         bigint generated by default as identity primary key,
    name       text not null unique,
    created_at timestamptz not null default now()
);

create table if not exists public.chemical_items (
    id            bigint generated by default as identity primary key,
    item_code     text not null unique,
    name          text not null,
    category      text,
    unit          text not null default 'kg',
    supplier      text,
    reorder_level numeric(14,3) not null default 0,
    opening_qty   numeric(14,3) not null default 0,
    notes         text,
    created_by    text,
    created_at    timestamptz not null default now()
);

create table if not exists public.stock_transactions (
    id           bigint generated by default as identity primary key,
    item_id      bigint not null references public.chemical_items(id) on delete cascade,
    txn_type     text not null check (txn_type in ('IN','OUT','ADJUST')),
    quantity     numeric(14,3) not null,
    unit         text,
    batch_no     text,
    supplier     text,
    issued_to    text,
    reference    text,
    remarks      text,
    txn_date     date not null default current_date,
    created_by   text,
    created_at   timestamptz not null default now()
);
"""


def _table_exists(client: Client, table: str) -> bool:
    try:
        client.table(table).select("*", count="exact").limit(1).execute()
        return True
    except Exception:
        return False


def ensure_schema(client: Client) -> list[str]:
    """Best-effort creation of optional tables.

    PostgREST cannot execute DDL, so creation only succeeds when the connected
    key belongs to a role with direct Postgres access and the project exposes
    the ``/sql`` RPC. In practice these tables are usually created from the SQL
    in :data:`SCHEMA_SQL`; this function simply reports which are missing so the
    UI can guide the user. Returns the list of missing table names.
    """
    missing = [
        t for t in (T_CATEGORIES, T_ITEMS, T_TRANSACTIONS) if not _table_exists(client, t)
    ]
    return missing
