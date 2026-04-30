-- =============================================================================
-- Global Horizon Bank — Churn Risk & Cohort Retention
-- =============================================================================
-- Customer churn scoring (RFM-derived) and acquisition-cohort retention
-- analysis using window functions and recursive CTE for monthly cohort buckets.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. Churn Risk Scoring
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Churn_Risk', 'V') IS NOT NULL DROP VIEW dbo.vw_Churn_Risk;
GO
CREATE VIEW dbo.vw_Churn_Risk
AS
WITH activity AS (
    SELECT
        c.CustomerKey,
        c.CustomerID,
        c.FirstName,
        c.LastName,
        c.AgeGroup,
        c.State,
        MAX(d.FullDate)                                              AS LastActivityDate,
        COUNT(*)                                                     AS LifetimeTxns,
        SUM(f.Amount)                                                AS LifetimeVolume,
        DATEDIFF(DAY, MAX(d.FullDate), CAST(GETDATE() AS DATE))      AS DaysSinceLastTxn,
        COUNT(DISTINCT CAST(d.FullDate AS DATE))                     AS ActiveDays
    FROM dbo.Dim_Customer c
    LEFT JOIN dbo.Fact_Transaction f ON f.CustomerKey = c.CustomerKey
    LEFT JOIN dbo.Dim_Date d         ON d.DateKey = f.DateKey
    WHERE c.IsCurrent = 1
    GROUP BY c.CustomerKey, c.CustomerID, c.FirstName, c.LastName, c.AgeGroup, c.State
)
SELECT
    CustomerKey,
    CustomerID,
    FirstName, LastName, AgeGroup, State,
    LifetimeTxns,
    LifetimeVolume,
    DaysSinceLastTxn,
    CASE
        WHEN DaysSinceLastTxn IS NULL              THEN 'Inactive'
        WHEN DaysSinceLastTxn >= 180               THEN 'Critical'
        WHEN DaysSinceLastTxn >= 90                THEN 'High'
        WHEN DaysSinceLastTxn >= 45                THEN 'Medium'
        ELSE 'Low'
    END AS ChurnRiskTier,
    CAST(
        CASE
            WHEN DaysSinceLastTxn IS NULL THEN 95
            WHEN DaysSinceLastTxn >= 180  THEN 90
            WHEN DaysSinceLastTxn >= 90   THEN 70
            WHEN DaysSinceLastTxn >= 45   THEN 45
            WHEN DaysSinceLastTxn >= 15   THEN 25
            ELSE 10
        END
        - LEAST_100(LifetimeTxns * 0.1) * 0.2
        AS DECIMAL(6,2)
    ) AS ChurnRiskScore
FROM activity;
GO

-- -----------------------------------------------------------------------------
-- 2. Cohort Retention — by acquisition month
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Cohort_Retention', 'V') IS NOT NULL DROP VIEW dbo.vw_Cohort_Retention;
GO
CREATE VIEW dbo.vw_Cohort_Retention
AS
WITH first_activity AS (
    SELECT
        f.CustomerKey,
        DATEFROMPARTS(MIN(d.Year), MIN(d.Month), 1) AS CohortMonth
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.CustomerKey
),
activity_months AS (
    SELECT DISTINCT
        f.CustomerKey,
        DATEFROMPARTS(d.Year, d.Month, 1) AS ActivityMonth
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
)
SELECT
    fa.CohortMonth,
    DATEDIFF(MONTH, fa.CohortMonth, am.ActivityMonth) AS MonthsSinceCohort,
    COUNT(DISTINCT am.CustomerKey)                    AS ActiveCustomers,
    COUNT(DISTINCT fa.CustomerKey)                    AS CohortSize,
    CAST(100.0 * COUNT(DISTINCT am.CustomerKey)
              / NULLIF(COUNT(DISTINCT fa.CustomerKey), 0) AS DECIMAL(5,2)) AS RetentionPct
FROM first_activity fa
JOIN activity_months am
    ON am.CustomerKey = fa.CustomerKey
   AND am.ActivityMonth >= fa.CohortMonth
GROUP BY fa.CohortMonth, DATEDIFF(MONTH, fa.CohortMonth, am.ActivityMonth);
GO

-- -----------------------------------------------------------------------------
-- 3. Recursive CTE — generate calendar of cohort months for full grid
-- -----------------------------------------------------------------------------
WITH dates AS (
    SELECT MIN(FullDate) AS StartDate, MAX(FullDate) AS EndDate FROM dbo.Dim_Date
),
months(MonthDate) AS (
    SELECT DATEFROMPARTS(YEAR(StartDate), MONTH(StartDate), 1) FROM dates
    UNION ALL
    SELECT DATEADD(MONTH, 1, MonthDate)
    FROM months, dates
    WHERE DATEADD(MONTH, 1, MonthDate) <= dates.EndDate
)
SELECT MonthDate FROM months OPTION (MAXRECURSION 1200);
GO

PRINT 'Churn and cohort views installed.';
GO
