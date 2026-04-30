-- ==========================================
-- Phase 2: OLTP Database Design
-- Global Horizon Bank - Transactional System
-- ==========================================

USE master;
GO

IF DB_ID('GlobalHorizon_OLTP') IS NOT NULL
BEGIN
    ALTER DATABASE GlobalHorizon_OLTP SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE GlobalHorizon_OLTP;
END
GO

CREATE DATABASE GlobalHorizon_OLTP;
GO

USE GlobalHorizon_OLTP;
GO

-- 1. Branches Table
CREATE TABLE Branches (
    BranchID INT PRIMARY KEY,
    BranchName VARCHAR(100) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(100) NOT NULL,
    State VARCHAR(10) NOT NULL,
    ZipCode VARCHAR(20) NOT NULL
);

-- 2. Employees Table
CREATE TABLE Employees (
    EmployeeID INT PRIMARY KEY,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    Role VARCHAR(50) NOT NULL,
    BranchID INT NOT NULL,
    HireDate DATE NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES Branches(BranchID)
);

-- 3. Customers Table
CREATE TABLE Customers (
    CustomerID INT PRIMARY KEY,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    Phone VARCHAR(50) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(100) NOT NULL,
    State VARCHAR(10) NOT NULL,
    ZipCode VARCHAR(20) NOT NULL,
    DateOfBirth DATE NOT NULL,
    JoinDate DATE NOT NULL
);

-- 4. Accounts Table
CREATE TABLE Accounts (
    AccountID BIGINT PRIMARY KEY,
    CustomerID INT NOT NULL,
    BranchID INT NOT NULL,
    AccountType VARCHAR(50) NOT NULL CHECK (AccountType IN ('Checking', 'Savings', 'Credit')),
    Balance DECIMAL(18, 2) NOT NULL DEFAULT 0.00,
    OpenDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL CHECK (Status IN ('Active', 'Closed', 'Suspended')),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (BranchID) REFERENCES Branches(BranchID)
);

-- 5. Loans Table
CREATE TABLE Loans (
    LoanID INT PRIMARY KEY,
    CustomerID INT NOT NULL,
    BranchID INT NOT NULL,
    LoanType VARCHAR(50) NOT NULL,
    PrincipalAmount DECIMAL(18, 2) NOT NULL CHECK (PrincipalAmount > 0),
    InterestRate DECIMAL(5, 2) NOT NULL CHECK (InterestRate > 0),
    TermMonths INT NOT NULL CHECK (TermMonths > 0),
    StartDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL CHECK (Status IN ('Active', 'Paid', 'Defaulted')),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (BranchID) REFERENCES Branches(BranchID)
);

-- 6. Transactions Table
CREATE TABLE Transactions (
    TransactionID UNIQUEIDENTIFIER PRIMARY KEY,
    AccountID BIGINT NOT NULL,
    TransactionType VARCHAR(50) NOT NULL CHECK (TransactionType IN ('Deposit', 'Withdrawal', 'Transfer', 'Payment')),
    Amount DECIMAL(18, 2) NOT NULL CHECK (Amount > 0),
    TransactionDate DATETIME NOT NULL DEFAULT GETDATE(),
    Description VARCHAR(255),
    RelatedAccountID BIGINT NULL,
    FOREIGN KEY (AccountID) REFERENCES Accounts(AccountID),
    FOREIGN KEY (RelatedAccountID) REFERENCES Accounts(AccountID)
);

-- 7. Account_Customers (Many-to-Many Bridge Table for joint accounts)
CREATE TABLE Account_Customers (
    AccountID BIGINT NOT NULL,
    CustomerID INT NOT NULL,
    Role VARCHAR(50) NOT NULL CHECK (Role IN ('Primary', 'Joint')),
    PRIMARY KEY (AccountID, CustomerID),
    FOREIGN KEY (AccountID) REFERENCES Accounts(AccountID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
);
GO
