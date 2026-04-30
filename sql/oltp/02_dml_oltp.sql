-- ==========================================
-- Phase 3: OLTP Workload Simulation (DML)
-- Global Horizon Bank - Transactional System
-- ==========================================

USE GlobalHorizon_OLTP;
GO

/*
BULK INSERT INSTRUCTIONS
The synthetic data is generated via Python into the `data/raw/` directory.
You can import the data using SQL Server BULK INSERT.
Example paths should be updated to your absolute local paths.
*/

/*
BULK INSERT Branches
FROM 'C:\path\to\data\raw\branches.csv'
WITH (FORMAT='CSV', FIRSTROW=2);

BULK INSERT Customers
FROM 'C:\path\to\data\raw\customers.csv'
WITH (FORMAT='CSV', FIRSTROW=2);

BULK INSERT Employees
FROM 'C:\path\to\data\raw\employees.csv'
WITH (FORMAT='CSV', FIRSTROW=2);

BULK INSERT Accounts
FROM 'C:\path\to\data\raw\accounts.csv'
WITH (FORMAT='CSV', FIRSTROW=2);

BULK INSERT Loans
FROM 'C:\path\to\data\raw\loans.csv'
WITH (FORMAT='CSV', FIRSTROW=2);

BULK INSERT Transactions
FROM 'C:\path\to\data\raw\transactions.csv'
WITH (FORMAT='CSV', FIRSTROW=2);
*/

-- Transaction simulation (Phase 3 CRUD operations)

-- 1. INSERT: New account opening
BEGIN TRAN;
    DECLARE @NewAccountID BIGINT = 9998887776;
    DECLARE @CustomerID INT = 1; -- Assuming customer 1 exists
    
    INSERT INTO Accounts (AccountID, CustomerID, BranchID, AccountType, Balance, OpenDate, Status)
    VALUES (@NewAccountID, @CustomerID, 100, 'Checking', 500.00, GETDATE(), 'Active');
COMMIT TRAN;

-- 2. UPDATE: Deposit transaction updating balance
BEGIN TRAN;
    DECLARE @TxAmount DECIMAL(18,2) = 1500.00;
    
    INSERT INTO Transactions (TransactionID, AccountID, TransactionType, Amount, TransactionDate, Description)
    VALUES (NEWID(), 9998887776, 'Deposit', @TxAmount, GETDATE(), 'Branch Deposit');
    
    UPDATE Accounts
    SET Balance = Balance + @TxAmount
    WHERE AccountID = 9998887776;
COMMIT TRAN;

-- 3. DELETE (Soft Delete equivalent): Suspending an account
BEGIN TRAN;
    UPDATE Accounts
    SET Status = 'Suspended'
    WHERE AccountID = 9998887776;
COMMIT TRAN;
GO
