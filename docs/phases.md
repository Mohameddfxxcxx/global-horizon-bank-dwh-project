# Global Horizon Bank - Data Architecture Phases

This document details the 9 phases of the data architecture implementation, from the Transactional System (OLTP) to the Data Warehouse (OLAP).

## Phase 1: Business Understanding
**Objective**: Understand the banking domain and establish the analytical goals.
- **Domain**: Banking System (Global Horizon Bank)
- **Problem**: Need to move from slow, locked-up transactional databases to a scalable data warehouse for rapid analytics.
- **KPIs defined**: Total Transaction Volume, Active Accounts Transacting, Customer Growth, Regional Performance.

## Phase 2: OLTP Database Design
**Objective**: Design a fully normalized transactional database.
- **Schema**: 3NF schema including `Customers`, `Branches`, `Employees`, `Accounts`, `Loans`, and `Transactions`.
- **Integrity**: Primary Keys, Foreign Keys, CHECK constraints (e.g., `Amount > 0`), and UNIQUE constraints applied.

## Phase 3: OLTP Workload Simulation
**Objective**: Populate and stress-test the database.
- **Data Generation**: Utilized Python (`Faker` & `pandas`) to generate over 100,000 transactions and 10,000 customers.
- **Simulation**: Included bulk inserts to mimic real-world load.

## Phase 4: OLTP Limitations Analysis
**Objective**: Demonstrate why OLTP fails for analytics.
- **Findings**: Heavy I/O, locking, and blocking. Complex aggregations across `Transactions`, `Accounts`, and `Branches` without pre-aggregated data cause massive index scans.

## Phase 5: ETL Design
**Objective**: Move data from OLTP to the Data Warehouse.
- **Implementation**: SQL Server Stored Procedures (`sp_ETL_Dim_Customer`, `sp_ETL_Fact_Transaction`).
- **Logic**: Handles extracting new data, transforming age into AgeGroups, and loading into the Star Schema.

## Phase 6: Data Warehouse Design
**Objective**: Build a dimensional model (Star Schema).
- **Facts**: `Fact_Transaction`
- **Dimensions**: `Dim_Customer`, `Dim_Account`, `Dim_Branch`, `Dim_Date`.
- **Measures**: Additive (Amount).

## Phase 7: Advanced Modeling Concepts
**Objective**: Handle enterprise complexities.
- **SCD Type 2**: Implemented on `Dim_Customer` using `EffectiveDate`, `ExpirationDate`, and `IsCurrent` to track geographic movement over time accurately.
- **Surrogate Keys**: Used `IDENTITY` integers instead of natural business keys for performance and history tracking.

## Phase 8: Performance & Scalability
**Objective**: Optimize for millions of rows.
- **Partitioning**: Range partitioning applied on the `DateKey` (Yearly) to enable partition pruning on queries.
- **Indexing**: Designed Clustered Columnstore Indexes for `Fact_Transaction` and Non-Clustered Indexes for Foreign Keys.

## Phase 9: Analytical Queries & Reporting
**Objective**: Extract business insights.
- **Analytics**: Window functions for Period-over-Period growth, running totals for liquidity management, and rank functions for branch performance.
- **Visualization**: Streamlit Dashboard built using Plotly for interactive executive reporting.
