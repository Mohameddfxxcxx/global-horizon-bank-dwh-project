# KPI Catalog — Global Horizon Bank

The metric contract. Every KPI shown on the executive dashboard or referenced in business reports resolves to one of the formulas below, computed from the semantic layer.

---

## 1. Profitability

### Net Interest Margin (NIM)
**Definition:** (Interest Income – Interest Expense) / Average Earning Assets.
**Proxy SQL (illustrative):**
```sql
SELECT
    SUM(l.PrincipalAmount * l.InterestRate / 100.0) AS InterestIncome,
    AVG(a.Balance)                                  AS AvgEarningAssets
FROM dbo.Loans l, dbo.Accounts a
WHERE l.Status = 'Active' AND a.Status = 'Active';
```

### Branch Profitability Index
**Definition:** Composite percentile of Volume × AvgTicket × UniqueCustomers.
**Source:** `vw_Branch_Efficiency`.

### Revenue per Customer
```sql
SELECT TotalVolume * 1.0 / NULLIF(ActiveCustomers, 0) AS RevPerCustomer
FROM dbo.vw_Executive_KPI;
```

---

## 2. Growth

| KPI | Formula | View |
|---|---|---|
| **Deposit Growth Rate** | (DepositsNow – DepositsPrev) / DepositsPrev | `vw_Monthly_Trend` |
| **Loan Growth Rate** | (LoansNow – LoansPrev) / LoansPrev | `Loans` table |
| **Active-Customer Growth** | YoY change in distinct active customers | `vw_Monthly_Trend` |
| **Cross-Sell Index** | Avg products per customer | `Bridge_AccountCustomer` |

---

## 3. Risk

### NPL Ratio
**Formula:** Defaulted Principal ÷ Total Outstanding Principal.
```sql
SELECT
    100.0 * SUM(CASE WHEN Status='Defaulted' THEN PrincipalAmount END)
        / NULLIF(SUM(PrincipalAmount), 0) AS NPLRatio
FROM dbo.Loans;
```

### Delinquency Ratio
Loans past due (proxy: Active loans past schedule).

### Concentration Risk
```sql
SELECT TOP 5 BranchName,
    100.0 * SUM(Amount) / SUM(SUM(Amount)) OVER () AS BranchSharePct
FROM dbo.vw_Branch_Performance
GROUP BY BranchName
ORDER BY SUM(Amount) DESC;
```

### Composite Fraud Risk
**Source:** `vw_Fraud_Risk_Score`. Combines near-threshold structuring, z-score outliers, branch dispersion, weekend skew.

---

## 4. Customer

| KPI | Source |
|---|---|
| **CLV (24-month projected)** | `vw_Customer_CLV` |
| **RFM Segment** | `vw_Customer_RFM` |
| **Churn Risk Tier** | `vw_Churn_Risk` |
| **Recency / Frequency / Monetary** | `vw_Customer_RFM` |
| **Wallet-Share Estimate** | Customer-volume / Branch-volume |

---

## 5. Operations

| KPI | Definition |
|---|---|
| **Transactions per Day** | COUNT(*) / distinct dates |
| **Weekend Share** | Weekend volume ÷ total volume |
| **Peak-Hour Load** | MAX(hourly txn count) |
| **Branch Utilization** | Txns ÷ Employees per branch |

---

## 6. Fraud / AML

| KPI | View |
|---|---|
| **Velocity Score (5-txn rolling)** | `01_fraud_detection.sql` |
| **Structuring Indicator** | `01_fraud_detection.sql` |
| **Z-Score Outlier** | `01_fraud_detection.sql` |
| **Composite Fraud Risk** | `vw_Fraud_Risk_Score` |
| **Behavior Shift** | `vw_Customer_Behavior_Shift` |

---

## 7. Decision Thresholds

| KPI | Green | Amber | Red |
|---|---|---|---|
| NPL Ratio | ≤ 2% | 2–5% | > 5% |
| Branch Concentration | ≤ 20% | 20–35% | > 35% |
| Weekend Share | 15–35% | 35–45% | > 45% |
| Churn 90d (Active customers) | < 10% | 10–20% | > 20% |
| Fraud Risk Score | < 30 | 30–60 | ≥ 60 |
| DQ Score (Gold) | ≥ 99 | 95–99 | < 95 |
