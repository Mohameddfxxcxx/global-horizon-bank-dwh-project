-- =============================================================================
-- Global Horizon Bank — Customer Lifetime Value (CLV) & RFM Segmentation
-- =============================================================================
-- Estimates CLV, computes RFM scores, ranks customers into deciles, and assigns
-- actionable behavior segments (Champions, Loyal, At-Risk, etc.).
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. RFM Foundation
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Customer_RFM', 'V') IS NOT NULL DROP VIEW dbo.vw_Customer_RFM;
GO
CREATE VIEW dbo.vw_Customer_RFM
AS
WITH base AS (
    SELECT
        f.CustomerKey,
        DATEDIFF(DAY, MAX(d.FullDate), CAST(GETDATE() AS DATE)) AS Recency,
        COUNT(*)                                                AS Frequency,
        SUM(f.Amount)                                           AS Monetary,
        AVG(f.Amount)                                           AS AvgTicket
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.CustomerKey
),
scored AS (
    SELECT
        CustomerKey,
        Recency,
        Frequency,
        Monetary,
        AvgTicket,
        NTILE(5) OVER (ORDER BY Recency ASC)        AS R_Score,   -- low recency days = best
        NTILE(5) OVER (ORDER BY Frequency DESC)     AS F_Score,
        NTILE(5) OVER (ORDER BY Monetary DESC)      AS M_Score
    FROM base
)
SELECT
    s.CustomerKey,
    c.CustomerID,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    c.AgeGroup,
    c.State,
    s.Recency,
    s.Frequency,
    s.Monetary,
    s.AvgTicket,
    s.R_Score,
    s.F_Score,
    s.M_Score,
    CONCAT(s.R_Score, s.F_Score, s.M_Score) AS RFMCode,
    CASE
        WHEN s.R_Score = 5 AND s.F_Score >= 4 AND s.M_Score >= 4 THEN 'Champions'
        WHEN s.R_Score >= 4 AND s.F_Score >= 3 AND s.M_Score >= 3 THEN 'Loyal Customers'
        WHEN s.R_Score >= 4 AND s.F_Score <= 2                    THEN 'New / Promising'
        WHEN s.R_Score = 3 AND s.F_Score >= 3                     THEN 'Potential Loyalist'
        WHEN s.R_Score <= 2 AND s.F_Score >= 4 AND s.M_Score >= 4 THEN 'At Risk — High Value'
        WHEN s.R_Score = 1 AND s.F_Score = 1                      THEN 'Lost / Hibernating'
        ELSE 'Need Attention'
    END AS Segment
FROM scored s
JOIN dbo.Dim_Customer c ON c.CustomerKey = s.CustomerKey AND c.IsCurrent = 1;
GO

-- -----------------------------------------------------------------------------
-- 2. CLV — simple historic model with frequency/monetary projection
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Customer_CLV', 'V') IS NOT NULL DROP VIEW dbo.vw_Customer_CLV;
GO
CREATE VIEW dbo.vw_Customer_CLV
AS
WITH activity AS (
    SELECT
        f.CustomerKey,
        MIN(d.FullDate)        AS FirstTxn,
        MAX(d.FullDate)        AS LastTxn,
        COUNT(*)               AS Frequency,
        SUM(f.Amount)          AS Monetary,
        AVG(f.Amount)          AS AvgOrderValue
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.CustomerKey
)
SELECT
    a.CustomerKey,
    c.CustomerID,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    a.FirstTxn,
    a.LastTxn,
    a.Frequency,
    a.Monetary                                                                  AS LifetimeValue,
    DATEDIFF(DAY, a.FirstTxn, a.LastTxn) + 1                                    AS TenureDays,
    CAST(a.Frequency * 1.0 / NULLIF(DATEDIFF(MONTH, a.FirstTxn, a.LastTxn), 0)
        AS DECIMAL(8,2))                                                        AS TxnsPerMonth,
    -- Project 24-month CLV: avg monthly volume × 24 × retention proxy
    CAST(
        a.Monetary * 1.0 / NULLIF(DATEDIFF(MONTH, a.FirstTxn, a.LastTxn) + 1, 0)
        * 24
        * (1 - DATEDIFF(DAY, a.LastTxn, GETDATE()) / 365.0 * 0.3)
        AS DECIMAL(18,2)
    )                                                                           AS Projected24MonthCLV,
    NTILE(10) OVER (ORDER BY a.Monetary DESC)                                   AS CLVDecile
FROM activity a
JOIN dbo.Dim_Customer c ON c.CustomerKey = a.CustomerKey AND c.IsCurrent = 1;
GO

PRINT 'CLV and RFM views installed.';
GO
