# Strategic Roadmap — Global Horizon Bank Platform

A 12-month strategic plan, organized by quarter and capability theme.

---

## Q1 — Foundation Hardening

| Initiative | Outcome | Owner |
|---|---|---|
| Production SQL Server cluster (Always On AG) | RPO 15 min, RTO 1 h | DBA |
| Enable TDE encryption-at-rest | Full FIPS 140-2 alignment | Security |
| Promote RLS policy `sp_BranchAccess` to ON in prod | Branch-bounded teller access | Security |
| Add CDC on `Transactions` | Near real-time fact table | Data Eng |

## Q2 — Real-Time Analytics

| Initiative | Outcome | Owner |
|---|---|---|
| Streaming ingest via Kafka / Event Hubs | Sub-minute fact freshness | Data Eng |
| Operational data store (ODS) layer | Decoupled real-time vs batch | Architecture |
| Materialized aggregates → in-memory OLAP | Sub-second drill-downs | Performance |

## Q3 — Predictive Productionization

| Initiative | Outcome | Owner |
|---|---|---|
| Model registry + lineage (MLflow) | Auditable model versions | ML |
| Champion-Challenger framework for fraud model | A/B model evaluation | Risk |
| Real-time scoring service (FastAPI) | < 100 ms scoring SLA | ML / Eng |
| Drift monitoring + retraining cadence | Automated DQ-aware retrains | ML Ops |

## Q4 — Customer Intelligence Expansion

| Initiative | Outcome | Owner |
|---|---|---|
| Next-Best-Offer model integrated to dashboard | +3% cross-sell | Marketing + ML |
| Campaign performance tracking | Closed-loop attribution | BI |
| Multi-modal data (call logs, web journeys) | 360° customer view | Architecture |

---

## Capability Themes

### Data Engineering
- Migration from CSV bootstrap → CDC + streaming.
- dbt-style transformations with test layers.
- Parquet-first lake, with Iceberg/Delta exploration.

### BI / Analytics
- Drill-through into transaction grain from every executive tile.
- Self-service semantic layer (Cube/dbt-metrics) for analysts.
- Mobile dashboard for branch managers.

### ML / AI
- Graph-based fraud rings detection.
- Sequence models (RNN/Transformers) for transaction anomaly.
- Causal inference for marketing uplift.

### Governance
- Active Directory federation for DB principals.
- Quarterly SOC2-aligned audits.
- Data product ownership model with SLAs.

---

## Tech Debt Watchlist

- Migrate `BULK INSERT` examples in `02_dml_oltp.sql` to a parameterized loader.
- Consolidate Bronze → Silver type-coercion into a shared schema-registry.
- Replace heuristic fraud score with the Isolation Forest output once pinned to a model version.
- Refactor demo dataset to use the same Faker config as production data generator.
