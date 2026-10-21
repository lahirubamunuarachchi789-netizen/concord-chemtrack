"""Visual QA renderer (no Supabase required).

Runs app.py against the fake backend and serialises the real Streamlit element
tree (markdown/HTML, forms, inputs, buttons, dataframes, alerts) into static
HTML pages with the production stylesheet, preserving the nesting of
containers/columns so layout can be checked in a browser.

Usage: python tools_render_static.py   ->   qa/login.html, qa/dashboard.html, qa/report.html
"""

from __future__ import annotations

import html as html_lib
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import fake_supabase  # noqa: E402,F401  (patches config to the in-memory backend)
from streamlit.testing.v1 import AppTest  # noqa: E402

from src.styles import GLOBAL_CSS  # noqa: E402

OUT = ROOT / "qa"


def render_tree(node, depth: int = 0) -> str:
    """Recursively convert an element-tree node into HTML."""
    block_type = getattr(node, "type", "")
    proto = getattr(node, "proto", None)

    # ------------------------------------------------------------- leaves
    if block_type in ("markdown", "html"):
        return proto.body

    if block_type == "button":
        return (
            f'<div class="stButton"><button class="st-emotion-cache">'
            f"{html_lib.escape(proto.label)}</button></div>"
        )

    if block_type == "form_submit_button":
        return (
            '<div class="stFormSubmitButton">'
            f'<button type="submit">{html_lib.escape(proto.label)}</button></div>'
        )

    if block_type == "text_input":
        return (
            f'<div class="stTextInput"><label>{html_lib.escape(proto.label)}</label>'
            f'<input placeholder="{html_lib.escape(proto.placeholder or "")}"></div>'
        )

    if block_type == "number_input":
        return (
            f'<div class="stNumberInput"><label>{html_lib.escape(proto.label)}</label>'
            f'<input type="number" value="{proto.value}"></div>'
        )

    if block_type == "text_area":
        return (
            f'<div class="stTextArea"><label>{html_lib.escape(proto.label)}</label>'
            '<textarea rows="2"></textarea></div>'
        )

    if block_type == "selectbox":
        default = ""
        options = list(getattr(proto, "options", []) or [])
        index = int(getattr(proto, "index", 0) or 0)
        if options:
            opt = options[index] if index < len(options) else options[0]
            default = getattr(opt, "text", opt)
        return (
            f'<div class="stSelectbox"><label>{html_lib.escape(proto.label)}</label>'
            f'<div class="select">▾&nbsp; {html_lib.escape(default)}</div></div>'
        )

    if block_type in ("checkbox", "multiselect", "date_input", "download_button"):
        label = getattr(proto, "label", "") or getattr(proto, "placeholder", "")
        return f'<div class="st{block_type.title().replace("_", "")}">' \
               f'<label>{html_lib.escape(str(label))}</label></div>'

    if block_type == "alert":
        body = "".join(render_tree(c, depth + 1) for c in node.children.values())
        return f'<div class="stAlert">{body}</div>'

    if block_type in ("dataframe", "arrow_data_frame", "bar_chart"):
        return ('<div data-testid="stDataFrame" style="padding:.7rem;font-size:.76rem;color:#5B6B84">'
                "▦ table / chart rendered here</div>")

    if block_type == "code":
        return f'<pre style="font-size:.68rem;overflow:auto">{html_lib.escape(proto.body[:400])}</pre>'

    # ---------------------------------------------------------- containers
    children = list((getattr(node, "children", None) or {}).values())
    if not children:
        return ""
    inner = "".join(render_tree(child, depth + 1) for child in children)

    if block_type in ("horizontal_block", "flex_container"):
        return f'<div class="stHorizontalBlock" data-testid="stHorizontalBlock">{inner}</div>'
    if block_type == "column":
        width = getattr(node, "weight", None) or 1
        return (
            f'<div class="stColumn" data-testid="column" style="flex:{width} 1 0">'
            f"{inner}</div>"
        )
    if block_type == "form":
        return f'<form class="stForm" data-testid="stForm">{inner}</form>'
    if block_type == "tabs":
        return f'<div class="stTabs">{inner}</div>'
    if block_type == "tab":
        return f'<div class="stTab">{inner}</div>'
    if block_type == "expander":
        return f'<details open><summary>{html_lib.escape(proto.label)}</summary>{inner}</details>'
    return f'<div class="stVerticalBlock" data-testid="stVerticalBlock">{inner}</div>'


PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Concord ChemTrack - QA</title>
<style>{css}</style>
<style>
  /* Minimal stand-ins for Streamlit's own layout primitives */
  .stVerticalBlock {{ display:flex; flex-direction:column; gap:.55rem; }}
  .stHorizontalBlock {{ display:flex; gap:.8rem; align-items:flex-start; }}
  .stColumn {{ flex:1 1 0; min-width:0; }}
  /* Markdown is a block in real Streamlit: it never sits beside a sibling */
  .stMarkdown, .stMarkdownContainer {{ display:block; width:100%; }}
  .stColumn > .stVerticalBlock {{ gap:.4rem; }}
  /* Inline ``st.markdown`` inside a form is emitted as a new block by the test
     tree, so emulate Streamlit's behaviour by keeping it at its natural height */
  form.stForm > .stVerticalBlock {{ gap:.5rem; }}
  form.stForm {{ display:flex; flex-direction:column; gap:.5rem; }}
  form.stForm .stHorizontalBlock {{ flex-direction:row; }}
  .stTextInput label,.stSelectbox label,.stNumberInput label,.stTextArea label {{
     display:block; font-size:.78rem; font-weight:700; color:#5B6B84; margin-bottom:.2rem; }}
  .stTextInput input,.stNumberInput input,.stTextArea textarea {{
     width:100%; box-sizing:border-box; padding:.5rem .6rem; font-size:.9rem;
     border:1px solid #DFE6F1; border-radius:10px; background:#FBFCFE; }}
  .select {{ border:1px solid #DFE6F1; border-radius:10px; background:#FBFCFE;
            padding:.5rem .6rem; font-size:.9rem; }}
  details {{ background:#fff; border:1px solid #DFE6F1; border-radius:12px; padding:.6rem .8rem; }}
  summary {{ font-weight:700; cursor:pointer; font-size:.9rem; }}
  button {{ cursor:pointer; border:1px solid #DFE6F1; background:#fff; border-radius:10px;
           padding:.5rem .9rem; font-weight:700; font-family:inherit; font-size:.9rem; }}
  .stDataFrame {{ background:#fff; border:1px solid #DFE6F1; border-radius:12px; }}
  .stAlert {{ background:#fff; border:1px solid #DFE6F1; border-left:4px solid #2E6BE6;
             border-radius:10px; padding:.6rem .8rem; font-size:.84rem; }}
</style>
</head><body>
<div data-testid="stAppViewContainer" style="position:relative;display:flex">
  {sidebar}
  <div data-testid="stMain" style="flex:1;min-width:0">
    <div data-testid="stMainBlockContainer" class="block-container">{main}</div>
  </div>
</div></body></html>"""


def build(state: dict, name: str, sidebar: bool) -> None:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, [e.value for e in at.exception]

    main_html = render_tree(at.main)

    side_html = ""
    if sidebar:
        side_html = (
            '<div data-testid="stSidebar" style="width:250px;flex:0 0 250px;'
            'padding:1rem .85rem">' + render_tree(at.sidebar) + "</div>"
        )

    css = GLOBAL_CSS.replace("<style>", "").replace("</style>", "")
    (OUT / f"{name}.html").write_text(
        PAGE.format(css=css, sidebar=side_html, main=main_html), encoding="utf-8"
    )
    print(f"wrote qa/{name}.html")


OUT.mkdir(exist_ok=True)
build({"logged_in": False, "auth_view": "login"}, "login", sidebar=False)
build({"logged_in": True, "username": "tester", "user_id": "u1",
       "auth_view": "login", "nav": "Chemical Add_on"}, "dashboard", sidebar=True)
build({"logged_in": True, "username": "tester", "user_id": "u1",
       "auth_view": "login", "nav": "Report"}, "report", sidebar=True)
