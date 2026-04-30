-- ==========================================
-- Phase 5: ETL Design
-- Global Horizon Bank - ETL Pipelines
-- ==========================================

USE GlobalHorizon_DWH;
GO

/*
ETL PROCEDURE: Extract, Transform, Load from OLTP to DWH
This script defines the Stored Procedures to populate the Star Schema.
*/

CREATE OR ALTER PROCEDURE sp_ETL_Dim_Customer
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Insert new customers (SCD Type 2 Initial Load)
    INSERT INTO GlobalHorizon_DWH.dbo.Dim_Customer 
        (CustomerID, FirstName, LastName, AgeGroup, City, State, EffectiveDate, ExpirationDate, IsCurrent)
    SELECT 
        c.CustomerID,
        c.FirstName,
        c.LastName,
        CASE 
            WHEN DATEDIFF(YEAR, c.DateOfBirth, GETDATE()) < 25 THEN '18-24'
            WHEN DATEDIFF(YEAR, c.DateOfBirth, GETDATE()) BETWEEN 25 AND 35 THEN '25-35'
            WHEN DATEDIFF(YEAR, c.DateOfBirth, GETDATE()) BETWEEN 36 AND 50 THEN '36-50'
            ELSE '51+' 
        END AS AgeGroup,
        c.City,
        c.State,
        GETDATE() AS EffectiveDate,
        NULL AS ExpirationDate,
        1 AS IsCurrent
    FROM 
        GlobalHorizon_OLTP.dbo.Customers c
    WHERE 
        NOT EXISTS (
            SELECT 1 FROM GlobalHorizon_DWH.dbo.Dim_Customer dc 
            WHERE dc.CustomerID = c.CustomerID
        );

    -- Future updates would expire old records and insert new ones.
END;
GO


CREATE OR ALTER PROCEDURE sp_ETL_Dim_Branch
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO GlobalHorizon_DWH.dbo.Dim_Branch (BranchID, BranchName, City, State, ZipCode)
    SELECT 
        BranchID, BranchName, City, State, ZipCode
    FROM 
        GlobalHorizon_OLTP.dbo.Branches b
    WHERE 
        NOT EXISTS (
            SELECT 1 FROM GlobalHorizon_DWH.dbo.Dim_Branch db WHERE db.BranchID = b.BranchID
        );
END;
GO


CREATE OR ALTER PROCEDURE sp_ETL_Dim_Account
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO GlobalHorizon_DWH.dbo.Dim_Account (AccountID, AccountType, OpenDate, Status)
    SELECT 
        AccountID, AccountType, OpenDate, Status
    FROM 
        GlobalHorizon_OLTP.dbo.Accounts a
    WHERE 
        NOT EXISTS (
            SELECT 1 FROM GlobalHorizon_DWH.dbo.Dim_Account da WHERE da.AccountID = a.AccountID
        );
END;
GO

CREATE OR ALTER PROCEDURE sp_ETL_Dim_Date
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Build Dim_Date to fully cover transaction history.
    DECLARE @StartDate DATE;
    DECLARE @EndDate DATE;

    SELECT
        @StartDate = MIN(CAST(t.TransactionDate AS DATE)),
        @EndDate = MAX(CAST(t.TransactionDate AS DATE))
    FROM GlobalHorizon_OLTP.dbo.Transactions t;

    -- Fallback for empty source tables.
    IF @StartDate IS NULL OR @EndDate IS NULL
    BEGIN
        SET @StartDate = DATEADD(YEAR, -1, CAST(GETDATE() AS DATE));
        SET @EndDate = CAST(GETDATE() AS DATE);
    END
    
    WHILE @StartDate <= @EndDate
    BEGIN
        DECLARE @DateKey INT = CAST(CONVERT(VARCHAR(8), @StartDate, 112) AS INT);
        
        IF NOT EXISTS (SELECT 1 FROM GlobalHorizon_DWH.dbo.Dim_Date WHERE DateKey = @DateKey)
        BEGIN
            INSERT INTO GlobalHorizon_DWH.dbo.Dim_Date 
            (DateKey, FullDate, Year, Quarter, Month, MonthName, DayOfMonth, DayOfWeek, DayName, IsWeekend)
            VALUES (
                @DateKey,
                @StartDate,
                YEAR(@StartDate),
                DATEPART(qq, @StartDate),
                MONTH(@StartDate),
                DATENAME(mm, @StartDate),
                DAY(@StartDate),
                DATEPART(dw, @StartDate),
                DATENAME(dw, @StartDate),
                CASE WHEN DATEPART(dw, @StartDate) IN (1, 7) THEN 1 ELSE 0 END
            );
        END
        SET @StartDate = DATEADD(dd, 1, @StartDate);
    END
END;
GO


CREATE OR ALTER PROCEDURE sp_ETL_Fact_Transaction
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Incremental Load Pattern: Load transactions that don't exist in the fact table yet.
    INSERT INTO GlobalHorizon_DWH.dbo.Fact_Transaction 
        (TransactionID, DateKey, CustomerKey, AccountKey, BranchKey, TransactionType, Amount)
    SELECT 
        t.TransactionID,
        CAST(CONVERT(VARCHAR(8), t.TransactionDate, 112) AS INT) AS DateKey,
        dc.CustomerKey,
        da.AccountKey,
        db.BranchKey,
        t.TransactionType,
        t.Amount
    FROM 
        GlobalHorizon_OLTP.dbo.Transactions t
    JOIN 
        GlobalHorizon_OLTP.dbo.Accounts a ON t.AccountID = a.AccountID
    JOIN 
        GlobalHorizon_DWH.dbo.Dim_Customer dc ON a.CustomerID = dc.CustomerID AND dc.IsCurrent = 1
    JOIN 
        GlobalHorizon_DWH.dbo.Dim_Account da ON t.AccountID = da.AccountID
    JOIN 
        GlobalHorizon_DWH.dbo.Dim_Branch db ON a.BranchID = db.BranchID
    WHERE 
        NOT EXISTS (
            SELECT 1 FROM GlobalHorizon_DWH.dbo.Fact_Transaction ft 
            WHERE ft.TransactionID = t.TransactionID
        );
END;
GO

-- Execute the ETL Pipeline
/*
EXEC sp_ETL_Dim_Customer;
EXEC sp_ETL_Dim_Branch;
EXEC sp_ETL_Dim_Account;
-- Ensure Dim_Date is populated before running Fact load
EXEC sp_ETL_Fact_Transaction;
*/
