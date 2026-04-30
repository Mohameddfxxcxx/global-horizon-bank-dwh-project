# SQL Implementation Guide

This document is the operator's manual for executing the SQL layer of the Global Horizon Bank platform. It defines the run order, prerequisites, and the architectural reasoning behind each script.

---

## Execution Order

| # | Script | DB | Purpose |
|---|---|---|---|
| 1 | `sql/oltp/01_ddl_oltp.sql` | OLTP | Create database + 3NF schema |
| 2 | `sql/oltp/02_dml_oltp.sql` | OLTP | Workload simulation + bulk-import templates |
| 3 | `sql/oltp/03_queries_oltp.sql` | OLTP | OLTP limitations demonstration |
| 4 | `sql/oltp/04_constraints_triggers.sql` | OLTP | Triggers, audit schema, business CHECKs |
| 5 | `sql/oltp/05_stored_procedures.sql` | OLTP | Money-movement and account procs |
| 6 | `sql/oltp/06_security_rbac.sql` | OLTP | Roles, RLS, dynamic masking |
| 7 | `sql/olap/01_ddl_star_schema.sql` | DWH | Core star schema |
| 8 | `sql/olap/02_advanced_modeling.sql` | DWH | SCD2 demonstration |
| 9 | `sql/olap/03_indexing_partitioning.sql` | DWH | Columnstore + partitioning |
| 10 | `sql/olap/05_advanced_modeling_pro.sql` | DWH | Bridges, factless, junk dims, aggregates |
| 11 | `sql/olap/06_views_semantic_layer.sql` | DWH | Business-facing views |
| 12 | `sql/etl/01_etl_procedures.sql` | DWH | Dim + Fact loaders |
| 13 | `sql/etl/02_etl_orchestration.sql` | DWH | Master pipeline + audit log |
| 14 | `sql/olap/04_analytical_queries.sql` | DWH | Foundational analytics |
| 15 | `sql/analytics/01_fraud_detection.sql` | DWH | Fraud heuristics |
| 16 | `sql/analytics/02_churn_cohort.sql` | DWH | Churn + cohort retention |
| 17 | `sql/analytics/03_customer_lifetime_value.sql` | DWH | RFM + CLV |
| 18 | `sql/analytics/04_branch_benchmarking.sql` | DWH | Efficiency frontier |
| 19 | `sql/analytics/05_anomaly_detection.sql` | DWH | Rolling z-score anomaly |

The Python entry point `src/setup_sqlserver.py` runs steps 1–13 end-to-end in order. Steps 14–19 are read-only analytical scripts you run on demand from SSMS / Azure Data Studio.

---

## OLTP Architecture

Designed in **Third Normal Form** for write-optimized transactional workloads.

- **Constraints:** PK/FK integrity, CHECK constraints (`Amount > 0`, `InterestRate BETWEEN 0.01 AND 99.99`), UNIQUE on `Email`, lightweight email format check.
- **Audit:** Every change to `Accounts` and every insert into `Transactions` is logged to `audit.AccountChanges` / `audit.TransactionLog` with username, host, app, and UTC timestamp.
- **Defensive triggers:** `tr_Transactions_AccountStatusGuard` blocks transactions on non-Active accounts before they enter the table.
- **Stored procedures:**
  - `usp_TransferFunds` — atomic deadlock-resilient transfer (deterministic lock ordering, retry on victim).
  - `usp_OpenAccount` — idempotent account opening with optional initial deposit.
  - `usp_PostTransaction` — single-row posting with status validation.

---

## ETL Architecture

- **Master orchestration:** `usp_RunMasterPipeline` runs date → branch → customer (SCD2) → account → fact → aggregates, with each step audited in `dbo.ETL_Audit_Log` (run id, start, end, rows, status, DQ score).
- **Incremental fact load:** `sp_ETL_Fact_Transaction` uses `NOT EXISTS` so only new transactions are loaded.
- **SCD2 customer:** `sp_ETL_Dim_Customer` inserts new customers and is structured for future expiration of changed records.

---

## OLAP / DWH Architecture

- **Star schema** at the core: `Fact_Transaction`, `Fact_Daily_Balance`, `Fact_Loan` joined to `Dim_Date`, `Dim_Customer` (SCD2), `Dim_Account`, `Dim_Branch`, `Dim_Loan`.
- **Bridges & factless:** `Bridge_AccountCustomer` for joint ownership; `Factless_BranchVisit` for coverage analysis.
- **Junk dimension:** `Dim_Junk_TxnFlags` collapses weekend / channel / value flags.
- **Aggregates:** `Agg_Branch_Monthly` and `Agg_Customer_Annual` populate via `usp_RefreshAggregates` for sub-second dashboard reads.
- **Late-arriving dimension** placeholder: `CustomerID = -1` `UNKNOWN` row.

---

## Performance Strategy

| Technique | Object | Effect |
|---|---|---|
| Clustered Columnstore | `Fact_Transaction` | 10–40× compression and aggregation speed |
| Range partitioning by year | `pf_TransactionYear` / `ps_TransactionYear` | Partition pruning |
| Covering NC index | `IX_FactTransaction_DateKey INCLUDE (Amount, TransactionType)` | Index-only scans |
| Surrogate keys | All dimensions | Stable joins under business-key churn |
| Materialized aggregates | `Agg_*` tables | Sub-second drill-downs |

---

## Analytics Toolkit

- **Fraud (`01_fraud_detection.sql`):** velocity windows, structuring near $9000–$9999, per-customer z-score outliers, composite `vw_Fraud_Risk_Score` capped at 100.
- **Churn (`02_churn_cohort.sql`):** tiered churn risk based on inactivity and lifetime metrics; cohort retention via paired CTEs; recursive CTE for full month grid.
- **CLV / RFM (`03_customer_lifetime_value.sql`):** quintile RFM scoring, named segments, 24-month projected CLV with retention proxy and decile ranking.
- **Branch (`04_branch_benchmarking.sql`):** percentile-rank-driven efficiency, governorate league table, account-type rankings.
- **Anomaly (`05_anomaly_detection.sql`):** rolling 30-day z-score on branch daily volumes, 30d-vs-baseline customer behavior shift.
