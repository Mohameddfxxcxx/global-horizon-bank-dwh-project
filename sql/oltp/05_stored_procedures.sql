-- =============================================================================
-- Global Horizon Bank — OLTP Stored Procedures
-- =============================================================================
-- Production-grade procedures for money movement, account lifecycle, and
-- defensive transactional programming with deadlock-safe retry semantics.
-- =============================================================================

USE GlobalHorizon_OLTP;
GO

-- -----------------------------------------------------------------------------
-- usp_TransferFunds — Atomic, deadlock-resilient inter-account transfer
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.usp_TransferFunds', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_TransferFunds;
GO
CREATE PROCEDURE dbo.usp_TransferFunds
    @FromAccountID  BIGINT,
    @ToAccountID    BIGINT,
    @Amount         DECIMAL(18, 2),
    @Description    VARCHAR(255) = N'Internal transfer',
    @TransactionID  UNIQUEIDENTIFIER = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

    IF @Amount <= 0 BEGIN RAISERROR('Amount must be positive.', 16, 1); RETURN; END;
    IF @FromAccountID = @ToAccountID BEGIN RAISERROR('Cannot transfer to the same account.', 16, 1); RETURN; END;

    DECLARE @Retry  INT = 0;
    DECLARE @MaxRetry INT = 3;
    DECLARE @Success BIT = 0;

    WHILE @Retry < @MaxRetry AND @Success = 0
    BEGIN
        BEGIN TRY
            BEGIN TRAN;

            -- Lock accounts in a deterministic order to prevent deadlocks
            DECLARE @FirstID BIGINT  = CASE WHEN @FromAccountID < @ToAccountID THEN @FromAccountID ELSE @ToAccountID END;
            DECLARE @SecondID BIGINT = CASE WHEN @FromAccountID < @ToAccountID THEN @ToAccountID   ELSE @FromAccountID END;

            DECLARE @FirstBal DECIMAL(18,2), @SecondBal DECIMAL(18,2);

            SELECT @FirstBal  = Balance FROM dbo.Accounts WITH (UPDLOCK, HOLDLOCK) WHERE AccountID = @FirstID;
            SELECT @SecondBal = Balance FROM dbo.Accounts WITH (UPDLOCK, HOLDLOCK) WHERE AccountID = @SecondID;

            IF @FirstBal IS NULL OR @SecondBal IS NULL
            BEGIN
                RAISERROR('One of the accounts does not exist.', 16, 1);
            END;

            -- Verify funds (only check the source)
            DECLARE @FromBalance DECIMAL(18,2) =
                CASE WHEN @FromAccountID = @FirstID THEN @FirstBal ELSE @SecondBal END;

            IF @FromBalance < @Amount
            BEGIN
                RAISERROR('Insufficient funds.', 16, 1);
            END;

            -- Apply movements
            UPDATE dbo.Accounts SET Balance = Balance - @Amount WHERE AccountID = @FromAccountID;
            UPDATE dbo.Accounts SET Balance = Balance + @Amount WHERE AccountID = @ToAccountID;

            SET @TransactionID = NEWID();
            INSERT INTO dbo.Transactions (TransactionID, AccountID, TransactionType, Amount, TransactionDate, Description, RelatedAccountID)
            VALUES (@TransactionID, @FromAccountID, 'Transfer', @Amount, GETDATE(), @Description, @ToAccountID);

            COMMIT TRAN;
            SET @Success = 1;
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRAN;
            -- Retry only on deadlock victim
            IF ERROR_NUMBER() = 1205 AND @Retry < @MaxRetry - 1
            BEGIN
                SET @Retry = @Retry + 1;
                WAITFOR DELAY '00:00:00.250';
                CONTINUE;
            END;
            DECLARE @msg NVARCHAR(2048) = ERROR_MESSAGE();
            RAISERROR(@msg, 16, 1);
            RETURN;
        END CATCH;
    END;
END;
GO

-- -----------------------------------------------------------------------------
-- usp_OpenAccount — Idempotent account opening
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.usp_OpenAccount', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_OpenAccount;
GO
CREATE PROCEDURE dbo.usp_OpenAccount
    @CustomerID     INT,
    @BranchID       INT,
    @AccountType    VARCHAR(50),
    @InitialDeposit DECIMAL(18, 2) = 0,
    @AccountID      BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRAN;

        IF NOT EXISTS (SELECT 1 FROM dbo.Customers WHERE CustomerID = @CustomerID)
            RAISERROR('Customer not found.', 16, 1);

        IF NOT EXISTS (SELECT 1 FROM dbo.Branches WHERE BranchID = @BranchID)
            RAISERROR('Branch not found.', 16, 1);

        SET @AccountID = ABS(CHECKSUM(NEWID())) % 9000000000 + 1000000000;

        INSERT INTO dbo.Accounts (AccountID, CustomerID, BranchID, AccountType, Balance, OpenDate, Status)
        VALUES (@AccountID, @CustomerID, @BranchID, @AccountType, @InitialDeposit, CAST(GETDATE() AS DATE), 'Active');

        IF @InitialDeposit > 0
        BEGIN
            INSERT INTO dbo.Transactions (TransactionID, AccountID, TransactionType, Amount, TransactionDate, Description)
            VALUES (NEWID(), @AccountID, 'Deposit', @InitialDeposit, GETDATE(), N'Initial deposit');
        END;

        COMMIT TRAN;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;
        DECLARE @msg NVARCHAR(2048) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
    END CATCH;
END;
GO

-- -----------------------------------------------------------------------------
-- usp_PostTransaction — Single posting with status validation
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.usp_PostTransaction', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_PostTransaction;
GO
CREATE PROCEDURE dbo.usp_PostTransaction
    @AccountID       BIGINT,
    @TransactionType VARCHAR(50),
    @Amount          DECIMAL(18, 2),
    @Description     VARCHAR(255) = NULL,
    @TransactionID   UNIQUEIDENTIFIER = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRAN;

        IF NOT EXISTS (SELECT 1 FROM dbo.Accounts WHERE AccountID = @AccountID AND Status = 'Active')
            RAISERROR('Account is not active.', 16, 1);

        IF @TransactionType = 'Withdrawal' OR @TransactionType = 'Payment'
        BEGIN
            DECLARE @Balance DECIMAL(18,2);
            SELECT @Balance = Balance FROM dbo.Accounts WITH (UPDLOCK) WHERE AccountID = @AccountID;
            IF @Balance < @Amount RAISERROR('Insufficient funds.', 16, 1);
            UPDATE dbo.Accounts SET Balance = Balance - @Amount WHERE AccountID = @AccountID;
        END
        ELSE IF @TransactionType = 'Deposit'
        BEGIN
            UPDATE dbo.Accounts SET Balance = Balance + @Amount WHERE AccountID = @AccountID;
        END;

        SET @TransactionID = NEWID();
        INSERT INTO dbo.Transactions (TransactionID, AccountID, TransactionType, Amount, TransactionDate, Description)
        VALUES (@TransactionID, @AccountID, @TransactionType, @Amount, GETDATE(), @Description);

        COMMIT TRAN;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;
        DECLARE @msg NVARCHAR(2048) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
    END CATCH;
END;
GO

PRINT 'OLTP stored procedures installed.';
GO
