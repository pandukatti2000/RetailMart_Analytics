-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 08_advanced_analytics.sql
-- Purpose: Advanced analytical SQL showcasing CTEs, Window Functions, Rolling Averages,
--          Multi-table joins, and End-to-End Pure SQL RFM Customer Segmentation.
-- Dialect: MySQL 8.0+
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. 3-Month Rolling Average Revenue & Running Cumulative Sales
-- Combines LAG, Moving Averages (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
-- and Running Totals to smooth month-to-month volatility.
-- ------------------------------------------------------------------------------
WITH monthly_data AS (
    SELECT 
        DATE_FORMAT(o.orderDate, '%Y-%m') AS order_year_month,
        COUNT(DISTINCT o.orderNumber) AS orders_count,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS monthly_revenue
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY DATE_FORMAT(o.orderDate, '%Y-%m')
)
SELECT 
    order_year_month,
    orders_count,
    monthly_revenue,
    -- Running Cumulative Total
    ROUND(SUM(monthly_revenue) OVER (ORDER BY order_year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_cumulative_revenue,
    -- 3-Month Moving Average (Current month + 2 prior months)
    ROUND(AVG(monthly_revenue) OVER (ORDER BY order_year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS three_month_moving_avg_revenue,
    -- Prior Month Revenue
    LAG(monthly_revenue, 1) OVER (ORDER BY order_year_month) AS prior_month_revenue,
    -- Subsequent Month Revenue (Forward visibility)
    LEAD(monthly_revenue, 1) OVER (ORDER BY order_year_month) AS next_month_revenue
FROM monthly_data
ORDER BY order_year_month;

-- ------------------------------------------------------------------------------
-- 2. Top Product per Product Line using ROW_NUMBER()
-- Partitions by category to isolate the #1 best-selling SKU in every single line.
-- ------------------------------------------------------------------------------
WITH product_sales AS (
    SELECT 
        p.productLine,
        p.productCode,
        p.productName,
        SUM(od.quantityOrdered) AS units_sold,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS realized_revenue,
        ROW_NUMBER() OVER (PARTITION BY p.productLine ORDER BY SUM(od.quantityOrdered * od.priceEach) DESC) AS category_rank
    FROM products p
    JOIN orderdetails od ON p.productCode = od.productCode
    JOIN orders o ON od.orderNumber = o.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY p.productLine, p.productCode, p.productName
)
SELECT 
    productLine,
    productCode,
    productName,
    units_sold,
    realized_revenue
FROM product_sales
WHERE category_rank = 1
ORDER BY realized_revenue DESC;

-- ------------------------------------------------------------------------------
-- 3. Pure SQL Customer RFM Segmentation
-- Reproducible RFM scoring using benchmark cutoff date '2005-06-01'.
-- Scores Recency (NTILE), Frequency (CASE), and Monetary (NTILE) to build 8 actionable segments.
-- ------------------------------------------------------------------------------
WITH customer_raw_rfm AS (
    SELECT 
        c.customerNumber,
        c.customerName,
        c.country,
        -- Recency: Days between benchmark '2005-06-01' and customer's latest shipped order
        DATEDIFF('2005-06-01', MAX(o.orderDate)) AS recency_days,
        -- Frequency: Distinct count of shipped orders
        COUNT(DISTINCT o.orderNumber) AS frequency_orders,
        -- Monetary: Total realized revenue
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS monetary_value
    FROM customers c
    JOIN orders o ON c.customerNumber = o.customerNumber
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY c.customerNumber, c.customerName, c.country
),
rfm_scored AS (
    SELECT 
        customerNumber,
        customerName,
        country,
        recency_days,
        frequency_orders,
        monetary_value,
        -- R_Score: 4 = Most Recent, 1 = Least Recent (using NTILE 4)
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
        -- F_Score: Rule-based bins matching retail behavior (1 = 1 order, 2 = 2 orders, 3 = 3 orders, 4 = 4+ orders)
        CASE 
            WHEN frequency_orders = 1 THEN 1
            WHEN frequency_orders = 2 THEN 2
            WHEN frequency_orders = 3 THEN 3
            ELSE 4
        END AS f_score,
        -- M_Score: 4 = Highest Monetary, 1 = Lowest Monetary (using NTILE 4)
        NTILE(4) OVER (ORDER BY monetary_value ASC) AS m_score
    FROM customer_raw_rfm
),
rfm_segmented AS (
    SELECT 
        customerNumber,
        customerName,
        country,
        recency_days,
        frequency_orders,
        monetary_value,
        r_score,
        f_score,
        m_score,
        CONCAT(r_score, f_score, m_score) AS rfm_code,
        CASE 
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 2 THEN 'Loyal Customers'
            WHEN r_score >= 3 AND f_score = 1 THEN 'New / Potential Loyalists'
            WHEN r_score = 2 AND f_score >= 2 AND m_score >= 3 THEN 'High Value At Risk'
            WHEN r_score = 2 THEN 'Needs Attention'
            WHEN r_score = 1 AND m_score >= 3 THEN 'High Value At Risk'
            WHEN r_score = 1 AND f_score >= 2 THEN 'At Risk'
            ELSE 'Hibernating'
        END AS customer_segment
    FROM rfm_scored
)
SELECT 
    customer_segment,
    COUNT(*) AS customer_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 2) AS segment_share_pct,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(frequency_orders), 1) AS avg_order_frequency,
    ROUND(SUM(monetary_value), 2) AS total_segment_revenue,
    ROUND(SUM(monetary_value) / SUM(SUM(monetary_value)) OVER () * 100, 2) AS revenue_share_pct,
    ROUND(AVG(monetary_value), 2) AS avg_customer_value
FROM rfm_segmented
GROUP BY customer_segment
ORDER BY total_segment_revenue DESC;

-- ------------------------------------------------------------------------------
-- 4. Cross-Fulfillment Fulfillment Cycle Time & Late Shipment Bottlenecks
-- Analyzes order SLA compliance, shipping delay distribution, and duration quantiles.
-- ------------------------------------------------------------------------------
SELECT 
    o.orderNumber,
    o.orderDate,
    o.requiredDate,
    o.shippedDate,
    DATEDIFF(o.shippedDate, o.orderDate) AS fulfillment_duration_days,
    DATEDIFF(o.shippedDate, o.requiredDate) AS days_relative_to_deadline,
    CASE 
        WHEN o.shippedDate > o.requiredDate THEN 'Late Shipment SLA Breach'
        ELSE 'On-Time SLA Compliant'
    END AS sla_compliance_status,
    c.customerName,
    c.country
FROM orders o
JOIN customers c ON o.customerNumber = c.customerNumber
WHERE o.status = 'Shipped' AND o.shippedDate > o.requiredDate;
