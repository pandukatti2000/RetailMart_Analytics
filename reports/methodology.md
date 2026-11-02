# RetailMart 360: Analytical Methodology & Technical Reference

**Prepared by:** Senior Data Analyst & Analytics Consultant  
**Project:** RetailMart 360 — Retail Sales & Customer Intelligence  
**Document Purpose:** Technical methodology reference for data models, business formulas, segmentation algorithms, and data governance.

---

## 1. Relational Data Modeling & Grain Definitions

A core responsibility of a Senior Data Analyst is enforcing mathematical rigor across relational grains. In the RetailMart ecosystem, data exists across four distinct transactional and dimensional grains:

| Level | Table | Grain Definition | Primary Key | Key Fields |
| :--- | :--- | :--- | :--- | :--- |
| **Order Line** | `orderdetails` | 1 row per catalog SKU ordered within an order header (2,996 rows). | (`orderNumber`, `productCode`) | `quantityOrdered`, `priceEach`, `orderLineNumber` |
| **Order Header** | `orders` | 1 row per customer order transaction header (326 rows). | `orderNumber` | `orderDate`, `requiredDate`, `shippedDate`, `status`, `customerNumber` |
| **Customer Account** | `customers` | 1 row per registered business or retail entity (122 rows). | `customerNumber` | `customerName`, `city`, `country`, `creditLimit`, `salesRepEmployeeNumber` |
| **Remittance** | `payments` | 1 row per check payment received from a customer (273 rows). | (`customerNumber`, `checkNumber`) | `paymentDate`, `amount` |

---

## 2. Join Safety Rules & Avoiding the Fan-Out Trap

### The Fundamental Relational Pitfall
In this schema, **payments are NOT directly linked to order headers** (there is no `orderNumber` in the `payments` table). Payments are recorded against the customer account as a whole.

```
WRONG APPROACH (Cartesian Fan-Out):
SELECT SUM(od.quantityOrdered * od.priceEach), SUM(p.amount)
FROM customers c
JOIN orders o ON c.customerNumber = o.customerNumber
JOIN orderdetails od ON o.orderNumber = od.orderNumber
JOIN payments p ON c.customerNumber = p.customerNumber;
--> Multiplies revenue by the count of payments, and multiplies payments by the count of order lines!
```

### The Standardized Senior Analyst Solution:
Always aggregate `orderdetails` to the order header, then aggregate order totals to the customer grain. Separately, aggregate `payments` to the customer grain. Join the two pre-aggregated summaries on `customerNumber`.

```sql
WITH customer_orders AS (
    SELECT o.customerNumber, SUM(od.quantityOrdered * od.priceEach) AS total_shipped_rev
    FROM orders o
    JOIN orderdetails od ON o.orderNumber = od.orderNumber
    WHERE o.status = 'Shipped'
    GROUP BY o.customerNumber
),
customer_payments AS (
    SELECT customerNumber, SUM(amount) AS total_cash
    FROM payments
    GROUP BY customerNumber
)
SELECT c.customerNumber, co.total_shipped_rev, cp.total_cash, (co.total_shipped_rev - cp.total_cash) AS balance_proxy
FROM customers c
LEFT JOIN customer_orders co ON c.customerNumber = co.customerNumber
LEFT JOIN customer_payments cp ON c.customerNumber = cp.customerNumber;
```

---

## 3. Revenue Recognition & Profitability Policy

### 3.1. Shipped Realized Revenue Proxy
* In commercial reporting, orders marked as `Shipped` constitute realized analytical revenue ($8,865,094.64).
* Orders marked as `In Process`, `On Hold`, `Disputed`, `Resolved`, or `Cancelled` represent booked commitments ($9,604,190.61 total).
* By setting Shipped orders as our default analytical reporting standard, we avoid recognizing revenue on cancelled or unfulfilled orders while clearly reporting booked pipeline figures.

### 3.2. Estimated Gross Profit Proxy
* Factory unit cost is captured in `products.buyPrice`.
* Realized gross profit is calculated as:
  $$\text{Estimated Gross Profit} = \sum \text{quantityOrdered} \times (\text{priceEach} - \text{buyPrice})$$
* Margin Percentage is calculated as:
  $$\text{Estimated Gross Margin \%} = \frac{\text{Estimated Gross Profit}}{\text{Realized Revenue}} \times 100$$
* *Assumption Boundary:* `buyPrice` is a static catalog snapshot. It does not reflect historical purchase price variance (PPV), inbound ocean shipping costs, import tariffs, or holding costs. It serves as a gross merchandising contribution proxy.

---

## 4. RFM Customer Segmentation Algorithm

### 4.1. Reproducibility & Fixed Snapshot Date
To guarantee deterministic, reproducible segmentation across runs and tools, we benchmark Recency against a fixed date: **`2005-06-01`** (the first day after the last transaction in the dataset, `2005-05-31`).

### 4.2. Metric Formulations
* **Recency ($R$):** Days elapsed between `2005-06-01` and the customer's most recent shipped order date.
* **Frequency ($F$):** Total count of distinct shipped order numbers placed by the customer.
* **Monetary ($M$):** Cumulative realized shipped revenue placed by the customer.

### 4.3. Scoring Rules (Quartile / Quintile Bins)
* **$R\_Score$ (1 to 4):** Quantile-based (`pd.qcut` on recency days). Lower recency days receive higher scores (4 = most recent, 1 = least recent).
* **$F\_Score$ (1 to 4):** Retail frequency thresholds:
  - 1 order $\rightarrow$ Score 1
  - 2 orders $\rightarrow$ Score 2
  - 3 orders $\rightarrow$ Score 3
  - 4+ orders $\rightarrow$ Score 4
* **$M\_Score$ (1 to 4):** Quantile-based (`pd.qcut` on monetary revenue).

### 4.4. Segment Mapping Matrix
| Segment Name | Scoring Condition | Business Profile |
| :--- | :--- | :--- |
| **Champions** | $R \ge 3$, $F \ge 3$, $M \ge 3$ | High spenders, frequent orders, recently active. Premium VIP tier. |
| **Loyal Customers** | $R \ge 3$, $F \ge 2$ | Regular buyers with dependable purchase frequency. |
| **New / Potential Loyalists** | $R \ge 3$, $F = 1$ | High recency but single purchase. Prime targets for 2nd order conversion. |
| **High Value At Risk** | $R \le 2$, $F \ge 2$, $M \ge 3$ | Top lifetime spenders who have not purchased in >260 days. Immediate churn danger. |
| **Needs Attention** | $R = 2$, $F \le 2$ | Moderate spenders showing early dormancy signs. |
| **At Risk** | $R = 1$, $F \ge 2$ | Former repeat buyers with high dormancy (>350 days). |
| **Hibernating** | $R = 1$, $F = 1$, $M \le 2$ | Low spenders with ancient last purchase dates. |
| **Prospect / Inactive** | $F = 0$, $M = 0$ | Registered accounts that have never purchased. |

---

## 5. ABC Inventory Classification Methodology

* Based on the Pareto principle applied to cumulative realized shipped revenue:
  1. Aggregate total realized shipped revenue per catalog SKU.
  2. Sort products descending by revenue.
  3. Calculate cumulative revenue share:
     $$\text{Cum Share}_i = \frac{\sum_{k=1}^i \text{Revenue}_k}{\sum \text{Revenue}}$$
  4. Segment:
     - **Class A:** Cumulative share $\le 80.0\%$ (Top 60 SKUs, driving 79.8% of sales).
     - **Class B:** Cumulative share between $80.0\%$ and $95.0\%$ (29 SKUs, driving 15.1% of sales).
     - **Class C:** Cumulative share $> 95.0\%$ (Bottom 20 SKUs, driving 5.1% of sales).

---

## 6. AI Integration & Data Privacy Architecture

### Safe, Bounded Decision Co-Pilot Architecture
The OpenAI integration is deliberately decoupled from raw database transactions to ensure data privacy, speed, and mathematical truth:
1. **Zero Hallucination of Numbers:** All numerical calculations (sums, counts, averages, growth rates) are computed deterministically via Python/Pandas and verified via unit tests.
2. **Zero PII Exposure:** Raw customer names, street addresses, phone numbers, and employee email addresses are never transmitted to OpenAI.
3. **Structured Context Payloads:** Only high-level aggregated data summaries (e.g. monthly trend tables, segment breakdowns, top SKU rankings) are passed to the language model for interpretation and executive communication.
4. **Offline Resiliency:** When `OPENAI_API_KEY` is not present, the dashboard seamlessly displays clean deterministic data tables and fallback metrics without crashing or degrading user experience.
