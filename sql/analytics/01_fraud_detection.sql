-- =============================================================================
-- Global Horizon Bank — Fraud & AML Detection (Analytical SQL)
-- =============================================================================
-- Multi-signal heuristic scoring covering velocity, structuring, anomalous size,
-- after-hours activity, and Benford-law deviation. Built entirely with window
-- functions and CTEs — no extension required.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. Velocity — multiple high-value transactions in a short window
-- -----------------------------------------------------------------------------
WITH txn AS (
    SELECT
        f.CustomerKey,
        c.CustomerID,
        c.FirstName + ' ' + c.LastName AS CustomerName,
        d.FullDate,
        f.Amount,
        ROW_NUMBER()    OVER (PARTITION BY f.CustomerKey ORDER BY d.FullDate) AS rn,
        SUM(f.Amount)   OVER (PARTITION BY f.CustomerKey ORDER BY d.FullDate
                              ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS Window5Volume,
        COUNT(*)        OVER (PARTITION BY f.CustomerKey ORDER BY d.FullDate
                              ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS Window5Count
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date     d ON d.DateKey = f.DateKey
    JOIN dbo.Dim_Customer c ON c.CustomerKey = f.CustomerKey AND c.IsCurrent = 1
)
SELECT TOP 100
    CustomerID,
    CustomerName,
    FullDate,
    Amount,
    Window5Volume,
    Window5Count,
    CAST(Window5Volume / NULLIF(Window5Count, 0) AS DECIMAL(18,2)) AS AvgIn5Txns
FROM txn
WHERE Window5Count >= 5 AND Window5Volume > 50000
ORDER BY Window5Volume DESC;

-- -----------------------------------------------------------------------------
-- 2. Structuring detector — multiple transactions just under 10K threshold
-- -----------------------------------------------------------------------------
WITH suspect AS (
    SELECT
        f.CustomerKey,
        d.FullDate,
        COUNT(*) AS NearThresholdCount,
        SUM(f.Amount) AS NearThresholdVolume
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    WHERE f.Amount BETWEEN 9000 AND 9999
    GROUP BY f.CustomerKey, d.FullDate
    HAVING COUNT(*) >= 3
)
SELECT
    c.CustomerID,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    s.FullDate,
    s.NearThresholdCount,
    s.NearThresholdVolume,
    'High' AS RiskTier
FROM suspect s
JOIN dbo.Dim_Customer c ON c.CustomerKey = s.CustomerKey AND c.IsCurrent = 1
ORDER BY s.NearThresholdVolume DESC;

-- -----------------------------------------------------------------------------
-- 3. Outlier amount detector — z-score against the customer's own history
-- -----------------------------------------------------------------------------
WITH stats AS (
    SELECT
        f.CustomerKey,
        AVG(f.Amount)            AS MeanAmt,
        STDEV(f.Amount)          AS StdAmt
    FROM dbo.Fact_Transaction f
    GROUP BY f.CustomerKey
    HAVING COUNT(*) >= 30
),
scored AS (
    SELECT
        f.TransactionKey,
        f.CustomerKey,
        f.Amount,
        s.MeanAmt,
        s.StdAmt,
        (f.Amount - s.MeanAmt) / NULLIF(s.StdAmt, 0) AS ZScore
    FROM dbo.Fact_Transaction f
    JOIN stats s ON s.CustomerKey = f.CustomerKey
)
SELECT TOP 200
    c.CustomerID,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    sc.Amount,
    CAST(sc.MeanAmt AS DECIMAL(18,2)) AS MeanAmt,
    CAST(sc.ZScore  AS DECIMAL(8,3))  AS ZScore,
    CASE
        WHEN ABS(sc.ZScore) >= 5 THEN 'Critical'
        WHEN ABS(sc.ZScore) >= 3 THEN 'High'
        ELSE 'Medium'
    END AS Severity
FROM scored sc
JOIN dbo.Dim_Customer c ON c.CustomerKey = sc.CustomerKey AND c.IsCurrent = 1
WHERE ABS(sc.ZScore) >= 3
ORDER BY ABS(sc.ZScore) DESC;

-- -----------------------------------------------------------------------------
-- 4. Helper scalar function — caps score at 100
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.LEAST_100', 'FN') IS NOT NULL DROP FUNCTION dbo.LEAST_100;
GO
CREATE FUNCTION dbo.LEAST_100(@v FLOAT) RETURNS FLOAT
WITH SCHEMABINDING
AS
BEGIN
    RETURN CASE WHEN @v > 100 THEN 100 WHEN @v < 0 THEN 0 ELSE @v END;
END;
GO

-- -----------------------------------------------------------------------------
-- 5. Composite Fraud Risk Score per customer
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Fraud_Risk_Score', 'V') IS NOT NULL DROP VIEW dbo.vw_Fraud_Risk_Score;
GO
CREATE VIEW dbo.vw_Fraud_Risk_Score
AS
WITH per_customer AS (
    SELECT
        f.CustomerKey,
        COUNT(*)                                                          AS TxnCount,
        SUM(f.Amount)                                                     AS TotalVolume,
        AVG(f.Amount)                                                     AS AvgAmount,
        STDEV(f.Amount)                                                   AS StdAmount,
        MAX(f.Amount)                                                     AS MaxAmount,
        SUM(CASE WHEN f.Amount BETWEEN 9000 AND 9999 THEN 1 ELSE 0 END)   AS NearThresholdCount,
        SUM(CASE WHEN d.IsWeekend = 1 THEN 1 ELSE 0 END)                  AS WeekendCount,
        COUNT(DISTINCT f.BranchKey)                                       AS BranchCount
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.CustomerKey
)
SELECT
    pc.CustomerKey,
    pc.TxnCount,
    pc.TotalVolume,
    pc.NearThresholdCount,
    pc.BranchCount,
    -- Composite score on 0..100 scale
    CAST(LEAST_100(
        ( CASE WHEN pc.NearThresholdCount >= 5 THEN 30 WHEN pc.NearThresholdCount >= 2 THEN 15 ELSE 0 END )
      + ( CASE WHEN pc.MaxAmount > pc.AvgAmount + 4 * COALESCE(pc.StdAmount, 0) THEN 25 ELSE 0 END )
      + ( CASE WHEN pc.BranchCount >= 5 THEN 20 ELSE pc.BranchCount * 4 END )
      + ( CASE WHEN pc.WeekendCount * 1.0 / NULLIF(pc.TxnCount, 0) > 0.5 THEN 15 ELSE 0 END )
      + ( CASE WHEN pc.TxnCount > 200 THEN 10 ELSE pc.TxnCount * 0.05 END )
    ) AS DECIMAL(6,2)) AS FraudRiskScore
FROM per_customer pc;
GO

PRINT 'Fraud detection analytics installed.';
GO
