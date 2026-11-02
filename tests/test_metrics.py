"""
RetailMart 360 - Automated Metric & Data Validation Test Suite
Verifies KPI calculation accuracy, cross-tool numerical consistency, and referential integrity.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.data_loader import load_processed_table
from src.metrics import (
    calc_total_revenue, calc_total_orders, calc_total_units,
    calc_average_order_value, calc_estimated_gross_profit,
    calc_estimated_gross_margin_pct, calc_customer_counts,
    calc_repeat_customer_rate, calc_abc_analysis, calc_operational_metrics
)
from src.analytics import get_customer_balance_proxy, get_inventory_health


@pytest.fixture(scope="module")
def processed_data():
    mart = load_processed_table("sales_analytical_mart")
    rfm = load_processed_table("customer_rfm")
    orders = load_processed_table("orders_clean")
    orderdetails = load_processed_table("orderdetails_clean")
    products = load_processed_table("products_clean")
    customers = load_processed_table("customers_clean")
    employees = load_processed_table("employees_clean")
    offices = load_processed_table("offices_clean")
    payments = load_processed_table("payments_clean")
    return {
        "mart": mart,
        "rfm": rfm,
        "orders": orders,
        "orderdetails": orderdetails,
        "products": products,
        "customers": customers,
        "employees": employees,
        "offices": offices,
        "payments": payments
    }


def test_revenue_calculations(processed_data):
    """Verifies that realized revenue and booked revenue match verified figures exactly."""
    mart = processed_data["mart"]
    
    # Realized revenue (shipped only)
    shipped_rev = calc_total_revenue(mart, shipped_only=True)
    assert shipped_rev == 8865094.64, f"Expected 8865094.64, got {shipped_rev}"
    
    # Booked revenue (all statuses)
    all_rev = calc_total_revenue(mart, shipped_only=False)
    assert all_rev == 9604190.61, f"Expected 9604190.61, got {all_rev}"
    
    # Order counts
    shipped_orders = calc_total_orders(mart, shipped_only=True)
    assert shipped_orders == 303, f"Expected 303 shipped orders, got {shipped_orders}"
    
    all_orders = calc_total_orders(mart, shipped_only=False)
    assert all_orders == 326, f"Expected 326 total orders, got {all_orders}"


def test_average_order_value(processed_data):
    """Verifies AOV formula: total revenue / distinct orders."""
    mart = processed_data["mart"]
    aov = calc_average_order_value(mart, shipped_only=True)
    expected_aov = round(8865094.64 / 303, 2)
    assert aov == expected_aov, f"Expected {expected_aov}, got {aov}"


def test_gross_profit_and_margin(processed_data):
    """Verifies estimated gross profit and margin calculations."""
    mart = processed_data["mart"]
    profit = calc_estimated_gross_profit(mart, shipped_only=True)
    margin_pct = calc_estimated_gross_margin_pct(mart, shipped_only=True)
    
    assert profit > 0, "Gross profit must be positive"
    assert 38.0 <= margin_pct <= 45.0, f"Expected gross margin between 38-45%, got {margin_pct}%"
    expected_margin = round((profit / 8865094.64) * 100, 2)
    assert margin_pct == expected_margin


def test_customer_metrics(processed_data):
    """Verifies customer base counts and repeat purchasing behavior."""
    customers = processed_data["customers"]
    orders = processed_data["orders"]
    
    counts = calc_customer_counts(customers)
    assert counts["total_customers"] == 122
    assert counts["active_customers"] == 98
    assert counts["inactive_prospects"] == 24
    
    repeat = calc_repeat_customer_rate(orders)
    assert repeat["purchasing_customers"] == 98
    assert repeat["repeat_customers"] == 97
    assert repeat["single_order_customers"] == 1
    assert repeat["repeat_customer_rate_pct"] == 98.98


def test_rfm_segmentation_integrity(processed_data):
    """Verifies customer RFM mart completeness and segment assignments."""
    rfm = processed_data["rfm"]
    assert len(rfm) == 122, "RFM mart must include all 122 registered customers"
    
    # 24 inactive prospects
    prospects = rfm[rfm["segment"] == "Prospect / Inactive"]
    assert len(prospects) == 24
    
    # Active accounts must have positive monetary value
    active = rfm[rfm["segment"] != "Prospect / Inactive"]
    assert len(active) == 98
    assert (active["monetary"] > 0).all()


def test_abc_analysis_integrity(processed_data):
    """Verifies ABC product classification totals."""
    mart = processed_data["mart"]
    abc = calc_abc_analysis(mart)
    
    # Exactly 109 ordered products in historical sales
    assert len(abc) == 109
    assert set(abc["abc_class"].unique()) == {"A", "B", "C"}
    
    # Cumulative revenue share reaches 1.0 at the end
    assert np.isclose(abc["cum_revenue_share"].iloc[-1], 1.0, atol=1e-4)


def test_dead_stock_detection(processed_data):
    """Verifies that 1985 Toyota Supra (S18_3233) is accurately flagged as dead stock."""
    products = processed_data["products"]
    orderdetails = processed_data["orderdetails"]
    
    inv = get_inventory_health(products, orderdetails)
    dead = inv[inv["inventoryHealthCategory"] == "Dead Stock (Zero Demand)"]
    assert len(dead) == 1
    assert dead.iloc[0]["productCode"] == "S18_3233"
    assert dead.iloc[0]["quantityInStock"] == 7733
    assert dead.iloc[0]["totalUnitsSold"] == 0


def test_safe_account_reconciliation_no_fanout(processed_data):
    """Verifies that customer order value vs payment collections does NOT multiply revenue."""
    orders = processed_data["orders"]
    orderdetails = processed_data["orderdetails"]
    payments = processed_data["payments"]
    customers = processed_data["customers"]
    
    bal = get_customer_balance_proxy(orders, orderdetails, payments, customers)
    assert len(bal) == 122
    
    # Sum of customer order values must equal total shipped revenue exactly
    total_reconciled_orders = bal["totalShippedOrderValue"].sum()
    assert np.isclose(total_reconciled_orders, 8865094.64, atol=0.01)
    
    # Sum of customer payments must equal total payments collected exactly
    total_reconciled_payments = bal["totalPaymentsCollected"].sum()
    expected_payments = payments["amount"].sum()
    assert np.isclose(total_reconciled_payments, expected_payments, atol=0.01)
