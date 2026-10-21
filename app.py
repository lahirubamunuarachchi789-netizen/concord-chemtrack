"""Concord ChemTrack - Streamlit entry point.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

# Bootstrap
from src import ui
from src.auth import init_session, logout_user, render_auth_page
from src.config import ensure_secrets_template
from src.styles import inject_css

st.set_page_config(
    page_title="Concord ChemTrack",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Page metadata + theme
inject_css()
ensure_secrets_template()
init_session()

NAV_OPTIONS = {
    "Chemical Add_on": "🧪",
    "Report": "📊",
}


# --------------------------------------------------------------------------
# Sidebar (post-login only)
# --------------------------------------------------------------------------
def render_sidebar() -> None:
    with st.sidebar:
        ui.brand_block()
        st.markdown(
            f'<div class="cc-muted" style="font-size:.7rem;margin:-.4rem 0 .9rem 0;'
            f'letter-spacing:.06em;text-transform:uppercase">{ui.esc(ui.COMPANY)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(ui.user_chip(st.session_state.username), unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:.68rem;letter-spacing:.1em;color:#7E93B4;'
            'text-transform:uppercase;font-weight:800;margin:.4rem 0 .35rem .2rem">Menu</div>',
            unsafe_allow_html=True,
        )

        for name, icon in NAV_OPTIONS.items():
            active = st.session_state.nav == name
            # ``st.html`` renders in place, so the marker becomes a true sibling
            # of the button block and CSS can style the active item reliably.
            st.html(f'<span class="cc-nav-item {"cc-nav-active" if active else ""}"></span>')
            if st.button(
                f"{icon}  {name}",
                key=f"nav_{name}",
                width="stretch",
                type="primary",
            ):
                if not active:
                    st.session_state.nav = name
                    st.rerun()

        st.markdown("<hr style='margin:1rem 0 .6rem 0'>", unsafe_allow_html=True)
        st.html('<span class="cc-nav-item"></span>')
        if st.button("⎋  Sign out", key="nav_logout", width="stretch", type="primary"):
            logout_user()
            st.rerun()

        st.markdown(
            f'<div style="position:relative;margin-top:1rem;font-size:.68rem;color:#7E93B4">'
            f'Concord ChemTrack v1.0 · {dt.date.today():%Y}</div>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------
# Dashboard pages
# --------------------------------------------------------------------------
def render_dashboard() -> None:
    page = st.session_state.get("nav", "Chemical Add_on")

    if page == "Chemical Add_on":
        ui.page_header(
            "Chemical Add_on",
            "Register chemicals, record stock receipts and issues",
            right_html="",
        )
        from src import inventory

        inventory.render()
    elif page == "Report":
        ui.page_header(
            "Report",
            "Transaction logs, movement summaries and current stock position",
        )
        from src import reports

        reports.render()
    else:  # defensive fallback
        st.session_state.nav = "Chemical Add_on"
        st.rerun()


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    if not st.session_state.logged_in:
        render_auth_page()
        return

    render_sidebar()
    render_dashboard()


if __name__ == "__main__":
    main()
