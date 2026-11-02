-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 04_product_analysis.sql
-- Purpose: Product portfolio performance, estimated gross profit/margins, inventory health.
-- Dialect: MySQL 8.0+
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. Product Portfolio Performance & Profitability Ranking
-- Computes realized revenue, estimated gross profit, and gross margin percentage.
-- Note: buyPrice represents static acquisition cost proxy.
-- ------------------------------------------------------------------------------
SELECT 
    p.productCode,
    p.productName,
    p.productLine,
    p.productScale,
    p.quantityInStock,
    p.buyPrice,
    p.MSRP,
    SUM(od.quantityOrdered) AS total_units_sold,
    COUNT(DISTINCT od.orderNumber) AS orders_count,
    ROUND(AVG(od.priceEach), 2) AS avg_selling_price,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS realized_revenue,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS estimated_gross_profit,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) / SUM(od.quantityOrdered * od.priceEach) * 100, 2) AS gross_margin_pct,
    DENSE_RANK() OVER (ORDER BY SUM(od.quantityOrdered * od.priceEach) DESC) AS revenue_rank,
    DENSE_RANK() OVER (ORDER BY SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) DESC) AS profit_rank
FROM products p
JOIN orderdetails od ON p.productCode = od.productCode
JOIN orders o ON od.orderNumber = o.orderNumber
WHERE o.status = 'Shipped'
GROUP BY p.productCode, p.productName, p.productLine, p.productScale, p.quantityInStock, p.buyPrice, p.MSRP
ORDER BY realized_revenue DESC;

-- ------------------------------------------------------------------------------
-- 2. Inventory Velocity & Stock-to-Sales Demand Ratio
-- Benchmarks warehouse on-hand inventory against historical units sold.
-- Isolates:
--   a) Dead-Stock / Zero-Demand SKUs
--   b) Over-Stocked SKUs (Stock-to-Demand > 5.0)
--   c) Low-Stock Replenishment Risks (Stock-to-Demand < 0.20)
-- ------------------------------------------------------------------------------
WITH product_demand AS (
    SELECT 
        od.productCode,
        SUM(od.quantityOrdered) AS units_sold,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS historical_revenue
    FROM orderdetails od
    JOIN orders o ON od.orderNumber = o.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY od.productCode
)
SELECT 
    p.productCode,
    p.productName,
    p.productLine,
    p.quantityInStock,
    p.buyPrice,
    ROUND(p.quantityInStock * p.buyPrice, 2) AS inventory_carrying_value,
    COALESCE(pd.units_sold, 0) AS total_units_sold,
    CASE 
        WHEN pd.units_sold IS NULL OR pd.units_sold = 0 THEN 999.0
        ELSE ROUND(p.quantityInStock / pd.units_sold, 2)
    END AS stock_to_demand_ratio,
    CASE 
        WHEN pd.units_sold IS NULL OR pd.units_sold = 0 THEN 'Dead Stock (Zero Historical Orders)'
        WHEN (p.quantityInStock / pd.units_sold) > 5.0 THEN 'Severely Over-Stocked'
        WHEN (p.quantityInStock / pd.units_sold) < 0.25 THEN 'Low Stock Reorder Alert'
        ELSE 'Healthy Stock Range'
    END AS inventory_health_status
FROM products p
LEFT JOIN productdemand pd ON p.productCode = pd.productCode
ORDER BY stock_to_demand_ratio DESC;

-- ------------------------------------------------------------------------------
-- 3. Dead-Stock Inventory Case Study: 1985 Toyota Supra (S18_3233)
-- Examines catalog items that have never been ordered across the 2.4-year history.
-- ------------------------------------------------------------------------------
SELECT 
    p.productCode,
    p.productName,
    p.productLine,
    p.quantityInStock,
    p.buyPrice,
    p.MSRP,
    ROUND(p.quantityInStock * p.buyPrice, 2) AS tied_up_capital_cost,
    ROUND(p.quantityInStock * p.MSRP, 2) AS potential_retail_value,
    COUNT(od.orderNumber) AS total_orders_placed
FROM products p
LEFT JOIN orderdetails od ON p.productCode = od.productCode
GROUP BY p.productCode, p.productName, p.productLine, p.quantityInStock, p.buyPrice, p.MSRP
HAVING total_orders_placed = 0;

-- ------------------------------------------------------------------------------
-- 4. ABC Inventory & Revenue Contribution Classification
-- Categorizes products into A (top 80% revenue), B (next 15%), and C (bottom 5%).
-- ------------------------------------------------------------------------------
WITH product_revenue_ranked AS (
    SELECT 
        p.productCode,
        p.productName,
        p.productLine,
        SUM(od.quantityOrdered) AS units_sold,
        ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS realized_revenue,
        SUM(SUM(od.quantityOrdered * od.priceEach)) OVER () AS total_portfolio_revenue
    FROM products p
    JOIN orderdetails od ON p.productCode = od.productCode
    JOIN orders o ON od.orderNumber = o.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY p.productCode, p.productName, p.productLine
),
cumulative_shares AS (
    SELECT 
        productCode,
        productName,
        productLine,
        units_sold,
        realized_revenue,
        ROUND(realized_revenue / total_portfolio_revenue * 100, 2) AS revenue_share_pct,
        ROUND(
            SUM(realized_revenue) OVER (ORDER BY realized_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) 
            / total_portfolio_revenue * 100, 2
        ) AS cumulative_revenue_pct
    FROM product_revenue_ranked
)
SELECT 
    productCode,
    productName,
    productLine,
    units_sold,
    realized_revenue,
    revenue_share_pct,
    cumulative_revenue_pct,
    CASE 
        WHEN cumulative_revenue_pct <= 80.00 THEN 'Class A (Core 80%)'
        WHEN cumulative_revenue_pct <= 95.00 THEN 'Class B (Secondary 15%)'
        ELSE 'Class C (Long-Tail 5%)'
    END AS abc_classification
FROM cumulative_shares
ORDER BY realized_revenue DESC;

-- ------------------------------------------------------------------------------
-- 5. Manufacturing Partner (Vendor) Performance & Realized Margins
-- ------------------------------------------------------------------------------
SELECT 
    p.productVendor,
    COUNT(DISTINCT p.productCode) AS vendor_sku_count,
    SUM(od.quantityOrdered) AS total_units_sold,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS vendor_realized_revenue,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS vendor_estimated_profit,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) / SUM(od.quantityOrdered * od.priceEach) * 100, 2) AS vendor_gross_margin_pct
FROM products p
JOIN orderdetails od ON p.productCode = od.productCode
JOIN orders o ON od.orderNumber = o.orderNumber
WHERE o.status = 'Shipped'
GROUP BY p.productVendor
ORDER BY vendor_realized_revenue DESC;
