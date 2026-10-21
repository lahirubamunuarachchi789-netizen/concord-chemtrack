"""Chemical Add_on module: register master chemical items and record stock entries.

A *stock entry* is a row in ``stock_transactions`` of type IN / OUT / ADJUST.
Current balance per item is derived as::

    balance = opening_qty + SUM(IN) + SUM(ADJUST) - SUM(OUT)
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st

from src import ui
from src.config import T_CATEGORIES, T_ITEMS, T_TRANSACTIONS, friendly_db_error, require_client

UNITS = ["kg", "g", "L", "mL", "pcs", "bags", "drums", "packs"]
TXN_TYPES = ["IN", "OUT", "ADJUST"]


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
def fetch_items(client) -> pd.DataFrame:
    """All master items (empty dataframe on error)."""
    try:
        rows = (
            client.table(T_ITEMS)
            .select("*")
            .order("name")
            .execute()
            .data
            or []
        )
        return pd.DataFrame(rows)
    except Exception as exc:
        st.error(f"Could not load chemical items. {friendly_db_error(exc)}", icon="⚠️")
        return pd.DataFrame()


def fetch_categories(client) -> list[str]:
    """Category names from the optional categories table (falls back to item data)."""
    try:
        rows = client.table(T_CATEGORIES).select("name").order("name").execute().data or []
        return [r["name"] for r in rows if r.get("name")]
    except Exception:
        return []


def fetch_balances(client) -> pd.DataFrame:
    """Compute current stock balance per item.

    Returns columns: item_id, name, item_code, unit, reorder_level, opening_qty,
    total_in, total_out, total_adjust, balance.
    """
    items = fetch_items(client)
    if items.empty:
        return pd.DataFrame()

    try:
        txns = client.table(T_TRANSACTIONS).select("item_id, txn_type, quantity").execute().data or []
    except Exception as exc:
        st.warning(f"Stock movements could not be loaded. {friendly_db_error(exc)}", icon="⚠️")
        txns = []

    df_txn = pd.DataFrame(txns)
    if not df_txn.empty:
        df_txn["quantity"] = pd.to_numeric(df_txn["quantity"], errors="coerce").fillna(0)
        pv = df_txn.pivot_table(index="item_id", columns="txn_type", values="quantity", aggfunc="sum").fillna(0)
        for col in TXN_TYPES:
            if col not in pv.columns:
                pv[col] = 0.0
        pv = pv.rename(columns={"IN": "total_in", "OUT": "total_out", "ADJUST": "total_adjust"})
        pv = pv[["total_in", "total_out", "total_adjust"]].reset_index()
    else:
        pv = pd.DataFrame(columns=["item_id", "total_in", "total_out", "total_adjust"])

    out = items.copy()
    out["opening_qty"] = pd.to_numeric(out.get("opening_qty", 0), errors="coerce").fillna(0)
    out["reorder_level"] = pd.to_numeric(out.get("reorder_level", 0), errors="coerce").fillna(0)
    out = out.merge(pv, how="left", left_on="id", right_on="item_id")
    for col in ("total_in", "total_out", "total_adjust"):
        out[col] = pd.to_numeric(out.get(col, 0), errors="coerce").fillna(0)
    out["balance"] = out["opening_qty"] + out["total_in"] + out["total_adjust"] - out["total_out"]
    return out


def create_item(client, payload: dict) -> tuple[bool, str]:
    try:
        client.table(T_ITEMS).insert(payload).execute()
        return True, f"Item “{payload['name']}” added to the master list."
    except Exception as exc:
        return False, friendly_db_error(exc)


def create_transaction(client, payload: dict) -> tuple[bool, str]:
    try:
        client.table(T_TRANSACTIONS).insert(payload).execute()
        label = {"IN": "Stock received", "OUT": "Stock issued", "ADJUST": "Adjustment"}[payload["txn_type"]]
        return True, f"{label}: {payload['quantity']} {payload.get('unit') or ''}".strip()
    except Exception as exc:
        return False, friendly_db_error(exc)


# --------------------------------------------------------------------------
# UI sections
# --------------------------------------------------------------------------
def _next_item_code(items: pd.DataFrame) -> str:
    """Suggest the next sequential code (CFC-0001, CFC-0002, …)."""
    if items.empty or "item_code" not in items:
        return "CFC-0001"
    numbers = []
    for code in items["item_code"].dropna().astype(str):
        digits = "".join(ch for ch in code if ch.isdigit())
        if digits:
            numbers.append(int(digits))
    return f"CFC-{max(numbers, default=0) + 1:04d}"


def _status_badge(row) -> str:
    if row["balance"] <= 0:
        return "OUT OF STOCK"
    if row["reorder_level"] and row["balance"] <= row["reorder_level"]:
        return "LOW"
    return "OK"


def render() -> None:
    client = require_client()
    if client is None:
        return

    balances = fetch_balances(client)
    items = fetch_items(client) if balances.empty else balances

    # ------------------------------------------------------------- KPIs
    total_items = int(len(balances)) if not balances.empty else 0
    low_count = 0
    out_count = 0
    total_qty = 0.0
    if not balances.empty:
        statuses = balances.apply(_status_badge, axis=1)
        low_count = int((statuses == "LOW").sum())
        out_count = int((statuses == "OUT OF STOCK").sum())
        total_qty = float(balances["balance"].sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.kpi("Master items", total_items, "chemicals registered")
    with c2:
        ui.kpi("Total stock", f"{total_qty:,.2f}", "across all units")
    with c3:
        ui.kpi("Low stock", low_count, "at or below reorder level")
    with c4:
        ui.kpi("Out of stock", out_count, "requires immediate action")

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    tab_entry, tab_master = st.tabs(["📥  Stock entry", "🧪  Chemical master items"])

    with tab_entry:
        _render_stock_entry(client, balances, items)

    with tab_master:
        _render_master_items(client, balances)


# --------------------------------------------------------------------------
def _render_stock_entry(client, balances: pd.DataFrame, items: pd.DataFrame) -> None:
    ui.section_title("Record a stock entry", "Receive, issue or adjust chemical stock")
    if balances.empty:
        st.info("Add at least one chemical to the master list before recording stock.", icon="🧪")
        return

    options = {
        f"{r['item_code']} — {r['name']} ({r.get('unit') or 'unit n/a'})": r["id"]
        for _, r in balances.sort_values("name").iterrows()
    }
    lookup = {r["id"]: r for _, r in balances.iterrows()}

    with st.form("stock_entry_form", clear_on_submit=True):
        col_a, col_b = st.columns([1.6, 1])
        with col_a:
            selected = st.selectbox("Chemical item *", list(options.keys()))
        with col_b:
            txn_type = st.selectbox("Transaction type *", TXN_TYPES, index=0)

        current = lookup[options[selected]]
        col_c, col_d = st.columns(2)
        with col_c:
            quantity = st.number_input("Quantity *", min_value=0.0, step=0.5, format="%.3f")
            batch_no = st.text_input("Batch / lot no.", placeholder="e.g. B-2026-014")
            supplier = st.text_input("Supplier", value=(current.get("supplier") or ""))
        with col_d:
            txn_date = st.date_input("Date *", value=dt.date.today())
            reference = st.text_input("Reference / invoice", placeholder="e.g. GRN-1042")
            issued_to = st.text_input("Issued to", placeholder="Department / person")

        remarks = st.text_area("Remarks", placeholder="Any additional notes…", height=70)

        submitted = st.form_submit_button("Save stock entry", width="stretch")

    if not submitted:
        st.caption(
            f"Current balance of **{current.get('name')}**: "
            f"{float(current.get('balance', 0)):,.3f} {current.get('unit') or ''}"
        )
        return

    if quantity is None or float(quantity) <= 0:
        st.error("Quantity must be greater than zero.", icon="⚠️")
        return

    payload = {
        "item_id": options[selected],
        "txn_type": txn_type,
        "quantity": float(quantity),
        "unit": current.get("unit"),
        "batch_no": (batch_no or "").strip() or None,
        "supplier": (supplier or "").strip() or None,
        "issued_to": (issued_to or "").strip() or None,
        "reference": (reference or "").strip() or None,
        "remarks": (remarks or "").strip() or None,
        "txn_date": txn_date.isoformat(),
        "created_by": st.session_state.get("username"),
    }
    with st.spinner("Saving entry…"):
        ok, message = create_transaction(client, payload)

    if ok:
        st.success(message, icon="✅")
        st.rerun()
    else:
        st.error(message, icon="⚠️")


# --------------------------------------------------------------------------
def _render_master_items(client, balances: pd.DataFrame) -> None:
    ui.section_title("Chemical master items", "Manage the catalogue of chemicals used by Concord")

    with st.expander("➕  Add a new chemical item", expanded=balances.empty):
        categories = fetch_categories(client)
        existing_categories = (
            sorted(balances["category"].dropna().unique().tolist())
            if not balances.empty and "category" in balances
            else []
        )
        all_categories = sorted(set(categories) | set(existing_categories))

        with st.form("add_item_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                item_code = st.text_input("Item code *", value=_next_item_code(balances))
                name = st.text_input("Chemical name *", placeholder="e.g. Toluene")
                category = st.selectbox(
                    "Category",
                    ["(none)"] + all_categories + ["Other…"],
                    help="Group chemicals for quicker filtering in reports.",
                )
                custom_category = st.text_input("New category name", placeholder="Only if 'Other…' is selected")
            with c2:
                unit = st.selectbox("Unit *", UNITS, index=0)
                supplier = st.text_input("Default supplier")
                reorder_level = st.number_input("Reorder level", min_value=0.0, step=1.0, format="%.3f")
                opening_qty = st.number_input("Opening stock qty", min_value=0.0, step=1.0, format="%.3f")

            notes = st.text_area("Notes / hazard info", height=70, placeholder="Storage conditions, hazard class…")
            submitted = st.form_submit_button("Save chemical item", width="stretch")

        if submitted:
            item_code = (item_code or "").strip().upper()
            name = (name or "").strip()
            if not item_code or not name:
                st.error("Item code and chemical name are required.", icon="⚠️")
            else:
                if category == "Other…":
                    category = (custom_category or "").strip()
                payload = {
                    "item_code": item_code,
                    "name": name,
                    "category": None if category in ("", "(none)") else category,
                    "unit": unit,
                    "supplier": (supplier or "").strip() or None,
                    "reorder_level": float(reorder_level or 0),
                    "opening_qty": float(opening_qty or 0),
                    "notes": (notes or "").strip() or None,
                    "created_by": st.session_state.get("username"),
                }
                with st.spinner("Saving item…"):
                    ok, message = create_item(client, payload)
                if ok:
                    st.success(message, icon="✅")
                    st.rerun()
                else:
                    st.error(message, icon="⚠️")

    # ------------------------------------------------------------ table
    if balances.empty:
        st.info("No chemical items yet. Use the form above to add your first item.", icon="🧪")
        return

    f1, f2 = st.columns([2, 1])
    with f1:
        search = st.text_input("Search", placeholder="Search by name or code…", label_visibility="collapsed")
    with f2:
        only_alerts = st.checkbox("Show low / out of stock only", value=False)

    view = balances.copy()
    view["status"] = view.apply(_status_badge, axis=1)
    if search:
        term = search.lower()
        view = view[
            view["name"].str.lower().str.contains(term, na=False)
            | view["item_code"].astype(str).str.lower().str.contains(term, na=False)
        ]
    if only_alerts:
        view = view[view["status"].isin(["LOW", "OUT OF STOCK"])]

    view = view.sort_values(["status", "name"], ascending=[False, True])
    display = view[
        ["item_code", "name", "category", "unit", "opening_qty", "total_in", "total_out", "balance", "reorder_level", "status", "supplier"]
    ].rename(
        columns={
            "item_code": "Code",
            "name": "Chemical",
            "category": "Category",
            "unit": "Unit",
            "opening_qty": "Opening",
            "total_in": "Received",
            "total_out": "Issued",
            "balance": "Balance",
            "reorder_level": "Reorder",
            "status": "Status",
            "supplier": "Supplier",
        }
    )

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=min(560, 56 + 35 * len(display)),
        column_config={
            "Opening": st.column_config.NumberColumn(format="%.3f"),
            "Received": st.column_config.NumberColumn(format="%.3f"),
            "Issued": st.column_config.NumberColumn(format="%.3f"),
            "Balance": st.column_config.NumberColumn(format="%.3f"),
            "Reorder": st.column_config.NumberColumn(format="%.3f"),
            "Status": st.column_config.TextColumn(width="small"),
        },
    )
    st.caption(f"{len(display)} of {len(balances)} items shown")

    st.download_button(
        "⬇️  Export master list (Excel)",
        data=ui.download_excel(display, "chemical_master.xlsx"),
        file_name=f"concord_chem_master_{dt.date.today():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="content",
    )
