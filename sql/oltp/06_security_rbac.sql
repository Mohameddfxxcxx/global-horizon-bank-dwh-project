-- =============================================================================
-- Global Horizon Bank — RBAC, Row-Level Security & Dynamic Data Masking
-- =============================================================================
-- Implements least-privilege access, branch-bounded row-level security and
-- PII masking for analyst-class principals.
-- =============================================================================

USE GlobalHorizon_OLTP;
GO

-- -----------------------------------------------------------------------------
-- 1. Database Roles
-- -----------------------------------------------------------------------------
IF DATABASE_PRINCIPAL_ID('role_executive') IS NULL CREATE ROLE role_executive;
IF DATABASE_PRINCIPAL_ID('role_engineer')  IS NULL CREATE ROLE role_engineer;
IF DATABASE_PRINCIPAL_ID('role_analyst')   IS NULL CREATE ROLE role_analyst;
IF DATABASE_PRINCIPAL_ID('role_teller')    IS NULL CREATE ROLE role_teller;
GO

-- -----------------------------------------------------------------------------
-- 2. Role Permissions
-- -----------------------------------------------------------------------------
-- Engineer: full schema control over operational tables
GRANT SELECT, INSERT, UPDATE ON SCHEMA::dbo TO role_engineer;
GRANT EXECUTE ON SCHEMA::dbo TO role_engineer;

-- Analyst: read-only with masked PII
GRANT SELECT ON SCHEMA::dbo TO role_analyst;
DENY  INSERT, UPDATE, DELETE ON SCHEMA::dbo TO role_analyst;

-- Teller: only execute money-movement procs
GRANT EXECUTE ON dbo.usp_OpenAccount      TO role_teller;
GRANT EXECUTE ON dbo.usp_PostTransaction  TO role_teller;
GRANT EXECUTE ON dbo.usp_TransferFunds    TO role_teller;
DENY  SELECT  ON dbo.audit.AccountChanges TO role_teller;

-- Executive: read-only across analytics surface
GRANT SELECT ON SCHEMA::dbo TO role_executive;
GO

-- -----------------------------------------------------------------------------
-- 3. Dynamic Data Masking (PII)
-- -----------------------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.masked_columns
    WHERE object_id = OBJECT_ID('dbo.Customers') AND name = 'Email'
)
ALTER TABLE dbo.Customers ALTER COLUMN Email ADD MASKED WITH (FUNCTION = 'email()');

IF NOT EXISTS (
    SELECT 1 FROM sys.masked_columns
    WHERE object_id = OBJECT_ID('dbo.Customers') AND name = 'Phone'
)
ALTER TABLE dbo.Customers ALTER COLUMN Phone ADD MASKED WITH (FUNCTION = 'partial(0, "+20XXXXXX", 4)');

IF NOT EXISTS (
    SELECT 1 FROM sys.masked_columns
    WHERE object_id = OBJECT_ID('dbo.Customers') AND name = 'Address'
)
ALTER TABLE dbo.Customers ALTER COLUMN Address ADD MASKED WITH (FUNCTION = 'default()');
GO

-- Analyst sees masked, executive/engineer see real values
GRANT UNMASK TO role_engineer;
GRANT UNMASK TO role_executive;
GO

-- -----------------------------------------------------------------------------
-- 4. Row-Level Security — branch-bounded access for tellers
-- -----------------------------------------------------------------------------
IF SCHEMA_ID('rls') IS NULL EXEC('CREATE SCHEMA rls AUTHORIZATION dbo;');
GO

-- Branch context table: maps DB user → BranchID
IF OBJECT_ID('rls.UserBranch', 'U') IS NULL
CREATE TABLE rls.UserBranch (
    UserName  SYSNAME PRIMARY KEY,
    BranchID  INT     NOT NULL
);
GO

-- Predicate function — a teller may only see accounts at their assigned branch
IF OBJECT_ID('rls.fn_BranchAccessPredicate', 'IF') IS NOT NULL DROP FUNCTION rls.fn_BranchAccessPredicate;
GO
CREATE FUNCTION rls.fn_BranchAccessPredicate(@BranchID AS INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN
    SELECT 1 AS allowed
    WHERE
        IS_MEMBER('role_executive') = 1
        OR IS_MEMBER('role_engineer') = 1
        OR IS_MEMBER('db_owner')      = 1
        OR EXISTS (
            SELECT 1
            FROM rls.UserBranch ub
            WHERE ub.UserName = SUSER_SNAME() AND ub.BranchID = @BranchID
        );
GO

-- Apply security policy
IF EXISTS (SELECT 1 FROM sys.security_policies WHERE name = 'sp_BranchAccess')
    DROP SECURITY POLICY rls.sp_BranchAccess;
GO
CREATE SECURITY POLICY rls.sp_BranchAccess
    ADD FILTER PREDICATE rls.fn_BranchAccessPredicate(BranchID) ON dbo.Accounts,
    ADD FILTER PREDICATE rls.fn_BranchAccessPredicate(BranchID) ON dbo.Loans,
    ADD FILTER PREDICATE rls.fn_BranchAccessPredicate(BranchID) ON dbo.Employees
WITH (STATE = OFF);  -- enable in production
GO

PRINT 'Security objects installed. Enable RLS policy with: ALTER SECURITY POLICY rls.sp_BranchAccess WITH (STATE = ON);';
GO
