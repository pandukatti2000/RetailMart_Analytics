"""
RetailMart 360 - Data Cleaning & Validation Pipeline
Transforms raw retail tables into validated, standardized analytical datasets.
"""

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import numpy as np

from src.data_loader import load_all_raw_tables, PROJECT_ROOT, PROCESSED_DATA_DIR


def clean_offices(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans offices table, ensuring 'NA' territory is preserved as North America."""
    clean = df.copy()
    # Fill missing territory with NA (North America) if pandas read it as NaN
    clean["territory"] = clean["territory"].fillna("NA").astype(str).str.strip()
    clean["officeCode"] = clean["officeCode"].astype(str).str.strip()
    clean["city"] = clean["city"].astype(str).str.strip()
    clean["country"] = clean["country"].astype(str).str.strip()
    return clean


def clean_employees(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans employees table, preserving CEO null reportsTo and creating employeeName."""
    clean = df.copy()
    clean["employeeNumber"] = clean["employeeNumber"].astype(int)
    clean["officeCode"] = clean["officeCode"].astype(str).str.strip()
    clean["firstName"] = clean["firstName"].astype(str).str.strip()
    clean["lastName"] = clean["lastName"].astype(str).str.strip()
    clean["employeeName"] = clean["firstName"] + " " + clean["lastName"]
    clean["email"] = clean["email"].astype(str).str.strip().str.lower()
    clean["jobTitle"] = clean["jobTitle"].astype(str).str.strip()
    # reportsTo is nullable for Diane Murphy (President)
    clean["reportsTo"] = pd.to_numeric(clean["reportsTo"], errors="coerce")
    return clean


def clean_customers(df: pd.DataFrame, orders_df: pd.DataFrame) -> pd.DataFrame:
    """Cleans customers table, tagging active purchasers and standardizing geographic fields."""
    clean = df.copy()
    clean["customerNumber"] = clean["customerNumber"].astype(int)
    clean["customerName"] = clean["customerName"].astype(str).str.strip()
    clean["contactFirstName"] = clean["contactFirstName"].astype(str).str.strip()
    clean["contactLastName"] = clean["contactLastName"].astype(str).str.strip()
    clean["contactName"] = clean["contactFirstName"] + " " + clean["contactLastName"]
    clean["city"] = clean["city"].astype(str).str.strip()
    clean["country"] = clean["country"].astype(str).str.strip()
    clean["creditLimit"] = pd.to_numeric(clean["creditLimit"], errors="coerce").fillna(0.0)
    clean["salesRepEmployeeNumber"] = pd.to_numeric(clean["salesRepEmployeeNumber"], errors="coerce")
    
    # Active purchaser flag
    active_customers = set(orders_df["customerNumber"].unique())
    clean["has_ordered"] = clean["customerNumber"].isin(active_customers)
    clean["is_assigned_rep"] = clean["salesRepEmployeeNumber"].notna()
    return clean


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans products table, calculating markup and catalog inventory value."""
    clean = df.copy()
    clean["productCode"] = clean["productCode"].astype(str).str.strip()
    clean["productName"] = clean["productName"].astype(str).str.strip()
    clean["productLine"] = clean["productLine"].astype(str).str.strip()
    clean["quantityInStock"] = pd.to_numeric(clean["quantityInStock"], errors="coerce").fillna(0).astype(int)
    clean["buyPrice"] = pd.to_numeric(clean["buyPrice"], errors="coerce").round(2)
    clean["MSRP"] = pd.to_numeric(clean["MSRP"], errors="coerce").round(2)
    clean["markupAmount"] = (clean["MSRP"] - clean["buyPrice"]).round(2)
    clean["markupPct"] = ((clean["markupAmount"] / clean["buyPrice"]) * 100).round(2)
    clean["inventoryCostValue"] = (clean["quantityInStock"] * clean["buyPrice"]).round(2)
    return clean


def clean_productlines(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans productlines table."""
    clean = df.copy()
    clean["productLine"] = clean["productLine"].astype(str).str.strip()
    clean["textDescription"] = clean["textDescription"].astype(str).str.strip()
    # htmlDescription and image are 100% null in sample DB; retain clean structure
    return clean[["productLine", "textDescription"]]


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans orders table, parsing dates and deriving SLA / shipping duration flags."""
    clean = df.copy()
    clean["orderNumber"] = clean["orderNumber"].astype(int)
    clean["customerNumber"] = clean["customerNumber"].astype(int)
    clean["status"] = clean["status"].astype(str).str.strip()
    
    clean["orderDate"] = pd.to_datetime(clean["orderDate"], errors="coerce")
    clean["requiredDate"] = pd.to_datetime(clean["requiredDate"], errors="coerce")
    clean["shippedDate"] = pd.to_datetime(clean["shippedDate"], errors="coerce")
    
    # Derivations
    clean["orderYear"] = clean["orderDate"].dt.year
    clean["orderMonth"] = clean["orderDate"].dt.month
    clean["orderYearMonth"] = clean["orderDate"].dt.to_period("M").astype(str)
    
    clean["is_shipped"] = clean["status"] == "Shipped"
    clean["shippingDays"] = (clean["shippedDate"] - clean["orderDate"]).dt.days
    clean["isLateShipment"] = (clean["shippedDate"] > clean["requiredDate"])
    return clean


def clean_orderdetails(df: pd.DataFrame, products_clean: pd.DataFrame) -> pd.DataFrame:
    """Cleans order details and merges product cost to compute line-item revenue and profit."""
    clean = df.copy()
    clean["orderNumber"] = clean["orderNumber"].astype(int)
    clean["productCode"] = clean["productCode"].astype(str).str.strip()
    clean["quantityOrdered"] = pd.to_numeric(clean["quantityOrdered"], errors="coerce").astype(int)
    clean["priceEach"] = pd.to_numeric(clean["priceEach"], errors="coerce").round(2)
    clean["orderLineNumber"] = pd.to_numeric(clean["orderLineNumber"], errors="coerce").astype(int)
    
    # Calculate realized line revenue
    clean["revenue"] = (clean["quantityOrdered"] * clean["priceEach"]).round(2)
    
    # Merge buyPrice and MSRP from products
    prod_sub = products_clean[["productCode", "buyPrice", "MSRP", "productName", "productLine"]]
    clean = clean.merge(prod_sub, on="productCode", how="left")
    
    clean["estimatedCost"] = (clean["quantityOrdered"] * clean["buyPrice"]).round(2)
    clean["estimatedGrossProfit"] = (clean["revenue"] - clean["estimatedCost"]).round(2)
    clean["estimatedGrossMarginPct"] = (
        np.where(clean["revenue"] > 0, (clean["estimatedGrossProfit"] / clean["revenue"]) * 100, 0.0)
    ).round(2)
    clean["discountPct"] = (
        np.where(clean["MSRP"] > 0, ((clean["MSRP"] - clean["priceEach"]) / clean["MSRP"]) * 100, 0.0)
    ).round(2)
    
    return clean


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans payments table, parsing paymentDate and monetary amount."""
    clean = df.copy()
    clean["customerNumber"] = clean["customerNumber"].astype(int)
    clean["checkNumber"] = clean["checkNumber"].astype(str).str.strip()
    clean["paymentDate"] = pd.to_datetime(clean["paymentDate"], errors="coerce")
    clean["paymentYear"] = clean["paymentDate"].dt.year
    clean["paymentMonth"] = clean["paymentDate"].dt.month
    clean["paymentYearMonth"] = clean["paymentDate"].dt.to_period("M").astype(str)
    clean["amount"] = pd.to_numeric(clean["amount"], errors="coerce").round(2)
    return clean


def build_sales_analytical_mart(
    orderdetails_clean: pd.DataFrame,
    orders_clean: pd.DataFrame,
    customers_clean: pd.DataFrame,
    employees_clean: pd.DataFrame,
    offices_clean: pd.DataFrame
) -> pd.DataFrame:
    """
    Constructs a fully denormalized order-line analytical mart.
    Grain: 1 row per order line item (2,996 rows).
    """
    # Join orderdetails with orders
    mart = orderdetails_clean.merge(
        orders_clean[[
            "orderNumber", "orderDate", "requiredDate", "shippedDate",
            "status", "orderYear", "orderMonth", "orderYearMonth",
            "is_shipped", "shippingDays", "isLateShipment", "customerNumber"
        ]],
        on="orderNumber",
        how="inner"
    )
    
    # Join with customers
    mart = mart.merge(
        customers_clean[[
            "customerNumber", "customerName", "contactName",
            "city", "state", "country", "salesRepEmployeeNumber", "creditLimit"
        ]].rename(columns={"city": "customerCity", "state": "customerState", "country": "customerCountry"}),
        on="customerNumber",
        how="inner"
    )
    
    # Join with employees (sales rep)
    mart = mart.merge(
        employees_clean[[
            "employeeNumber", "employeeName", "jobTitle", "officeCode"
        ]].rename(columns={
            "employeeNumber": "salesRepEmployeeNumber",
            "employeeName": "salesRepName",
            "jobTitle": "salesRepTitle"
        }),
        on="salesRepEmployeeNumber",
        how="left"
    )
    
    # Fill unassigned sales reps
    mart["salesRepName"] = mart["salesRepName"].fillna("Unassigned / Direct")
    
    # Join with offices
    mart = mart.merge(
        offices_clean[[
            "officeCode", "city", "country", "territory"
        ]].rename(columns={
            "city": "officeCity",
            "country": "officeCountry",
            "territory": "officeTerritory"
        }),
        on="officeCode",
        how="left"
    )
    
    mart["officeCity"] = mart["officeCity"].fillna("Unassigned Office")
    mart["officeCountry"] = mart["officeCountry"].fillna("Unassigned Office")
    mart["officeTerritory"] = mart["officeTerritory"].fillna("Unassigned Territory")
    
    return mart


def build_customer_rfm_mart(
    customers_clean: pd.DataFrame,
    orders_clean: pd.DataFrame,
    orderdetails_clean: pd.DataFrame,
    snapshot_date: str = "2005-06-01"
) -> pd.DataFrame:
    """
    Constructs reproducible RFM customer segmentation.
    Snapshot Date: 2005-06-01 (first day after dataset cutoff of 2005-05-31).
    Qualifying orders: Shipped orders only for realized customer value.
    """
    ref_date = pd.to_datetime(snapshot_date)
    
    # Filter for qualifying shipped orders
    shipped_orders = orders_clean[orders_clean["is_shipped"]].copy()
    shipped_lines = orderdetails_clean[orderdetails_clean["orderNumber"].isin(shipped_orders["orderNumber"])].copy()
    
    order_rev = shipped_lines.groupby("orderNumber")["revenue"].sum().reset_index()
    shipped_orders = shipped_orders.merge(order_rev, on="orderNumber", how="inner")
    
    # Aggregate to customer level
    cust_rfm = shipped_orders.groupby("customerNumber").agg(
        last_order_date=("orderDate", "max"),
        frequency=("orderNumber", "nunique"),
        monetary=("revenue", "sum")
    ).reset_index()
    
    cust_rfm["recency_days"] = (ref_date - cust_rfm["last_order_date"]).dt.days
    
    # Merge with full customer list to account for prospect customers
    full_rfm = customers_clean[[
        "customerNumber", "customerName", "contactName", "city", "country",
        "salesRepEmployeeNumber", "creditLimit"
    ]].merge(cust_rfm, on="customerNumber", how="left")
    
    # Active vs Inactive
    full_rfm["is_active"] = full_rfm["frequency"].notna() & (full_rfm["frequency"] > 0)
    full_rfm["frequency"] = full_rfm["frequency"].fillna(0).astype(int)
    full_rfm["monetary"] = full_rfm["monetary"].fillna(0.0).round(2)
    full_rfm["recency_days"] = full_rfm["recency_days"].fillna(999).astype(int)
    
    # Scoring active customers using quintiles / transparent bounds
    active = full_rfm[full_rfm["is_active"]].copy()
    
    # Recency score: lower recency_days = higher score (5 is most recent)
    active["r_score"] = pd.qcut(active["recency_days"], q=4, labels=[4, 3, 2, 1]).astype(int)
    
    # Frequency score: frequency ranges from 1 to 26
    # Map by cut thresholds: 1-2 -> 1, 3 -> 2, 4 -> 3, 5+ -> 4
    active["f_score"] = pd.cut(
        active["frequency"],
        bins=[0, 1, 2, 3, 100],
        labels=[1, 2, 3, 4],
        include_lowest=True
    ).astype(int)
    
    # Monetary score: quintiles/quartiles
    active["m_score"] = pd.qcut(active["monetary"], q=4, labels=[1, 2, 3, 4]).astype(int)
    
    active["rfm_score"] = (
        active["r_score"].astype(str) + 
        active["f_score"].astype(str) + 
        active["m_score"].astype(str)
    )
    
    # Segmentation logic
    def assign_segment(row):
        r = row["r_score"]
        f = row["f_score"]
        m = row["m_score"]
        
        if r >= 3 and f >= 3 and m >= 3:
            return "Champions"
        elif r >= 3 and f >= 2:
            return "Loyal Customers"
        elif r >= 3 and f == 1:
            return "New / Potential Loyalists"
        elif r == 2 and f >= 2 and m >= 3:
            return "High Value At Risk"
        elif r == 2:
            return "Needs Attention"
        elif r == 1 and m >= 3:
            return "High Value At Risk"
        elif r == 1 and f >= 2:
            return "At Risk"
        else:
            return "Hibernating"
            
    active["segment"] = active.apply(assign_segment, axis=1)
    
    # Re-merge segments back to full_rfm
    full_rfm = full_rfm.merge(
        active[["customerNumber", "r_score", "f_score", "m_score", "rfm_score", "segment"]],
        on="customerNumber",
        how="left"
    )
    full_rfm["segment"] = full_rfm["segment"].fillna("Prospect / Inactive")
    full_rfm["rfm_score"] = full_rfm["rfm_score"].fillna("000")
    
    return full_rfm


def run_pipeline() -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """Executes the complete cleaning pipeline and saves all processed files."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    raw = load_all_raw_tables()
    
    offices_c = clean_offices(raw["offices"])
    employees_c = clean_employees(raw["employees"])
    orders_c = clean_orders(raw["orders"])
    customers_c = clean_customers(raw["customers"], orders_c)
    products_c = clean_products(raw["products"])
    productlines_c = clean_productlines(raw["productlines"])
    orderdetails_c = clean_orderdetails(raw["orderdetails"], products_c)
    payments_c = clean_payments(raw["payments"])
    
    # Analytical Marts
    sales_mart = build_sales_analytical_mart(
        orderdetails_c, orders_c, customers_c, employees_c, offices_c
    )
    customer_rfm = build_customer_rfm_mart(
        customers_c, orders_c, orderdetails_c, snapshot_date="2005-06-01"
    )
    
    clean_tables = {
        "offices_clean": offices_c,
        "employees_clean": employees_c,
        "customers_clean": customers_c,
        "products_clean": products_c,
        "productlines_clean": productlines_c,
        "orders_clean": orders_c,
        "orderdetails_clean": orderdetails_c,
        "payments_clean": payments_c,
        "sales_analytical_mart": sales_mart,
        "customer_rfm": customer_rfm
    }
    
    for name, df in clean_tables.items():
        out_path = PROCESSED_DATA_DIR / f"{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved {name}: {len(df)} rows -> {out_path}")
        
    return clean_tables, sales_mart, customer_rfm


if __name__ == "__main__":
    run_pipeline()
