# Executive Dashboard Guide

The Streamlit application at `dashboard/app_executive.py` is the primary consumption surface of the platform. It loads from CSV (default), falls back to SQL Server when the driver is available, and finally to a deterministic demo dataset.

> The original `dashboard/app.py` is preserved for backward compatibility with existing deployments. The executive dashboard is the recommended entry point.

---

## Tab Architecture

| # | Tab | Audience | Key Insights |
|---|---|---|---|
| 1 | 🏛️ Executive Summary | C-Suite | Volume, transactions, avg ticket, active accounts/customers, net flow, volume trend |
| 2 | 💵 Revenue & Profitability | CFO / COO | Top branches, transaction mix, profitability ranking, governorate revenue |
| 3 | 👥 Customer Intelligence | CMO / RM | RFM segments, CLV deciles, demographic decomposition, cohort retention |
| 4 | 🛡️ Risk & Fraud | CRO / AML | Suspicious counts, velocity heatmap, structuring flags, top high-risk transactions |
| 5 | 💰 Loan Portfolio | Credit | Principal by type, status mix, NPL ratio, vintage, rate distribution |
| 6 | 🏢 Branch Performance | Regional Heads | Efficiency frontier, top-N branches, league table |
| 7 | ⚙️ Operations & SLA | Branch Ops | Weekend share, peak hour, hourly throughput, weekday distribution |
| 8 | 🧪 Data Quality Center | Data Eng | Overall DQ score, completeness, uniqueness, validity, freshness |
| 9 | 🔮 Forecasting Lab | Strategy | Holt-Winters volume forecast, churn-tier distribution |

---

## Filters & Controls

| Control | Behavior |
|---|---|
| Date Range | Bounds the working slice; previous-period delta is automatic |
| Transaction Types | Multi-select |
| Governorates | Multi-select |
| Age Groups | Multi-select |
| Account Types | Multi-select |
| Amount Range | Slider |
| Primary Metric | Sum (volume) or Count |
| Time Grain | Year / Quarter / Month |
| Top N | Ranking depth |

---

## Data Source Strategy

| Mode | When | Indicator |
|---|---|---|
| **CSV** | `data/raw/*.csv` exists | Sidebar: green |
| **SQL** | CSV missing & `pymssql` driver available | Sidebar: blue |
| **Demo** | Both unavailable | Sidebar: orange |

The app is deterministic and resilient: switching off the SQL Server, removing the CSVs, or running on a fresh machine all produce a working dashboard.

---

## Operational Notes

- **Caching:** `@st.cache_data(ttl=3600)` on the loader. Use *Refresh Data* to invalidate.
- **Performance:** All aggregations are vectorized over the filtered dataframe; expect sub-second updates on the bundled dataset.
- **Theming:** Theme-aware CSS adapts to light/dark Streamlit themes; premium gradient banner.
- **Embedded analytics:** RFM scoring, churn tiers, fraud heuristics, and cohort retention are all computed client-side from the joined dataframe — no extra service is needed for the demo to work.

---

## Running

```bash
# Local
streamlit run dashboard/app_executive.py

# Docker (full stack with SQL Server)
docker compose up
# Open http://localhost:8501
```

Set the SQL Server environment variables (`SQLSERVER_HOST`, `SQLSERVER_USER`, `SQLSERVER_PASSWORD`, `SQLSERVER_DB`) to use the warehouse-backed mode.

---

## Backward Compatibility

The legacy `dashboard/app.py` preserves the original 4-tab layout (Overview / Loans / Recommendations / Raw Data). Existing Streamlit Cloud deployments pointing at `app.py` continue to work; new deployments should target `app_executive.py`.
