-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 03_customer_analysis.sql
-- Purpose: Customer intelligence, purchase frequency, lifetime value, and cohort distribution.
-- Dialect: MySQL 8.0+
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. Customer Base Overview: Active Buyers vs Inactive Prospects
-- ------------------------------------------------------------------------------
SELECT 
    COUNT(c.customerNumber) AS total_registered_customers,
    COUNT(DISTINCT o.customerNumber) AS active_purchasing_customers,
    COUNT(c.customerNumber) - COUNT(DISTINCT o.customerNumber) AS inactive_prospect_customers,
    ROUND(COUNT(DISTINCT o.customerNumber) / COUNT(c.customerNumber) * 100, 2) AS customer_conversion_rate_pct
FROM customers c
LEFT JOIN orders o ON c.customerNumber = o.customerNumber;

-- List inactive prospect accounts that have never placed an order
SELECT 
    c.customerNumber,
    c.customerName,
    c.city,
    c.country,
    c.creditLimit,
    e.employeeNumber AS assigned_sales_rep,
    CONCAT(e.firstName, ' ', e.lastName) AS sales_rep_name
FROM customers c
LEFT JOIN orders o ON c.customerNumber = o.customerNumber
LEFT JOIN employees e ON c.salesRepEmployeeNumber = e.employeeNumber
WHERE o.orderNumber IS NULL
ORDER BY c.country, c.customerName;

-- ------------------------------------------------------------------------------
-- 2. Customer Order Frequency & Repeat Purchase Analysis
-- Categorizes purchasing customers into Single-Order vs. Multi-Order Repeat Buyers.
-- ------------------------------------------------------------------------------
WITH customer_order_frequencies AS (
    SELECT 
        c.customerNumber,
        c.customerName,
        COUNT(DISTINCT o.orderNumber) AS total_orders,
        MIN(o.orderDate) AS first_order_date,
        MAX(o.orderDate) AS last_order_date,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_lifetime_revenue
    FROM customers c
    JOIN orders o ON c.customerNumber = o.customerNumber
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY c.customerNumber, c.customerName
)
SELECT 
    CASE 
        WHEN total_orders = 1 THEN '1 Order (One-Time Buyer)'
        WHEN total_orders = 2 THEN '2 Orders (Repeat Buyer)'
        WHEN total_orders BETWEEN 3 AND 4 THEN '3-4 Orders (Frequent Buyer)'
        ELSE '5+ Orders (VIP High-Frequency)'
    END AS purchase_frequency_tier,
    COUNT(customerNumber) AS customer_count,
    ROUND(COUNT(customerNumber) / SUM(COUNT(customerNumber)) OVER () * 100, 2) AS customer_share_pct,
    ROUND(SUM(total_lifetime_revenue), 2) AS total_revenue_contribution,
    ROUND(SUM(total_lifetime_revenue) / SUM(SUM(total_lifetime_revenue)) OVER () * 100, 2) AS revenue_share_pct,
    ROUND(AVG(total_lifetime_revenue), 2) AS avg_customer_lifetime_value
FROM customer_order_frequencies
GROUP BY 
    CASE 
        WHEN total_orders = 1 THEN '1 Order (One-Time Buyer)'
        WHEN total_orders = 2 THEN '2 Orders (Repeat Buyer)'
        WHEN total_orders BETWEEN 3 AND 4 THEN '3-4 Orders (Frequent Buyer)'
        ELSE '5+ Orders (VIP High-Frequency)'
    END
ORDER BY total_revenue_contribution DESC;

-- ------------------------------------------------------------------------------
-- 3. Customer Lifetime Value (CLV) & Cumulative Revenue Contribution (Pareto)
-- Calculates cumulative contribution percentage to evaluate 80/20 customer concentration.
-- ------------------------------------------------------------------------------
WITH customer_revenue_summary AS (
    SELECT 
        c.customerNumber,
        c.customerName,
        c.country,
        COUNT(DISTINCT o.orderNumber) AS order_count,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_clv_revenue,
        ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS estimated_gross_profit
    FROM customers c
    JOIN orders o ON c.customerNumber = o.customerNumber
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    JOIN products p ON od.productCode = p.productCode
    WHERE o.status = 'Shipped'
    GROUP BY c.customerNumber, c.customerName, c.country
),
ranked_customers AS (
    SELECT 
        customerNumber,
        customerName,
        country,
        order_count,
        total_clv_revenue,
        estimated_gross_profit,
        DENSE_RANK() OVER (ORDER BY total_clv_revenue DESC) AS sales_rank,
        SUM(total_clv_revenue) OVER (ORDER BY total_clv_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_cumulative_revenue,
        SUM(total_clv_revenue) OVER () AS overall_total_revenue
    FROM customer_revenue_summary
)
SELECT 
    sales_rank,
    customerNumber,
    customerName,
    country,
    order_count,
    total_clv_revenue,
    estimated_gross_profit,
    ROUND((estimated_gross_profit / total_clv_revenue) * 100, 2) AS gross_margin_pct,
    ROUND((running_cumulative_revenue / overall_total_revenue) * 100, 2) AS cumulative_revenue_pct
FROM ranked_customers
ORDER BY sales_rank;

-- ------------------------------------------------------------------------------
-- 4. Customer Credit Limit vs. Realized Purchasing Exposure
-- Identifies accounts where purchasing volume approaches or exceeds credit limits.
-- ------------------------------------------------------------------------------
SELECT 
    c.customerNumber,
    c.customerName,
    c.country,
    c.creditLimit,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_shipped_order_value,
    ROUND(SUM(od.quantityOrdered * od.priceEach) - c.creditLimit, 2) AS value_over_credit_limit,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / NULLIF(c.creditLimit, 0) * 100, 2) AS credit_utilization_proxy_pct
FROM customers c
JOIN orders o ON c.customerNumber = o.customerNumber
JOIN orderdetails od ON o.orderNumber = od.orderNumber
WHERE o.status = 'Shipped'
GROUP BY c.customerNumber, c.customerName, c.country, c.creditLimit
ORDER BY total_shipped_order_value DESC
LIMIT 15;

-- ------------------------------------------------------------------------------
-- 5. Sales Representative Account Assignment Distribution
-- Examines account distribution and revenue attribution per employee.
-- ------------------------------------------------------------------------------
SELECT 
    COALESCE(CONCAT(e.firstName, ' ', e.lastName), 'Unassigned / Direct') AS sales_representative,
    e.jobTitle,
    off.city AS office_city,
    COUNT(DISTINCT c.customerNumber) AS total_assigned_accounts,
    COUNT(DISTINCT CASE WHEN o.orderNumber IS NOT NULL THEN c.customerNumber END) AS active_ordering_accounts,
    COUNT(DISTINCT o.orderNumber) AS total_shipped_orders,
    ROUND(COALESCE(SUM(od.quantityOrdered * od.priceEach), 0), 2) AS attributed_shipped_revenue
FROM customers c
LEFT JOIN employees e ON c.salesRepEmployeeNumber = e.employeeNumber
LEFT JOIN offices off ON e.officeCode = off.officeCode
LEFT JOIN orders o ON c.customerNumber = o.customerNumber AND o.status = 'Shipped'
LEFT JOIN orderdetails od ON o.orderNumber = od.orderNumber
GROUP BY e.employeeNumber, e.firstName, e.lastName, e.jobTitle, off.city
ORDER BY attributed_shipped_revenue DESC;
