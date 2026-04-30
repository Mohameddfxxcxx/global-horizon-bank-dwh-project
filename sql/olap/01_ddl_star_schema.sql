-- ==========================================
-- Phase 6: Data Warehouse Design (Star Schema)
-- Global Horizon Bank - OLAP System
-- ==========================================

USE master;
GO

IF DB_ID('GlobalHorizon_DWH') IS NOT NULL
BEGIN
    ALTER DATABASE GlobalHorizon_DWH SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE GlobalHorizon_DWH;
END
GO

CREATE DATABASE GlobalHorizon_DWH;
GO

USE GlobalHorizon_DWH;
GO

-- ==========================================
-- Dimension Tables
-- ==========================================

-- 1. Dim_Date (Time Dimension)
CREATE TABLE Dim_Date (
    DateKey INT PRIMARY KEY, -- Format YYYYMMDD
    FullDate DATE NOT NULL,
    Year INT NOT NULL,
    Quarter INT NOT NULL,
    Month INT NOT NULL,
    MonthName VARCHAR(20) NOT NULL,
    DayOfMonth INT NOT NULL,
    DayOfWeek INT NOT NULL,
    DayName VARCHAR(20) NOT NULL,
    IsWeekend BIT NOT NULL
);

-- 2. Dim_Branch
CREATE TABLE Dim_Branch (
    BranchKey INT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    BranchID INT NOT NULL, -- Business Key
    BranchName VARCHAR(100) NOT NULL,
    City VARCHAR(100) NOT NULL,
    State VARCHAR(10) NOT NULL,
    ZipCode VARCHAR(20) NOT NULL
);

-- 3. Dim_Customer (SCD Type 2)
CREATE TABLE Dim_Customer (
    CustomerKey INT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    CustomerID INT NOT NULL, -- Business Key
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    AgeGroup VARCHAR(20),
    City VARCHAR(100) NOT NULL,
    State VARCHAR(10) NOT NULL,
    -- SCD Type 2 tracking columns
    EffectiveDate DATE NOT NULL,
    ExpirationDate DATE NULL,
    IsCurrent BIT NOT NULL DEFAULT 1
);

-- 4. Dim_Account
CREATE TABLE Dim_Account (
    AccountKey INT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    AccountID BIGINT NOT NULL, -- Business Key
    AccountType VARCHAR(50) NOT NULL,
    OpenDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL
);

-- ==========================================
-- Fact Tables
-- ==========================================

-- 1. Fact_Transaction (Transactional Grain)
CREATE TABLE Fact_Transaction (
    TransactionKey INT IDENTITY(1,1) PRIMARY KEY,
    TransactionID UNIQUEIDENTIFIER NOT NULL, -- Degenerate Dimension
    DateKey INT NOT NULL,
    CustomerKey INT NOT NULL,
    AccountKey INT NOT NULL,
    BranchKey INT NOT NULL,
    TransactionType VARCHAR(50) NOT NULL,
    Amount DECIMAL(18, 2) NOT NULL, -- Additive Measure
    FOREIGN KEY (DateKey) REFERENCES Dim_Date(DateKey),
    FOREIGN KEY (CustomerKey) REFERENCES Dim_Customer(CustomerKey),
    FOREIGN KEY (AccountKey) REFERENCES Dim_Account(AccountKey),
    FOREIGN KEY (BranchKey) REFERENCES Dim_Branch(BranchKey)
);

-- 2. Fact_Daily_Balance (Periodic Snapshot Grain)
CREATE TABLE Fact_Daily_Balance (
    SnapshotDateKey INT NOT NULL,
    AccountKey INT NOT NULL,
    CustomerKey INT NOT NULL,
    BranchKey INT NOT NULL,
    EndOfDayBalance DECIMAL(18, 2) NOT NULL, -- Semi-additive Measure
    PRIMARY KEY (SnapshotDateKey, AccountKey),
    FOREIGN KEY (SnapshotDateKey) REFERENCES Dim_Date(DateKey),
    FOREIGN KEY (AccountKey) REFERENCES Dim_Account(AccountKey),
    FOREIGN KEY (CustomerKey) REFERENCES Dim_Customer(CustomerKey),
    FOREIGN KEY (BranchKey) REFERENCES Dim_Branch(BranchKey)
);
GO
