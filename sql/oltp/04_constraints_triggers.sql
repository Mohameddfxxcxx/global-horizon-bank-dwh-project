-- =============================================================================
-- Global Horizon Bank — OLTP Constraints, Triggers & Audit
-- =============================================================================
-- Purpose: Enforce data integrity, build an immutable audit trail, and provide
-- deadlock-safe operations for the transactional core.
-- =============================================================================

USE GlobalHorizon_OLTP;
GO

-- -----------------------------------------------------------------------------
-- 1. Audit Schema and Tables
-- -----------------------------------------------------------------------------
IF SCHEMA_ID('audit') IS NULL EXEC('CREATE SCHEMA audit AUTHORIZATION dbo;');
GO

IF OBJECT_ID('audit.AccountChanges', 'U') IS NOT NULL DROP TABLE audit.AccountChanges;
CREATE TABLE audit.AccountChanges (
    AuditID         BIGINT IDENTITY(1,1) PRIMARY KEY,
    AccountID       BIGINT          NOT NULL,
    ChangeType      VARCHAR(10)     NOT NULL CHECK (ChangeType IN ('INSERT','UPDATE','DELETE')),
    OldBalance      DECIMAL(18, 2)  NULL,
    NewBalance      DECIMAL(18, 2)  NULL,
    OldStatus       VARCHAR(20)     NULL,
    NewStatus       VARCHAR(20)     NULL,
    ChangedBy       SYSNAME         NOT NULL DEFAULT SUSER_SNAME(),
    ChangedAtUTC    DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
    HostName        SYSNAME         NOT NULL DEFAULT HOST_NAME(),
    AppName         SYSNAME         NULL     DEFAULT APP_NAME()
);
GO

IF OBJECT_ID('audit.TransactionLog', 'U') IS NOT NULL DROP TABLE audit.TransactionLog;
CREATE TABLE audit.TransactionLog (
    AuditID         BIGINT IDENTITY(1,1) PRIMARY KEY,
    TransactionID   UNIQUEIDENTIFIER NOT NULL,
    AccountID       BIGINT           NOT NULL,
    TransactionType VARCHAR(50)      NOT NULL,
    Amount          DECIMAL(18, 2)   NOT NULL,
    LoggedAtUTC     DATETIME2(3)     NOT NULL DEFAULT SYSUTCDATETIME(),
    LoggedBy        SYSNAME          NOT NULL DEFAULT SUSER_SNAME()
);
GO

-- -----------------------------------------------------------------------------
-- 2. Additional Business Constraints
-- -----------------------------------------------------------------------------
-- Prevent self-transfers
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Transactions_NoSelfTransfer')
    ALTER TABLE Transactions
        ADD CONSTRAINT CK_Transactions_NoSelfTransfer
        CHECK (RelatedAccountID IS NULL OR RelatedAccountID <> AccountID);

-- Customers cannot be born in the future or before 1900
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Customers_DOB_Range')
    ALTER TABLE Customers
        ADD CONSTRAINT CK_Customers_DOB_Range
        CHECK (DateOfBirth BETWEEN '1900-01-01' AND CAST(GETDATE() AS DATE));

-- Loans interest rate must be reasonable
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Loans_InterestRange')
    ALTER TABLE Loans
        ADD CONSTRAINT CK_Loans_InterestRange
        CHECK (InterestRate BETWEEN 0.01 AND 99.99);

-- Email must contain '@' (lightweight format check)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Customers_EmailFormat')
    ALTER TABLE Customers
        ADD CONSTRAINT CK_Customers_EmailFormat
        CHECK (Email LIKE '%_@_%._%');
GO

-- -----------------------------------------------------------------------------
-- 3. Trigger: Audit Account changes
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.tr_Accounts_Audit', 'TR') IS NOT NULL DROP TRIGGER dbo.tr_Accounts_Audit;
GO
CREATE TRIGGER dbo.tr_Accounts_Audit
ON dbo.Accounts
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- INSERT
    IF EXISTS (SELECT 1 FROM inserted) AND NOT EXISTS (SELECT 1 FROM deleted)
    BEGIN
        INSERT INTO audit.AccountChanges (AccountID, ChangeType, NewBalance, NewStatus)
        SELECT AccountID, 'INSERT', Balance, Status FROM inserted;
        RETURN;
    END;

    -- DELETE
    IF NOT EXISTS (SELECT 1 FROM inserted) AND EXISTS (SELECT 1 FROM deleted)
    BEGIN
        INSERT INTO audit.AccountChanges (AccountID, ChangeType, OldBalance, OldStatus)
        SELECT AccountID, 'DELETE', Balance, Status FROM deleted;
        RETURN;
    END;

    -- UPDATE
    INSERT INTO audit.AccountChanges (AccountID, ChangeType, OldBalance, NewBalance, OldStatus, NewStatus)
    SELECT i.AccountID, 'UPDATE', d.Balance, i.Balance, d.Status, i.Status
    FROM inserted i
    JOIN deleted  d ON i.AccountID = d.AccountID
    WHERE i.Balance <> d.Balance OR i.Status <> d.Status;
END;
GO

-- -----------------------------------------------------------------------------
-- 4. Trigger: Log every transaction to immutable audit
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.tr_Transactions_Audit', 'TR') IS NOT NULL DROP TRIGGER dbo.tr_Transactions_Audit;
GO
CREATE TRIGGER dbo.tr_Transactions_Audit
ON dbo.Transactions
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO audit.TransactionLog (TransactionID, AccountID, TransactionType, Amount)
    SELECT TransactionID, AccountID, TransactionType, Amount FROM inserted;
END;
GO

-- -----------------------------------------------------------------------------
-- 5. Trigger: Prevent transactions on closed/suspended accounts
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.tr_Transactions_AccountStatusGuard', 'TR') IS NOT NULL
    DROP TRIGGER dbo.tr_Transactions_AccountStatusGuard;
GO
CREATE TRIGGER dbo.tr_Transactions_AccountStatusGuard
ON dbo.Transactions
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Accounts a ON a.AccountID = i.AccountID
        WHERE a.Status <> 'Active'
    )
    BEGIN
        RAISERROR('Cannot post a transaction to a non-Active account.', 16, 1);
        RETURN;
    END;

    INSERT INTO dbo.Transactions
        (TransactionID, AccountID, TransactionType, Amount, TransactionDate, Description, RelatedAccountID)
    SELECT TransactionID, AccountID, TransactionType, Amount, TransactionDate, Description, RelatedAccountID
    FROM inserted;
END;
GO

PRINT 'OLTP constraints, triggers, and audit objects installed.';
GO
