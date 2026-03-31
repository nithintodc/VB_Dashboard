import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import numpy as np
import io
from pathlib import Path

try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent
    load_dotenv(_root / ".env")
except Exception:
    pass

# TODC light theme for all Plotly charts
PLOTLY_THEME = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#000000", family="Open Sans, sans-serif"),
)
COLORS = ["#FF5E1A", "#FE7A3B", "#282828", "#FC5304", "#4FC3F7", "#81C784", "#BA68C8", "#FF8A65"]

st.set_page_config(page_title="TODC - Virtual Brands Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=Open+Sans:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Open Sans', sans-serif; color: #000000; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Montserrat', sans-serif !important; color: #000000; }
    .stApp { background-color: #FFFFFF; color: #000000; }

    /* Header banner */
    .main-header {
        background: #FF5E1A;
        padding: 2.5rem 2rem; border-radius: 12px; margin-bottom: 2rem;
        text-align: center; color: #ffffff; box-shadow: 0 4px 16px rgba(255,94,26,0.25);
    }
    .main-header h1 { margin:0; font-size:2.8rem; font-weight:700; letter-spacing:-1px; color:#fff; font-family:'Montserrat',sans-serif; }
    .main-header p { margin-top:0.5rem; font-size:1.1rem; opacity:0.95; color:#fff; font-family:'Open Sans',sans-serif; }

    /* Metrics */
    div[data-testid="stMetricValue"] { font-size:1.8rem; font-weight:700; color:#000000; }
    div[data-testid="stMetricLabel"] { font-weight:600; color:#282828; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color:#F5EEEB; border-right:1px solid #e0d6d0; }
    section[data-testid="stSidebar"] .stMarkdown { color:#000000; }
    section[data-testid="stSidebar"] label { color:#000000 !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color:#282828 !important; }

    /* Data frames */
    .stDataFrame { border-radius:8px; overflow:hidden; border:1px solid #e0d6d0; }

    /* Primary buttons — TODC dark accent style */
    .stButton button[kind="primary"],
    .stButton button[data-testid="stBaseButton-primary"] {
        background-color: #282828 !important;
        border: none !important; color: #FFFFFF !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important; border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important; font-size: 0.95rem !important;
        box-shadow: 0 2px 8px rgba(40,40,40,0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="primary"]:hover,
    .stButton button[data-testid="stBaseButton-primary"]:hover {
        background-color: #FF5E1A !important; color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(255,94,26,0.3) !important;
    }

    /* Secondary buttons */
    .stButton button[kind="secondary"],
    .stButton button[data-testid="stBaseButton-secondary"] {
        background-color: #FFFFFF !important;
        border: 2px solid #282828 !important; color: #282828 !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important; border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important; font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="secondary"]:hover,
    .stButton button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #F5EEEB !important; border-color: #FF5E1A !important;
        color: #FF5E1A !important;
    }

    /* Text */
    .stMarkdown { color:#000000; }
    .stMarkdown p, .stMarkdown li { color:#282828; }
    [data-testid="stCaptionContainer"] { color:#666666; }
    .stAlert { background-color:#F5EEEB; border-color:#e0d6d0; color:#282828; }

    /* Tabs */
    .stTabs [data-baseweb="tab"] { font-family:'Montserrat',sans-serif; font-weight:600; color:#282828; }
    .stTabs [aria-selected="true"] { border-bottom-color:#FF5E1A !important; color:#FF5E1A !important; }

    /* Expanders */
    .streamlit-expanderHeader { font-family:'Montserrat',sans-serif; font-weight:600; color:#282828; }

    /* Links */
    a { color: #FF5E1A; }
    a:hover { color: #FC5304; }

    /* Dividers */
    hr { border-color: #e0d6d0 !important; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Helpers
# =============================================================================
def _fmt(val, fmt_type="number"):
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return "—"
    if fmt_type == "pct":
        return f"{val:.1f}%"
    if fmt_type == "currency":
        return f"${val:,.2f}"
    if fmt_type == "time":
        return f"{val:.1f} min"
    if fmt_type == "roas":
        return f"{val:.2f}x"
    if fmt_type == "int":
        return f"{int(val):,}"
    return f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"


def _safe_pct(num, denom):
    return (num / denom * 100) if denom else 0


def _plotly_bar(df, x, y, title, color=None, horizontal=False):
    if horizontal:
        fig = px.bar(df, y=x, x=y, title=title, orientation="h",
                     color_discrete_sequence=[color or COLORS[0]])
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                     color_discrete_sequence=[color or COLORS[0]])
    fig.update_layout(**PLOTLY_THEME, margin=dict(t=40, b=0))
    return fig


def _plotly_pie(df, names, values, title):
    fig = px.pie(df, names=names, values=values, title=title,
                 color_discrete_sequence=COLORS)
    fig.update_layout(**PLOTLY_THEME, margin=dict(t=40, b=0))
    return fig


def _plotly_line(df, x, y, title, y2=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=y, line=dict(color=COLORS[0])))
    if y2:
        fig.add_trace(go.Scatter(x=df[x], y=df[y2], name=y2, yaxis="y2",
                                 line=dict(color=COLORS[1])))
        fig.update_layout(yaxis2=dict(title=y2, side="right", overlaying="y",
                                      gridcolor="#e0d6d0"))
    fig.update_layout(**PLOTLY_THEME, title=title,
                      xaxis=dict(gridcolor="#e0d6d0"), yaxis=dict(gridcolor="#e0d6d0"),
                      margin=dict(t=40, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig


def _parse_duration_to_minutes(s):
    """Parse HH:MM:SS.mmm or similar duration strings to float minutes."""
    if pd.isna(s) or not s:
        return np.nan
    try:
        parts = str(s).split(":")
        if len(parts) == 3:
            h, m, sec = float(parts[0]), float(parts[1]), float(parts[2])
            return h * 60 + m + sec / 60
        return float(s)
    except Exception:
        return np.nan


# =============================================================================
# DOORDASH RENDERERS
# =============================================================================
def render_dd_sales(data):
    """DoorDash Sales tab — from SALES_viewByStore_aggregate."""
    # Prefer the raw sales aggregate (store-level with all columns)
    raw_agg = data.get("sales_aggregate_df")
    fin = raw_agg if (raw_agg is not None and not raw_agg.empty) else data.get("financial_df")
    if fin is None or fin.empty:
        st.info("No DoorDash sales data loaded.")
        return

    df = fin.copy()
    for col in ["Gross Sales", "Total Orders Including Cancelled Orders",
                "Total Delivered or Picked Up Orders", "AOV", "Total Commission",
                "Total Promotion Fees | (for historical reference only)",
                "Total Ad Fees | (for historical reference only)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    gross_col = "Gross Sales" if "Gross Sales" in df.columns else "Subtotal"
    orders_col = "Total Delivered or Picked Up Orders" if "Total Delivered or Picked Up Orders" in df.columns else None
    orders_incl_cancel = "Total Orders Including Cancelled Orders" if "Total Orders Including Cancelled Orders" in df.columns else None
    aov_col = "AOV" if "AOV" in df.columns else None
    comm_col = "Total Commission" if "Total Commission" in df.columns else None
    promo_fee_col = "Total Promotion Fees | (for historical reference only)" if "Total Promotion Fees | (for historical reference only)" in df.columns else None
    ad_fee_col = "Total Ad Fees | (for historical reference only)" if "Total Ad Fees | (for historical reference only)" in df.columns else None

    total_gross = df[gross_col].sum() if gross_col in df.columns else 0
    total_orders = int(df[orders_col].sum()) if orders_col and orders_col in df.columns else 0
    total_orders_incl = int(df[orders_incl_cancel].sum()) if orders_incl_cancel and orders_incl_cancel in df.columns else 0
    avg_aov = (total_gross / total_orders) if total_orders else 0
    total_commission = df[comm_col].sum() if comm_col and comm_col in df.columns else 0
    total_promo = df[promo_fee_col].sum() if promo_fee_col and promo_fee_col in df.columns else 0
    total_ads = df[ad_fee_col].sum() if ad_fee_col and ad_fee_col in df.columns else 0
    stores_count = df["Store Name"].nunique() if "Store Name" in df.columns else df["Store name"].nunique() if "Store name" in df.columns else 0

    # KPI cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Gross Sales", _fmt(total_gross, "currency"))
    c2.metric("Delivered Orders", _fmt(total_orders, "int"))
    c3.metric("AOV", _fmt(avg_aov, "currency"))
    c4.metric("Commission", _fmt(total_commission, "currency"))
    c5.metric("Promo Fees", _fmt(total_promo, "currency"))
    c6.metric("Active Stores", _fmt(stores_count, "int"))

    st.markdown("---")

    # Store-level table
    store_col = "Store Name" if "Store Name" in df.columns else "Store name"
    display_cols = [c for c in [store_col, gross_col, orders_col, orders_incl_cancel, aov_col, comm_col, promo_fee_col, ad_fee_col] if c and c in df.columns]
    store_df = df[display_cols].copy()
    store_df = store_df.sort_values(gross_col, ascending=False)
    st.markdown("#### Store-Level Sales")
    st.dataframe(store_df, use_container_width=True, height=400)

    col_a, col_b = st.columns(2)
    with col_a:
        top20 = store_df.head(20)
        fig = _plotly_bar(top20, store_col, gross_col, "Top 20 Stores by Gross Sales")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        # Revenue waterfall
        waterfall_data = {
            "Category": ["Gross Sales", "Commission", "Promo Fees", "Ad Fees", "Net Revenue"],
            "Amount": [total_gross, total_commission, total_promo, total_ads,
                       total_gross + total_commission + total_promo + total_ads],
        }
        wf = pd.DataFrame(waterfall_data)
        fig = go.Figure(go.Waterfall(
            x=wf["Category"], y=wf["Amount"],
            measure=["absolute", "relative", "relative", "relative", "total"],
            connector=dict(line=dict(color="#e0d6d0")),
            increasing=dict(marker=dict(color="#81C784")),
            decreasing=dict(marker=dict(color="#f87171")),
            totals=dict(marker=dict(color=COLORS[0])),
        ))
        fig.update_layout(**PLOTLY_THEME, title="Revenue Waterfall", margin=dict(t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # Sales distribution histogram
    if gross_col in df.columns:
        active = df[df[gross_col] > 0]
        if not active.empty:
            fig = px.histogram(active, x=gross_col, nbins=30, title="Sales Distribution Across Stores",
                               color_discrete_sequence=[COLORS[0]])
            fig.update_layout(**PLOTLY_THEME, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)


def render_dd_marketing(data):
    """DoorDash Marketing tab — Promotions + Sponsored Listings."""
    promo_df = data.get("promo_df")
    ads_df = data.get("ads_df")

    if (promo_df is None or promo_df.empty) and (ads_df is None or ads_df.empty):
        st.info("No DoorDash marketing data loaded.")
        return

    # === PROMOTIONS ===
    if promo_df is not None and not promo_df.empty:
        st.markdown("### Promotions (Order Discounts)")
        df = promo_df.copy()
        for col in ["Orders", "Sales", "ROAS", "New customers acquired",
                     "Customer discounts from marketing | (Funded by you)",
                     "Marketing fees | (including any applicable taxes)",
                     "Average order value"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        total_orders = int(df["Orders"].sum()) if "Orders" in df.columns else 0
        total_sales = df["Sales"].sum() if "Sales" in df.columns else 0
        avg_roas = df.loc[df["ROAS"] > 0, "ROAS"].mean() if "ROAS" in df.columns else 0
        new_cust = int(df["New customers acquired"].sum()) if "New customers acquired" in df.columns else 0
        spend_col = "Customer discounts from marketing | (Funded by you)"
        total_spend = df[spend_col].sum() if spend_col in df.columns else 0
        fee_col = "Marketing fees | (including any applicable taxes)"
        total_fees = df[fee_col].sum() if fee_col in df.columns else 0
        cac = (total_spend / new_cust) if new_cust else 0

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Promo Orders", _fmt(total_orders, "int"))
        c2.metric("Promo Sales", _fmt(total_sales, "currency"))
        c3.metric("Avg ROAS", _fmt(avg_roas, "roas"))
        c4.metric("New Customers", _fmt(new_cust, "int"))
        c5.metric("Your Spend", _fmt(total_spend, "currency"))
        c6.metric("CAC", _fmt(cac, "currency"))

        st.markdown("---")

        # By Promotion Type pivot
        if "Type of promotion" in df.columns:
            type_pivot = df.groupby("Type of promotion").agg(
                Orders=("Orders", "sum"),
                Sales=("Sales", "sum"),
                Avg_ROAS=("ROAS", "mean"),
                New_Customers=("New customers acquired", "sum"),
            ).reset_index().sort_values("Sales", ascending=False)
            type_pivot["Avg_ROAS"] = type_pivot["Avg_ROAS"].round(2)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### By Promotion Type")
                st.dataframe(type_pivot, use_container_width=True)
            with col_b:
                fig = _plotly_pie(type_pivot, "Type of promotion", "Sales", "Sales by Promotion Type")
                st.plotly_chart(fig, use_container_width=True)

        # By Store pivot
        store_col = "Store name" if "Store name" in df.columns else "Store Name"
        if store_col in df.columns:
            store_pivot = df.groupby(store_col).agg(
                Orders=("Orders", "sum"),
                Sales=("Sales", "sum"),
                Avg_ROAS=("ROAS", "mean"),
                New_Customers=("New customers acquired", "sum"),
            ).reset_index().sort_values("Sales", ascending=False)
            store_pivot["Avg_ROAS"] = store_pivot["Avg_ROAS"].round(2)
            st.markdown("#### By Store (Promotions)")
            st.dataframe(store_pivot.head(50), use_container_width=True, height=350)

        # Daily trend
        if "Date" in df.columns or "_date" in df.columns:
            date_col = "Date" if "Date" in df.columns else "_date"
            daily = df.groupby(date_col).agg(
                Orders=("Orders", "sum"), Sales=("Sales", "sum"), Avg_ROAS=("ROAS", "mean")
            ).reset_index()
            daily["Avg_ROAS"] = daily["Avg_ROAS"].round(2)
            fig = _plotly_line(daily, date_col, "Sales", "Daily Promo Sales & ROAS", y2="Avg_ROAS")
            st.plotly_chart(fig, use_container_width=True)

        # ROAS distribution
        if "ROAS" in df.columns:
            roas_data = df[df["ROAS"] > 0]["ROAS"]
            if not roas_data.empty:
                fig = px.histogram(roas_data, nbins=40, title="ROAS Distribution (Promotions)",
                                   color_discrete_sequence=[COLORS[0]],
                                   labels={"value": "ROAS", "count": "Campaigns"})
                fig.add_vline(x=4, line_dash="dash", line_color="red",
                              annotation_text="Target ROAS = 4x")
                fig.update_layout(**PLOTLY_THEME, margin=dict(t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

        # Low ROAS campaigns
        if "ROAS" in df.columns and store_col in df.columns:
            low_roas = df[(df["ROAS"] > 0) & (df["ROAS"] < 4) & (df["Orders"] > 0)]
            if not low_roas.empty:
                low_agg = low_roas.groupby(store_col).agg(
                    Campaigns=("ROAS", "count"), Avg_ROAS=("ROAS", "mean"),
                    Total_Spend=(spend_col, "sum") if spend_col in df.columns else ("Sales", "sum"),
                ).reset_index().sort_values("Avg_ROAS")
                low_agg["Avg_ROAS"] = low_agg["Avg_ROAS"].round(2)
                with st.expander(f"Stores with ROAS < 4x ({len(low_agg)} stores)"):
                    st.dataframe(low_agg, use_container_width=True, height=300)

    # === SPONSORED LISTINGS ===
    if ads_df is not None and not ads_df.empty:
        st.markdown("---")
        st.markdown("### Sponsored Listings (Ads)")
        df = ads_df.copy()
        for col in ["Impressions", "Clicks", "Orders", "Sales", "ROAS",
                     "Marketing fees | (including any applicable taxes)", "Average CPA"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        total_imp = int(df["Impressions"].sum()) if "Impressions" in df.columns else 0
        total_clicks = int(df["Clicks"].sum()) if "Clicks" in df.columns else 0
        ctr = _safe_pct(total_clicks, total_imp)
        total_orders = int(df["Orders"].sum()) if "Orders" in df.columns else 0
        total_sales = df["Sales"].sum() if "Sales" in df.columns else 0
        ad_fee_col = "Marketing fees | (including any applicable taxes)"
        total_ad_spend = df[ad_fee_col].sum() if ad_fee_col in df.columns else 0
        avg_roas = df.loc[df["ROAS"] > 0, "ROAS"].mean() if "ROAS" in df.columns else 0
        avg_cpa = df.loc[df["Average CPA"] > 0, "Average CPA"].mean() if "Average CPA" in df.columns else 0
        conversion = _safe_pct(total_orders, total_clicks)

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Impressions", _fmt(total_imp, "int"))
        c2.metric("Clicks (CTR)", f"{_fmt(total_clicks, 'int')} ({ctr:.1f}%)")
        c3.metric("Orders (Conv)", f"{_fmt(total_orders, 'int')} ({conversion:.1f}%)")
        c4.metric("Ad Sales", _fmt(total_sales, "currency"))
        c5.metric("Ad Spend", _fmt(total_ad_spend, "currency"))
        c6.metric("Avg ROAS / CPA", f"{_fmt(avg_roas, 'roas')} / {_fmt(avg_cpa, 'currency')}")

        # Funnel chart
        col_a, col_b = st.columns(2)
        with col_a:
            funnel_df = pd.DataFrame({
                "Stage": ["Impressions", "Clicks", "Orders"],
                "Count": [total_imp, total_clicks, total_orders],
            })
            fig = px.funnel(funnel_df, x="Count", y="Stage", title="Ads Conversion Funnel",
                            color_discrete_sequence=[COLORS[0]])
            fig.update_layout(**PLOTLY_THEME, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            # Daily ad trend
            date_col = "Date" if "Date" in df.columns else "_date"
            if date_col in df.columns:
                daily = df.groupby(date_col).agg(
                    Impressions=("Impressions", "sum"), Clicks=("Clicks", "sum"),
                    Orders=("Orders", "sum"), Sales=("Sales", "sum"),
                ).reset_index()
                fig = _plotly_line(daily, date_col, "Impressions", "Daily Ads Performance", y2="Orders")
                st.plotly_chart(fig, use_container_width=True)

        # By Store
        store_col = "Store name" if "Store name" in df.columns else "Store Name"
        if store_col in df.columns:
            store_ads = df.groupby(store_col).agg(
                Impressions=("Impressions", "sum"), Clicks=("Clicks", "sum"),
                Orders=("Orders", "sum"), Sales=("Sales", "sum"),
                Avg_ROAS=("ROAS", "mean"),
                Ad_Spend=(ad_fee_col, "sum") if ad_fee_col in df.columns else ("Sales", "count"),
            ).reset_index()
            store_ads["CTR"] = (store_ads["Clicks"] / store_ads["Impressions"].replace(0, np.nan) * 100).round(2)
            store_ads["Conv_Rate"] = (store_ads["Orders"] / store_ads["Clicks"].replace(0, np.nan) * 100).round(2)
            store_ads["Avg_ROAS"] = store_ads["Avg_ROAS"].round(2)
            store_ads = store_ads.sort_values("Sales", ascending=False)
            st.markdown("#### By Store (Ads)")
            st.dataframe(store_ads.head(50), use_container_width=True, height=350)


def render_dd_operations(data):
    """DoorDash Operations tab — aggregate + detail views."""
    ops = data.get("operations", {})
    fin = data.get("financial_df")

    # === Aggregate scorecard ===
    # Try to get the aggregate ops data from the raw loaded data
    cancel_df = ops.get("cancellations")
    downtime_df = ops.get("downtime")
    missing_df = ops.get("missing_incorrect")

    # Check if financial_df is actually the ops aggregate (has ops columns)
    agg_df = None
    if fin is not None and not fin.empty and "Total Cancellation Rate %" in fin.columns:
        agg_df = fin.copy()
    elif fin is not None and not fin.empty and "Missing/Incorrect %" in fin.columns:
        agg_df = fin.copy()

    has_any = any([
        agg_df is not None and not agg_df.empty,
        cancel_df is not None and not cancel_df.empty,
        downtime_df is not None and not downtime_df.empty,
        missing_df is not None and not missing_df.empty,
    ])
    if not has_any:
        st.info("No DoorDash operations data loaded.")
        return

    st.markdown("### Operations Overview")

    # KPIs from cancellations, downtime, missing
    total_cancel_events = 0
    if cancel_df is not None and not cancel_df.empty and "Count of Orders" in cancel_df.columns:
        cancel_df["Count of Orders"] = pd.to_numeric(cancel_df["Count of Orders"], errors="coerce").fillna(0)
        total_cancel_events = int(cancel_df["Count of Orders"].sum())

    total_downtime_mins = 0
    if downtime_df is not None and not downtime_df.empty and "Minutes Downtime" in downtime_df.columns:
        downtime_df["Minutes Downtime"] = pd.to_numeric(downtime_df["Minutes Downtime"], errors="coerce").fillna(0)
        total_downtime_mins = int(downtime_df["Minutes Downtime"].sum())

    total_errors = 0
    if missing_df is not None and not missing_df.empty and "Count of Item Errors" in missing_df.columns:
        missing_df["Count of Item Errors"] = pd.to_numeric(missing_df["Count of Item Errors"], errors="coerce").fillna(0)
        total_errors = int(missing_df["Count of Item Errors"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cancellation Events", _fmt(total_cancel_events, "int"))
    c2.metric("Total Downtime", f"{total_downtime_mins:,} min ({total_downtime_mins / 60:.0f} hrs)")
    c3.metric("Item Errors", _fmt(total_errors, "int"))
    st.markdown("---")

    # === Cancellations ===
    if cancel_df is not None and not cancel_df.empty:
        st.markdown("#### Cancellations")
        cat_col = "Cancellation Category - Short" if "Cancellation Category - Short" in cancel_df.columns else None
        desc_col = "Cancellation Category - Description" if "Cancellation Category - Description" in cancel_df.columns else None
        store_col = "Store Name" if "Store Name" in cancel_df.columns else "Store name"

        col_a, col_b = st.columns(2)
        with col_a:
            if cat_col:
                cat_pivot = cancel_df.groupby(cat_col)["Count of Orders"].sum().reset_index().sort_values("Count of Orders", ascending=False)
                fig = _plotly_bar(cat_pivot, cat_col, "Count of Orders", "Cancellations by Category")
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            if desc_col:
                desc_pivot = cancel_df.groupby(desc_col)["Count of Orders"].sum().reset_index().sort_values("Count of Orders", ascending=True).tail(10)
                fig = _plotly_bar(desc_pivot, desc_col, "Count of Orders", "Top 10 Cancellation Reasons", horizontal=True)
                st.plotly_chart(fig, use_container_width=True)

        # Store pivot
        if store_col in cancel_df.columns:
            store_cancel = cancel_df.groupby(store_col)["Count of Orders"].sum().reset_index().sort_values("Count of Orders", ascending=False)
            with st.expander(f"Cancellations by Store ({len(store_cancel)} stores)"):
                st.dataframe(store_cancel.head(50), use_container_width=True, height=300)

    # === Downtime ===
    if downtime_df is not None and not downtime_df.empty:
        st.markdown("#### Downtime")
        cat_col = "Downtime Category - Short" if "Downtime Category - Short" in downtime_df.columns else None
        desc_col = "Downtime Category - Description" if "Downtime Category - Description" in downtime_df.columns else None
        store_col = "Store Name" if "Store Name" in downtime_df.columns else "Store name"

        col_a, col_b = st.columns(2)
        with col_a:
            if cat_col:
                cat_pivot = downtime_df.groupby(cat_col)["Minutes Downtime"].sum().reset_index().sort_values("Minutes Downtime", ascending=False)
                fig = _plotly_bar(cat_pivot, cat_col, "Minutes Downtime", "Downtime by Category")
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            if desc_col:
                desc_pivot = downtime_df.groupby(desc_col)["Minutes Downtime"].sum().reset_index().sort_values("Minutes Downtime", ascending=True).tail(10)
                fig = _plotly_bar(desc_pivot, desc_col, "Minutes Downtime", "Top 10 Downtime Reasons", horizontal=True)
                st.plotly_chart(fig, use_container_width=True)

        if store_col in downtime_df.columns:
            store_dt = downtime_df.groupby(store_col)["Minutes Downtime"].sum().reset_index().sort_values("Minutes Downtime", ascending=False)
            with st.expander(f"Downtime by Store ({len(store_dt)} stores)"):
                st.dataframe(store_dt.head(50), use_container_width=True, height=300)

    # === Missing / Incorrect ===
    if missing_df is not None and not missing_df.empty:
        st.markdown("#### Missing & Incorrect Items")
        err_col = "Error Category" if "Error Category" in missing_df.columns else None
        store_col = "Store Name" if "Store Name" in missing_df.columns else "Store name"

        col_a, col_b = st.columns(2)
        with col_a:
            if err_col:
                err_pivot = missing_df.groupby(err_col)["Count of Item Errors"].sum().reset_index().sort_values("Count of Item Errors", ascending=False)
                fig = _plotly_pie(err_pivot, err_col, "Count of Item Errors", "Errors by Category")
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            if store_col in missing_df.columns:
                store_err = missing_df.groupby(store_col)["Count of Item Errors"].sum().reset_index().sort_values("Count of Item Errors", ascending=False).head(15)
                fig = _plotly_bar(store_err, store_col, "Count of Item Errors", "Top 15 Stores by Item Errors")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# GRUBHUB RENDERERS
# =============================================================================
def render_gh_sales(data):
    """Grubhub Sales tab — from GH_Sales_Report."""
    fin = data.get("financial_df")
    if fin is None or fin.empty:
        st.info("No Grubhub sales data loaded.")
        return

    df = fin.copy()
    for col in ["total_orders", "subtotal_sales", "commission", "merchant_net_total",
                "merchant_total", "merchant_funded_promotion_and_loyalty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    total_orders = int(df["total_orders"].sum()) if "total_orders" in df.columns else 0
    total_sales = df["subtotal_sales"].sum() if "subtotal_sales" in df.columns else 0
    total_commission = df["commission"].sum() if "commission" in df.columns else 0
    total_net = df["merchant_net_total"].sum() if "merchant_net_total" in df.columns else 0
    total_promo = df["merchant_funded_promotion_and_loyalty"].sum() if "merchant_funded_promotion_and_loyalty" in df.columns else 0
    avg_aov = (total_sales / total_orders) if total_orders else 0
    stores = df["store_name"].nunique() if "store_name" in df.columns else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Orders", _fmt(total_orders, "int"))
    c2.metric("Subtotal Sales", _fmt(total_sales, "currency"))
    c3.metric("AOV", _fmt(avg_aov, "currency"))
    c4.metric("Commission", _fmt(total_commission, "currency"))
    c5.metric("Merchant Net", _fmt(total_net, "currency"))
    c6.metric("Active Stores", _fmt(stores, "int"))
    st.markdown("---")

    # Weekly trend
    if "week_start_date" in df.columns or "_date" in df.columns:
        date_col = "week_start_date" if "week_start_date" in df.columns else "_date"
        weekly = df.groupby(date_col).agg(
            Orders=("total_orders", "sum") if "total_orders" in df.columns else ("Subtotal", "count"),
            Sales=("subtotal_sales", "sum") if "subtotal_sales" in df.columns else ("Subtotal", "sum"),
            Net=("merchant_net_total", "sum") if "merchant_net_total" in df.columns else ("Subtotal", "sum"),
        ).reset_index().sort_values(date_col)

        col_a, col_b = st.columns(2)
        with col_a:
            fig = _plotly_bar(weekly, date_col, "Sales", "Weekly Sales Trend")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            fig = _plotly_line(weekly, date_col, "Orders", "Weekly Orders", y2="Net")
            st.plotly_chart(fig, use_container_width=True)

    # By Store
    if "store_name" in df.columns:
        store_pivot = df.groupby("store_name").agg(
            Orders=("total_orders", "sum"),
            Sales=("subtotal_sales", "sum"),
            Commission=("commission", "sum"),
            Net=("merchant_net_total", "sum"),
        ).reset_index()
        store_pivot["AOV"] = (store_pivot["Sales"] / store_pivot["Orders"].replace(0, np.nan)).round(2)
        store_pivot["Commission_Rate"] = (store_pivot["Commission"] / store_pivot["Sales"].replace(0, np.nan) * 100).round(1)
        store_pivot = store_pivot.sort_values("Sales", ascending=False)

        st.markdown("#### Store Performance")
        st.dataframe(store_pivot.head(50), use_container_width=True, height=350)

        col_a, col_b = st.columns(2)
        with col_a:
            fig = _plotly_bar(store_pivot.head(20), "store_name", "Sales", "Top 20 Stores by Sales")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            # By State
            if "state" in df.columns:
                state_pivot = df.groupby("state").agg(
                    Orders=("total_orders", "sum"), Sales=("subtotal_sales", "sum"),
                ).reset_index().sort_values("Sales", ascending=False)
                fig = _plotly_bar(state_pivot.head(15), "state", "Sales", "Sales by State")
                st.plotly_chart(fig, use_container_width=True)

    # Revenue waterfall
    waterfall_data = {
        "Category": ["Subtotal Sales", "Commission", "Promos", "Net Total"],
        "Amount": [total_sales, total_commission, total_promo,
                   total_sales + total_commission + total_promo],
    }
    wf = pd.DataFrame(waterfall_data)
    fig = go.Figure(go.Waterfall(
        x=wf["Category"], y=wf["Amount"],
        measure=["absolute", "relative", "relative", "total"],
        connector=dict(line=dict(color="#e0d6d0")),
        increasing=dict(marker=dict(color="#81C784")),
        decreasing=dict(marker=dict(color="#f87171")),
        totals=dict(marker=dict(color=COLORS[0])),
    ))
    fig.update_layout(**PLOTLY_THEME, title="Revenue Waterfall", margin=dict(t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)


def render_gh_operations(data):
    """Grubhub Operations tab — from GH_Ops_Reports."""
    ops_df = data.get("operations_df")
    if ops_df is None or ops_df.empty:
        st.info("No Grubhub operations data loaded.")
        return

    df = ops_df.copy()
    for col in ["total_orders", "total_canceled_orders", "avoidable_canceled_orders",
                "adjusted_orders", "new_customer_orders", "gh_plus_customer_orders",
                "ratings_all", "ratings_5_stars", "ratings_1_star", "reviews"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Parse duration columns
    for col in ["avg_driver_time_at_store", "avg_avoidable_driver_wait_time",
                "avg_order_to_delivery_time", "avg_delivery_route_time"]:
        if col in df.columns:
            df[col + "_min"] = df[col].apply(_parse_duration_to_minutes)

    total_orders = int(df["total_orders"].sum())
    total_canceled = int(df["total_canceled_orders"].sum())
    cancel_rate = _safe_pct(total_canceled, total_orders)
    total_avoidable = int(df["avoidable_canceled_orders"].sum())
    new_cust = int(df["new_customer_orders"].sum())
    ghplus = int(df["gh_plus_customer_orders"].sum())
    avg_driver_wait = df["avg_driver_time_at_store_min"].mean() if "avg_driver_time_at_store_min" in df.columns else 0
    avg_avoid_wait = df["avg_avoidable_driver_wait_time_min"].mean() if "avg_avoidable_driver_wait_time_min" in df.columns else 0
    total_ratings = int(df["ratings_all"].sum())
    five_star = int(df["ratings_5_stars"].sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Orders", _fmt(total_orders, "int"))
    c2.metric("Canceled", f"{_fmt(total_canceled, 'int')} ({cancel_rate:.1f}%)")
    c3.metric("Avoidable Cancels", _fmt(total_avoidable, "int"))
    c4.metric("Avg Driver Wait", _fmt(avg_driver_wait, "time"))
    c5.metric("New Customer Orders", _fmt(new_cust, "int"))
    c6.metric("Ratings", f"{total_ratings} total ({five_star} ★5)")
    st.markdown("---")

    # Weekly trends
    date_col = "week_start_date" if "week_start_date" in df.columns else "_date"
    if date_col in df.columns:
        weekly = df.groupby(date_col).agg(
            Orders=("total_orders", "sum"),
            Canceled=("total_canceled_orders", "sum"),
            New_Customers=("new_customer_orders", "sum"),
            GHPlus=("gh_plus_customer_orders", "sum"),
        ).reset_index().sort_values(date_col)
        weekly["Cancel_Rate"] = (weekly["Canceled"] / weekly["Orders"].replace(0, np.nan) * 100).round(1)

        col_a, col_b = st.columns(2)
        with col_a:
            fig = _plotly_bar(weekly, date_col, "Canceled", "Weekly Cancellations")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            fig = _plotly_line(weekly, date_col, "New_Customers", "Weekly Customer Mix", y2="GHPlus")
            st.plotly_chart(fig, use_container_width=True)

    # Store-level ops
    if "store_name" in df.columns:
        store_ops = df.groupby("store_name").agg(
            Orders=("total_orders", "sum"),
            Canceled=("total_canceled_orders", "sum"),
            Avoidable=("avoidable_canceled_orders", "sum"),
            Avg_Driver_Wait=("avg_driver_time_at_store_min", "mean") if "avg_driver_time_at_store_min" in df.columns else ("total_orders", "count"),
            Ratings=("ratings_all", "sum"),
        ).reset_index()
        store_ops["Cancel_Rate"] = (store_ops["Canceled"] / store_ops["Orders"].replace(0, np.nan) * 100).round(1)
        store_ops = store_ops.sort_values("Cancel_Rate", ascending=False)

        st.markdown("#### Store Operations Scorecard")
        st.dataframe(store_ops.head(50), use_container_width=True, height=350)

        worst = store_ops[store_ops["Orders"] >= 3].head(15)
        if not worst.empty:
            fig = _plotly_bar(worst, "store_name", "Cancel_Rate", "Highest Cancellation Rate Stores (3+ orders)")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # Ratings distribution
    if "ratings_5_stars" in df.columns:
        rating_cols = ["ratings_5_stars", "ratings_4_stars", "ratings_3_stars", "ratings_2_stars", "ratings_1_star"]
        existing = [c for c in rating_cols if c in df.columns]
        if existing:
            rating_totals = {c.replace("ratings_", "").replace("_stars", "").replace("_star", "") + " Star": int(df[c].sum()) for c in existing}
            rating_df = pd.DataFrame(list(rating_totals.items()), columns=["Rating", "Count"])
            fig = _plotly_bar(rating_df, "Rating", "Count", "Ratings Distribution", color=COLORS[2])
            st.plotly_chart(fig, use_container_width=True)


def render_gh_marketing(_data):
    st.info("No Grubhub marketing data available. Upload Grubhub promo/ads exports to enable this tab.")


# =============================================================================
# UBER EATS RENDERERS
# =============================================================================
def render_ue_sales(data):
    """Uber Eats Sales tab — from Order History + Payout Summary."""
    fin = data.get("financial_df")
    if fin is None or fin.empty:
        st.info("No Uber Eats sales data loaded.")
        return

    df = fin.copy()
    for col in ["Subtotal", "Ticket Size"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Detect if this is order-history style (has Order Status, Ticket Size) or payout-summary style
    is_order_history = "Order Status" in df.columns or "Ticket Size" in df.columns
    amount_col = "Ticket Size" if "Ticket Size" in df.columns else "Subtotal"
    store_col = "Store" if "Store" in df.columns else "Store name"

    total_orders = len(df)
    total_sales = df[amount_col].sum()
    avg_aov = (total_sales / total_orders) if total_orders else 0
    stores = df[store_col].nunique() if store_col in df.columns else 0

    # Order-history specific metrics
    completed = canceled = completion_rate = avg_delivery = avg_wait = 0
    if "Order Status" in df.columns:
        completed = int((df["Order Status"] == "completed").sum())
        canceled = int((df["Order Status"].str.contains("cancel", case=False, na=False)).sum())
        completion_rate = _safe_pct(completed, total_orders)
    if "Total Delivery Time" in df.columns:
        df["Total Delivery Time"] = pd.to_numeric(df["Total Delivery Time"], errors="coerce")
        avg_delivery = df["Total Delivery Time"].mean()
    if "Courier Wait Time (Restaurant)" in df.columns:
        df["Courier Wait Time (Restaurant)"] = pd.to_numeric(df["Courier Wait Time (Restaurant)"], errors="coerce")
        avg_wait = df["Courier Wait Time (Restaurant)"].mean()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Orders", _fmt(total_orders, "int"))
    c2.metric("Total Sales", _fmt(total_sales, "currency"))
    c3.metric("AOV", _fmt(avg_aov, "currency"))
    c4.metric("Active Stores", _fmt(stores, "int"))
    if is_order_history:
        c5.metric("Completion Rate", f"{completion_rate:.1f}%")
        c6.metric("Avg Delivery Time", _fmt(avg_delivery, "time"))
    st.markdown("---")

    # Daily trend
    if "_date" in df.columns:
        daily = df.groupby(df["_date"].dt.date).agg(
            Orders=(amount_col, "count"), Sales=(amount_col, "sum")
        ).reset_index()
        daily.columns = ["Date", "Orders", "Sales"]
        daily["AOV"] = (daily["Sales"] / daily["Orders"].replace(0, np.nan)).round(2)

        col_a, col_b = st.columns(2)
        with col_a:
            fig = _plotly_line(daily, "Date", "Orders", "Daily Orders & AOV", y2="AOV")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            fig = _plotly_bar(daily, "Date", "Sales", "Daily Sales")
            st.plotly_chart(fig, use_container_width=True)

    # Order status breakdown
    if "Order Status" in df.columns:
        status_counts = df["Order Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        col_a, col_b = st.columns(2)
        with col_a:
            fig = _plotly_pie(status_counts, "Status", "Count", "Order Status Breakdown")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            # Channel breakdown
            if "Order Channel" in df.columns:
                channel_counts = df["Order Channel"].value_counts().reset_index()
                channel_counts.columns = ["Channel", "Count"]
                fig = _plotly_pie(channel_counts, "Channel", "Count", "Orders by Channel")
                st.plotly_chart(fig, use_container_width=True)

    # Subscription impact
    if "Subscription Pass" in df.columns:
        sub_pivot = df.groupby(df["Subscription Pass"].fillna("None")).agg(
            Orders=(amount_col, "count"), Avg_Ticket=(amount_col, "mean"),
        ).reset_index()
        sub_pivot.columns = ["Subscription", "Orders", "Avg_Ticket"]
        sub_pivot["Avg_Ticket"] = sub_pivot["Avg_Ticket"].round(2)
        st.markdown("#### Subscription Impact")
        st.dataframe(sub_pivot, use_container_width=True)

    # By Store
    if store_col in df.columns:
        store_pivot = df.groupby(store_col).agg(
            Orders=(amount_col, "count"),
            Sales=(amount_col, "sum"),
        ).reset_index()
        store_pivot["AOV"] = (store_pivot["Sales"] / store_pivot["Orders"].replace(0, np.nan)).round(2)
        store_pivot = store_pivot.sort_values("Sales", ascending=False)

        st.markdown("#### Store Performance")
        st.dataframe(store_pivot.head(50), use_container_width=True, height=350)

        fig = _plotly_bar(store_pivot.head(20), store_col, "Sales", "Top 20 Stores by Sales")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # By City
    city_col = "City" if "City" in df.columns else None
    if city_col:
        city_pivot = df.groupby(city_col).agg(
            Orders=(amount_col, "count"), Sales=(amount_col, "sum"),
        ).reset_index().sort_values("Sales", ascending=False)

        col_a, col_b = st.columns(2)
        with col_a:
            fig = _plotly_bar(city_pivot.head(15), city_col, "Sales", "Sales by City")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            fig = _plotly_bar(city_pivot.head(15), city_col, "Orders", "Orders by City")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # Fulfillment type
    if "Fulfillment Type" in df.columns:
        ft = df["Fulfillment Type"].value_counts().reset_index()
        ft.columns = ["Type", "Count"]
        fig = _plotly_pie(ft, "Type", "Count", "Fulfillment Type")
        st.plotly_chart(fig, use_container_width=True)


def render_ue_operations(data):
    """Uber Eats Operations — Inaccurate Orders + Paused Details."""
    inacc_df = data.get("inaccurate_df")
    pause_df = data.get("downtime_df")
    fin = data.get("financial_df")

    has_any = any([
        inacc_df is not None and not inacc_df.empty,
        pause_df is not None and not pause_df.empty,
    ])
    if not has_any:
        st.info("No Uber Eats operations data loaded.")
        return

    # === Inaccurate Orders ===
    if inacc_df is not None and not inacc_df.empty:
        st.markdown("### Inaccurate Orders")
        df = inacc_df.copy()
        for col in ["Ticket Size", "Customer Refunded", "Refund Covered by Merchant", "Refund Not Covered by Merchant"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        total_inacc = len(df)
        total_refund = df["Customer Refunded"].sum() if "Customer Refunded" in df.columns else 0
        merchant_liable = df["Refund Covered by Merchant"].sum() if "Refund Covered by Merchant" in df.columns else 0
        platform_liable = df["Refund Not Covered by Merchant"].sum() if "Refund Not Covered by Merchant" in df.columns else 0
        avg_ticket = df["Ticket Size"].mean() if "Ticket Size" in df.columns else 0

        # Error rate vs total orders
        total_ue_orders = len(fin) if fin is not None and not fin.empty else 0
        error_rate = _safe_pct(total_inacc, total_ue_orders) if total_ue_orders else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Inaccurate Orders", _fmt(total_inacc, "int"))
        c2.metric("Error Rate", f"{error_rate:.1f}%" if total_ue_orders else "—")
        c3.metric("Total Refunds", _fmt(total_refund, "currency"))
        c4.metric("Merchant Liable", _fmt(merchant_liable, "currency"))
        c5.metric("Platform Liable", _fmt(platform_liable, "currency"))

        col_a, col_b = st.columns(2)
        with col_a:
            if "Order Issue" in df.columns:
                issue_counts = df["Order Issue"].value_counts().reset_index()
                issue_counts.columns = ["Issue", "Count"]
                fig = _plotly_pie(issue_counts, "Issue", "Count", "Issue Type Breakdown")
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            # Refund liability split
            liability = pd.DataFrame({
                "Party": ["Merchant", "Platform (Uber)"],
                "Amount": [merchant_liable, platform_liable],
            })
            fig = _plotly_pie(liability, "Party", "Amount", "Refund Liability Split")
            st.plotly_chart(fig, use_container_width=True)

        # By Store
        store_col = "Store" if "Store" in df.columns else "Store name"
        if store_col in df.columns:
            store_inacc = df.groupby(store_col).agg(
                Issues=(store_col, "count"),
                Refunded=("Customer Refunded", "sum"),
                Merchant_Liable=("Refund Covered by Merchant", "sum"),
            ).reset_index().sort_values("Issues", ascending=False)
            st.markdown("#### By Store")
            st.dataframe(store_inacc.head(30), use_container_width=True, height=300)

        # Item issues
        if "Item Issue Details" in df.columns:
            item_issues = df["Item Issue Details"].value_counts().reset_index().head(15)
            item_issues.columns = ["Issue Detail", "Count"]
            fig = _plotly_bar(item_issues, "Issue Detail", "Count", "Top Item Issues", horizontal=True)
            st.plotly_chart(fig, use_container_width=True)

    # === Paused Details ===
    if pause_df is not None and not pause_df.empty:
        st.markdown("---")
        st.markdown("### Store Pauses (Downtime)")
        df = pause_df.copy()

        total_pauses = len(df)
        stores_paused = df["Store"].nunique() if "Store" in df.columns else 0

        # Parse duration
        if "Pause Duration" in df.columns:
            df["Duration_min"] = df["Pause Duration"].apply(_parse_duration_to_minutes)
            total_pause_mins = df["Duration_min"].sum()
            avg_pause_mins = df["Duration_min"].mean()
        else:
            total_pause_mins = avg_pause_mins = 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Pause Events", _fmt(total_pauses, "int"))
        c2.metric("Stores Affected", _fmt(stores_paused, "int"))
        c3.metric("Total Pause Time", f"{total_pause_mins:.0f} min ({total_pause_mins / 60:.1f} hrs)")
        c4.metric("Avg Pause Duration", _fmt(avg_pause_mins, "time"))

        col_a, col_b = st.columns(2)
        with col_a:
            if "Reason For Pausing" in df.columns:
                reason_counts = df["Reason For Pausing"].value_counts().reset_index()
                reason_counts.columns = ["Reason", "Count"]
                fig = _plotly_pie(reason_counts, "Reason", "Count", "Pause Reasons")
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            if "Store" in df.columns:
                store_pauses = df.groupby("Store").agg(
                    Pauses=("Store", "count"),
                    Total_Min=("Duration_min", "sum") if "Duration_min" in df.columns else ("Store", "count"),
                ).reset_index().sort_values("Pauses", ascending=False).head(15)
                fig = _plotly_bar(store_pauses, "Store", "Pauses", "Most Paused Stores")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Pause Details")
        show_cols = [c for c in ["Store", "City", "Pause Start", "Pause Duration", "Reason For Pausing"] if c in df.columns]
        st.dataframe(df[show_cols] if show_cols else df, use_container_width=True, height=300)


def render_ue_marketing(_data):
    st.info("No Uber Eats marketing data available. Upload UE promo/ads exports to enable this tab.")


# =============================================================================
# CROSS-PLATFORM SUMMARY
# =============================================================================
def render_cross_platform_summary(all_data):
    """Show a quick cross-platform comparison."""
    rows = []
    for key, label in [("doordash", "DoorDash"), ("grubhub", "Grubhub"), ("uber_eats", "Uber Eats")]:
        payload = all_data.get(key)
        if not payload:
            continue
        fin = payload.get("financial_df")
        if fin is None or fin.empty:
            continue
        orders = len(fin)
        # Try to get sales amount
        for col in ["Subtotal", "Ticket Size", "subtotal_sales", "Gross Sales"]:
            if col in fin.columns:
                sales = pd.to_numeric(fin[col], errors="coerce").fillna(0).sum()
                break
        else:
            sales = 0
        aov = (sales / orders) if orders else 0
        stores = 0
        for col in ["Store name", "Store Name", "Store", "store_name"]:
            if col in fin.columns:
                stores = fin[col].nunique()
                break
        rows.append({"Platform": label, "Orders": orders, "Sales": sales, "AOV": round(aov, 2), "Stores": stores})

    if not rows:
        return
    summary = pd.DataFrame(rows)

    st.markdown("### Cross-Platform Summary")
    cols = st.columns(len(rows))
    for i, row in enumerate(rows):
        with cols[i]:
            st.markdown(f"**{row['Platform']}**")
            st.metric("Orders", _fmt(row["Orders"], "int"))
            st.metric("Sales", _fmt(row["Sales"], "currency"))
            st.metric("AOV", _fmt(row["AOV"], "currency"))
            st.metric("Stores", _fmt(row["Stores"], "int"))

    # Side-by-side bar
    col_a, col_b = st.columns(2)
    with col_a:
        fig = _plotly_bar(summary, "Platform", "Sales", "Sales by Platform")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = _plotly_bar(summary, "Platform", "Orders", "Orders by Platform", color=COLORS[2])
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")


# =============================================================================
# EXCEL EXPORT: Store mapping workbook
# =============================================================================
def _build_mapping_excel(matrix, mapping_df):
    """Build an Excel workbook with mapping results: Matched, Only in Data, Only in Airtable sheets."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Summary sheet
        summary_rows = []
        for r in matrix:
            summary_rows.append({
                "File": r["file_name"],
                "Platform": r["platform"],
                "IDs in Data": r["store_ids_in_data"],
                "IDs in Airtable": r["store_ids_in_airtable"],
                "Matched": r["matched_count"],
                "Only in Data": r["only_in_data_count"],
                "Only in Airtable": r["only_in_airtable_count"],
            })
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)

        # Per-platform detail sheets
        all_matched = []
        all_only_data = []
        all_only_airtable = []
        for r in matrix:
            plat = r["platform"]
            for sid in r.get("matched_sample", []):
                all_matched.append({"Platform": plat, "Store ID": sid, "File": r["file_name"]})
            for sid in r.get("only_in_data_sample", []):
                all_only_data.append({"Platform": plat, "Store ID": sid, "File": r["file_name"]})
            for sid in r.get("only_in_airtable_sample", []):
                all_only_airtable.append({"Platform": plat, "Store ID": sid})

        if all_matched:
            pd.DataFrame(all_matched).to_excel(writer, sheet_name="Matched (Data + Airtable)", index=False)
        if all_only_data:
            pd.DataFrame(all_only_data).to_excel(writer, sheet_name="Only in Data", index=False)
        if all_only_airtable:
            pd.DataFrame(all_only_airtable).to_excel(writer, sheet_name="Only in Airtable", index=False)

        # Raw Airtable mapping
        if mapping_df is not None and not mapping_df.empty:
            mapping_df.to_excel(writer, sheet_name="Airtable Store Mapping", index=False)

    output.seek(0)
    return output


# =============================================================================
# MAIN
# =============================================================================
def main():
    st.markdown("""
    <div class="main-header">
        <h1>The On Demand Company</h1>
        <p>Virtual Brands Dashboard — DoorDash  ·  Uber Eats  ·  Grubhub</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- Sidebar: data upload ----
    st.sidebar.markdown("### Data Upload")
    st.sidebar.caption("Upload your CSV/Excel data folder or use the bundled **data/** folder.")

    if "accumulated_uploads" not in st.session_state:
        st.session_state["accumulated_uploads"] = []
    if "_last_folder_key" not in st.session_state:
        st.session_state["_last_folder_key"] = None

    def _set_folder_files(batch):
        if not batch:
            st.session_state["_last_folder_key"] = None
            return
        new_key = tuple(sorted(getattr(f, "name", str(f)) for f in batch))
        if new_key != st.session_state.get("_last_folder_key"):
            st.session_state["accumulated_uploads"] = []
            for f in batch:
                raw = f.getvalue() if hasattr(f, "getvalue") else (f.read() if hasattr(f, "read") else b"")
                st.session_state["accumulated_uploads"].append({"name": getattr(f, "name", str(f)), "content": raw})
            st.session_state["_last_folder_key"] = new_key

    folder_batch = st.sidebar.file_uploader(
        "Select your data folder", type=["csv", "xlsx", "xls"],
        accept_multiple_files="directory", key="folder_uploader",
    )
    _set_folder_files(folder_batch)

    class _BytesFile:
        def __init__(self, name, content):
            self.name = name
            self._content = content
        def getvalue(self):
            return self._content

    accumulated = st.session_state.get("accumulated_uploads", [])
    all_uploads = [_BytesFile(x["name"], x["content"]) for x in accumulated]

    if accumulated:
        total_mb = sum(len(x.get("content", b"")) for x in accumulated) / (1024 * 1024)
        st.sidebar.success(f"**{len(accumulated)}** file(s) ({total_mb:.1f} MB)")
    if accumulated and st.sidebar.button("Clear All Uploads", key="clear_uploads"):
        st.session_state["accumulated_uploads"] = []
        st.session_state["_last_folder_key"] = None
        st.rerun()

    st.sidebar.markdown("---")
    run_btn = st.sidebar.button("Run Analysis", type="primary", use_container_width=True, key="run_analysis_main")
    st.sidebar.caption("Loads data, fetches Airtable mapping, and runs full analysis.")

    # ---- Run Analysis: load data + mapping ----
    review_data = st.session_state.get("review_data")
    review_source = st.session_state.get("review_source")
    data_loaded = st.session_state.get("analysis_data")
    mapping_matrix = st.session_state.get("mapping_matrix")
    mapping_df_cached = st.session_state.get("mapping_df")

    if run_btn:
        try:
            from data_loader import collect_review_from_uploads, collect_review_from_data_folder
            from data_loader import load_from_review_data, load_all_from_data_folder
            import importlib, store_mapping
            importlib.reload(store_mapping)

            with st.spinner("Loading data and fetching Airtable store mapping..."):
                # Step 1: Build review data
                if all_uploads:
                    review_data = collect_review_from_uploads(all_uploads, store_content=False)
                    review_source = "uploads"
                else:
                    review_data = collect_review_from_data_folder("data")
                    review_source = "data_folder"
                st.session_state["review_data"] = review_data
                st.session_state["review_source"] = review_source

                # Step 2: Load analysis data
                if review_data and review_source == "uploads":
                    data_loaded = load_from_review_data(review_data, upload_file_lookup=all_uploads)
                else:
                    data_loaded = load_all_from_data_folder("data")
                st.session_state["analysis_data"] = data_loaded

                # Step 3: Fetch Airtable mapping and build matrix
                name_to_content = {x["name"]: x["content"] for x in accumulated} if review_source == "uploads" else {}
                file_items = []
                for item in review_data:
                    content = item.get("content") or (name_to_content.get(item.get("name")) if name_to_content else None)
                    file_items.append({"name": item.get("name", "?"), "platform": item.get("platform", ""), "path": item.get("path"), "content": content})

                # Fetch mapping from Airtable
                mapping_df_cached, mapping_err = store_mapping.get_store_mapping_df()
                st.session_state["mapping_df"] = mapping_df_cached

                build_fn = getattr(store_mapping, "build_store_mapping_matrix_with_debug", None)
                if build_fn:
                    mapping_matrix, debug_steps, err = build_fn(file_items, mapping_df=mapping_df_cached)
                else:
                    mapping_matrix, err = store_mapping.build_store_mapping_matrix(file_items, mapping_df=mapping_df_cached)
                    debug_steps = []
                st.session_state["mapping_matrix"] = mapping_matrix
                st.session_state["mapping_debug"] = debug_steps
                st.session_state["mapping_error"] = err

            st.sidebar.success("Analysis loaded.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))
            import traceback
            with st.sidebar.expander("Error details"):
                st.code(traceback.format_exc())

    # ---- Sidebar: Airtable Filters ----
    QA_COL = "QA Auditor (from Account Name)"
    CSA_COL = "CSA Name (from Account Name)"
    selected_qa = []
    selected_csa = []

    def _dict_to_label(d: dict) -> str:
        # Airtable often returns linked records as dicts like {"id": "...", "name": "..."}
        if not isinstance(d, dict):
            return str(d)
        for k in ("name", "Name", "label", "Label", "value", "Value", "id", "Id"):
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        try:
            import json

            return json.dumps(d, sort_keys=True)
        except Exception:
            return str(d)

    def _cell_to_str_list(x):
        if x is None:
            return []
        try:
            # handles np.nan / pd.NA
            if pd.isna(x):
                return []
        except Exception:
            pass

        if isinstance(x, str):
            s = x.strip()
            return [s] if s else []
        if isinstance(x, dict):
            s = _dict_to_label(x)
            return [s] if s else []
        if isinstance(x, (list, tuple, set)):
            out = []
            for item in x:
                out.extend(_cell_to_str_list(item))
            return [s for s in out if isinstance(s, str) and s.strip()]
        return [str(x)]

    if mapping_df_cached is not None and not mapping_df_cached.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Filters")

        # QA Auditor filter
        if QA_COL in mapping_df_cached.columns:
            qa_values = sorted(
                {
                    v
                    for x in mapping_df_cached[QA_COL].dropna().tolist()
                    for v in _cell_to_str_list(x)
                }
            )
            if qa_values:
                selected_qa = st.sidebar.multiselect("QA Auditor", options=qa_values, key="filter_qa")

        # CSA Name filter
        if CSA_COL in mapping_df_cached.columns:
            csa_values = sorted(
                {
                    v
                    for x in mapping_df_cached[CSA_COL].dropna().tolist()
                    for v in _cell_to_str_list(x)
                }
            )
            if csa_values:
                selected_csa = st.sidebar.multiselect("CSA Name", options=csa_values, key="filter_csa")

    # Apply filters to mapping_df
    filtered_mapping_df = mapping_df_cached
    if mapping_df_cached is not None and not mapping_df_cached.empty:
        if selected_qa and QA_COL in mapping_df_cached.columns:
            mask = mapping_df_cached[QA_COL].apply(
                lambda x: bool(set(_cell_to_str_list(x)) & set(selected_qa))
            )
            filtered_mapping_df = filtered_mapping_df[mask]
        if selected_csa and CSA_COL in mapping_df_cached.columns:
            mask = filtered_mapping_df[CSA_COL].apply(
                lambda x: bool(set(_cell_to_str_list(x)) & set(selected_csa))
            )
            filtered_mapping_df = filtered_mapping_df[mask]

    # Rebuild mapping matrix if filters are active
    if (selected_qa or selected_csa) and filtered_mapping_df is not None and review_data:
        try:
            import importlib, store_mapping
            importlib.reload(store_mapping)
            name_to_content = {x["name"]: x["content"] for x in accumulated} if review_source == "uploads" else {}
            file_items = []
            for item in review_data:
                content = item.get("content") or (name_to_content.get(item.get("name")) if name_to_content else None)
                file_items.append({"name": item.get("name", "?"), "platform": item.get("platform", ""), "path": item.get("path"), "content": content})
            build_fn = getattr(store_mapping, "build_store_mapping_matrix_with_debug", None)
            if build_fn:
                mapping_matrix, _, _ = build_fn(file_items, mapping_df=filtered_mapping_df)
            else:
                mapping_matrix, _ = store_mapping.build_store_mapping_matrix(file_items, mapping_df=filtered_mapping_df)
        except Exception:
            pass  # fall back to unfiltered matrix

    # ---- Nothing loaded yet ----
    if not data_loaded and not review_data:
        st.info("Upload your data folder in the sidebar, then click **Run Analysis**. Without uploads, the bundled **data/** folder is used.")
        return

    # ====================================================================
    # TOP-LEVEL TABS: Data Verification | Mapping | Analysis
    # ====================================================================
    top_tabs = st.tabs(["Data Verification", "Mapping", "Analysis"])

    # ------------------------------------------------------------------
    # TAB 1: DATA VERIFICATION
    # ------------------------------------------------------------------
    with top_tabs[0]:
        if not review_data:
            st.info("Click **Run Analysis** in the sidebar to load and verify data.")
        else:
            st.markdown("### Uploaded Files")
            st.caption("Source: **" + ("Uploaded files" if review_source == "uploads" else "data/ folder") + "**")

            # File summary table
            file_summary_rows = []
            for item in review_data:
                size_kb = item.get("size_bytes", 0) / 1024
                file_summary_rows.append({
                    "File Name": item.get("name", "?"),
                    "Platform": item.get("platform", "—"),
                    "Rows": item.get("rows", 0),
                    "Size": f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB",
                })
            st.dataframe(pd.DataFrame(file_summary_rows), use_container_width=True)

            # Expandable column details
            for item in review_data:
                name = item.get("name", "?")
                platform = item.get("platform", "—")
                rows = item.get("rows", 0)
                with st.expander(f"{name} — {platform} — {rows:,} rows"):
                    st.code(", ".join(item.get("columns", [])))

            st.markdown("---")

            # Debug steps from mapping fetch
            debug_steps = st.session_state.get("mapping_debug", [])
            mapping_err = st.session_state.get("mapping_error")
            if debug_steps:
                with st.expander("Debug: Airtable Fetch Steps", expanded=bool(mapping_err)):
                    for d in debug_steps:
                        status = d.get("status", "info")
                        fn = st.success if status == "ok" else (st.error if status == "fail" else st.info)
                        fn(f"**{d.get('step', '?')}** — {d.get('detail', '')}")
                    st.markdown("**First 5 rows (Airtable store mapping)**")
                    if mapping_df_cached is not None and not mapping_df_cached.empty:
                        st.dataframe(mapping_df_cached.head(5), use_container_width=True)
                    else:
                        st.caption("No mapping table in session — run **Run Analysis** after a successful Airtable fetch.")

    # ------------------------------------------------------------------
    # TAB 2: MAPPING
    # ------------------------------------------------------------------
    with top_tabs[1]:
        if not mapping_matrix:
            mapping_err = st.session_state.get("mapping_error")
            if mapping_err:
                st.warning(f"Could not load mapping: {mapping_err}")
            else:
                st.info("Click **Run Analysis** in the sidebar to fetch store mapping from Airtable.")
        else:
            st.markdown("### Store ID Mapping — Data vs Airtable")
            st.caption("Compares store IDs in uploaded data files against the Airtable store mapping (Nithin's view). "
                       "DD ↔ DoorDash StoreID, GH ↔ Grubhub CID, UE ↔ UberEats UUID.")

            # Summary table
            summary_rows = []
            for r in mapping_matrix:
                summary_rows.append({
                    "File": r["file_name"],
                    "Platform": r["platform"],
                    "IDs in Data": r["store_ids_in_data"],
                    "IDs in Airtable": r["store_ids_in_airtable"],
                    "Matched": r["matched_count"],
                    "Only in Data": r["only_in_data_count"],
                    "Only in Airtable": r["only_in_airtable_count"],
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            st.markdown("---")

            # Detailed breakdown per file
            for r in mapping_matrix:
                with st.expander(f"**{r['file_name']}** ({r['platform']}) — Matched: {r['matched_count']}, Only Data: {r['only_in_data_count']}, Only Airtable: {r['only_in_airtable_count']}"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown("**Matched (Both)**")
                        matched_ids = r.get("matched_sample", [])
                        if matched_ids:
                            st.dataframe(pd.DataFrame({"Store ID": matched_ids}), use_container_width=True, height=200)
                        else:
                            st.caption("No matched IDs")
                    with col_b:
                        st.markdown("**Only in Data**")
                        data_only_ids = r.get("only_in_data_sample", [])
                        if data_only_ids:
                            st.dataframe(pd.DataFrame({"Store ID": data_only_ids}), use_container_width=True, height=200)
                        else:
                            st.caption("None — all data IDs found in Airtable")
                    with col_c:
                        st.markdown("**Only in Airtable**")
                        airtable_only_ids = r.get("only_in_airtable_sample", [])
                        if airtable_only_ids:
                            st.dataframe(pd.DataFrame({"Store ID": airtable_only_ids}), use_container_width=True, height=200)
                        else:
                            st.caption("None — all Airtable IDs found in data")

            st.markdown("---")

            # Filter info
            if selected_qa or selected_csa:
                filter_parts = []
                if selected_qa:
                    filter_parts.append(f"QA Auditor: {', '.join(selected_qa)}")
                if selected_csa:
                    filter_parts.append(f"CSA Name: {', '.join(selected_csa)}")
                st.info(f"Filtered by: {' | '.join(filter_parts)} — showing {len(filtered_mapping_df)} of {len(mapping_df_cached)} Airtable records")

            # Download Excel button
            excel_data = _build_mapping_excel(mapping_matrix, filtered_mapping_df)
            st.download_button(
                label="Download Mapping Report (Excel)",
                data=excel_data,
                file_name="TODC_Store_Mapping_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
                type="primary",
                use_container_width=True,
            )

    # ------------------------------------------------------------------
    # TAB 3: ANALYSIS
    # ------------------------------------------------------------------
    with top_tabs[2]:
        if not data_loaded:
            st.info("Click **Run Analysis** in the sidebar to load platform data.")
            return

        # Determine which platforms have data
        platforms_available = []
        if data_loaded.get("doordash"):
            platforms_available.append("DoorDash")
        if data_loaded.get("uber_eats"):
            platforms_available.append("Uber Eats")
        if data_loaded.get("grubhub"):
            platforms_available.append("Grubhub")

        if not platforms_available:
            st.warning("No platform data found.")
            return

        # Cross-platform summary
        render_cross_platform_summary(data_loaded)

        # Platform tabs (nested within Analysis)
        platform_tabs = st.tabs(platforms_available)

        for i, plat_name in enumerate(platforms_available):
            with platform_tabs[i]:
                if plat_name == "DoorDash":
                    dd = data_loaded["doordash"]
                    sub_tabs = st.tabs(["Sales", "Marketing", "Operations"])
                    with sub_tabs[0]:
                        render_dd_sales(dd)
                    with sub_tabs[1]:
                        render_dd_marketing(dd)
                    with sub_tabs[2]:
                        render_dd_operations(dd)

                elif plat_name == "Uber Eats":
                    ue = data_loaded["uber_eats"]
                    sub_tabs = st.tabs(["Sales", "Marketing", "Operations"])
                    with sub_tabs[0]:
                        render_ue_sales(ue)
                    with sub_tabs[1]:
                        render_ue_marketing(ue)
                    with sub_tabs[2]:
                        render_ue_operations(ue)

                elif plat_name == "Grubhub":
                    gh = data_loaded["grubhub"]
                    sub_tabs = st.tabs(["Sales", "Marketing", "Operations"])
                    with sub_tabs[0]:
                        render_gh_sales(gh)
                    with sub_tabs[1]:
                        render_gh_marketing(gh)
                    with sub_tabs[2]:
                        render_gh_operations(gh)

    st.markdown("---")
    st.caption("The On Demand Company · Virtual Brands Dashboard")


if __name__ == "__main__":
    main()
