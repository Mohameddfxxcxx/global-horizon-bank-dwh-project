-- ==========================================
-- Phase 7: Advanced Modeling Concepts
-- Global Horizon Bank - OLAP System
-- ==========================================

USE GlobalHorizon_DWH;
GO

/*
ADVANCED MODELING: Slowly Changing Dimensions (SCD Type 2)
Concept: We track changes in customer information over time (e.g., when a customer moves to a new state).
Instead of overwriting their old record (Type 1), we insert a new row with new EffectiveDates.
*/

-- 1. Insert initial customer record (Day 1)
INSERT INTO Dim_Customer (CustomerID, FirstName, LastName, AgeGroup, City, State, EffectiveDate, ExpirationDate, IsCurrent)
VALUES (101, 'John', 'Doe', '30-45', 'Los Angeles', 'CA', '2023-01-01', NULL, 1);

-- 2. Observe the current state
SELECT * FROM Dim_Customer WHERE CustomerID = 101;

/*
Result:
CustomerKey: 1, CustomerID: 101, State: CA, EffectiveDate: 2023-01-01, ExpirationDate: NULL, IsCurrent: 1
*/

-- 3. Customer moves to New York (Day 200)
-- Step 3a: Expire the old record
UPDATE Dim_Customer
SET ExpirationDate = '2023-07-20',
    IsCurrent = 0
WHERE CustomerID = 101 AND IsCurrent = 1;

-- Step 3b: Insert the new record
INSERT INTO Dim_Customer (CustomerID, FirstName, LastName, AgeGroup, City, State, EffectiveDate, ExpirationDate, IsCurrent)
VALUES (101, 'John', 'Doe', '30-45', 'New York', 'NY', '2023-07-21', NULL, 1);

-- 4. Observe the SCD Type 2 history
SELECT CustomerKey, CustomerID, State, EffectiveDate, ExpirationDate, IsCurrent 
FROM Dim_Customer 
WHERE CustomerID = 101;

/*
Result:
CustomerKey: 1, State: CA, Effective: 2023-01-01, Expiration: 2023-07-20, IsCurrent: 0 (Historic record)
CustomerKey: 2, State: NY, Effective: 2023-07-21, Expiration: NULL, IsCurrent: 1       (Active record)

Business Value:
When querying transactions from March 2023, they will link to CustomerKey = 1 (CA).
Transactions from August 2023 will link to CustomerKey = 2 (NY).
This ensures geographic revenue reporting remains historically accurate.
*/
GO
