"""
RetailMart 360 - Analytical Engine
Provides aggregated analytical views and business summaries for notebooks and dashboard.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def get_monthly_sales_trend(mart_df: pd.DataFrame, shipped_only: bool = True) -> pd.DataFrame:
    """Monthly revenue, orders, units, and MoM growth rate."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    
    monthly = df.groupby("orderYearMonth").agg(
        revenue=("revenue", "sum"),
        estimatedGrossProfit=("estimatedGrossProfit", "sum"),
        orders=("orderNumber", "nunique"),
        units=("quantityOrdered", "sum")
    ).reset_index().sort_values("orderYearMonth")
    
    monthly["estimatedGrossMarginPct"] = ((monthly["estimatedGrossProfit"] / monthly["revenue"]) * 100).round(2)
    monthly["aov"] = (monthly["revenue"] / monthly["orders"]).round(2)
    monthly["mom_revenue_growth_pct"] = (monthly["revenue"].pct_change() * 100).round(2)
    return monthly


def get_yearly_sales_trend(mart_df: pd.DataFrame, shipped_only: bool = True) -> pd.DataFrame:
    """Yearly revenue, gross profit, margin %, and YoY growth rate."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    
    yearly = df.groupby("orderYear").agg(
        revenue=("revenue", "sum"),
        estimatedGrossProfit=("estimatedGrossProfit", "sum"),
        orders=("orderNumber", "nunique"),
        units=("quantityOrdered", "sum")
    ).reset_index().sort_values("orderYear")
    
    yearly["estimatedGrossMarginPct"] = ((yearly["estimatedGrossProfit"] / yearly["revenue"]) * 100).round(2)
    yearly["aov"] = (yearly["revenue"] / yearly["orders"]).round(2)
    yearly["yoy_revenue_growth_pct"] = (yearly["revenue"].pct_change() * 100).round(2)
    return yearly


def get_product_line_performance(mart_df: pd.DataFrame, shipped_only: bool = True) -> pd.DataFrame:
    """Product line revenue, units, gross profit, and margin %."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    total_rev = df["revenue"].sum()
    
    pl = df.groupby("productLine").agg(
        revenue=("revenue", "sum"),
        estimatedGrossProfit=("estimatedGrossProfit", "sum"),
        units=("quantityOrdered", "sum"),
        orders=("orderNumber", "nunique")
    ).reset_index().sort_values("revenue", ascending=False)
    
    pl["revenueSharePct"] = ((pl["revenue"] / total_rev) * 100).round(2) if total_rev > 0 else 0.0
    pl["estimatedGrossMarginPct"] = ((pl["estimatedGrossProfit"] / pl["revenue"]) * 100).round(2)
    return pl


def get_country_performance(mart_df: pd.DataFrame, shipped_only: bool = True) -> pd.DataFrame:
    """Customer country revenue, active customers, orders, and contribution share."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    total_rev = df["revenue"].sum()
    
    geo = df.groupby("customerCountry").agg(
        revenue=("revenue", "sum"),
        estimatedGrossProfit=("estimatedGrossProfit", "sum"),
        activeCustomers=("customerNumber", "nunique"),
        orders=("orderNumber", "nunique")
    ).reset_index().sort_values("revenue", ascending=False)
    
    geo["revenueSharePct"] = ((geo["revenue"] / total_rev) * 100).round(2) if total_rev > 0 else 0.0
    geo["estimatedGrossMarginPct"] = ((geo["estimatedGrossProfit"] / geo["revenue"]) * 100).round(2)
    return geo


def get_sales_rep_performance(mart_df: pd.DataFrame, shipped_only: bool = True) -> pd.DataFrame:
    """Sales representative revenue attribution, account counts, and office location."""
    df = mart_df[mart_df["is_shipped"]] if shipped_only else mart_df
    total_rev = df["revenue"].sum()
    
    rep = df.groupby(["salesRepName", "salesRepTitle", "officeCity", "officeCountry", "officeTerritory"]).agg(
        revenue=("revenue", "sum"),
        estimatedGrossProfit=("estimatedGrossProfit", "sum"),
        customersCount=("customerNumber", "nunique"),
        ordersCount=("orderNumber", "nunique")
    ).reset_index().sort_values("revenue", ascending=False)
    
    rep["revenueSharePct"] = ((rep["revenue"] / total_rev) * 100).round(2) if total_rev > 0 else 0.0
    rep["estimatedGrossMarginPct"] = ((rep["estimatedGrossProfit"] / rep["revenue"]) * 100).round(2)
    rep["aov"] = (rep["revenue"] / rep["ordersCount"]).round(2)
    return rep


def get_customer_balance_proxy(
    orders_clean: pd.DataFrame,
    orderdetails_clean: pd.DataFrame,
    payments_clean: pd.DataFrame,
    customers_clean: pd.DataFrame
) -> pd.DataFrame:
    """
    Computes account-level order value vs collected payments proxy.
    Safely aggregates orders and payments separately before joining to avoid cross-product fan-out.
    """
    # 1. Total Shipped Order Value per customer
    shipped_orders = orders_clean[orders_clean["is_shipped"]]["orderNumber"]
    shipped_lines = orderdetails_clean[orderdetails_clean["orderNumber"].isin(shipped_orders)]
    cust_orders = shipped_lines.groupby("orderNumber").agg(
        order_rev=("revenue", "sum")
    ).reset_index().merge(orders_clean[["orderNumber", "customerNumber"]], on="orderNumber", how="inner")
    
    cust_shipped_rev = cust_orders.groupby("customerNumber")["order_rev"].sum().reset_index()
    cust_shipped_rev.rename(columns={"order_rev": "totalShippedOrderValue"}, inplace=True)
    
    # 2. Total Payments per customer
    cust_payments = payments_clean.groupby("customerNumber")["amount"].sum().reset_index()
    cust_payments.rename(columns={"amount": "totalPaymentsCollected"}, inplace=True)
    
    # 3. Merge at customer level
    bal = customers_clean[["customerNumber", "customerName", "contactName", "country", "creditLimit"]].merge(
        cust_shipped_rev, on="customerNumber", how="left"
    ).merge(
        cust_payments, on="customerNumber", how="left"
    )
    
    bal["totalShippedOrderValue"] = bal["totalShippedOrderValue"].fillna(0.0).round(2)
    bal["totalPaymentsCollected"] = bal["totalPaymentsCollected"].fillna(0.0).round(2)
    bal["netOutstandingProxy"] = (bal["totalShippedOrderValue"] - bal["totalPaymentsCollected"]).round(2)
    bal["paymentCoverageRatio"] = np.where(
        bal["totalShippedOrderValue"] > 0,
        (bal["totalPaymentsCollected"] / bal["totalShippedOrderValue"]).round(4),
        1.0
    )
    
    return bal.sort_values("netOutstandingProxy", ascending=False)


def get_inventory_health(
    products_clean: pd.DataFrame,
    orderdetails_clean: pd.DataFrame
) -> pd.DataFrame:
    """
    Evaluates catalog inventory levels against historical sales demand and identifies dead-stock candidates.
    """
    demand = orderdetails_clean.groupby("productCode").agg(
        totalUnitsSold=("quantityOrdered", "sum"),
        totalOrdersCount=("orderNumber", "nunique"),
        totalRealizedRevenue=("revenue", "sum")
    ).reset_index()
    
    inv = products_clean.merge(demand, on="productCode", how="left")
    inv["totalUnitsSold"] = inv["totalUnitsSold"].fillna(0).astype(int)
    inv["totalOrdersCount"] = inv["totalOrdersCount"].fillna(0).astype(int)
    inv["totalRealizedRevenue"] = inv["totalRealizedRevenue"].fillna(0.0).round(2)
    
    # Stock-to-demand ratio
    inv["stockToDemandRatio"] = np.where(
        inv["totalUnitsSold"] > 0,
        (inv["quantityInStock"] / inv["totalUnitsSold"]).round(2),
        999.0
    )
    
    # Identify health category
    def categorize_inventory(row):
        if row["totalUnitsSold"] == 0:
            return "Dead Stock (Zero Demand)"
        elif row["stockToDemandRatio"] > 5.0:
            return "Over-Stocked"
        elif row["stockToDemandRatio"] < 0.20:
            return "Low Stock Risk"
        else:
            return "Balanced Stock"
            
    inv["inventoryHealthCategory"] = inv.apply(categorize_inventory, axis=1)
    return inv.sort_values("stockToDemandRatio", ascending=False)
