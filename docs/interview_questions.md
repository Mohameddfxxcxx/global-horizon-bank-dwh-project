# Senior Data Engineering / Analytics Interview Bank

A curated set of advanced questions, mapped to the design choices made in this platform. Use as study material or as a recruiter probe sheet.

---

## A. Dimensional Modeling

**1. When would you choose a snowflake schema over a star?**
When dimensions have very high cardinality with stable hierarchies (geo) and storage cost matters. Star is faster for joins; snowflake is more normalized but costs analytical query speed. We chose **star** because executive query latency dominates storage cost.

**2. Explain SCD Type 2 and where you used it.**
We track `Dim_Customer` history with `EffectiveDate`, `ExpirationDate`, `IsCurrent`. When a customer relocates, the prior row is expired and a new row inserted. Fact joins resolve via the surrogate `CustomerKey` so historical reports remain accurate.

**3. What is a factless fact?**
A fact table that records the existence of an event with no measure — e.g., `Factless_BranchVisit`. Useful for coverage analysis ("which customers haven't visited any branch this quarter?").

**4. Why surrogate keys?**
They insulate fact joins from changes in the source system business key, support SCD2, and are smaller integers improving join performance.

**5. What's a junk dimension?**
A dimension that combines several low-cardinality flags (weekend, high-value, channel) to avoid bloating the fact table with multiple boolean columns.

---

## B. Performance

**6. When are columnstore indexes appropriate?**
For analytical workloads scanning millions of rows with aggregation. They compress 10–40× and are read in batches. We use a clustered columnstore on `Fact_Transaction`.

**7. Difference between partition pruning and partition elimination.**
Same concept — the query optimizer skips partitions that can't satisfy the predicate. We partition `Fact_Transaction` by `DateKey` so date-bounded queries scan only relevant year partitions.

**8. What is a covering index?**
A non-clustered index that includes all columns referenced by the query, eliminating bookmark lookups. We use `IX_FactTransaction_DateKey INCLUDE (Amount, TransactionType)`.

**9. How would you diagnose a slow analytical query?**
`SET STATISTICS IO, TIME ON`, inspect actual execution plan, look for scans where seeks were expected, parameter-sniffing skew, missing stats, and tempdb pressure.

---

## C. ETL & Pipelines

**10. Idempotent loads — how?**
`NOT EXISTS` guards in dimension loaders, MERGE for SCD2, deterministic surrogate generation, and an immutable Bronze zone we can replay from.

**11. How do you detect schema drift?**
Bronze records column hash + ingestion timestamp; Silver validates against expected schema. Drift produces a critical issue blocking promotion to Gold.

**12. What's a late-arriving dimension?**
A fact arrives before its dimension key exists. We keep an `UNKNOWN` placeholder (CustomerID = -1) and replay the fact when the dim row arrives.

---

## D. Banking Domain

**13. Define NIM, NPL, and NFI.**
- **NIM (Net Interest Margin):** (Interest income − Interest expense) / Avg earning assets.
- **NPL (Non-Performing Loan ratio):** Defaulted principal / Total principal.
- **NFI (Non-Funded Income):** Fee income share — diversification metric.

**14. How would you detect transaction structuring?**
Customers issuing many transactions just below a regulatory threshold (e.g., 9000–9999) on the same day. We flag it in `01_fraud_detection.sql`.

**15. What does Benford's Law tell you about fraud?**
Genuine financial figures follow a logarithmic distribution of leading digits. Significant deviation suggests fabricated numbers.

---

## E. SQL Mastery

**16. Window function vs GROUP BY?**
Window keeps row-level grain while computing partitioned aggregates. GROUP BY collapses to one row per group.

**17. Show me a recursive CTE.**
See `02_churn_cohort.sql` — generates monthly cohort buckets across full history.

**18. RANK vs DENSE_RANK vs ROW_NUMBER?**
- ROW_NUMBER: unique sequential.
- RANK: gaps after ties.
- DENSE_RANK: no gaps after ties.

---

## F. Governance

**19. What is RLS?**
Row-Level Security — table-level filter predicate enforces row visibility based on session context. We bound tellers to their `BranchID`.

**20. Difference between dynamic data masking and encryption?**
Masking is a presentation-layer obfuscation; the underlying data is unchanged. Encryption transforms storage; only key holders can read.

---

## G. ML / AI

**21. How would you evaluate a churn model?**
ROC-AUC, precision/recall at the operating threshold, lift at top-K decile. For business: revenue retained per intervention.

**22. Why Isolation Forest for fraud?**
Unsupervised, performs well in high-dimensional sparse anomaly detection, no need for labeled fraud data.

**23. K-Means vs DBSCAN for segmentation?**
K-Means: globular clusters, fast, requires `k`. DBSCAN: arbitrary shapes, handles noise, no `k` but parameter-sensitive.

---

## H. Architecture

**24. Why medallion (Bronze/Silver/Gold)?**
Separation of concerns: raw immutability (Bronze), conformed quality (Silver), business-ready (Gold). Enables replay, lineage, and clear SLAs per zone.

**25. Build vs buy for a data warehouse?**
Build for unique business logic and competitive differentiation; buy for commodity infrastructure (storage, orchestration). We built modeling and analytics; we use SQL Server, Docker, and scikit-learn off-the-shelf.

---

## I. System Design Scenario

> *"Design a real-time fraud scoring system for 10K txn/s."*

Components: Kafka ingest → stream processor (Flink/Spark Structured Streaming) computing rolling features → low-latency feature store → model service (FastAPI) → decision engine → action queue (block/notify). Persistence: Bronze (Kafka topic dump), Silver (parquet on S3), Gold (DWH). Observability: Prometheus + Grafana on latency, hit-rate, false-positive-rate.

---

## J. Behavioral / Stakeholder

**26. How do you handle KPI definition disputes?**
Bring all stakeholders to the semantic layer view. The view is the contract; if the formula is wrong we change it once, in one place, and notify consumers.

**27. Tell me about a difficult data quality issue.**
Use the STAR framework. Reference the validation framework + DQ scoring as your durable mechanism.
