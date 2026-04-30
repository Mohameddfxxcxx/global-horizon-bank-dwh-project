-- ==========================================
-- Phase 9: Analytical Queries & Reporting
-- Global Horizon Bank - OLAP System
-- ==========================================

USE GlobalHorizon_DWH;
GO

-- 1. Top N Customers by Transaction Volume
-- Business Insight: Identifies the most valuable and active customers for VIP targeting.
SELECT TOP 10
    c.FirstName,
    c.LastName,
    c.State,
    COUNT(f.TransactionKey) AS TotalTransactions,
    SUM(f.Amount) AS TotalVolume
FROM 
    Fact_Transaction f
JOIN 
    Dim_Customer c ON f.CustomerKey = c.CustomerKey
WHERE 
    f.TransactionType IN ('Deposit', 'Transfer') AND c.IsCurrent = 1
GROUP BY 
    c.FirstName,
    c.LastName,
    c.State
ORDER BY 
    TotalVolume DESC;


-- 2. Monthly Revenue/Transaction Trends with Period-over-Period Comparison using Window Functions
-- Business Insight: Shows transaction volume growth and compares current month to previous month to detect seasonal dips.
WITH MonthlyStats AS (
    SELECT 
        d.Year,
        d.Month,
        d.MonthName,
        SUM(f.Amount) AS CurrentMonthVolume
    FROM 
        Fact_Transaction f
    JOIN 
        Dim_Date d ON f.DateKey = d.DateKey
    WHERE 
        f.TransactionType = 'Deposit'
    GROUP BY 
        d.Year,
        d.Month,
        d.MonthName
)
SELECT 
    Year,
    MonthName,
    CurrentMonthVolume,
    LAG(CurrentMonthVolume, 1) OVER (ORDER BY Year, Month) AS PreviousMonthVolume,
    (CurrentMonthVolume - LAG(CurrentMonthVolume, 1) OVER (ORDER BY Year, Month)) / NULLIF(LAG(CurrentMonthVolume, 1) OVER (ORDER BY Year, Month), 0) * 100 AS GrowthPercentage
FROM 
    MonthlyStats
ORDER BY 
    Year, Month;


-- 3. Running Totals for Branch Daily Performance
-- Business Insight: Tracks cumulative daily transaction flow for liquidity management at the branch level.
WITH LatestMonth AS (
    SELECT TOP 1
        d.Year,
        d.Month
    FROM Dim_Date d
    ORDER BY d.Year DESC, d.Month DESC
)
SELECT 
    b.BranchName,
    d.FullDate,
    SUM(f.Amount) AS DailyTotal,
    SUM(SUM(f.Amount)) OVER (PARTITION BY b.BranchName ORDER BY d.FullDate ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS CumulativeTotal
FROM 
    Fact_Transaction f
JOIN 
    Dim_Date d ON f.DateKey = d.DateKey
JOIN 
    Dim_Branch b ON f.BranchKey = b.BranchKey
JOIN
    LatestMonth lm ON d.Year = lm.Year AND d.Month = lm.Month
GROUP BY 
    b.BranchName,
    d.FullDate
ORDER BY 
    b.BranchName,
    d.FullDate;


-- 4. Best Performing Products (Account Types) by Region
-- Business Insight: Helps marketing understand which products succeed in which geographic regions.
SELECT 
    c.State,
    a.AccountType,
    COUNT(DISTINCT a.AccountID) AS NumberOfAccounts,
    SUM(f.Amount) AS TotalTransactionVolume,
    RANK() OVER (PARTITION BY c.State ORDER BY SUM(f.Amount) DESC) AS RankInState
FROM 
    Fact_Transaction f
JOIN 
    Dim_Customer c ON f.CustomerKey = c.CustomerKey
JOIN 
    Dim_Account a ON f.AccountKey = a.AccountKey
GROUP BY 
    c.State,
    a.AccountType;
GO
