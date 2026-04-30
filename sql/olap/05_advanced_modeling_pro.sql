-- =============================================================================
-- Global Horizon Bank — Advanced Dimensional Modeling
-- =============================================================================
-- Bridge tables, factless facts, late-arriving dimensions, junk dimensions and
-- materialized aggregates that round out the warehouse for executive analytics.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. Loan Dimension and Fact (loan-grain analytics)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.Dim_Loan', 'U') IS NULL
CREATE TABLE dbo.Dim_Loan (
    LoanKey         INT IDENTITY(1,1) PRIMARY KEY,
    LoanID          INT          NOT NULL,
    LoanType        VARCHAR(50)  NOT NULL,
    PrincipalAmount DECIMAL(18,2) NOT NULL,
    InterestRate    DECIMAL(5,2)  NOT NULL,
    TermMonths      INT          NOT NULL,
    Status          VARCHAR(20)  NOT NULL,
    StartDate       DATE         NOT NULL
);
GO

IF OBJECT_ID('dbo.Fact_Loan', 'U') IS NULL
CREATE TABLE dbo.Fact_Loan (
    LoanFactKey      INT IDENTITY(1,1) PRIMARY KEY,
    LoanKey          INT NOT NULL,
    CustomerKey      INT NOT NULL,
    BranchKey        INT NOT NULL,
    StartDateKey     INT NOT NULL,
    PrincipalAmount  DECIMAL(18,2) NOT NULL,
    OutstandingBalance DECIMAL(18,2) NOT NULL,
    DaysSinceStart   INT NOT NULL,
    IsDelinquent     BIT NOT NULL DEFAULT 0,
    IsDefaulted      BIT NOT NULL DEFAULT 0,
    FOREIGN KEY (LoanKey)      REFERENCES Dim_Loan(LoanKey),
    FOREIGN KEY (CustomerKey)  REFERENCES Dim_Customer(CustomerKey),
    FOREIGN KEY (BranchKey)    REFERENCES Dim_Branch(BranchKey),
    FOREIGN KEY (StartDateKey) REFERENCES Dim_Date(DateKey)
);
GO

-- -----------------------------------------------------------------------------
-- 2. Bridge Table — Joint account ownership (M:N customer ↔ account)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.Bridge_AccountCustomer', 'U') IS NULL
CREATE TABLE dbo.Bridge_AccountCustomer (
    AccountKey   INT NOT NULL,
    CustomerKey  INT NOT NULL,
    OwnershipPct DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    Role         VARCHAR(20) NOT NULL,
    PRIMARY KEY (AccountKey, CustomerKey),
    FOREIGN KEY (AccountKey)  REFERENCES Dim_Account(AccountKey),
    FOREIGN KEY (CustomerKey) REFERENCES Dim_Customer(CustomerKey)
);
GO

-- -----------------------------------------------------------------------------
-- 3. Factless Fact — Customer-Branch-Day touchpoints (no measure, only event)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.Factless_BranchVisit', 'U') IS NULL
CREATE TABLE dbo.Factless_BranchVisit (
    VisitKey      INT IDENTITY(1,1) PRIMARY KEY,
    DateKey       INT NOT NULL,
    CustomerKey   INT NOT NULL,
    BranchKey     INT NOT NULL,
    FOREIGN KEY (DateKey)     REFERENCES Dim_Date(DateKey),
    FOREIGN KEY (CustomerKey) REFERENCES Dim_Customer(CustomerKey),
    FOREIGN KEY (BranchKey)   REFERENCES Dim_Branch(BranchKey)
);
GO

-- -----------------------------------------------------------------------------
-- 4. Junk Dimension — collapse low-cardinality flags
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.Dim_Junk_TxnFlags', 'U') IS NULL
CREATE TABLE dbo.Dim_Junk_TxnFlags (
    JunkKey      INT IDENTITY(1,1) PRIMARY KEY,
    IsWeekend    BIT NOT NULL,
    IsHighValue  BIT NOT NULL,
    Channel      VARCHAR(20) NOT NULL,
    UNIQUE (IsWeekend, IsHighValue, Channel)
);
GO

-- Populate junk dimension
IF NOT EXISTS (SELECT 1 FROM dbo.Dim_Junk_TxnFlags)
INSERT INTO dbo.Dim_Junk_TxnFlags (IsWeekend, IsHighValue, Channel)
SELECT w.b, h.b, c.ch
FROM (VALUES (0),(1)) w(b)
CROSS JOIN (VALUES (0),(1)) h(b)
CROSS JOIN (VALUES ('Branch'),('Online'),('Mobile'),('ATM')) c(ch);
GO

-- -----------------------------------------------------------------------------
-- 5. Late-Arriving Dimension placeholder
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM dbo.Dim_Customer WHERE CustomerID = -1)
INSERT INTO dbo.Dim_Customer (CustomerID, FirstName, LastName, AgeGroup, City, State, EffectiveDate, ExpirationDate, IsCurrent)
VALUES (-1, 'UNKNOWN', 'UNKNOWN', 'UNK', 'UNK', 'UNK', '1900-01-01', NULL, 1);
GO

-- -----------------------------------------------------------------------------
-- 6. Materialized Aggregates (for sub-second dashboard queries)
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.Agg_Branch_Monthly', 'U') IS NULL
CREATE TABLE dbo.Agg_Branch_Monthly (
    BranchKey         INT NOT NULL,
    YearMonth         INT NOT NULL,
    TransactionCount  BIGINT NOT NULL,
    TotalVolume       DECIMAL(20,2) NOT NULL,
    DepositVolume     DECIMAL(20,2) NOT NULL,
    WithdrawalVolume  DECIMAL(20,2) NOT NULL,
    UniqueCustomers   INT NOT NULL,
    PRIMARY KEY (BranchKey, YearMonth)
);
GO

IF OBJECT_ID('dbo.Agg_Customer_Annual', 'U') IS NULL
CREATE TABLE dbo.Agg_Customer_Annual (
    CustomerKey       INT NOT NULL,
    YearValue         INT NOT NULL,
    TransactionCount  BIGINT NOT NULL,
    TotalVolume       DECIMAL(20,2) NOT NULL,
    AvgTicket         DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (CustomerKey, YearValue)
);
GO

-- -----------------------------------------------------------------------------
-- 7. Aggregate Loader Procedure
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.usp_RefreshAggregates', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_RefreshAggregates;
GO
CREATE PROCEDURE dbo.usp_RefreshAggregates
AS
BEGIN
    SET NOCOUNT ON;

    TRUNCATE TABLE dbo.Agg_Branch_Monthly;
    INSERT INTO dbo.Agg_Branch_Monthly (BranchKey, YearMonth, TransactionCount, TotalVolume, DepositVolume, WithdrawalVolume, UniqueCustomers)
    SELECT
        f.BranchKey,
        d.Year * 100 + d.Month                                                 AS YearMonth,
        COUNT_BIG(*)                                                           AS TransactionCount,
        SUM(f.Amount)                                                          AS TotalVolume,
        SUM(CASE WHEN f.TransactionType = 'Deposit'    THEN f.Amount ELSE 0 END) AS DepositVolume,
        SUM(CASE WHEN f.TransactionType = 'Withdrawal' THEN f.Amount ELSE 0 END) AS WithdrawalVolume,
        COUNT(DISTINCT f.CustomerKey)                                          AS UniqueCustomers
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.BranchKey, d.Year, d.Month;

    TRUNCATE TABLE dbo.Agg_Customer_Annual;
    INSERT INTO dbo.Agg_Customer_Annual (CustomerKey, YearValue, TransactionCount, TotalVolume, AvgTicket)
    SELECT
        f.CustomerKey,
        d.Year,
        COUNT_BIG(*),
        SUM(f.Amount),
        AVG(f.Amount)
    FROM dbo.Fact_Transaction f
    JOIN dbo.Dim_Date d ON d.DateKey = f.DateKey
    GROUP BY f.CustomerKey, d.Year;
END;
GO

PRINT 'Advanced dimensional objects and aggregate loader installed.';
GO
