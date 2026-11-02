-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 05_regional_analysis.sql
-- Purpose: Geographic market penetration, country rankings, office vs customer geography.
-- Dialect: MySQL 8.0+
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. Sales by Customer Sovereign Market (Customer Country)
-- Measures end-market customer demand across 28 global countries.
-- ------------------------------------------------------------------------------
SELECT 
    c.country AS customer_country,
    COUNT(DISTINCT c.customerNumber) AS total_customers_in_market,
    COUNT(DISTINCT CASE WHEN o.orderNumber IS NOT NULL THEN c.customerNumber END) AS active_purchasers,
    COUNT(DISTINCT o.orderNumber) AS orders_count,
    SUM(od.quantityOrdered) AS units_sold,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS total_realized_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / SUM(SUM(od.quantityOrdered * od.priceEach)) OVER () * 100, 2) AS market_share_pct,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS estimated_gross_profit,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) / SUM(od.quantityOrdered * od.priceEach) * 100, 2) AS gross_margin_pct,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / COUNT(DISTINCT o.orderNumber), 2) AS market_aov,
    DENSE_RANK() OVER (ORDER BY SUM(od.quantityOrdered * od.priceEach) DESC) AS country_rank
FROM customers c
LEFT JOIN orders o ON c.customerNumber = o.customerNumber AND o.status = 'Shipped'
LEFT JOIN orderdetails od ON o.orderNumber = od.orderNumber
LEFT JOIN products p ON od.productCode = p.productCode
GROUP BY c.country
ORDER BY total_realized_revenue DESC;

-- ------------------------------------------------------------------------------
-- 2. Sales by Regional Sales Office Location
-- Evaluates the 7 physical retail offices where sales reps reside.
-- ------------------------------------------------------------------------------
SELECT 
    off.officeCode,
    off.city AS office_city,
    off.country AS office_country,
    off.territory AS office_territory,
    COUNT(DISTINCT e.employeeNumber) AS assigned_staff_count,
    COUNT(DISTINCT c.customerNumber) AS managed_customer_accounts,
    COUNT(DISTINCT o.orderNumber) AS fulfilled_orders,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS office_attributed_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / SUM(SUM(od.quantityOrdered * od.priceEach)) OVER () * 100, 2) AS office_revenue_share_pct,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)), 2) AS office_gross_profit,
    ROUND(SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) / SUM(od.quantityOrdered * od.priceEach) * 100, 2) AS office_gross_margin_pct
FROM offices off
JOIN employees e ON off.officeCode = e.officeCode
JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber
JOIN orders o ON c.customerNumber = o.customerNumber
JOIN orderdetails od ON o.orderNumber = od.orderNumber
JOIN products p ON od.productCode = p.productCode
WHERE o.status = 'Shipped'
GROUP BY off.officeCode, off.city, off.country, off.territory
ORDER BY office_attributed_revenue DESC;

-- ------------------------------------------------------------------------------
-- 3. Office Operating Territory Contribution (NA, EMEA, APAC, Japan)
-- Aggregates performance by corporate theater of operations.
-- ------------------------------------------------------------------------------
SELECT 
    off.territory AS operating_territory,
    COUNT(DISTINCT off.officeCode) AS operating_offices_count,
    COUNT(DISTINCT e.employeeNumber) AS sales_reps_count,
    COUNT(DISTINCT c.customerNumber) AS active_accounts,
    COUNT(DISTINCT o.orderNumber) AS orders_count,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS territory_revenue,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / SUM(SUM(od.quantityOrdered * od.priceEach)) OVER () * 100, 2) AS territory_share_pct,
    ROUND(SUM(od.quantityOrdered * od.priceEach) / COUNT(DISTINCT o.orderNumber), 2) AS territory_aov
FROM offices off
JOIN employees e ON off.officeCode = e.officeCode
JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber
JOIN orders o ON c.customerNumber = o.customerNumber
JOIN orderdetails od ON o.orderNumber = od.orderNumber
WHERE o.status = 'Shipped'
GROUP BY off.territory
ORDER BY territory_revenue DESC;

-- ------------------------------------------------------------------------------
-- 4. Geographic Cross-Flow: Office Geography vs. Customer Sovereign Territory
-- Highlights international account distribution managed across regional hubs.
-- ------------------------------------------------------------------------------
SELECT 
    off.city AS sales_office_city,
    off.country AS office_country,
    c.country AS client_customer_country,
    COUNT(DISTINCT c.customerNumber) AS active_client_count,
    ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS cross_border_revenue
FROM offices off
JOIN employees e ON off.officeCode = e.officeCode
JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber
JOIN orders o ON c.customerNumber = o.customerNumber
JOIN orderdetails od ON o.orderNumber = od.orderNumber
WHERE o.status = 'Shipped'
GROUP BY off.city, off.country, c.country
ORDER BY off.city, cross_border_revenue DESC;
