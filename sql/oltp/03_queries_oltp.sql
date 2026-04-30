-- ==========================================
-- Phase 4: OLTP Limitations Analysis
-- Global Horizon Bank - Transactional System
-- ==========================================

USE GlobalHorizon_OLTP;
GO

/*
LIMITATION ANALYSIS:
Running complex aggregations on the OLTP database causes heavy I/O,
locking, and row-by-row scanning, leading to performance degradation.
The following query joins 4 tables to get a monthly summary of transaction amounts by branch.
*/

-- Enable execution plan visualization in SSMS (Ctrl + M) before running this.
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

SELECT 
    b.BranchName,
    b.State,
    YEAR(t.TransactionDate) AS TxYear,
    MONTH(t.TransactionDate) AS TxMonth,
    c.State AS CustomerState,
    COUNT(t.TransactionID) AS TotalTransactions,
    SUM(t.Amount) AS TotalVolume
FROM 
    Transactions t
JOIN 
    Accounts a ON t.AccountID = a.AccountID
JOIN 
    Customers c ON a.CustomerID = c.CustomerID
JOIN 
    Branches b ON a.BranchID = b.BranchID
WHERE 
    t.TransactionType IN ('Deposit', 'Withdrawal')
GROUP BY 
    b.BranchName,
    b.State,
    YEAR(t.TransactionDate),
    MONTH(t.TransactionDate),
    c.State
ORDER BY 
    TotalVolume DESC;

SET STATISTICS IO OFF;
SET STATISTICS TIME OFF;

/*
Observation Notes:
1. No pre-aggregated data means the engine must scan thousands/millions of transaction rows.
2. Multiple JOINs across large tables (Transactions, Accounts, Customers) are expensive.
3. String manipulation (YEAR(), MONTH()) on the TransactionDate column prevents index usage (non-sargable), resulting in Index Scans instead of Seeks.
4. If run during peak business hours, this query would lock tables and block operational INSERT/UPDATE transactions.
*/
GO
