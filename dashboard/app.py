"""
RetailMart 360 - Interactive Retail Sales & Customer Intelligence Dashboard
Executive BI application developed with Streamlit and Plotly.
"""

import sys
import os
from pathlib import Path
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_processed_table
from src.metrics import (
    calc_total_revenue, calc_total_orders, calc_total_units,
    calc_average_order_value, calc_estimated_gross_profit,
    calc_estimated_gross_margin_pct, calc_repeat_customer_rate,
    calc_customer_concentration, calc_abc_analysis, calc_operational_metrics
)
from src.analytics import (
    get_monthly_sales_trend, get_yearly_sales_trend,
    get_product_line_performance, get_country_performance,
    get_sales_rep_performance, get_customer_balance_proxy,
    get_inventory_health
)
from src.ai_insights import (
    is_openai_available, generate_ai_executive_summary,
    answer_catalog_question, explain_chart_insight, get_configured_model, QUESTION_CATALOG
)
from dotenv import load_dotenv

# Ensure .env is loaded on app execution
load_dotenv(override=True)

# ------------------------------------------------------------------------------
# App Configuration & Executive BI Styling
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="RetailMart 360 | Executive Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom executive CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .metric-title {
        color: #64748B;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #0F172A;
        font-size: 1.65rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-sub {
        color: #10B981;
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 4px;
    }
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        border-bottom: 2px solid #F1F5F9;
        padding-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# Data Loading & Caching
# ------------------------------------------------------------------------------
@st.cache_data
def load_all_data():
    mart = load_processed_table("sales_analytical_mart")
    rfm = load_processed_table("customer_rfm")
    orders = load_processed_table("orders_clean")
    orderdetails = load_processed_table("orderdetails_clean")
    products = load_processed_table("products_clean")
    customers = load_processed_table("customers_clean")
    employees = load_processed_table("employees_clean")
    offices = load_processed_table("offices_clean")
    payments = load_processed_table("payments_clean")
    return mart, rfm, orders, orderdetails, products, customers, employees, offices, payments

try:
    mart_raw, rfm_df, orders_df, od_df, products_df, customers_df, employees_df, offices_df, payments_df = load_all_data()
except Exception as e:
    st.error(f"Error loading analytical data: {e}. Please ensure data_cleaning.py has been executed.")
    st.stop()


# ------------------------------------------------------------------------------
# Sidebar Navigation & Reactive Filters
# ------------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/fluency/96/combo-chart.png", width=54)
st.sidebar.title("RetailMart 360")
st.sidebar.caption("Executive Retail Intelligence & Analytics Suite")

pages = [
    "Executive Overview",
    "Sales Performance",
    "Customer Intelligence",
    "Product & Profitability",
    "Geographic & Sales Team",
    "Orders & Payments",
    "AI Business Analyst"
]
selected_page = st.sidebar.radio("Navigation", pages)

st.sidebar.markdown("---")
st.sidebar.subheader("Filter Controls")

# Date range filter
min_date = pd.to_datetime(mart_raw["orderDate"]).min().date()
max_date = pd.to_datetime(mart_raw["orderDate"]).max().date()
date_range = st.sidebar.date_input(
    "Order Date Span",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Status filter
available_statuses = sorted(mart_raw["status"].unique().tolist())
default_statuses = ["Shipped"] if "Shipped" in available_statuses else available_statuses
selected_statuses = st.sidebar.multiselect("Order Status", available_statuses, default=default_statuses)

# Product line filter
available_pl = sorted(mart_raw["productLine"].unique().tolist())
selected_pl = st.sidebar.multiselect("Product Line", available_pl, default=available_pl)

# Customer country filter
available_countries = sorted(mart_raw["customerCountry"].unique().tolist())
selected_countries = st.sidebar.multiselect("Customer Country", available_countries, default=available_countries)

# Apply filters
filtered_mart = mart_raw.copy()
filtered_mart["orderDate_dt"] = pd.to_datetime(filtered_mart["orderDate"]).dt.date

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
    filtered_mart = filtered_mart[(filtered_mart["orderDate_dt"] >= start_d) & (filtered_mart["orderDate_dt"] <= end_d)]

if selected_statuses:
    filtered_mart = filtered_mart[filtered_mart["status"].isin(selected_statuses)]
else:
    filtered_mart = filtered_mart.iloc[0:0]

if selected_pl:
    filtered_mart = filtered_mart[filtered_mart["productLine"].isin(selected_pl)]
else:
    filtered_mart = filtered_mart.iloc[0:0]

if selected_countries:
    filtered_mart = filtered_mart[filtered_mart["customerCountry"].isin(selected_countries)]
else:
    filtered_mart = filtered_mart.iloc[0:0]


# ------------------------------------------------------------------------------
# PAGE 1: EXECUTIVE OVERVIEW
# ------------------------------------------------------------------------------
if "Executive Overview" in selected_page:
    st.title("Executive Commercial Overview")
    st.markdown("High-level commercial KPIs, revenue trajectory, and business contribution summary.")

    if len(filtered_mart) == 0:
        st.warning("No records match the active filter criteria. Please broaden your filter selection.")
        st.stop()

    # Core Metrics
    total_rev = filtered_mart["revenue"].sum()
    total_orders = filtered_mart["orderNumber"].nunique()
    aov = total_rev / total_orders if total_orders > 0 else 0.0
    gross_profit = filtered_mart["estimatedGrossProfit"].sum()
    gross_margin = (gross_profit / total_rev * 100) if total_rev > 0 else 0.0
    active_customers = filtered_mart["customerNumber"].nunique()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Revenue", f"${total_rev:,.2f}", f"{len(filtered_mart):,} line items")
    with c2:
        st.metric("Total Orders", f"{total_orders:,}", f"{filtered_mart['quantityOrdered'].sum():,} units")
    with c3:
        st.metric("Avg Order Value", f"${aov:,.2f}", "Revenue per order")
    with c4:
        st.metric("Est. Gross Profit", f"${gross_profit:,.2f}", f"{gross_margin:.1f}% margin")
    with c5:
        st.metric("Active Customers", f"{active_customers:,}", "Purchasing accounts")

    st.markdown('<div class="section-header">Commercial Performance Trends</div>', unsafe_allow_html=True)
    col_left, col_right = st.columns([7, 5])

    with col_left:
        # Monthly Revenue Chart
        monthly_trend = filtered_mart.groupby("orderYearMonth").agg(
            revenue=("revenue", "sum"),
            orders=("orderNumber", "nunique")
        ).reset_index().sort_values("orderYearMonth")

        fig_rev = px.line(
            monthly_trend,
            x="orderYearMonth",
            y="revenue",
            markers=True,
            title="Monthly Revenue Trend (USD)",
            labels={"orderYearMonth": "Month", "revenue": "Revenue ($)"},
            color_discrete_sequence=["#1e3d59"]
        )
        fig_rev.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_rev, use_container_width=True)

    with col_right:
        # Product Line Share
        pl_share = filtered_mart.groupby("productLine")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
        fig_pl = px.pie(
            pl_share,
            names="productLine",
            values="revenue",
            title="Revenue Contribution by Product Line",
            color_discrete_sequence=px.colors.qualitative.Prism,
            hole=0.4
        )
        fig_pl.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_pl, use_container_width=True)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.subheader("Top 5 Customer Accounts")
        top_cust = filtered_mart.groupby(["customerNumber", "customerName", "customerCountry"]).agg(
            revenue=("revenue", "sum"),
            orders=("orderNumber", "nunique")
        ).reset_index().sort_values("revenue", ascending=False).head(5)
        top_cust["revenue_formatted"] = top_cust["revenue"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(top_cust[["customerName", "customerCountry", "orders", "revenue_formatted"]], use_container_width=True)

    with col_b2:
        st.subheader("Top 5 Sovereign Markets")
        top_countries = filtered_mart.groupby("customerCountry")["revenue"].sum().reset_index().sort_values("revenue", ascending=False).head(5)
        top_countries["share_pct"] = (top_countries["revenue"] / total_rev * 100).round(1).astype(str) + "%"
        top_countries["revenue_formatted"] = top_countries["revenue"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(top_countries[["customerCountry", "revenue_formatted", "share_pct"]], use_container_width=True)


# ------------------------------------------------------------------------------
# PAGE 2: SALES PERFORMANCE
# ------------------------------------------------------------------------------
elif "Sales Performance" in selected_page:
    st.title("Sales & Revenue Performance")
    st.markdown("Detailed breakdown of monthly and annual commercial trends, order status shares, and AOV evolution.")

    if len(filtered_mart) == 0:
        st.warning("No records match the active filters.")
        st.stop()

    monthly_perf = get_monthly_sales_trend(filtered_mart, shipped_only=False)

    col1, col2 = st.columns(2)
    with col1:
        fig_mom = px.bar(
            monthly_perf,
            x="orderYearMonth",
            y="mom_revenue_growth_pct",
            title="Month-over-Month (MoM) Revenue Growth (%)",
            labels={"mom_revenue_growth_pct": "Growth Rate (%)", "orderYearMonth": "Month"},
            color="mom_revenue_growth_pct",
            color_continuous_scale=["#EF4444", "#94A3B8", "#10B981"]
        )
        st.plotly_chart(fig_mom, use_container_width=True)

    with col2:
        fig_aov = px.line(
            monthly_perf,
            x="orderYearMonth",
            y="aov",
            markers=True,
            title="Average Order Value (AOV) Trajectory ($)",
            labels={"aov": "AOV ($)", "orderYearMonth": "Month"},
            color_discrete_sequence=["#17b978"]
        )
        st.plotly_chart(fig_aov, use_container_width=True)

    st.subheader("Monthly Performance Ledger")
    display_monthly = monthly_perf.copy()
    display_monthly["revenue"] = display_monthly["revenue"].apply(lambda x: f"${x:,.2f}")
    display_monthly["estimatedGrossProfit"] = display_monthly["estimatedGrossProfit"].apply(lambda x: f"${x:,.2f}")
    display_monthly["aov"] = display_monthly["aov"].apply(lambda x: f"${x:,.2f}")
    st.dataframe(display_monthly, use_container_width=True)

    st.download_button(
        "Download Monthly Sales CSV",
        data=monthly_perf.to_csv(index=False),
        file_name="retailmart_monthly_sales.csv",
        mime="text/csv"
    )


# ------------------------------------------------------------------------------
# PAGE 3: CUSTOMER INTELLIGENCE
# ------------------------------------------------------------------------------
elif "Customer Intelligence" in selected_page:
    st.title("Customer Intelligence & RFM Segmentation")
    st.markdown("Customer lifetime value, behavioral RFM segmentation, Pareto concentration, and account drill-down.")

    # RFM Segment Summary
    seg_summary = rfm_df.groupby("segment").agg(
        accounts=("customerNumber", "count"),
        total_revenue=("monetary", "sum"),
        avg_recency=("recency_days", "mean"),
        avg_frequency=("frequency", "mean")
    ).reset_index().sort_values("total_revenue", ascending=False)
    seg_summary["revenue_share_pct"] = (seg_summary["total_revenue"] / seg_summary["total_revenue"].sum() * 100).round(1)

    c1, c2 = st.columns([6, 6])
    with c1:
        fig_seg_rev = px.bar(
            seg_summary[seg_summary["segment"] != "Prospect / Inactive"],
            x="total_revenue",
            y="segment",
            orientation="h",
            title="Revenue Contribution by Customer Segment ($)",
            labels={"total_revenue": "Realized Revenue ($)", "segment": "Segment"},
            color_discrete_sequence=["#1e3d59"]
        )
        st.plotly_chart(fig_seg_rev, use_container_width=True)

    with c2:
        fig_seg_cnt = px.pie(
            seg_summary,
            names="segment",
            values="accounts",
            title="Customer Account Distribution by Segment",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_seg_cnt, use_container_width=True)

    st.markdown('<div class="section-header">Customer Pareto Concentration (80/20)</div>', unsafe_allow_html=True)
    concentration = calc_customer_concentration(mart_raw, top_n=10)
    st.info(
        f"**Pareto Insight:** Top 10 customer accounts generate **${concentration['top_n_revenue']:,.2f}** "
        f"({concentration['top_n_revenue_pct']}% of total revenue). "
        f"Exactly **{concentration['pareto_80_customer_count']} accounts ({concentration['pareto_80_customer_share_pct']}%)** "
        f"generate 80% of all commercial sales."
    )

    st.markdown('<div class="section-header">Customer Account Drill-Down</div>', unsafe_allow_html=True)
    search_term = st.text_input("Search Customer Account by Name, Country, or Segment:", "")
    view_rfm = rfm_df.copy()
    if search_term:
        view_rfm = view_rfm[
            view_rfm["customerName"].str.contains(search_term, case=False, na=False) |
            view_rfm["country"].str.contains(search_term, case=False, na=False) |
            view_rfm["segment"].str.contains(search_term, case=False, na=False)
        ]
    
    st.dataframe(
        view_rfm[["customerNumber", "customerName", "country", "segment", "frequency", "monetary", "recency_days", "creditLimit"]].sort_values("monetary", ascending=False),
        use_container_width=True
    )


# ------------------------------------------------------------------------------
# PAGE 4: PRODUCT & PROFITABILITY
# ------------------------------------------------------------------------------
elif "Product & Profitability" in selected_page:
    st.title("Product Merchandising & Profitability")
    st.markdown("SKU profitability, ABC categorization, inventory velocity, and dead-stock identification.")

    if len(filtered_mart) == 0:
        st.warning("No records match active filters.")
        st.stop()

    abc_df = calc_abc_analysis(filtered_mart)
    abc_summary = abc_df.groupby("abc_class").agg(
        sku_count=("productCode", "count"),
        total_revenue=("revenue", "sum"),
        total_units=("units_sold", "sum")
    ).reset_index()
    abc_summary["revenue_pct"] = (abc_summary["total_revenue"] / abc_summary["total_revenue"].sum() * 100).round(1)

    c1, c2 = st.columns(2)
    with c1:
        fig_abc = px.pie(
            abc_summary,
            names="abc_class",
            values="total_revenue",
            title="Revenue Share by ABC Category (A: 80%, B: 15%, C: 5%)",
            color_discrete_sequence=["#1e3d59", "#17b978", "#ff6e40"]
        )
        st.plotly_chart(fig_abc, use_container_width=True)

    with c2:
        top10_prod = abc_df.head(10).sort_values("revenue", ascending=True)
        fig_p10 = px.bar(
            top10_prod,
            x="revenue",
            y="productName",
            orientation="h",
            title="Top 10 Products by Realized Revenue ($)",
            labels={"revenue": "Revenue ($)", "productName": ""},
            color_discrete_sequence=["#1e3d59"]
        )
        st.plotly_chart(fig_p10, use_container_width=True)

    st.markdown('<div class="section-header">Warehouse Inventory Health & Dead Stock Alert</div>', unsafe_allow_html=True)
    inv_health = get_inventory_health(products_df, od_df)
    
    # Dead stock banner
    dead_stock = inv_health[inv_health["inventoryHealthCategory"] == "Dead Stock (Zero Demand)"]
    if len(dead_stock) > 0:
        row = dead_stock.iloc[0]
        st.error(
            f"**CRITICAL DEAD-STOCK ALERT:** SKU `{row['productCode']}` ({row['productName']}) "
            f"has **{row['quantityInStock']:,} units** sitting in warehouse inventory with **ZERO historical orders**! "
            f"Tied-up capital cost: **${row['inventoryCostValue']:,.2f}**."
        )

    st.dataframe(
        inv_health[["productCode", "productName", "productLine", "quantityInStock", "buyPrice", "totalUnitsSold", "stockToDemandRatio", "inventoryHealthCategory"]].sort_values("stockToDemandRatio", ascending=False),
        use_container_width=True
    )


# ------------------------------------------------------------------------------
# PAGE 5: GEOGRAPHIC & SALES TEAM PERFORMANCE
# ------------------------------------------------------------------------------
elif "Geographic" in selected_page:
    st.title("Geographic Markets & Sales Team Benchmarking")
    st.markdown("Sovereign country revenue, regional office performance, and sales representative quota attainment.")

    if len(filtered_mart) == 0:
        st.warning("No records match active filters.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        geo_perf = get_country_performance(filtered_mart, shipped_only=False).head(10)
        fig_geo = px.bar(
            geo_perf.sort_values("revenue", ascending=True),
            x="revenue",
            y="customerCountry",
            orientation="h",
            title="Top 10 Sovereign Markets by Revenue ($)",
            labels={"revenue": "Revenue ($)", "customerCountry": "Country"},
            color_discrete_sequence=["#1e3d59"]
        )
        st.plotly_chart(fig_geo, use_container_width=True)

    with c2:
        rep_perf = get_sales_rep_performance(filtered_mart, shipped_only=False)
        fig_rep = px.bar(
            rep_perf.sort_values("revenue", ascending=True),
            x="revenue",
            y="salesRepName",
            orientation="h",
            title="Sales Representative Revenue Attribution ($)",
            labels={"revenue": "Attributed Revenue ($)", "salesRepName": "Sales Rep"},
            color_discrete_sequence=["#17b978"]
        )
        st.plotly_chart(fig_rep, use_container_width=True)

    st.subheader("Sales Representative Performance Ledger")
    st.dataframe(rep_perf, use_container_width=True)


# ------------------------------------------------------------------------------
# PAGE 6: ORDERS & PAYMENTS
# ------------------------------------------------------------------------------
elif "Orders & Payments" in selected_page:
    st.title("Fulfillment Operations & Cash Collections")
    st.markdown("Shipping duration analysis, SLA tracking, payment receipts, and customer balance proxies.")

    ops = calc_operational_metrics(orders_df)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Order Headers", f"{ops['total_orders']:,}")
    with c2:
        st.metric("Shipped Orders Rate", f"{ops['shipped_pct']:.1f}%", f"{ops['shipped_count']} shipped")
    with c3:
        st.metric("Avg Shipping Duration", f"{ops['avg_shipping_duration_days']:.1f} Days")
    with c4:
        st.metric("Late Shipments", f"{ops['late_shipments_count']} ({ops['late_shipments_pct']:.2f}%)")

    col_l, col_r = st.columns(2)
    with col_l:
        # Shipping Duration Distribution
        shipped_orders = orders_df[orders_df["is_shipped"]].copy()
        fig_ship = px.histogram(
            shipped_orders,
            x="shippingDays",
            nbins=12,
            title="Distribution of Order Shipping Duration (Days)",
            labels={"shippingDays": "Fulfillment Duration (Days)", "count": "Orders"},
            color_discrete_sequence=["#1e3d59"]
        )
        st.plotly_chart(fig_ship, use_container_width=True)

    with col_r:
        # Monthly Payments Trend
        monthly_pay = payments_df.groupby("paymentYearMonth")["amount"].sum().reset_index()
        fig_pay = px.line(
            monthly_pay,
            x="paymentYearMonth",
            y="amount",
            markers=True,
            title="Monthly Cash Remittance Collections ($)",
            labels={"paymentYearMonth": "Month", "amount": "Collections ($)"},
            color_discrete_sequence=["#10B981"]
        )
        st.plotly_chart(fig_pay, use_container_width=True)

    st.markdown('<div class="section-header">Customer Account Balance Proxy (Orders vs Payments)</div>', unsafe_allow_html=True)
    bal_proxy = get_customer_balance_proxy(orders_df, od_df, payments_df, customers_df)
    st.dataframe(
        bal_proxy.head(15)[["customerNumber", "customerName", "country", "creditLimit", "totalShippedOrderValue", "totalPaymentsCollected", "netOutstandingProxy", "paymentCoverageRatio"]],
        use_container_width=True
    )


# ------------------------------------------------------------------------------
# PAGE 7: AI BUSINESS ANALYST
# ------------------------------------------------------------------------------
elif "AI Business Analyst" in selected_page:
    st.title("AI Business Analyst & Decision Co-Pilot")
    st.markdown("Natural-language strategic insights, executive summaries, and safe bounded business question answering.")

    openai_active = is_openai_available()
    if not openai_active:
        st.warning(
            "**OpenAI API Key Not Detected:** The dashboard is operating in deterministic analytical mode. "
            "To enable live OpenAI natural language interpretation, configure `OPENAI_API_KEY` in your `.env` file."
        )
    else:
        st.success(f"**OpenAI Assistant Online:** Successfully connected using model `{get_configured_model()}`.")

    st.markdown('<div class="section-header">Feature 1: AI Executive Business Summary</div>', unsafe_allow_html=True)
    st.caption("Synthesizes active filtered metrics into an executive briefing using calculated business KPIs.")
    
    if st.button("Generate AI Business Summary", type="primary"):
        with st.spinner("Analyzing business KPIs and preparing executive summary..."):
            kpi_payload = {
                "total_revenue": filtered_mart["revenue"].sum(),
                "total_orders": filtered_mart["orderNumber"].nunique(),
                "aov": filtered_mart["revenue"].sum() / filtered_mart["orderNumber"].nunique() if filtered_mart["orderNumber"].nunique() > 0 else 0,
                "total_units": filtered_mart["quantityOrdered"].sum(),
                "gross_profit": filtered_mart["estimatedGrossProfit"].sum(),
                "gross_margin_pct": (filtered_mart["estimatedGrossProfit"].sum() / filtered_mart["revenue"].sum() * 100) if filtered_mart["revenue"].sum() > 0 else 0,
                "active_customers": filtered_mart["customerNumber"].nunique(),
                "total_customers": len(customers_df),
                "top_product_line": filtered_mart.groupby("productLine")["revenue"].sum().idxmax() if len(filtered_mart) > 0 else "N/A",
                "top_product_line_share": (filtered_mart.groupby("productLine")["revenue"].sum().max() / filtered_mart["revenue"].sum() * 100) if filtered_mart["revenue"].sum() > 0 else 0,
                "avg_shipping_days": orders_df[orders_df["is_shipped"]]["shippingDays"].mean(),
                "on_time_shipping_pct": (1.0 - (orders_df[orders_df["is_shipped"]]["isLateShipment"].sum() / len(orders_df[orders_df["is_shipped"]]))) * 100
            }
            summary_text = generate_ai_executive_summary(kpi_payload)
            st.markdown(summary_text)

    st.markdown('<div class="section-header">Feature 2: Ask RetailMart AI (Bounded Question Catalog)</div>', unsafe_allow_html=True)
    st.caption("Select a validated commercial question from the analytics catalog to review calculated metrics and executive explanations.")

    question_options = list(QUESTION_CATALOG.keys())
    selected_q = st.selectbox(
        "Choose an analytical question to ask:",
        question_options,
        format_func=lambda k: QUESTION_CATALOG[k]
    )

    if st.button("Submit Question"):
        with st.spinner("Executing analytical query and generating response..."):
            res = answer_catalog_question(selected_q, filtered_mart, rfm_df, products_df)
            st.markdown(f"### Q: {res['question']}")
            st.markdown(res["ai_explanation"])
            with st.expander("Inspect Underlying Deterministic Calculation"):
                st.code(res["data_summary"])

    st.markdown('<div class="section-header">Feature 3: Strategic Executive Recommendations</div>', unsafe_allow_html=True)
    st.markdown("""
    1. **Liquidate Dead-Stock Inventory ($456K):** Bundle the 7,733 unsold units of *1985 Toyota Supra* (`S18_3233`) with popular Classic Cars at a promotional 35% discount to recover frozen warehouse capital.
    2. **Re-engage 14 'High Value At Risk' Accounts ($1.91M):** Assign top sales reps to conduct targeted outreach to dormant high-spending accounts before customer churn becomes irreversible.
    3. **Replenish Critical Low-Stock SKUs:** Expedite factory reorders for the *1968 Ford Mustang* (`S12_1099`), currently down to only 15 units against high historical demand.
    4. **Establish Milestone Terms on High-Exposure Accounts:** Implement milestone progress payments on large international buyers like *Euro+ Shopping Channel* to mitigate uncollected net balance exposure.
    5. **Activate 22 Dormant Prospects:** Formally allocate the 22 unassigned prospect accounts across regional sales offices to drive new account conversion.
    """)
else:
    st.info("Please select an analytics page from the sidebar navigation.")
