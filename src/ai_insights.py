"""
RetailMart 360 - OpenAI Analytics Assistant Module
Provides safe, deterministic, bounded AI business explanations and question-answering.
All numerical calculations are derived deterministically; OpenAI is used solely
for business interpretation, strategic narrative, and executive synthesis.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
from dotenv import load_dotenv

# Path to .env file in project root
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def _reload_env():
    """Dynamically reloads .env if it exists so key updates take effect immediately."""
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
    else:
        load_dotenv(override=True)

# Initial load
_reload_env()


def is_openai_available() -> bool:
    """Checks whether OpenAI API key is configured."""
    _reload_env()
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(key and len(key) > 10)


def get_openai_client():
    """Initializes and returns OpenAI client if key is configured, else None."""
    _reload_env()
    if not is_openai_available():
        return None
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        return OpenAI(api_key=api_key)
    except Exception as e:
        return None


def get_configured_model() -> str:
    """Returns the configured model or defaults to gpt-4o-mini."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()


# ------------------------------------------------------------------------------
# Feature 1: AI Executive Summary
# ------------------------------------------------------------------------------

def generate_ai_executive_summary(kpis: Dict[str, Any]) -> str:
    """
    Generates a natural-language executive summary of calculated business KPIs.
    Guaranteed: No raw customer PII is sent; all metrics are pre-aggregated.
    """
    client = get_openai_client()
    if client is None:
        return (
            "**Notice:** OpenAI API key is not configured. "
            "Please configure `OPENAI_API_KEY` in your `.env` file to enable AI-powered summaries.\n\n"
            f"**Calculated Highlights:**\n"
            f"- **Realized Shipped Revenue:** ${kpis.get('total_revenue', 0):,.2f}\n"
            f"- **Distinct Orders:** {kpis.get('total_orders', 0):,}\n"
            f"- **Average Order Value:** ${kpis.get('aov', 0):,.2f}\n"
            f"- **Estimated Gross Profit:** ${kpis.get('gross_profit', 0):,.2f} ({kpis.get('gross_margin_pct', 0):.1f}% margin)\n"
            f"- **Active Purchasing Accounts:** {kpis.get('active_customers', 0)} of {kpis.get('total_customers', 0)} registered accounts."
        )

    model = get_configured_model()
    prompt = f"""
You are the Chief Analytics Officer for RetailMart 360, a global high-end scale model vehicle retailer.
Below are the exact, verified business metrics computed across the filtered dataset:

- Realized Shipped Revenue: ${kpis.get('total_revenue', 0):,.2f}
- Booked Orders Count: {kpis.get('total_orders', 0):,}
- Average Order Value (AOV): ${kpis.get('aov', 0):,.2f}
- Total Physical Units Sold: {kpis.get('total_units', 0):,}
- Estimated Gross Contribution Profit: ${kpis.get('gross_profit', 0):,.2f}
- Estimated Gross Margin: {kpis.get('gross_margin_pct', 0):.1f}%
- Active Purchasing Customers: {kpis.get('active_customers', 0)} (out of {kpis.get('total_customers', 0)} total registered accounts)
- Top Product Line by Share: {kpis.get('top_product_line', 'Classic Cars')} ({kpis.get('top_product_line_share', 0):.1f}% of revenue)
- Average Shipping Duration: {kpis.get('avg_shipping_days', 3.76):.1f} calendar days
- Late Shipment SLA Compliance: {kpis.get('on_time_shipping_pct', 99.7):.1f}% on-time

Instructions:
1. Provide a concise, 3-paragraph executive briefing for the Board of Directors.
2. Structure your briefing:
   - **Performance Overview:** Revenue, profitability, and deal size health.
   - **Operational & Customer Highlights:** Volume, customer retention, fulfillment speed.
   - **Strategic Recommendations:** 2 concrete commercial actions management should take next.
3. CRITICAL: Strictly use the numbers provided above. DO NOT invent or extrapolate fabricated metrics.
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert executive data analyst who explains retail metrics with precision, conciseness, and zero hallucination."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"**Error generating AI summary:** {str(e)}\n\nPlease verify your API key and connection."


# ------------------------------------------------------------------------------
# Feature 2: Safe Bounded Question Answering Catalog
# ------------------------------------------------------------------------------

QUESTION_CATALOG = {
    "top_products": "What are the top 5 products by revenue and profitability?",
    "customer_segments": "Which customer segments generate the most sales and represent churn risks?",
    "regional_sales": "Which sovereign geographical markets contribute the most revenue?",
    "seasonality_trends": "What are the primary seasonal patterns in monthly revenue?",
    "product_margins": "Which product lines have the highest estimated gross profit margins?",
    "inventory_dead_stock": "What warehouse inventory issues or dead-stock items exist?",
    "executive_priorities": "What are the top prioritized management actions to improve profitability?"
}

def answer_catalog_question(question_key: str, mart_df: pd.DataFrame, rfm_df: pd.DataFrame, products_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Executes a deterministic calculation for a catalog question and passes verified figures to AI for explanation.
    """
    shipped = mart_df[mart_df["is_shipped"]]
    total_rev = shipped["revenue"].sum()
    
    if question_key == "top_products":
        top = shipped.groupby(["productCode", "productName", "productLine"]).agg(
            revenue=("revenue", "sum"),
            gross_profit=("estimatedGrossProfit", "sum"),
            units=("quantityOrdered", "sum")
        ).reset_index().sort_values("revenue", ascending=False).head(5)
        top["margin_pct"] = ((top["gross_profit"] / top["revenue"]) * 100).round(1)
        
        data_summary = top.to_string(index=False)
        user_prompt = f"Explain the business significance of our top 5 revenue-generating products:\n{data_summary}\nTotal portfolio revenue is ${total_rev:,.2f}."
        
    elif question_key == "customer_segments":
        seg = rfm_df.groupby("segment").agg(
            accounts=("customerNumber", "count"),
            revenue=("monetary", "sum")
        ).reset_index().sort_values("revenue", ascending=False)
        seg["rev_share"] = ((seg["revenue"] / seg["revenue"].sum()) * 100).round(1)
        
        data_summary = seg.to_string(index=False)
        user_prompt = f"Analyze the RFM customer segment distribution below and identify immediate retention risks and value concentration:\n{data_summary}"
        
    elif question_key == "regional_sales":
        geo = shipped.groupby("customerCountry").agg(
            revenue=("revenue", "sum"),
            orders=("orderNumber", "nunique"),
            customers=("customerNumber", "nunique")
        ).reset_index().sort_values("revenue", ascending=False).head(5)
        geo["share_pct"] = ((geo["revenue"] / total_rev) * 100).round(1)
        
        data_summary = geo.to_string(index=False)
        user_prompt = f"Analyze our top 5 sovereign geographic retail markets:\n{data_summary}"
        
    elif question_key == "seasonality_trends":
        monthly = shipped.groupby("orderYearMonth")["revenue"].sum().reset_index()
        top_months = monthly.sort_values("revenue", ascending=False).head(3)
        bottom_months = monthly.sort_values("revenue", ascending=True).head(3)
        
        data_summary = f"Peak Months:\n{top_months.to_string(index=False)}\nTrough Months:\n{bottom_months.to_string(index=False)}"
        user_prompt = f"Explain the seasonal revenue patterns shown in our monthly sales data:\n{data_summary}"
        
    elif question_key == "product_margins":
        pl = shipped.groupby("productLine").agg(
            revenue=("revenue", "sum"),
            gross_profit=("estimatedGrossProfit", "sum")
        ).reset_index().sort_values("revenue", ascending=False)
        pl["margin_pct"] = ((pl["gross_profit"] / pl["revenue"]) * 100).round(1)
        
        data_summary = pl.to_string(index=False)
        user_prompt = f"Evaluate the estimated gross margin performance across our 7 product lines:\n{data_summary}"
        
    elif question_key == "inventory_dead_stock":
        dead = products_df[~products_df["productCode"].isin(shipped["productCode"])].copy()
        dead["tied_up_cost"] = dead["quantityInStock"] * dead["buyPrice"]
        
        data_summary = dead[["productCode", "productName", "productLine", "quantityInStock", "buyPrice", "tied_up_cost"]].to_string(index=False)
        user_prompt = f"Analyze this dead-stock inventory finding and provide actionable liquidation recommendations:\n{data_summary}"
        
    else: # executive_priorities
        data_summary = f"Total Realized Revenue: ${total_rev:,.2f}; Total Shipped Orders: {shipped['orderNumber'].nunique()}; Active Customers: {shipped['customerNumber'].nunique()}."
        user_prompt = f"Synthesize top 3 immediate commercial priorities based on: {data_summary}"

    client = get_openai_client()
    if client is None:
        ai_response = (
            "*(OpenAI API key not configured. Below is the deterministic data summary:)*\n\n"
            f"```\n{data_summary}\n```"
        )
    else:
        try:
            model = get_configured_model()
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a Senior Retail Analytics Advisor. Provide concise, high-impact business interpretations based strictly on the supplied data."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            ai_response = resp.choices[0].message.content.strip()
        except Exception as e:
            ai_response = f"*(Error calling OpenAI: {str(e)})*\n\n```\n{data_summary}\n```"
            
    return {
        "question": QUESTION_CATALOG.get(question_key, question_key),
        "data_summary": data_summary,
        "ai_explanation": ai_response
    }


# ------------------------------------------------------------------------------
# Feature 3: AI Chart Interpretation
# ------------------------------------------------------------------------------

def explain_chart_insight(chart_name: str, context_data: Dict[str, Any]) -> str:
    """Provides analytical interpretation of a specific dashboard chart."""
    client = get_openai_client()
    if client is None:
        return f"**Deterministic Chart Context ({chart_name}):** {str(context_data)}"
        
    prompt = f"""
Interpret this retail analytics chart for an executive stakeholder:
Chart Title: {chart_name}
Aggregated Data Context: {str(context_data)}

Instructions:
1. Explain the primary trend visible in the data.
2. Highlight significant drivers or outliers.
3. State the operational or commercial implication.
4. Distinguish verified facts from analytical hypotheses. Keep under 150 words.
"""
    try:
        model = get_configured_model()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a concise BI dashboard co-pilot providing clear chart takeaways."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"*(Chart interpretation unavailable: {str(e)})*"
