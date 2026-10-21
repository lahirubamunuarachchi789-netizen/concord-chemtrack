"""Report module: filtered stock transaction log, summaries and Excel export."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st

from src import ui
from src.config import T_ITEMS, T_TRANSACTIONS, friendly_db_error, require_client
from src.inventory import TXN_TYPES, fetch_balances


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
def fetch_transactions(client, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Transactions joined with item master data for the given date range."""
    try:
        txns = (
            client.table(T_TRANSACTIONS)
            .select("*")
            .gte("txn_date", start.isoformat())
            .lte("txn_date", end.isoformat())
            .order("txn_date", desc=True)
            .execute()
            .data
            or []
        )
        items = client.table(T_ITEMS).select("id, item_code, name, category, unit").execute().data or []
    except Exception as exc:
        st.error(f"Could not load stock transactions. {friendly_db_error(exc)}", icon="⚠️")
        return pd.DataFrame()

    if not txns:
        return pd.DataFrame()

    df = pd.DataFrame(txns)
    df_items = pd.DataFrame(items).rename(
        columns={"id": "item_id", "name": "chemical", "unit": "item_unit", "item_code": "code"}
    )
    df = df.merge(df_items, how="left", on="item_id")
    df["chemical"] = df["chemical"].fillna("(deleted item)")
    df["code"] = df["code"].fillna("—")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["signed_qty"] = df.apply(
        lambda r: -r["quantity"] if r["txn_type"] == "OUT" else r["quantity"], axis=1
    )
    return df


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
_LOG_COLUMNS = [
    "txn_date", "code", "chemical", "txn_type", "quantity", "unit",
    "batch_no", "supplier", "issued_to", "reference", "created_by",
]


def sorted_column_view(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the standard log columns, newest first.

    Columns absent in the source (e.g. ``created_at`` when the join produced
    no rows) are tolerated instead of raising ``KeyError``.
    """
    sort_keys = [c for c in ("txn_date", "created_at") if c in df.columns]
    view = df.sort_values(sort_keys, ascending=False) if sort_keys else df
    keep = [c for c in _LOG_COLUMNS if c in view.columns]
    return view[keep].copy()


def render() -> None:
    client = require_client()
    if client is None:
        return

    # ------------------------------------------------------------ filters
    ui.section_title("Report filters", "Narrow down the transaction log")

    with st.form("report_filters"):
        c1, c2, c3 = st.columns([1, 1, 1.2])
        with c1:
            default_start = dt.date.today().replace(day=1)
            start_date = st.date_input("From date", value=default_start)
        with c2:
            end_date = st.date_input("To date", value=dt.date.today())
        with c3:
            txn_filter = st.multiselect("Transaction type", TXN_TYPES, default=TXN_TYPES)

        c4, c5 = st.columns([2, 1])
        with c4:
            search = st.text_input("Search", placeholder="Chemical, batch, supplier, reference, user…")
        with c5:
            submitted = st.form_submit_button("Apply filters", width="stretch")

    if start_date > end_date:
        st.error("The 'From date' must be earlier than or equal to the 'To date'.", icon="⚠️")
        return

    with st.spinner("Loading transactions…"):
        df = fetch_transactions(client, start_date, end_date)

    if df.empty:
        st.info("No stock transactions found for the selected period.", icon="📄")
        _render_summary_empty()
        return

    # apply filters
    filtered = df.copy()
    if txn_filter:
        filtered = filtered[filtered["txn_type"].isin(txn_filter)]
    if search:
        term = search.lower()
        haystack_cols = ["chemical", "code", "batch_no", "supplier", "reference", "issued_to", "created_by", "remarks"]
        mask = pd.Series(False, index=filtered.index)
        for col in haystack_cols:
            if col in filtered:
                mask |= filtered[col].astype(str).str.lower().str.contains(term, na=False)
        filtered = filtered[mask]

    if filtered.empty:
        st.warning("No transactions match the current filters.", icon="🔍")
        return

    # ------------------------------------------------------------- KPIs
    total_in = float(filtered.loc[filtered["txn_type"] == "IN", "quantity"].sum())
    total_out = float(filtered.loc[filtered["txn_type"] == "OUT", "quantity"].sum())
    total_adj = float(filtered.loc[filtered["txn_type"] == "ADJUST", "quantity"].sum())

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        ui.kpi("Entries", len(filtered), f"{start_date:%d %b} – {end_date:%d %b}")
    with k2:
        ui.kpi("Total received", f"{total_in:,.2f}", "IN")
    with k3:
        ui.kpi("Total issued", f"{total_out:,.2f}", "OUT")
    with k4:
        ui.kpi("Adjustments", f"{total_adj:,.2f}", "ADJUST")

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    tab_log, tab_summary, tab_stock = st.tabs(
        ["📋  Transaction log", "📊  Summary", "📦  Stock position"]
    )

    # ---------------------------------------------------------- log tab
    with tab_log:
        log = sorted_column_view(filtered)
        log_view = log[
            ["txn_date", "code", "chemical", "txn_type", "quantity", "unit", "batch_no", "supplier", "issued_to", "reference", "created_by"]
        ].rename(
            columns={
                "txn_date": "Date",
                "code": "Code",
                "chemical": "Chemical",
                "txn_type": "Type",
                "quantity": "Qty",
                "unit": "Unit",
                "batch_no": "Batch",
                "supplier": "Supplier",
                "issued_to": "Issued To",
                "reference": "Reference",
                "created_by": "User",
            }
        )
        log_view["Date"] = pd.to_datetime(log_view["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        log_view = log_view.fillna("—")

        ui.dataframe_table(
            log_view,
            height=min(600, 56 + 35 * len(log_view)),
            column_config={
                "Qty": st.column_config.NumberColumn(format="%.3f"),
                "Type": st.column_config.TextColumn(width="small"),
            },
        )
        st.caption(f"{len(log_view)} transaction(s) displayed")

        d1, d2 = st.columns([1, 1])
        with d1:
            st.download_button(
                "⬇️  Export log (Excel)",
                data=ui.download_excel(log_view, "transaction_log.xlsx"),
                file_name=f"chem_transactions_{start_date:%Y%m%d}_{end_date:%Y%m%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        with d2:
            st.download_button(
                "⬇️  Export log (CSV)",
                data=log_view.to_csv(index=False).encode("utf-8"),
                file_name=f"chem_transactions_{start_date:%Y%m%d}_{end_date:%Y%m%d}.csv",
                mime="text/csv",
                width="stretch",
            )

    # ------------------------------------------------------ summary tab
    with tab_summary:
        _render_summary(filtered, start_date, end_date)

    # -------------------------------------------------------- stock tab
    with tab_stock:
        _render_stock_position(client)


# --------------------------------------------------------------------------
def _render_summary(df: pd.DataFrame, start: dt.date, end: dt.date) -> None:
    ui.section_title("Movement summary", f"{start:%d %b %Y} – {end:%d %b %Y}")

    pivot = (
        df.pivot_table(index=["code", "chemical"], columns="txn_type", values="quantity", aggfunc="sum")
        .fillna(0)
        .reset_index()
    )
    for col in TXN_TYPES:
        if col not in pivot:
            pivot[col] = 0.0
    pivot["Net movement"] = pivot["IN"] + pivot["ADJUST"] - pivot["OUT"]
    pivot = pivot.rename(
        columns={"code": "Code", "chemical": "Chemical", "IN": "Received Qty", "OUT": "Issued Qty", "ADJUST": "Adjusted"}
    )[["Code", "Chemical", "Received Qty", "Issued Qty", "Adjusted", "Net movement"]]
    pivot = pivot.sort_values("Net movement", ascending=False)

    left, right = st.columns([1.4, 1])
    with left:
        st.markdown("**Movement by chemical**", unsafe_allow_html=True)
        ui.dataframe_table(
            pivot,
            height=min(520, 56 + 35 * len(pivot)),
            column_config={
                "Received Qty": st.column_config.NumberColumn(format="%.3f"),
                "Issued Qty": st.column_config.NumberColumn(format="%.3f"),
                "Adjusted": st.column_config.NumberColumn(format="%.3f"),
                "Net movement": st.column_config.NumberColumn(format="%.3f"),
            },
        )
    with right:
        st.markdown("**Issued quantity by chemical**", unsafe_allow_html=True)
        issued = pivot[pivot["Issued Qty"] > 0][["Chemical", "Issued Qty"]].set_index("Chemical")
        if issued.empty:
            st.info("No issues recorded in this period.", icon="📉")
        else:
            st.bar_chart(issued, height=min(520, 120 + 34 * len(issued)), color="#0B1F3A")

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Activity by transaction type**", unsafe_allow_html=True)
        by_type = df.groupby("txn_type")["quantity"].sum().reindex(TXN_TYPES).fillna(0)
        st.bar_chart(by_type, height=220, color="#2E6BE6")
    with b2:
        st.markdown("**Activity by user**", unsafe_allow_html=True)
        by_user = (
            df.assign(user=df["created_by"].fillna("—"))
            .groupby("user")["quantity"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        st.bar_chart(by_user, height=220, color="#12305A")

    st.download_button(
        "⬇️  Export summary (Excel)",
        data=ui.download_excel(pivot, "summary.xlsx"),
        file_name=f"chem_summary_{start:%Y%m%d}_{end:%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_stock_position(client) -> None:
    ui.section_title("Current stock position", "Live balance per chemical item")
    balances = fetch_balances(client)
    if balances.empty:
        st.info("No chemical items have been registered yet.", icon="📦")
        return

    view = balances[["item_code", "name", "category", "unit", "opening_qty", "total_in", "total_out", "balance", "reorder_level"]].rename(
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
        }
    ).sort_values("Balance")

    ui.dataframe_table(
        view,
        height=min(560, 56 + 35 * len(view)),
        column_config={
            "Opening": st.column_config.NumberColumn(format="%.3f"),
            "Received": st.column_config.NumberColumn(format="%.3f"),
            "Issued": st.column_config.NumberColumn(format="%.3f"),
            "Balance": st.column_config.NumberColumn(format="%.3f"),
            "Reorder": st.column_config.NumberColumn(format="%.3f"),
        },
    )
    st.download_button(
        "⬇️  Export stock position (Excel)",
        data=ui.download_excel(view, "stock_position.xlsx"),
        file_name=f"chem_stock_position_{dt.date.today():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_summary_empty() -> None:
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    st.caption("Tip: widen the date range or clear the search box to see more history.")
