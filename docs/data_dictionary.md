# Data Dictionary — Global Horizon Bank

A complete, column-level reference for every operational and analytical table in the platform.

---

## OLTP — `GlobalHorizon_OLTP`

### `Branches`
| Column | Type | Constraints | Description |
|---|---|---|---|
| BranchID | INT | PK | Branch business key |
| BranchName | VARCHAR(100) | NOT NULL | Display name |
| Address | VARCHAR(255) | NOT NULL | Street address |
| City | VARCHAR(100) | NOT NULL | City |
| State | VARCHAR(10) | NOT NULL | Governorate code |
| ZipCode | VARCHAR(20) | NOT NULL | Postal code |

### `Employees`
| Column | Type | Constraints | Description |
|---|---|---|---|
| EmployeeID | INT | PK | Internal ID |
| FirstName | VARCHAR(50) | NOT NULL | |
| LastName | VARCHAR(50) | NOT NULL | |
| Role | VARCHAR(50) | NOT NULL | Teller / Manager / Loan Officer / CSR |
| BranchID | INT | FK → Branches | |
| HireDate | DATE | NOT NULL | |

### `Customers`
| Column | Type | Constraints | Description |
|---|---|---|---|
| CustomerID | INT | PK | |
| FirstName | VARCHAR(50) | NOT NULL | |
| LastName | VARCHAR(50) | NOT NULL | |
| Email | VARCHAR(100) | UNIQUE, format check, MASKED | PII |
| Phone | VARCHAR(50) | NOT NULL, MASKED | PII |
| Address | VARCHAR(255) | NOT NULL, MASKED | PII |
| City | VARCHAR(100) | NOT NULL | |
| State | VARCHAR(10) | NOT NULL | |
| ZipCode | VARCHAR(20) | NOT NULL | |
| DateOfBirth | DATE | NOT NULL, range check | PII |
| JoinDate | DATE | NOT NULL | Customer onboarding |

### `Accounts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| AccountID | BIGINT | PK | |
| CustomerID | INT | FK → Customers | |
| BranchID | INT | FK → Branches | |
| AccountType | VARCHAR(50) | CHECK (Checking / Savings / Credit) | |
| Balance | DECIMAL(18,2) | NOT NULL | |
| OpenDate | DATE | NOT NULL | |
| Status | VARCHAR(20) | CHECK (Active / Closed / Suspended) | |

### `Loans`
| Column | Type | Constraints | Description |
|---|---|---|---|
| LoanID | INT | PK | |
| CustomerID | INT | FK → Customers | |
| BranchID | INT | FK → Branches | |
| LoanType | VARCHAR(50) | NOT NULL | Mortgage / Auto / Personal / Student |
| PrincipalAmount | DECIMAL(18,2) | > 0 | |
| InterestRate | DECIMAL(5,2) | 0.01–99.99 | |
| TermMonths | INT | > 0 | |
| StartDate | DATE | NOT NULL | |
| Status | VARCHAR(20) | CHECK (Active / Paid / Defaulted) | |

### `Transactions`
| Column | Type | Constraints | Description |
|---|---|---|---|
| TransactionID | UNIQUEIDENTIFIER | PK | |
| AccountID | BIGINT | FK → Accounts | |
| TransactionType | VARCHAR(50) | CHECK (Deposit / Withdrawal / Transfer / Payment) | |
| Amount | DECIMAL(18,2) | > 0 | |
| TransactionDate | DATETIME | DEFAULT GETDATE() | |
| Description | VARCHAR(255) | nullable | |
| RelatedAccountID | BIGINT | FK → Accounts, ≠ AccountID | Counterparty (transfers) |

---

## DWH — `GlobalHorizon_DWH`

### `Dim_Date`
DateKey (PK, YYYYMMDD), FullDate, Year, Quarter, Month, MonthName, DayOfMonth, DayOfWeek, DayName, IsWeekend.

### `Dim_Branch`
BranchKey (PK, surrogate), BranchID (business key), BranchName, City, State, ZipCode.

### `Dim_Customer` *(SCD Type 2)*
CustomerKey (PK), CustomerID (business key), FirstName, LastName, AgeGroup, City, State, EffectiveDate, ExpirationDate, IsCurrent.

### `Dim_Account`
AccountKey (PK), AccountID, AccountType, OpenDate, Status.

### `Dim_Loan`
LoanKey (PK), LoanID, LoanType, PrincipalAmount, InterestRate, TermMonths, Status, StartDate.

### `Dim_Junk_TxnFlags`
JunkKey (PK), IsWeekend, IsHighValue, Channel.

### `Fact_Transaction`
TransactionKey (PK), TransactionID (degenerate dim), DateKey, CustomerKey, AccountKey, BranchKey, TransactionType, Amount.

### `Fact_Daily_Balance`
SnapshotDateKey + AccountKey (PK), CustomerKey, BranchKey, EndOfDayBalance.

### `Fact_Loan`
LoanFactKey (PK), LoanKey, CustomerKey, BranchKey, StartDateKey, PrincipalAmount, OutstandingBalance, DaysSinceStart, IsDelinquent, IsDefaulted.

### `Bridge_AccountCustomer`
AccountKey, CustomerKey, OwnershipPct, Role.

### `Factless_BranchVisit`
VisitKey, DateKey, CustomerKey, BranchKey.

### `Agg_Branch_Monthly`
BranchKey, YearMonth, TransactionCount, TotalVolume, DepositVolume, WithdrawalVolume, UniqueCustomers.

### `Agg_Customer_Annual`
CustomerKey, YearValue, TransactionCount, TotalVolume, AvgTicket.

### `ETL_Audit_Log`
AuditID, RunID, PipelineName, StepName, StartedAtUTC, EndedAtUTC, DurationSeconds (computed), RowsProcessed, Status, ErrorMessage, DataQualityScore.

---

## Semantic Views

| View | Purpose |
|---|---|
| `vw_Executive_KPI` | C-suite single-row cockpit |
| `vw_Branch_Performance` | Branch ranking with volume + customer counts |
| `vw_Customer_360` | Customer master with behavioral metrics |
| `vw_Monthly_Trend` | MoM and YoY growth |
| `vw_Loan_Portfolio` | Risk-aware loan book |
| `vw_Customer_RFM` | RFM scoring + segments |
| `vw_Customer_CLV` | 24-month CLV projection |
| `vw_Churn_Risk` | Tiered churn risk |
| `vw_Cohort_Retention` | Acquisition-cohort retention |
| `vw_Branch_Efficiency` | Composite efficiency score |
| `vw_Governorate_League` | Governorate leaderboards |
| `vw_Branch_Daily_Anomaly` | Rolling z-score anomalies |
| `vw_Customer_Behavior_Shift` | Surge/drop detection |
| `vw_Fraud_Risk_Score` | Composite fraud risk per customer |
