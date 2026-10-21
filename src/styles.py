"""Global CSS: modern Navy Blue + White theme, fully responsive.

Streamlit's DOM is addressed defensively (``data-testid`` + class selectors) so
the styling keeps working across recent versions. All rules are mobile-first;
``@media (min-width: ...)`` blocks enhance the desktop experience.
"""

NAVY = "#0B1F3A"
NAVY_600 = "#12305A"
NAVY_500 = "#1B4B8F"
NAVY_100 = "#E7EEF8"
ACCENT = "#2E6BE6"
SUCCESS = "#12A150"
DANGER = "#D64545"
WARNING = "#E5A100"
MUTED = "#5B6B84"

GLOBAL_CSS = f"""
<style>
/* ---------------------------------------------------------------- tokens */
:root {{
  --navy: {NAVY};
  --navy-600: {NAVY_600};
  --navy-500: {NAVY_500};
  --navy-100: {NAVY_100};
  --accent: {ACCENT};
  --success: {SUCCESS};
  --danger: {DANGER};
  --warning: {WARNING};
  --muted: {MUTED};
  --white: #FFFFFF;
  --bg: #F5F7FB;
  --border: #DFE6F1;
  --radius: 14px;
  --shadow-sm: 0 1px 2px rgba(11,31,58,.06), 0 2px 8px rgba(11,31,58,.05);
  --shadow-md: 0 10px 30px rgba(11,31,58,.10);
}}

/* ------------------------------------------------------------ base shell */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--bg);
  color: var(--navy);
  font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"] {{ right: .5rem; }}
[data-testid="stDecoration"] {{ display: none; }}
#MainMenu, footer {{ visibility: hidden; }}

.block-container {{
  padding: 1rem .9rem 3rem .9rem !important;
  max-width: 1240px;
}}
/* Markdown is a block: never let it join a flex row (keeps columns aligned) */
[data-testid="stMarkdownContainer"] {{ display: block; }}
[data-testid="stMarkdownContainer"] > div, [data-testid="stMarkdownContainer"] > p {{ margin: 0; }}
/* Empty spacer divs used for vertical rhythm */
.cc-spacer {{ display: block; height: .5rem; }}

/* ------------------------------------------------------------- typography */
h1, h2, h3, h4 {{ color: var(--navy); letter-spacing: -.01em; }}
h1 {{ font-size: 1.45rem; font-weight: 800; margin: 0; }}
h2 {{ font-size: 1.15rem; font-weight: 700; }}
h3 {{ font-size: 1rem; font-weight: 700; }}
p, label, span {{ color: var(--navy); }}
.cc-muted, .cc-muted * {{ color: var(--muted) !important; }}

/* --------------------------------------------------------------- sidebar */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, var(--navy) 0%, var(--navy-600) 100%);
  border-right: none;
}}
[data-testid="stSidebar"] * {{ color: #FFFFFF; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color: #C9D6EA; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.14); }}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"] button {{ color: #FFFFFF; }}

/* Sidebar navigation buttons: quiet until hovered / active */
[data-testid="stSidebar"] .stButton > button {{
  position: relative;
  width: 100%;
  text-align: left;
  justify-content: flex-start;
  background: transparent;
  border: 1px solid transparent;
  color: #E4ECF8;
  font-weight: 600;
  font-size: .92rem;
  padding: .62rem .8rem;
  border-radius: 10px;
  transition: background .15s ease, border-color .15s ease;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  background: rgba(255,255,255,.10);
  border-color: rgba(255,255,255,.16);
}}

/* Active navigation item.
   Each nav item is preceded by an ``st.html`` marker in the sidebar flow, so the
   marker and the button block are siblings and ``+`` works directly. */
.cc-nav-item {{ display: none; }}
[data-testid="stSidebar"] .cc-nav-active + div .stButton > button,
[data-testid="stSidebar"] .cc-nav-active + div.stButton > button,
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: #FFFFFF !important;
  color: var(--navy) !important;
  border-color: #FFFFFF !important;
  box-shadow: var(--shadow-sm);
  font-weight: 800 !important;
}}
[data-testid="stSidebar"] .cc-nav-active + div .stButton > button::before {{
  content: "";
  position: absolute;
  left: -.5rem;
  top: 50%;
  width: 3px; height: 18px;
  margin-top: -9px;
  border-radius: 3px;
  background: #9DBEF5;
}}

/* Sidebar brand block */
.cc-brand {{
  display: flex; align-items: center; gap: .65rem;
  padding: .35rem 0 1rem 0;
}}
.cc-brand-mark {{
  width: 40px; height: 40px; flex: 0 0 40px;
  border-radius: 11px;
  background: #FFFFFF;
  color: var(--navy);
  display: grid; place-items: center;
  font-weight: 900; font-size: 1.05rem;
  letter-spacing: -.5px;
}}
.cc-brand-name {{ font-weight: 800; font-size: 1rem; line-height: 1.15; color:#fff; }}
.cc-brand-sub {{ font-size: .72rem; color: #9FB3D1; letter-spacing: .08em; text-transform: uppercase; }}

.cc-user {{
  display: flex; align-items: center; gap: .6rem;
  padding: .7rem .8rem;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 12px;
  margin-bottom: .35rem;
}}
.cc-avatar {{
  width: 34px; height: 34px; border-radius: 50%;
  background: #FFFFFF; color: var(--navy);
  display: grid; place-items: center;
  font-weight: 800; font-size: .85rem; flex: 0 0 34px;
}}
.cc-user-name {{ font-weight: 700; font-size: .88rem; color:#fff; line-height:1.1; }}
.cc-user-role {{ font-size: .72rem; color: #9FB3D1; }}

/* ----------------------------------------------------------------- header */
.cc-page-header {{
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: .6rem;
  background: var(--white);
  border: 1px solid var(--border);
  border-left: 5px solid var(--navy);
  border-radius: var(--radius);
  padding: .95rem 1.1rem;
  box-shadow: var(--shadow-sm);
  margin-bottom: 1rem;
}}
/* First element after the header should not add a second gap */
.cc-page-header + div {{ margin-top: 0 !important; }}
.cc-page-header .cc-title {{ font-size: 1.18rem; font-weight: 800; color: var(--navy); }}
.cc-page-header .cc-sub {{ font-size: .8rem; color: var(--muted); }}

/* -------------------------------------------------------------- auth card */
.cc-auth-wrap {{ max-width: 430px; margin: 0 auto; }}
.cc-auth-brand {{ text-align: center; margin: 0 0 1.1rem 0; }}
.cc-auth-logo {{
  width: 62px; height: 62px; margin: 0 auto .6rem auto;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-500) 100%);
  color: #fff; display: grid; place-items: center;
  font-weight: 900; font-size: 1.4rem;
  box-shadow: var(--shadow-md);
}}
.cc-auth-title {{ font-size: 1.5rem; font-weight: 800; color: var(--navy); line-height: 1.2; }}
.cc-auth-sub {{ font-size: .84rem; color: var(--muted); margin-top: .2rem; }}

[data-testid="stForm"] {{
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1.15rem 1.1rem .6rem 1.1rem;
  box-shadow: var(--shadow-md);
}}

/* ------------------------------------------------------------------ cards */
.cc-card {{
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.05rem;
  box-shadow: var(--shadow-sm);
}}
.cc-card h4 {{ margin: 0 0 .15rem 0; font-size: .95rem; }}
.cc-kpi {{
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: .85rem .95rem;
  box-shadow: var(--shadow-sm);
  height: 100%;
}}
.cc-kpi-label {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); font-weight: 700; }}
.cc-kpi-value {{ font-size: 1.45rem; font-weight: 800; color: var(--navy); line-height: 1.25; }}
.cc-kpi-foot {{ font-size: .74rem; color: var(--muted); }}

/* ----------------------------------------------------------------- inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {{
  border-radius: 10px !important;
  border-color: var(--border) !important;
  background: #FBFCFE !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
  border-color: var(--navy) !important;
  box-shadow: 0 0 0 3px rgba(11,31,58,.10) !important;
}}
[data-testid="stWidgetLabel"] p {{
  font-size: .78rem !important;
  font-weight: 700 !important;
  color: var(--muted) !important;
  letter-spacing: .02em;
}}

  .cc-nav-item {{ display:none; }}
  /* Active nav highlight for Streamlit builds without a button "kind" attribute */
  [data-testid="stSidebar"] .cc-nav-active + div .stButton > button,
  [data-testid="stSidebar"] .cc-nav-active + div .stButton > button:hover {{
    background: #FFFFFF !important;
    color: var(--navy) !important;
    border-color: #FFFFFF !important;
  }}
  [data-testid="stSidebar"] .cc-nav-item + div .stButton > button {{
    background: transparent; color: #E4ECF8; border-color: transparent;
  }}

/* ---------------------------------------------------------------- buttons */
.stButton > button, .stFormSubmitButton > button, [data-testid="stFormSubmitButton"] button {{
  border-radius: 10px;
  font-weight: 700;
  padding: .55rem 1rem;
  transition: transform .05s ease, box-shadow .15s ease, background .15s ease;
}}
.stButton > button:active {{ transform: translateY(1px); }}
[data-testid="stFormSubmitButton"] button,
.stButton > button[kind="primary"] {{
  background: var(--navy);
  color: #FFFFFF;
  border: 1px solid var(--navy);
  width: 100%;
}}
[data-testid="stFormSubmitButton"] button:hover,
.stButton > button[kind="primary"]:hover {{
  background: var(--navy-500);
  border-color: var(--navy-500);
  box-shadow: var(--shadow-md);
}}
.stButton > button[kind="secondary"] {{
  background: #FFFFFF;
  color: var(--navy);
  border: 1px solid var(--border);
}}

/* Secondary buttons inside the sidebar keep the transparent look */
[data-testid="stSidebar"] .stButton > button {{
  background: transparent; color: #E4ECF8; border-color: transparent;
}}
/* Nav items (marker present) stay quiet; only the active one is highlighted */
[data-testid="stSidebar"] .cc-nav-item + div .stButton > button {{
  background: transparent; color: #E4ECF8; border-color: transparent;
}}
/* Keep the active nav item visible even when it also matches the rule above */
[data-testid="stSidebar"] .cc-nav-active .stButton > button,
[data-testid="stSidebar"] .cc-nav-active .stButton > button:hover {{
  background: #FFFFFF !important;
  color: var(--navy) !important;
  border-color: #FFFFFF !important;
}}

/* Forms: stack widgets predictably and top-align multi-column rows */
[data-testid="stForm"] [data-testid="stVerticalBlock"] {{
  gap: .55rem;
}}
[data-testid="stForm"] [data-testid="stHorizontalBlock"] {{ align-items: flex-start; }}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {{ width: 100%; }}

/* ------------------------------------------------------------------ tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  gap: .25rem; background: var(--white);
  padding: .3rem; border-radius: 12px; border: 1px solid var(--border);
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
  border-radius: 9px; padding: .45rem .85rem; font-weight: 700; font-size: .85rem;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
  background: var(--navy-100); color: var(--navy);
}}

/* ----------------------------------------------------------------- tables */
[data-testid="stDataFrame"] {{
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--white);
  box-shadow: var(--shadow-sm);
}}
[data-testid="stDataFrame"] [role="columnheader"] {{
  background: var(--navy-100) !important;
  color: var(--navy) !important;
  font-weight: 700 !important;
}}

/* -------------------------------------------------------------- badges */
.cc-badge {{
  display: inline-block; padding: .12rem .55rem; border-radius: 999px;
  font-size: .72rem; font-weight: 800; letter-spacing: .03em;
}}
.cc-badge-in   {{ background: #E6F6EC; color: #0E7A3B; }}
.cc-badge-out  {{ background: #FCEAEA; color: #A62B2B; }}
.cc-badge-low  {{ background: #FFF5DE; color: #8A6200; }}
.cc-badge-ok   {{ background: var(--navy-100); color: var(--navy); }}

/* ------------------------------------------------------------- messages */
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* ================================================== MOBILE (<= 640px) */
@media (max-width: 640px) {{
  .block-container {{ padding: .6rem .6rem 2.5rem .6rem !important; }}
  h1 {{ font-size: 1.2rem; }}
  .cc-page-header {{ padding: .8rem .85rem; border-left-width: 4px; }}
  .cc-page-header .cc-title {{ font-size: 1.02rem; }}
  .cc-auth-title {{ font-size: 1.28rem; }}
  .cc-auth-logo {{ width: 54px; height: 54px; font-size: 1.2rem; }}
  [data-testid="stForm"] {{ padding: .9rem .75rem .4rem .75rem; border-radius: 14px; }}
  .cc-kpi-value {{ font-size: 1.2rem; }}
  .cc-kpi {{ padding: .7rem .75rem; }}
  /* Stack metric / column rows tightly on phones */
  [data-testid="stHorizontalBlock"] {{ gap: .5rem; flex-wrap: wrap; }}
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
    min-width: calc(50% - .5rem) !important;
    flex: 1 1 calc(50% - .5rem) !important;
  }}
  [data-testid="stSidebar"] {{ width: 86vw !important; min-width: 86vw !important; }}
}}

/* Fold wide expander / form columns on tablets too */
@media (max-width: 900px) and (min-width: 641px) {{
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {{ min-width: 45% !important; }}
}}
</style>
"""


def inject_css() -> None:
    """Inject the global stylesheet once per rerun."""
    import streamlit as st

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
