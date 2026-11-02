"""
RetailMart 360 - Centralized Business KPI Framework
Standardized business formulas ensuring numerical consistency across SQL, Python, Notebooks, and Dashboard.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


# ---------------------------------------------------------
# Commercial Metrics
# ---------------------------------------------------------

def calc_total_revenue(mart_df: pd.DataFrame, shipped_only: bool = True) -> float:
    """
    Computes total order-line revenue.
    Default reporting policy: Shipped orders only (realized sales proxy).
    Formula: SUM(quantityOrdered * priceEach)
    """
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    return float(df["revenue"].sum().round(2))


def calc_total_orders(mart_df: pd.DataFrame, shipped_only: bool = True) -> int:
    """Distinct orders count."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    return int(df["orderNumber"].nunique())


def calc_total_units(mart_df: pd.DataFrame, shipped_only: bool = True) -> int:
    """Total physical quantity ordered."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    return int(df["quantityOrdered"].sum())


def calc_average_order_value(mart_df: pd.DataFrame, shipped_only: bool = True) -> float:
    """
    Average Order Value (AOV).
    Formula: Total Revenue / Total Distinct Orders
    """
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    orders = df["orderNumber"].nunique()
    if orders == 0:
        return 0.0
    return float((df["revenue"].sum() / orders).round(2))


def calc_estimated_gross_profit(mart_df: pd.DataFrame, shipped_only: bool = True) -> float:
    """
    Estimated Gross Profit.
    Formula: SUM(quantityOrdered * (priceEach - buyPrice))
    """
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    return float(df["estimatedGrossProfit"].sum().round(2))


def calc_estimated_gross_margin_pct(mart_df: pd.DataFrame, shipped_only: bool = True) -> float:
    """
    Estimated Gross Margin Percentage.
    Formula: (Estimated Gross Profit / Total Revenue) * 100
    """
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    rev = df["revenue"].sum()
    if rev == 0:
        return 0.0
    profit = df["estimatedGrossProfit"].sum()
    return float(((profit / rev) * 100).round(2))


# ---------------------------------------------------------
# Customer Metrics
# ---------------------------------------------------------

def calc_customer_counts(customers_df: pd.DataFrame) -> Dict[str, int]:
    """Total and active customers."""
    total = len(customers_df)
    active = int(customers_df["has_ordered"].sum())
    inactive = total - active
    return {
        "total_customers": total,
        "active_customers": active,
        "inactive_prospects": inactive
    }


def calc_repeat_customer_rate(orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates repeat customer rate for customers with >= 2 orders.
    """
    order_counts = orders_df.groupby("customerNumber")["orderNumber"].nunique()
    purchasers = len(order_counts)
    repeat_purchasers = int((order_counts >= 2).sum())
    single_purchasers = purchasers - repeat_purchasers
    rate = round((repeat_purchasers / purchasers) * 100, 2) if purchasers > 0 else 0.0
    
    return {
        "purchasing_customers": purchasers,
        "repeat_customers": repeat_purchasers,
        "single_order_customers": single_purchasers,
        "repeat_customer_rate_pct": rate
    }


def calc_customer_concentration(mart_df: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    """
    Evaluates revenue concentration among top customers.
    """
    shipped = mart_df[mart_df["is_shipped"]]
    total_rev = shipped["revenue"].sum()
    cust_rev = shipped.groupby(["customerNumber", "customerName"])["revenue"].sum().sort_values(ascending=False).reset_index()
    
    top_n_rev = float(cust_rev.head(top_n)["revenue"].sum())
    top_n_pct = round((top_n_rev / total_rev) * 100, 2) if total_rev > 0 else 0.0
    
    # Pareto 80/20 count
    cust_rev["cum_rev"] = cust_rev["revenue"].cumsum()
    cust_rev["cum_pct"] = cust_rev["cum_rev"] / total_rev
    pareto_count = int((cust_rev["cum_pct"] <= 0.80).sum()) + 1
    pareto_pct = round((pareto_count / len(cust_rev)) * 100, 2)
    
    return {
        "top_n": top_n,
        "top_n_revenue": round(top_n_rev, 2),
        "top_n_revenue_pct": top_n_pct,
        "pareto_80_customer_count": pareto_count,
        "pareto_80_customer_share_pct": pareto_pct,
        "top_customers_df": cust_rev.head(top_n)
    }


# ---------------------------------------------------------
# Product & Inventory Metrics
# ---------------------------------------------------------

def calc_abc_analysis(mart_df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs standard ABC segmentation on products based on cumulative shipped revenue.
    Class A: Top 80% of revenue
    Class B: Next 15% of revenue (80% to 95%)
    Class C: Final 5% of revenue (95% to 100%)
    """
    shipped = mart_df[mart_df["is_shipped"]]
    prod_rev = shipped.groupby(["productCode", "productName", "productLine"]).agg(
        revenue=("revenue", "sum"),
        units_sold=("quantityOrdered", "sum"),
        orders_count=("orderNumber", "nunique")
    ).reset_index()
    
    total_rev = prod_rev["revenue"].sum()
    prod_rev = prod_rev.sort_values(by="revenue", ascending=False).reset_index(drop=True)
    prod_rev["revenue_share"] = prod_rev["revenue"] / total_rev
    prod_rev["cum_revenue_share"] = prod_rev["revenue_share"].cumsum()
    
    def assign_abc(cum_share):
        if cum_share <= 0.80:
            return "A"
        elif cum_share <= 0.95:
            return "B"
        else:
            return "C"
            
    prod_rev["abc_class"] = prod_rev["cum_revenue_share"].apply(assign_abc)
    return prod_rev


# ---------------------------------------------------------
# Operations & Shipping Metrics
# ---------------------------------------------------------

def calc_operational_metrics(orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes shipping SLA, fulfillment durations, and status distribution.
    """
    total_orders = len(orders_df)
    shipped_orders = orders_df[orders_df["status"] == "Shipped"].copy()
    
    shipped_pct = round((len(shipped_orders) / total_orders) * 100, 2)
    avg_ship_duration = round(float(shipped_orders["shippingDays"].mean()), 2)
    
    late_orders = shipped_orders[shipped_orders["isLateShipment"]]
    late_count = len(late_orders)
    late_pct = round((late_count / len(shipped_orders)) * 100, 2) if len(shipped_orders) > 0 else 0.0
    
    status_counts = orders_df["status"].value_counts().to_dict()
    
    return {
        "total_orders": total_orders,
        "shipped_count": len(shipped_orders),
        "shipped_pct": shipped_pct,
        "avg_shipping_duration_days": avg_ship_duration,
        "late_shipments_count": late_count,
        "late_shipments_pct": late_pct,
        "status_distribution": status_counts
    }


# ---------------------------------------------------------
# Payment Collections Metrics
# ---------------------------------------------------------

def calc_collection_metrics(payments_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Summarizes remittance collections.
    """
    total_collections = round(float(payments_df["amount"].sum()), 2)
    payment_count = len(payments_df)
    paying_customers = int(payments_df["customerNumber"].nunique())
    avg_payment = round(float(payments_df["amount"].mean()), 2)
    
    return {
        "total_payments_amount": total_collections,
        "payment_transactions_count": payment_count,
        "paying_customers": paying_customers,
        "average_payment_amount": avg_payment
    }
