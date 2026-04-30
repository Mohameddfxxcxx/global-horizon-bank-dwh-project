-- =============================================================================
-- Global Horizon Bank — ETL Orchestration & Audit
-- =============================================================================
-- Master ETL pipeline with audit logging, error capture, and run-id tracing.
-- Each pipeline step records start/end timestamps, row counts, status and DQ
-- score, providing full observability and lineage.
-- =============================================================================

USE GlobalHorizon_DWH;
GO

-- -----------------------------------------------------------------------------
-- 1. ETL Audit Log
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.ETL_Audit_Log', 'U') IS NULL
CREATE TABLE dbo.ETL_Audit_Log (
    AuditID         BIGINT IDENTITY(1,1) PRIMARY KEY,
    RunID           UNIQUEIDENTIFIER NOT NULL,
    PipelineName    VARCHAR(100)   NOT NULL,
    StepName        VARCHAR(100)   NOT NULL,
    StartedAtUTC    DATETIME2(3)   NOT NULL,
    EndedAtUTC      DATETIME2(3)   NULL,
    DurationSeconds AS DATEDIFF(SECOND, StartedAtUTC, EndedAtUTC) PERSISTED,
    RowsProcessed   BIGINT         NULL,
    Status          VARCHAR(20)    NOT NULL,  -- RUNNING / SUCCESS / FAILED
    ErrorMessage    NVARCHAR(2048) NULL,
    DataQualityScore DECIMAL(5,2)  NULL
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'IX_ETL_Audit_Log_RunID'
       AND object_id = OBJECT_ID('dbo.ETL_Audit_Log')
)
    CREATE INDEX IX_ETL_Audit_Log_RunID ON dbo.ETL_Audit_Log(RunID);
GO

-- -----------------------------------------------------------------------------
-- 2. Helper: log pipeline step
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.usp_LogStep', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_LogStep;
GO
CREATE PROCEDURE dbo.usp_LogStep
    @RunID         UNIQUEIDENTIFIER,
    @PipelineName  VARCHAR(100),
    @StepName      VARCHAR(100),
    @Status        VARCHAR(20),
    @RowsProcessed BIGINT = NULL,
    @ErrorMessage  NVARCHAR(2048) = NULL,
    @DQScore       DECIMAL(5,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @Status = 'RUNNING'
    BEGIN
        INSERT INTO dbo.ETL_Audit_Log (RunID, PipelineName, StepName, StartedAtUTC, Status)
        VALUES (@RunID, @PipelineName, @StepName, SYSUTCDATETIME(), 'RUNNING');
    END
    ELSE
    BEGIN
        UPDATE dbo.ETL_Audit_Log
        SET EndedAtUTC      = SYSUTCDATETIME(),
            RowsProcessed   = COALESCE(@RowsProcessed, RowsProcessed),
            Status          = @Status,
            ErrorMessage    = @ErrorMessage,
            DataQualityScore = COALESCE(@DQScore, DataQualityScore)
        WHERE RunID = @RunID
          AND PipelineName = @PipelineName
          AND StepName = @StepName
          AND EndedAtUTC IS NULL;
    END;
END;
GO

-- -----------------------------------------------------------------------------
-- 3. Master Pipeline — orchestrates the full warehouse refresh
-- -----------------------------------------------------------------------------
IF OBJECT_ID('dbo.usp_RunMasterPipeline', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_RunMasterPipeline;
GO
CREATE PROCEDURE dbo.usp_RunMasterPipeline
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @RunID UNIQUEIDENTIFIER = NEWID();
    DECLARE @Pipe VARCHAR(100) = 'master_warehouse_refresh';
    DECLARE @Rows BIGINT;

    BEGIN TRY
        -- 1. Dim Date
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Date', 'RUNNING';
        EXEC dbo.sp_ETL_Dim_Date;
        SELECT @Rows = COUNT(*) FROM dbo.Dim_Date;
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Date', 'SUCCESS', @Rows;

        -- 2. Dim Branch
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Branch', 'RUNNING';
        EXEC dbo.sp_ETL_Dim_Branch;
        SELECT @Rows = COUNT(*) FROM dbo.Dim_Branch;
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Branch', 'SUCCESS', @Rows;

        -- 3. Dim Customer (SCD2)
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Customer', 'RUNNING';
        EXEC dbo.sp_ETL_Dim_Customer;
        SELECT @Rows = COUNT(*) FROM dbo.Dim_Customer;
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Customer', 'SUCCESS', @Rows;

        -- 4. Dim Account
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Account', 'RUNNING';
        EXEC dbo.sp_ETL_Dim_Account;
        SELECT @Rows = COUNT(*) FROM dbo.Dim_Account;
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Dim_Account', 'SUCCESS', @Rows;

        -- 5. Fact Transaction
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Fact_Transaction', 'RUNNING';
        EXEC dbo.sp_ETL_Fact_Transaction;
        SELECT @Rows = COUNT(*) FROM dbo.Fact_Transaction;
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'sp_ETL_Fact_Transaction', 'SUCCESS', @Rows;

        -- 6. Aggregates
        IF OBJECT_ID('dbo.usp_RefreshAggregates', 'P') IS NOT NULL
        BEGIN
            EXEC dbo.usp_LogStep @RunID, @Pipe, 'usp_RefreshAggregates', 'RUNNING';
            EXEC dbo.usp_RefreshAggregates;
            EXEC dbo.usp_LogStep @RunID, @Pipe, 'usp_RefreshAggregates', 'SUCCESS';
        END;
    END TRY
    BEGIN CATCH
        DECLARE @msg NVARCHAR(2048) = ERROR_MESSAGE();
        EXEC dbo.usp_LogStep @RunID, @Pipe, 'master_warehouse_refresh', 'FAILED', NULL, @msg;
        THROW;
    END CATCH;
END;
GO

PRINT 'ETL orchestration installed. Run: EXEC dbo.usp_RunMasterPipeline;';
GO
