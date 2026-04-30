import os

import pandas as pd
import pymssql

# SQL Server Configuration
SERVER = os.getenv('SQLSERVER_HOST', 'localhost')
PORT = int(os.getenv('SQLSERVER_PORT', '21433'))
USER = os.getenv('SQLSERVER_USER', 'sa')
PASSWORD = os.getenv('SQLSERVER_PASSWORD', 'MyStrongPass123!')
DATABASE_DWH = os.getenv('SQLSERVER_DB', 'GlobalHorizon_DWH')
DATA_DIR = '../data/raw'

def execute_sql_file(cursor, filepath):
    """Reads a SQL file, splits by GO, and executes the batches."""
    print(f"Executing {filepath}...")
    with open(filepath) as file:
        sql_script = file.read()

    # Split the script by 'GO' keyword to execute in batches
    batches = [b.strip() for b in sql_script.split('GO') if b.strip()]
    for batch in batches:
        try:
            cursor.execute(batch)
        except Exception as e:
            print(f"Error executing batch in {filepath}:\n{batch[:100]}...\n{e}")

def setup_databases():
    # Connect without specifying database (to create them)
    try:
        conn = pymssql.connect(server=SERVER, port=PORT, user=USER, password=PASSWORD, autocommit=True)
    except Exception as e:
        print(
            "Unable to connect to SQL Server. "
            f"Tried {SERVER}:{PORT} with user '{USER}'.\n"
            "Make sure SQL Server is running and mapped to this port.\n"
            "Tip: if using Docker, expose host port 21433 -> container 1433.\n"
            f"Original error: {e}"
        )
        return
    cursor = conn.cursor()

    try:
        # 1. Create OLTP & DWH Schemas
        base_path = os.path.dirname(__file__)
        execute_sql_file(cursor, os.path.join(base_path, '../sql/oltp/01_ddl_oltp.sql'))
        execute_sql_file(cursor, os.path.join(base_path, '../sql/olap/01_ddl_star_schema.sql'))

        # 2. Load OLTP Data via Pandas to SQL Server (GlobalHorizon_OLTP)
        print("Loading CSV data into OLTP database...")
        from sqlalchemy import create_engine
        # SQLAlchemy engine for fast pandas inserts
        engine_oltp = create_engine(
            f'mssql+pymssql://{USER}:{PASSWORD}@{SERVER}:{PORT}/GlobalHorizon_OLTP'
        )

        # Order matters due to Foreign Keys
        files_to_load = [
            ('branches.csv', 'Branches'),
            ('employees.csv', 'Employees'),
            ('customers.csv', 'Customers'),
            ('accounts.csv', 'Accounts'),
            ('loans.csv', 'Loans'),
            ('transactions.csv', 'Transactions')
        ]

        for filename, table in files_to_load:
            file_path = os.path.join(base_path, DATA_DIR, filename)
            if os.path.exists(file_path):
                print(f"  Inserting {table}...")
                df = pd.read_csv(file_path)
                df.to_sql(table, con=engine_oltp, if_exists='append', index=False)
            else:
                print(f"  Warning: {file_path} not found. Run data_generation.py first.")

        # 3. Create ETL Procedures & Execute them
        execute_sql_file(cursor, os.path.join(base_path, '../sql/etl/01_etl_procedures.sql'))

        print("Executing ETL Pipelines to populate the Data Warehouse...")
        cursor.execute(f"USE {DATABASE_DWH};")
        cursor.execute("EXEC sp_ETL_Dim_Customer;")
        cursor.execute("EXEC sp_ETL_Dim_Branch;")
        cursor.execute("EXEC sp_ETL_Dim_Account;")
        # Generate Date Dimension before Fact table
        print("  Generating Date Dimension...")
        cursor.execute("EXEC sp_ETL_Dim_Date;")

        # Fact table
        print("  Loading Fact Transactions...")
        cursor.execute("EXEC sp_ETL_Fact_Transaction;")

        print("Database setup and ETL execution completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    setup_databases()
