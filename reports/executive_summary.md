# RetailMart 360: Executive Project Summary

**Project Title:** RetailMart 360 — Retail Sales & Customer Intelligence  
**Role:** Senior Data Analyst, Analytics Consultant, BI Dashboard Designer  
**Scope:** Local Workspace Relational Data Analytics Platform  
**Target Audience:** Hiring Managers, C-Suite Stakeholders, Lead Data Analysts  

---

## 1. Project Mission & Business Context

**RetailMart 360** is a full-lifecycle commercial analytics and business intelligence solution developed on the Classic Models retail transactional database. The project was engineered to replicate the end-to-end deliverables of a Senior Data Analyst / Analytics Consultant:

1. **Relational Schema Audit & Cleaning:** Full audit of 8 relational tables (CSV & MySQL 8 dumps), rectifying ingestion anomalies (such as pandas parsing territory code `'NA'` as NaN), verifying primary/foreign key referential integrity (0 orphan records), and establishing strict join safety rules to prevent cross-product revenue duplication.
2. **Standardized KPI Framework:** Unified commercial formulas across SQL and Python to guarantee consistent figures for Realized Shipped Revenue ($8.87M), Estimated Gross Profit ($3.54M), and Gross Margin % (39.90%).
3. **Behavioral Customer Intelligence:** Reproducible RFM segmentation (8 distinct behavioral tiers) and Pareto (80/20) concentration analysis benchmarked against a fixed cutoff date of `2005-06-01`.
4. **Merchandising & Inventory Analytics:** ABC inventory classification (Classes A, B, C), stock-to-demand velocity ratios, and dead-stock capital exposure isolation.
5. **Interactive Executive BI Application:** Multi-page Streamlit application with interactive Plotly visualizations, responsive multi-variable filtering, and CSV export functionality.
6. **AI Decision Co-Pilot (OpenAI Integration):** Safe, bounded natural-language business explanations, chart interpretation co-pilots, and executive briefings powered by OpenAI when configured, while functioning independently via deterministic calculations when offline.

---

## 2. Key Business Metrics at a Glance

| Strategic Metric | Empirical Value | Analytical Context |
| :--- | :--- | :--- |
| **Total Realized Revenue (Shipped)** | **$8,865,094.64** | Realized sales proxy across 303 shipped orders. |
| **Total Booked Revenue (All Statuses)**| **$9,604,190.61** | Gross commitments across 326 total orders. |
| **Estimated Gross Profit** | **$3,536,929.17** | Realized markup over static factory `buyPrice` benchmark. |
| **Estimated Gross Margin %** | **39.90%** | Stable profit margin across the scale-model portfolio. |
| **Average Order Value (AOV)** | **$29,257.74** | Reflects wholesale / retail distributor purchase volume. |
| **Total Physical Units Sold** | **99,067 Units** | Across 109 ordered catalog SKUs. |
| **Active Purchasing Accounts** | **98 Accounts** | Out of 122 registered customer records (24 inactive prospects). |
| **Repeat Customer Rate** | **98.98%** | 97 repeat accounts; only 1 single-order account. |
| **Pareto Concentration (80% Revenue)**| **46 Accounts (46.9%)** | Top 10 accounts alone generate 27.2% of total sales ($2.41M). |
| **Average Shipping Fulfillment Time** | **3.76 Days** | 99.67% on-time SLA rate (1 late shipment out of 303). |
| **Total Cash Collections** | **$8,853,839.23** | 99.87% cash collection coverage against shipped orders. |

---

## 3. Top 4 Critical Strategic Discoveries

1. **Working Capital Frozen in Dead Stock ($456K):**  
   SKU `S18_3233` (*1985 Toyota Supra*, acquisition cost $58.98) has **7,733 units on hand** in the warehouse with **zero recorded orders** across the entire 2.4-year operating history. This single item traps **$456,092.34** in cash (12.4% of total inventory valuation).
2. **Immediate Customer Churn Vulnerability ($1.91M):**  
   14 high-spending customer accounts in the *High Value At Risk* RFM tier have not placed an order in over 260 days (avg recency 294 days), placing **21.6% of historical revenue** at risk.
3. **Core Automotive Product Engine (60.7% Share):**  
   *Classic Cars* ($3.58M, 40.4% share) and *Vintage Cars* ($1.80M, 20.3% share) generate over 60% of commercial sales with high ~41% gross margins.
4. **Credit Risk Concentration on Top Account ($105K Exposure):**  
   Top buyer *Euro+ Shopping Channel* carries a net uncollected balance proxy of **$104,950.56**, accounting for 93% of the company's net uncollected order value.

---

## 4. Technical Architecture & Technology Stack

* **SQL Analytics:** MySQL 8.0+ dialect (CTEs, recursive hierarchy queries, window functions: `ROW_NUMBER`, `DENSE_RANK`, `LAG`, `LEAD`, moving averages, pure SQL RFM).
* **Python Data Analysis:** Python 3.13, Pandas, NumPy, Matplotlib, Seaborn.
* **Testing & Data Validation:** Automated Pytest suite (`tests/test_metrics.py`) validating revenue formulas, join safety, and RFM scoring.
* **Interactive Dashboard:** Streamlit multi-page BI platform with Plotly charts.
* **AI Business Assistant:** Official OpenAI Python SDK (`gpt-4o-mini`) using bounded question catalogs and pre-aggregated KPI summaries.
