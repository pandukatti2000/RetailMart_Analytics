-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 02_sales_analysis.sql
-- Purpose: Commercial sales performance, revenue trends, AOV, MoM/YoY growth.
-- Dialect: MySQL 8.0+
-- Policy: Shipped orders represent realized sales; all statuses represent booked sales.
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. Executive Revenue Summary: Realized vs. Booked Sales
-- Demonstrates the exact financial impact of order status inclusion/exclusion.
-- ------------------------------------------------------------------------------
SELECT 
    o.status AS order_status,
    COUNT(DISTINCT o.orderNumber) AS orders_count,
    COUNT(od.orderLineNumber) AS line_items_count,
    SUM(od.quantityOrdered) AS total_units_sold,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / SUM(SUM(od.quantityOrdered * od.priceEach)) OVER () * 100, 2) AS revenue_share_pct
FROM orders o
JOIN orderdetails od ON o.orderNumber = od.orderNumber
GROUP BY o.status
ORDER BY total_revenue DESC;

-- Total Realized Revenue (Shipped Orders Proxy)
SELECT 
    'Realized Sales (Shipped Only)' AS revenue_metric,
    COUNT(DISTINCT o.orderNumber) AS total_orders,
    SUM(od.quantityOrdered) AS total_units_sold,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / COUNT(DISTINCT o.orderNumber), 2) AS average_order_value
FROM orders o
JOIN orderdetails od ON o.orderNumber = od.orderNumber
WHERE o.status = 'Shipped';

-- ------------------------------------------------------------------------------
-- 2. Monthly Revenue Trend & Month-over-Month (MoM) Growth
-- Utilizes Window Function LAG() to calculate sequential commercial growth.
-- ------------------------------------------------------------------------------
WITH monthly_sales AS (
    SELECT 
        DATE_FORMAT(o.orderDate, '%Y-%m') AS order_year_month,
        COUNT(DISTINCT o.orderNumber) AS orders_count,
        SUM(od.quantityOrdered) AS units_sold,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS monthly_revenue,
        ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS estimated_gross_profit
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    JOIN products p ON od.productCode = p.productCode
    WHERE o.status = 'Shipped'
    GROUP BY DATE_FORMAT(o.orderDate, '%Y-%m')
)
SELECT 
    order_year_month,
    orders_count,
    units_sold,
    monthly_revenue,
    LAG(monthly_revenue, 1) OVER (ORDER BY order_year_month) AS prior_month_revenue,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY order_year_month)) 
        / LAG(monthly_revenue, 1) OVER (ORDER BY order_year_month) * 100, 2
    ) AS mom_growth_pct,
    ROUND(monthly_revenue / orders_count, 2) AS average_order_value,
    estimated_gross_profit,
    ROUND((estimated_gross_profit / monthly_revenue) * 100, 2) AS estimated_gross_margin_pct
FROM monthly_sales
ORDER BY order_year_month;

-- ------------------------------------------------------------------------------
-- 3. Yearly Revenue Trend & Year-over-Year (YoY) Growth
-- Note: 2005 reflects an incomplete reporting period (January through May).
-- ------------------------------------------------------------------------------
WITH yearly_sales AS (
    SELECT 
        YEAR(o.orderDate) AS order_year,
        COUNT(DISTINCT o.orderNumber) AS orders_count,
        SUM(od.quantityOrdered) AS units_sold,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS yearly_revenue,
        ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS yearly_gross_profit
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    JOIN products p ON od.productCode = p.productCode
    WHERE o.status = 'Shipped'
    GROUP BY YEAR(o.orderDate)
)
SELECT 
    order_year,
    orders_count,
    units_sold,
    yearly_revenue,
    LAG(yearly_revenue, 1) OVER (ORDER BY order_year) AS prior_year_revenue,
    ROUND(
        (yearly_revenue - LAG(yearly_revenue, 1) OVER (ORDER BY order_year)) 
        / LAG(yearly_revenue, 1) OVER (ORDER BY order_year) * 100, 2
    ) AS yoy_growth_pct,
    ROUND(yearly_revenue / orders_count, 2) AS average_order_value,
    yearly_gross_profit,
    ROUND((yearly_gross_profit / yearly_revenue) * 100, 2) AS gross_margin_pct
FROM yearly_sales
ORDER BY order_year;

-- ------------------------------------------------------------------------------
-- 4. Best and Worst Performing Calendar Months (Seasonality Benchmark)
-- ------------------------------------------------------------------------------
WITH monthly_ranked AS (
    SELECT 
        DATE_FORMAT(o.orderDate, '%Y-%m') AS order_year_month,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS monthly_revenue,
        COUNT(DISTINCT o.orderNumber) AS orders_count,
        ROW_NUMBER() OVER (ORDER BY SUM(od.quantityOrdered * od.priceEach) DESC) AS rank_desc,
        ROW_NUMBER() OVER (ORDER BY SUM(od.quantityOrdered * od.priceEach) ASC) AS rank_asc
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY DATE_FORMAT(o.orderDate, '%Y-%m')
)
SELECT 
    'Top 3 Peak Months' AS performance_tier,
    rank_desc AS performance_rank,
    order_year_month,
    monthly_revenue,
    orders_count
FROM monthly_ranked
WHERE rank_desc <= 3
UNION ALL
SELECT 
    'Bottom 3 Trough Months',
    rank_asc,
    order_year_month,
    monthly_revenue,
    orders_count
FROM monthly_ranked
WHERE rank_asc <= 3
ORDER BY performance_tier, performance_rank;

-- ------------------------------------------------------------------------------
-- 5. Revenue by Product Line
-- Evaluates portfolio contribution across all 7 scale-model product lines.
-- ------------------------------------------------------------------------------
SELECT 
    p.productLine,
    COUNT(DISTINCT p.productCode) AS catalog_products_count,
    COUNT(DISTINCT od.orderNumber) AS orders_count,
    SUM(od.quantityOrdered) AS units_sold,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / SUM(SUM(od.quantityOrdered * od.priceEach)) OVER () * 100, 2) AS revenue_share_pct,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS estimated_gross_profit,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) / SUM(od.quantityOrdered * od.priceEach) * 100, 2) AS gross_margin_pct
FROM products p
JOIN orderdetails od ON p.productCode = od.productCode
JOIN orders o ON od.orderNumber = o.orderNumber
WHERE o.status = 'Shipped'
GROUP BY p.productLine
ORDER BY total_revenue DESC;

-- ------------------------------------------------------------------------------
-- 6. Top 10 Customers by Realized Sales
-- ------------------------------------------------------------------------------
SELECT 
    c.customerNumber,
    c.customerName,
    c.country,
    COUNT(DISTINCT o.orderNumber) AS total_orders,
    SUM(od.quantityOrdered) AS total_units_ordered,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / COUNT(DISTINCT o.orderNumber), 2) AS aov,
    DENSE_RANK() OVER (ORDER BY SUM(od.quantityOrdered * od.priceEach) DESC) AS customer_rank
FROM customers c
JOIN orders o ON c.customerNumber = o.customerNumber
JOIN orderdetails od ON o.orderNumber = od.orderNumber
WHERE o.status = 'Shipped'
GROUP BY c.customerNumber, c.customerName, c.country
ORDER BY total_revenue DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- 7. Top 10 Products by Realized Sales
-- ------------------------------------------------------------------------------
SELECT 
    p.productCode,
    p.productName,
    p.productLine,
    SUM(od.quantityOrdered) AS units_sold,
    ROUND(AVG(od.priceEach), 2) AS avg_selling_price,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_revenue,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS estimated_gross_profit,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) / SUM(od.quantityOrdered * od.priceEach) * 100, 2) AS gross_margin_pct,
    DENSE_RANK() OVER (ORDER BY SUM(od.quantityOrdered * od.priceEach) DESC) AS product_sales_rank
FROM products p
JOIN orderdetails od ON p.productCode = od.productCode
JOIN orders o ON od.orderNumber = o.orderNumber
WHERE o.status = 'Shipped'
GROUP BY p.productCode, p.productName, p.productLine, p.buyPrice
ORDER BY total_revenue DESC
LIMIT 10;
