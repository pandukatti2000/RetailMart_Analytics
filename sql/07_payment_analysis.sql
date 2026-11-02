-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 07_payment_analysis.sql
-- Purpose: Remittance collections, cash trends, customer payment totals, and balance proxies.
-- Dialect: MySQL 8.0+
-- Relational Note: Payments are logged at the customer level via checkNumber. 
--                  There is NO direct orderNumber foreign key in the payments table.
--                  We pre-aggregate orders and payments separately to avoid cross-product fan-out.
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. Monthly Collections & Cumulative Cash Inflow Trend
-- Tracks month-by-month cash remittance receipts and running total.
-- ------------------------------------------------------------------------------
WITH monthly_collections AS (
    SELECT 
        DATE_FORMAT(paymentDate, '%Y-%m') AS payment_year_month,
        COUNT(DISTINCT customerNumber) AS active_paying_customers,
        COUNT(checkNumber) AS payments_count,
        ROUND(SUM(amount), 2) AS monthly_collected_cash,
        ROUND(AVG(amount), 2) AS avg_payment_voucher_amount
    FROM payments
    GROUP BY DATE_FORMAT(paymentDate, '%Y-%m')
)
SELECT 
    payment_year_month,
    active_paying_customers,
    payments_count,
    monthly_collected_cash,
    LAG(monthly_collected_cash, 1) OVER (ORDER BY payment_year_month) AS prior_month_collections,
    ROUND(
        (monthly_collected_cash - LAG(monthly_collected_cash, 1) OVER (ORDER BY payment_year_month)) 
        / LAG(monthly_collected_cash, 1) OVER (ORDER BY payment_year_month) * 100, 2
    ) AS mom_collection_change_pct,
    ROUND(
        SUM(monthly_collected_cash) OVER (ORDER BY payment_year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2
    ) AS cumulative_cash_collected,
    avg_payment_voucher_amount
FROM monthly_collections
ORDER BY payment_year_month;

-- ------------------------------------------------------------------------------
-- 2. Yearly Payment Collections Summary
-- ------------------------------------------------------------------------------
SELECT 
    YEAR(paymentDate) AS payment_year,
    COUNT(DISTINCT customerNumber) AS paying_customers_count,
    COUNT(checkNumber) AS total_payment_transactions,
    ROUND(SUM(amount), 2) AS total_collected_amount,
    ROUND(AVG(amount), 2) AS avg_transaction_amount
FROM payments
GROUP BY YEAR(paymentDate)
ORDER BY payment_year;

-- ------------------------------------------------------------------------------
-- 3. Top 15 Remitting Customers by Total Cash Paid
-- ------------------------------------------------------------------------------
SELECT 
    c.customerNumber,
    c.customerName,
    c.country,
    c.creditLimit,
    COUNT(p.checkNumber) AS payment_frequency,
    MIN(p.paymentDate) AS first_payment_date,
    MAX(p.paymentDate) AS last_payment_date,
    ROUND(SUM(p.amount), 2) AS total_cash_remitted,
    ROUND(AVG(p.amount), 2) AS avg_check_amount,
    DENSE_RANK() OVER (ORDER BY SUM(p.amount) DESC) AS payment_rank
FROM customers c
JOIN payments p ON c.customerNumber = p.customerNumber
GROUP BY c.customerNumber, c.customerName, c.country, c.creditLimit
ORDER BY total_cash_remitted DESC
LIMIT 15;

-- ------------------------------------------------------------------------------
-- 4. Safe Account Reconciliation: Realized Order Value vs. Cash Collections Proxy
-- Pre-aggregates shipped order totals and payment totals at the customer grain,
-- then joins to compute Net Account Balance Proxy without multiplying rows.
-- ------------------------------------------------------------------------------
WITH customer_order_totals AS (
    SELECT 
        o.customerNumber,
        COUNT(DISTINCT o.orderNumber) AS shipped_orders_count,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_shipped_order_value
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY o.customerNumber
),
customer_payment_totals AS (
    SELECT 
        customerNumber,
        COUNT(checkNumber) AS payment_checks_count,
        ROUND(SUM(amount), 2) AS total_cash_collected
    FROM payments
    GROUP BY customerNumber
)
SELECT 
    c.customerNumber,
    c.customerName,
    c.country,
    c.creditLimit,
    COALESCE(cot.shipped_orders_count, 0) AS shipped_orders_count,
    COALESCE(cot.total_shipped_order_value, 0.00) AS total_shipped_order_value,
    COALESCE(cpt.payment_checks_count, 0) AS payment_checks_count,
    COALESCE(cpt.total_cash_collected, 0.00) AS total_cash_collected,
    ROUND(COALESCE(cot.total_shipped_order_value, 0.00) - COALESCE(cpt.total_cash_collected, 0.00), 2) AS net_outstanding_balance_proxy,
    CASE 
        WHEN COALESCE(cot.total_shipped_order_value, 0.00) > 0 
        THEN ROUND(COALESCE(cpt.total_cash_collected, 0.00) / cot.total_shipped_order_value * 100, 2)
        ELSE 100.00 
    END AS payment_coverage_pct
FROM customers c
LEFT JOIN customer_order_totals cot ON c.customerNumber = cot.customerNumber
LEFT JOIN customer_payment_totals cpt ON c.customerNumber = cpt.customerNumber
WHERE cot.total_shipped_order_value > 0 OR cpt.total_cash_collected > 0
ORDER BY net_outstanding_balance_proxy DESC;

-- ------------------------------------------------------------------------------
-- 5. High Outstanding Balance Exposure Accounts
-- Isolates accounts where shipped order value exceeds collected payments by over $10,000.
-- ------------------------------------------------------------------------------
WITH customer_order_totals AS (
    SELECT 
        o.customerNumber,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_shipped_order_value
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY o.customerNumber
),
customer_payment_totals AS (
    SELECT 
        customerNumber,
        ROUND(SUM(amount), 2) AS total_cash_collected
    FROM payments
    GROUP BY customerNumber
)
SELECT 
    c.customerNumber,
    c.customerName,
    c.country,
    c.creditLimit,
    cot.total_shipped_order_value,
    cpt.total_cash_collected,
    ROUND(cot.total_shipped_order_value - cpt.total_cash_collected, 2) AS net_exposure_amount
FROM customers c
JOIN customer_order_totals cot ON c.customerNumber = cot.customerNumber
JOIN customer_payment_totals cpt ON c.customerNumber = cpt.customerNumber
WHERE (cot.total_shipped_order_value - cpt.total_cash_collected) > 10000.00
ORDER BY net_exposure_amount DESC;
