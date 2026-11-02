-- ==============================================================================
-- RetailMart 360: SQL Analytics Suite
-- File: 01_data_validation.sql
-- Purpose: Schema validation, primary/foreign key audits, missingness, and integrity checks.
-- Dialect: MySQL 8.0+
-- ==============================================================================

USE classicmodels;

-- ------------------------------------------------------------------------------
-- 1. Table Record Counts & Inventory Audit
-- Verifies row counts against source extraction benchmarks.
-- ------------------------------------------------------------------------------
SELECT 'customers' AS table_name, COUNT(*) AS total_records FROM customers
UNION ALL
SELECT 'employees', COUNT(*) FROM employees
UNION ALL
SELECT 'offices', COUNT(*) FROM offices
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'orderdetails', COUNT(*) FROM orderdetails
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'productlines', COUNT(*) FROM productlines
UNION ALL
SELECT 'products', COUNT(*) FROM products;

-- ------------------------------------------------------------------------------
-- 2. Primary Key Uniqueness & Null Checks
-- Ensures no duplicate or missing primary keys across transactional & dimension tables.
-- ------------------------------------------------------------------------------

-- Check customers PK
SELECT customerNumber, COUNT(*) AS occurrences
FROM customers
GROUP BY customerNumber
HAVING occurrences > 1 OR customerNumber IS NULL;

-- Check employees PK
SELECT employeeNumber, COUNT(*) AS occurrences
FROM employees
GROUP BY employeeNumber
HAVING occurrences > 1 OR employeeNumber IS NULL;

-- Check offices PK
SELECT officeCode, COUNT(*) AS occurrences
FROM offices
GROUP BY officeCode
HAVING occurrences > 1 OR officeCode IS NULL;

-- Check orders PK
SELECT orderNumber, COUNT(*) AS occurrences
FROM orders
GROUP BY orderNumber
HAVING occurrences > 1 OR orderNumber IS NULL;

-- Check orderdetails Composite PK (orderNumber, productCode)
SELECT orderNumber, productCode, COUNT(*) AS occurrences
FROM orderdetails
GROUP BY orderNumber, productCode
HAVING occurrences > 1 OR orderNumber IS NULL OR productCode IS NULL;

-- Check payments Composite PK (customerNumber, checkNumber)
SELECT customerNumber, checkNumber, COUNT(*) AS occurrences
FROM payments
GROUP BY customerNumber, checkNumber
HAVING occurrences > 1 OR customerNumber IS NULL OR checkNumber IS NULL;

-- Check products PK
SELECT productCode, COUNT(*) AS occurrences
FROM products
GROUP BY productCode
HAVING occurrences > 1 OR productCode IS NULL;

-- ------------------------------------------------------------------------------
-- 3. Foreign Key Referential Integrity & Orphan Record Checks
-- Verifies parent-child relationship integrity across the relational model.
-- ------------------------------------------------------------------------------

-- 3.1. Customers to Employees (Sales Rep)
SELECT 'customers_without_valid_salesrep' AS check_type, COUNT(*) AS orphan_count
FROM customers c
LEFT JOIN employees e ON c.salesRepEmployeeNumber = e.employeeNumber
WHERE c.salesRepEmployeeNumber IS NOT NULL AND e.employeeNumber IS NULL;

-- 3.2. Orders to Customers
SELECT 'orders_without_valid_customer' AS check_type, COUNT(*) AS orphan_count
FROM orders o
LEFT JOIN customers c ON o.customerNumber = c.customerNumber
WHERE c.customerNumber IS NULL;

-- 3.3. Order Details to Orders
SELECT 'orderdetails_without_valid_order' AS check_type, COUNT(*) AS orphan_count
FROM orderdetails od
LEFT JOIN orders o ON od.orderNumber = o.orderNumber
WHERE o.orderNumber IS NULL;

-- 3.4. Order Details to Products
SELECT 'orderdetails_without_valid_product' AS check_type, COUNT(*) AS orphan_count
FROM orderdetails od
LEFT JOIN products p ON od.productCode = p.productCode
WHERE p.productCode IS NULL;

-- 3.5. Products to Product Lines
SELECT 'products_without_valid_line' AS check_type, COUNT(*) AS orphan_count
FROM products p
LEFT JOIN productlines pl ON p.productLine = pl.productLine
WHERE pl.productLine IS NULL;

-- 3.6. Payments to Customers
SELECT 'payments_without_valid_customer' AS check_type, COUNT(*) AS orphan_count
FROM payments py
LEFT JOIN customers c ON py.customerNumber = c.customerNumber
WHERE c.customerNumber IS NULL;

-- ------------------------------------------------------------------------------
-- 4. Date Validation & Chronological Boundaries
-- Identifies invalid dates, date anomalies, and chronological bounds.
-- ------------------------------------------------------------------------------
SELECT 
    'orders.orderDate' AS date_field,
    MIN(orderDate) AS earliest_date,
    MAX(orderDate) AS latest_date,
    COUNT(CASE WHEN orderDate IS NULL THEN 1 END) AS missing_dates
FROM orders
UNION ALL
SELECT 
    'orders.requiredDate',
    MIN(requiredDate),
    MAX(requiredDate),
    COUNT(CASE WHEN requiredDate IS NULL THEN 1 END)
FROM orders
UNION ALL
SELECT 
    'orders.shippedDate',
    MIN(shippedDate),
    MAX(shippedDate),
    COUNT(CASE WHEN shippedDate IS NULL THEN 1 END)
FROM orders
UNION ALL
SELECT 
    'payments.paymentDate',
    MIN(paymentDate),
    MAX(paymentDate),
    COUNT(CASE WHEN paymentDate IS NULL THEN 1 END)
FROM payments;

-- ------------------------------------------------------------------------------
-- 5. Business Logic & Anomaly Checks
-- Checks for negative monetary values, zero quantities, and impossible conditions.
-- ------------------------------------------------------------------------------
SELECT 
    COUNT(CASE WHEN quantityOrdered <= 0 THEN 1 END) AS non_positive_quantities,
    COUNT(CASE WHEN priceEach <= 0 THEN 1 END) AS non_positive_prices
FROM orderdetails;

SELECT 
    COUNT(CASE WHEN amount <= 0 THEN 1 END) AS non_positive_payments
FROM payments;

SELECT 
    COUNT(CASE WHEN quantityInStock < 0 THEN 1 END) AS negative_stock_count,
    COUNT(CASE WHEN buyPrice <= 0 THEN 1 END) AS non_positive_buyprice,
    COUNT(CASE WHEN MSRP < buyPrice THEN 1 END) AS msrp_below_cost_count
FROM products;

-- Verify shipping dates occurring BEFORE order placement (impossible chronological paradox)
SELECT orderNumber, orderDate, shippedDate, status
FROM orders
WHERE shippedDate < orderDate;
