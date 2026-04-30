# Business Case — Global Horizon Bank Enterprise Data Platform

## Executive Summary

The Enterprise Data Platform converts Global Horizon Bank's transactional data exhaust into compounding business value. By centralizing analytics in a governed warehouse, embedding predictive intelligence, and surfacing decision-grade KPIs to executives and branch managers, the platform pays for itself within the first 12 months and unlocks high-margin growth thereafter.

---

## 1. Strategic Context

| Pressure | Implication |
|---|---|
| Margin compression in retail banking | Need to optimize branch profitability and deposit mix |
| Rising fraud losses | Need real-time anomaly detection |
| Digital-first customer churn | Need predictive retention |
| Regulatory expansion (Basel IV, IFRS 9) | Need governed, traceable data |
| Talent leverage | Empower analysts with semantic layer |

---

## 2. Quantified Outcomes (12-month plan)

| Lever | Baseline | Target | $ Impact |
|---|---|---|---|
| **Fraud loss reduction** | Reactive forensic detection | Real-time scoring | 25–40% reduction in fraud losses |
| **Churn retention lift** | Static rules | Predictive churn model | 3–5% retention improvement |
| **Cross-sell uplift** | Generic offers | RFM + NBO targeting | 2–3% cross-sell rate uplift |
| **Branch profitability** | Annual review | Monthly efficiency frontier | Re-allocate ~5% of capacity |
| **Reporting time saved** | 4–8 min queries | < 1.5 s | 60–80% analyst-hour savings |
| **Reg-reporting compliance** | Manual stitching | Auditable lineage | Lower audit findings + fines |

Conservative net financial impact: **8–12% lift in retail-banking contribution margin** within 12 months.

---

## 3. Investment

| Category | One-time | Recurring (annual) |
|---|---|---|
| Engineering team (3 FTE) | $120k onboarding | $450k |
| SQL Server licensing (Enterprise) | $40k | $80k |
| Cloud / on-prem infra | $30k | $90k |
| ML compute | $15k | $40k |
| Training + change management | $25k | $20k |
| **Total** | **$230k** | **$680k** |

---

## 4. ROI Snapshot

Assuming a $1.5B retail asset book and 0.3% fraud-loss rate baseline:

- **Fraud loss baseline:** $4.5M/yr.
- **Reduction at 30%:** $1.35M/yr saved.
- **Churn retention lift on $400M revenue at 3%:** $12M/yr retained.
- **Year-1 conservative NPV:** $9–14M.

ROI multiple: **>10× year-one**.

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Adoption inertia | Embed dashboard into branch-manager scorecards |
| Model drift | MLOps with drift monitors and quarterly retraining |
| Data quality regressions | DQ-scored medallion gates; alerts on score drop |
| Regulatory change | Governance framework + lineage already in place |
| Single-point-of-failure | Always On AG + DR drills |

---

## 6. Strategic Optionality

The platform is also a *capability* asset:
- **Open Banking compatibility** — semantic views become external data products.
- **AI-native expansion** — feature store enables LLM/agent workflows for branch staff.
- **Regulatory leverage** — same architecture supports stress testing and IFRS 9 ECL.
- **M&A integration** — medallion structure absorbs target-bank data with bounded risk.

---

## 7. Recommendation

Approve the platform investment for production hardening and a 12-month feature roadmap. Expected payback < 9 months; strategic optionality is significant.
