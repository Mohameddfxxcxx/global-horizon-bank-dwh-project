-- ==========================================
-- Phase 8: Performance & Scalability
-- Global Horizon Bank - OLAP System
-- ==========================================

USE GlobalHorizon_DWH;
GO

/*
PARTITIONING STRATEGY:
We partition the Fact_Transaction table by Year to improve query performance.
Queries analyzing specific years will only scan the relevant partition (Partition Pruning).
*/

-- 1. Create a Partition Function for Years
CREATE PARTITION FUNCTION pf_TransactionYear (INT)
AS RANGE RIGHT FOR VALUES (20200101, 20210101, 20220101, 20230101, 20240101, 20250101, 20260101, 20270101);
GO

-- 2. Create a Partition Scheme mapping to the PRIMARY filegroup (or separate ones in production)
CREATE PARTITION SCHEME ps_TransactionYear
AS PARTITION pf_TransactionYear ALL TO ([PRIMARY]);
GO

-- Note: To apply this to Fact_Transaction, the table must be created on this scheme
-- CREATE TABLE Fact_Transaction (...) ON ps_TransactionYear(DateKey);

/*
INDEXING STRATEGY:
1. Columnstore Indexes: Highly compressed, ideal for aggregations over millions of rows.
2. Non-Clustered Indexes on Foreign Keys.
*/

-- Create a Clustered Columnstore Index on Fact_Transaction for massive analytical performance
CREATE CLUSTERED COLUMNSTORE INDEX CCI_Fact_Transaction
ON Fact_Transaction;
GO

-- Create Non-Clustered B-Tree Indexes on Foreign Keys
CREATE NONCLUSTERED INDEX IX_FactTransaction_CustomerKey 
ON Fact_Transaction(CustomerKey);
GO

CREATE NONCLUSTERED INDEX IX_FactTransaction_AccountKey 
ON Fact_Transaction(AccountKey);
GO

CREATE NONCLUSTERED INDEX IX_FactTransaction_BranchKey 
ON Fact_Transaction(BranchKey);
GO

CREATE NONCLUSTERED INDEX IX_FactTransaction_DateKey 
ON Fact_Transaction(DateKey)
INCLUDE (Amount, TransactionType); -- Covered Index
GO

-- Bitmap Indexes are not natively supported in SQL Server in the same way as Oracle, 
-- but Non-Clustered Indexes and Columnstore Indexes provide similar/better benefits for low-cardinality filtering.
