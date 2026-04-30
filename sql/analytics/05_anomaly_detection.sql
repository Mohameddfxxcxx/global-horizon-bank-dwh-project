-- =============================================================================
-- Global Horizon Bank — Statistical Anomaly Detection
-- =============================================================================
-- Daily volume anomalies (per branch) using a rolling 30-day window and
-- per-customer behavior shift detection. Identifies operational anomalies that
-- need investigation by branch managers and risk teams.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. Daily branch volume anomaly (z-score on rolling baseline)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Branch_Daily_Anomaly', 'V') IS NOT NULL DROP VIEW dbo.vw_Branch_Daily_Anomaly;
GO
CREATE VIEW dbo.vw_Branch_Daily_Anomaly
AS
WITH daily AS (
    SELECT
        f.BranchKey,
        d.FullDate,
        SUM(f.Amount) AS DailyVolume
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.BranchKey, d.FullDate
),
rolling AS (
    SELECT
        BranchKey,
        FullDate,
        DailyVolume,
        AVG(DailyVolume) OVER (PARTITION BY BranchKey ORDER BY FullDate
                               ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) AS RollingMean,
        STDEV(DailyVolume) OVER (PARTITION BY BranchKey ORDER BY FullDate
                                 ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) AS RollingStd
    FROM daily
)
SELECT
    b.BranchName,
    b.State,
    r.FullDate,
    CAST(r.DailyVolume   AS DECIMAL(18,2)) AS DailyVolume,
    CAST(r.RollingMean   AS DECIMAL(18,2)) AS RollingMean,
    CAST(r.RollingStd    AS DECIMAL(18,2)) AS RollingStd,
    CAST((r.DailyVolume - r.RollingMean) / NULLIF(r.RollingStd, 0) AS DECIMAL(8,3)) AS ZScore,
    CASE
        WHEN ABS((r.DailyVolume - r.RollingMean) / NULLIF(r.RollingStd, 0)) >= 4 THEN 'Critical'
        WHEN ABS((r.DailyVolume - r.RollingMean) / NULLIF(r.RollingStd, 0)) >= 3 THEN 'High'
        WHEN ABS((r.DailyVolume - r.RollingMean) / NULLIF(r.RollingStd, 0)) >= 2 THEN 'Medium'
        ELSE 'Normal'
    END AS Severity
FROM rolling r
JOIN dbo.Dim_Branch b ON b.BranchKey = r.BranchKey
WHERE r.RollingStd > 0;
GO

-- -----------------------------------------------------------------------------
-- 2. Behavior-shift detection (last 30d vs prior 60d)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Customer_Behavior_Shift', 'V') IS NOT NULL DROP VIEW dbo.vw_Customer_Behavior_Shift;
GO
CREATE VIEW dbo.vw_Customer_Behavior_Shift
AS
WITH recent AS (
    SELECT f.CustomerKey,
           SUM(f.Amount) AS RecentVolume,
           COUNT(*)      AS RecentCount
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    WHERE d.FullDate >= DATEADD(DAY, -30, CAST(GETDATE() AS DATE))
    GROUP BY f.CustomerKey
),
baseline AS (
    SELECT f.CustomerKey,
           AVG(f.Amount) * 30                                AS ExpectedVolume,
           COUNT(*) * 30.0 / NULLIF(DATEDIFF(DAY, MIN(d.FullDate), MAX(d.FullDate))+1, 0)
                                                              AS ExpectedCount
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    WHERE d.FullDate < DATEADD(DAY, -30, CAST(GETDATE() AS DATE))
    GROUP BY f.CustomerKey
)
SELECT
    c.CustomerID,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    r.RecentVolume,
    b.ExpectedVolume,
    CAST(r.RecentVolume / NULLIF(b.ExpectedVolume, 0) AS DECIMAL(8,3)) AS VolumeRatio,
    CASE
        WHEN r.RecentVolume / NULLIF(b.ExpectedVolume, 0) >= 3 THEN 'Surge'
        WHEN r.RecentVolume / NULLIF(b.ExpectedVolume, 0) <= 0.3 THEN 'Drop'
        ELSE 'Normal'
    END AS BehaviorChange
FROM recent   r
JOIN baseline b ON b.CustomerKey = r.CustomerKey
JOIN dbo.Dim_Customer c ON c.CustomerKey = r.CustomerKey AND c.IsCurrent = 1
WHERE b.ExpectedVolume > 0;
GO

PRINT 'Anomaly detection views installed.';
GO
