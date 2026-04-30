-- =============================================================================
-- Global Horizon Bank — Branch Benchmarking & Efficiency
-- =============================================================================
-- Branch-level benchmarking with productivity, efficiency frontier, and per-
-- governorate league tables. Uses ranking and percentile window functions.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. Branch Efficiency Score
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Branch_Efficiency', 'V') IS NOT NULL DROP VIEW dbo.vw_Branch_Efficiency;
GO
CREATE VIEW dbo.vw_Branch_Efficiency
AS
WITH branch_metrics AS (
    SELECT
        b.BranchKey,
        b.BranchID,
        b.BranchName,
        b.State,
        SUM(f.Amount)                  AS Volume,
        COUNT_BIG(*)                   AS TxnCount,
        COUNT(DISTINCT f.CustomerKey)  AS UniqueCustomers,
        COUNT(DISTINCT f.AccountKey)   AS UniqueAccounts,
        AVG(f.Amount)                  AS AvgTicket
    FROM dbo.Dim_Branch b
    LEFT JOIN dbo.Fact_Transaction f ON f.BranchKey = b.BranchKey
    GROUP BY b.BranchKey, b.BranchID, b.BranchName, b.State
)
SELECT
    *,
    PERCENT_RANK() OVER (ORDER BY Volume)                AS VolumePercentile,
    PERCENT_RANK() OVER (ORDER BY UniqueCustomers)       AS CustomersPercentile,
    PERCENT_RANK() OVER (ORDER BY AvgTicket)             AS TicketPercentile,
    -- Composite efficiency 0..100
    CAST(100 *
        (PERCENT_RANK() OVER (ORDER BY Volume) * 0.4
         + PERCENT_RANK() OVER (ORDER BY UniqueCustomers) * 0.4
         + PERCENT_RANK() OVER (ORDER BY AvgTicket) * 0.2)
    AS DECIMAL(6,2)) AS EfficiencyScore,
    RANK() OVER (PARTITION BY State ORDER BY Volume DESC) AS RankInState
FROM branch_metrics;
GO

-- -----------------------------------------------------------------------------
-- 2. Governorate League Table
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.vw_Governorate_League', 'V') IS NOT NULL DROP VIEW dbo.vw_Governorate_League;
GO
CREATE VIEW dbo.vw_Governorate_League
AS
SELECT
    b.State                              AS Governorate,
    COUNT(DISTINCT b.BranchKey)          AS BranchCount,
    COUNT_BIG(f.TransactionKey)          AS TotalTransactions,
    SUM(f.Amount)                        AS TotalVolume,
    AVG(f.Amount)                        AS AvgTicket,
    COUNT(DISTINCT f.CustomerKey)        AS UniqueCustomers,
    RANK() OVER (ORDER BY SUM(f.Amount) DESC)   AS VolumeRank,
    RANK() OVER (ORDER BY COUNT(DISTINCT f.CustomerKey) DESC) AS CustomerRank
FROM dbo.Dim_Branch b
LEFT JOIN dbo.Fact_Transaction f ON f.BranchKey = b.BranchKey
GROUP BY b.State;
GO

-- -----------------------------------------------------------------------------
-- 3. Best/Worst Branch in each Account-Type
-- -----------------------------------------------------------------------------
WITH product_branch AS (
    SELECT
        b.BranchKey,
        b.BranchName,
        a.AccountType,
        SUM(f.Amount) AS Volume
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Branch  b ON b.BranchKey = f.BranchKey
    JOIN dbo.Dim_Account a ON a.AccountKey = f.AccountKey
    GROUP BY b.BranchKey, b.BranchName, a.AccountType
)
SELECT
    AccountType,
    BranchName,
    Volume,
    RANK() OVER (PARTITION BY AccountType ORDER BY Volume DESC) AS Rnk
FROM product_branch
ORDER BY AccountType, Rnk;
GO

PRINT 'Branch benchmarking views installed.';
GO
