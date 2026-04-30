-- =============================================================================
-- Global Horizon Bank — Semantic Layer
-- =============================================================================
-- Business-facing views consumed by dashboards, ML pipelines, and ad-hoc analysts.
-- The semantic layer is the contract between data engineering and analytics — every
-- KPI in the catalog resolves to one of these views.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- vw_Executive_KPI — single-row C-suite cockpit
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Executive_KPI', 'V') IS NOT NULL DROP VIEW dbo.vw_Executive_KPI;
GO
CREATE VIEW dbo.vw_Executive_KPI
AS
WITH base AS (
    SELECT
        SUM(f.Amount)                                                AS TotalVolume,
        COUNT_BIG(*)                                                 AS TotalTransactions,
        COUNT(DISTINCT f.CustomerKey)                                AS ActiveCustomers,
        COUNT(DISTINCT f.AccountKey)                                 AS ActiveAccounts,
        AVG(f.Amount)                                                AS AvgTicket,
        SUM(CASE WHEN d.IsWeekend = 1 THEN f.Amount ELSE 0 END)      AS WeekendVolume,
        SUM(CASE WHEN f.TransactionType = 'Deposit'    THEN f.Amount ELSE 0 END) AS DepositVolume,
        SUM(CASE WHEN f.TransactionType = 'Withdrawal' THEN f.Amount ELSE 0 END) AS WithdrawalVolume
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
)
SELECT
    TotalVolume,
    TotalTransactions,
    ActiveCustomers,
    ActiveAccounts,
    AvgTicket,
    WeekendVolume,
    DepositVolume,
    WithdrawalVolume,
    CAST(WeekendVolume * 1.0 / NULLIF(TotalVolume, 0) AS DECIMAL(6,4)) AS WeekendShare,
    CAST((DepositVolume - WithdrawalVolume) AS DECIMAL(20,2))           AS NetFlow
FROM base;
GO

-- -----------------------------------------------------------------------------
-- vw_Branch_Performance
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Branch_Performance', 'V') IS NOT NULL DROP VIEW dbo.vw_Branch_Performance;
GO
CREATE VIEW dbo.vw_Branch_Performance
AS
SELECT
    b.BranchKey,
    b.BranchID,
    b.BranchName,
    b.City,
    b.State,
    COUNT_BIG(f.TransactionKey)                  AS TransactionCount,
    SUM(f.Amount)                                AS TotalVolume,
    AVG(f.Amount)                                AS AvgTicket,
    COUNT(DISTINCT f.CustomerKey)                AS UniqueCustomers,
    COUNT(DISTINCT f.AccountKey)                 AS UniqueAccounts,
    RANK() OVER (ORDER BY SUM(f.Amount) DESC)    AS VolumeRank
FROM dbo.Dim_Branch b
LEFT JOIN dbo.Fact_Transaction f ON f.BranchKey = b.BranchKey
GROUP BY b.BranchKey, b.BranchID, b.BranchName, b.City, b.State;
GO

-- -----------------------------------------------------------------------------
-- vw_Customer_360 — customer master with behavioral metrics
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Customer_360', 'V') IS NOT NULL DROP VIEW dbo.vw_Customer_360;
GO
CREATE VIEW dbo.vw_Customer_360
AS
SELECT
    c.CustomerKey,
    c.CustomerID,
    c.FirstName,
    c.LastName,
    c.AgeGroup,
    c.City,
    c.State,
    COUNT_BIG(f.TransactionKey)                              AS TransactionCount,
    SUM(f.Amount)                                            AS TotalVolume,
    AVG(f.Amount)                                            AS AvgTicket,
    MAX(d.FullDate)                                          AS LastActivityDate,
    DATEDIFF(DAY, MAX(d.FullDate), CAST(GETDATE() AS DATE))  AS DaysSinceLastActivity,
    COUNT(DISTINCT f.AccountKey)                             AS DistinctAccounts
FROM dbo.Dim_Customer c
LEFT JOIN dbo.Fact_Transaction f ON f.CustomerKey = c.CustomerKey
LEFT JOIN dbo.Dim_Date d         ON d.DateKey = f.DateKey
WHERE c.IsCurrent = 1
GROUP BY c.CustomerKey, c.CustomerID, c.FirstName, c.LastName, c.AgeGroup, c.City, c.State;
GO

-- -----------------------------------------------------------------------------
-- vw_Monthly_Trend — month-grain volume + growth (for executives)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Monthly_Trend', 'V') IS NOT NULL DROP VIEW dbo.vw_Monthly_Trend;
GO
CREATE VIEW dbo.vw_Monthly_Trend
AS
WITH monthly AS (
    SELECT
        d.Year,
        d.Month,
        d.MonthName,
        SUM(f.Amount)               AS Volume,
        COUNT_BIG(*)                AS TxCount,
        COUNT(DISTINCT f.CustomerKey) AS ActiveCustomers
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY d.Year, d.Month, d.MonthName
)
SELECT
    Year, Month, MonthName,
    Volume,
    TxCount,
    ActiveCustomers,
    LAG(Volume,  1) OVER (ORDER BY Year, Month) AS PrevMonthVolume,
    LAG(Volume, 12) OVER (ORDER BY Year, Month) AS PrevYearMonthVolume,
    100.0 * (Volume - LAG(Volume, 1)  OVER (ORDER BY Year, Month))
          / NULLIF(LAG(Volume, 1)  OVER (ORDER BY Year, Month), 0) AS MoMGrowthPct,
    100.0 * (Volume - LAG(Volume, 12) OVER (ORDER BY Year, Month))
          / NULLIF(LAG(Volume, 12) OVER (ORDER BY Year, Month), 0) AS YoYGrowthPct
FROM monthly;
GO

-- -----------------------------------------------------------------------------
-- vw_Loan_Portfolio — risk-aware loan book view
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Loan_Portfolio', 'V') IS NOT NULL DROP VIEW dbo.vw_Loan_Portfolio;
GO
CREATE VIEW dbo.vw_Loan_Portfolio
AS
SELECT
    fl.LoanFactKey,
    dl.LoanID,
    dl.LoanType,
    dl.PrincipalAmount,
    dl.InterestRate,
    dl.TermMonths,
    dl.Status,
    dl.StartDate,
    fl.OutstandingBalance,
    fl.DaysSinceStart,
    fl.IsDelinquent,
    fl.IsDefaulted,
    b.BranchName,
    b.State,
    c.AgeGroup
FROM dbo.Fact_Loan fl
JOIN dbo.Dim_Loan     dl ON dl.LoanKey     = fl.LoanKey
JOIN dbo.Dim_Branch   b  ON b.BranchKey    = fl.BranchKey
JOIN dbo.Dim_Customer c  ON c.CustomerKey  = fl.CustomerKey AND c.IsCurrent = 1;
GO

PRINT 'Semantic layer views installed.';
GO
