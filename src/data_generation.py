import os
import random
from datetime import datetime

import pandas as pd
from faker import Faker

# Initialize Faker
fake = Faker()
Faker.seed(42)
random.seed(42)

# Configuration
NUM_CUSTOMERS = 10000
NUM_BRANCHES = 50
NUM_EMPLOYEES = 200
NUM_ACCOUNTS = 12000
NUM_LOANS = 3000
NUM_TRANSACTIONS = 100000
TRANSACTION_START_DATE = datetime(2022, 1, 1)
TRANSACTION_END_DATE = datetime(2026, 12, 31, 23, 59, 59)

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, '../data/raw'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Egypt-focused reference data
EGYPT_FIRST_NAMES = [
    "Ahmed", "Mohamed", "Mahmoud", "Mostafa", "Omar", "Youssef", "Karim", "Hassan",
    "Mina", "Sherif", "Tarek", "Amr", "Hany", "Ibrahim", "Ayman", "Khaled",
    "Fatma", "Mona", "Nour", "Aya", "Salma", "Mariam", "Heba", "Yasmin",
    "Rania", "Dina", "Nesma", "Doaa", "Hoda", "Sara", "Laila", "Rehab"
]
EGYPT_LAST_NAMES = [
    "Hassan", "Mahmoud", "Abdelrahman", "Fathy", "Sayed", "Naguib", "Shawky", "Samir",
    "Farag", "Younes", "Mostafa", "Amin", "Adel", "Gamal", "Kamal", "Zaki",
    "Morsi", "Helmy", "Nassar", "Saleh", "Saad", "Ashraf", "Rashad", "Izzat"
]
EGYPT_CITIES = [
    ("Cairo", "Cairo"), ("Giza", "Giza"), ("Alexandria", "Alexandria"), ("Mansoura", "Dakahlia"),
    ("Tanta", "Gharbia"), ("Zagazig", "Sharqia"), ("Ismailia", "Ismailia"), ("Port Said", "PortSaid"),
    ("Suez", "Suez"), ("Fayoum", "Fayoum"), ("Beni Suef", "BeniSuef"), ("Minya", "Minya"),
    ("Assiut", "Assiut"), ("Sohag", "Sohag"), ("Qena", "Qena"), ("Luxor", "Luxor"),
    ("Aswan", "Aswan"), ("Damietta", "Damietta"), ("Kafr El Sheikh", "KafrElShk"), ("Hurghada", "RedSea")
]

def generate_branches():
    print("Generating Branches...")
    branches = []
    for _ in range(NUM_BRANCHES):
        city, governorate = random.choice(EGYPT_CITIES)
        branches.append({
            'BranchID': fake.unique.random_int(min=100, max=999),
            'BranchName': f"{city} Branch",
            'Address': f"{random.randint(1, 120)} Nile Street, {city}",
            'City': city,
            'State': governorate,
            'ZipCode': f"{random.randint(10000, 99999)}"
        })
    df = pd.DataFrame(branches)
    df.to_csv(f"{OUTPUT_DIR}/branches.csv", index=False)
    return df

def generate_employees(branches_df):
    print("Generating Employees...")
    employees = []
    branch_ids = branches_df['BranchID'].tolist()
    for i in range(1, NUM_EMPLOYEES + 1):
        employees.append({
            'EmployeeID': i,
            'FirstName': random.choice(EGYPT_FIRST_NAMES),
            'LastName': random.choice(EGYPT_LAST_NAMES),
            'Role': random.choice(['Teller', 'Manager', 'Loan Officer', 'Customer Service']),
            'BranchID': random.choice(branch_ids),
            'HireDate': fake.date_between(start_date='-10y', end_date='today')
        })
    df = pd.DataFrame(employees)
    df.to_csv(f"{OUTPUT_DIR}/employees.csv", index=False)
    return df

def generate_customers():
    print("Generating Customers...")
    customers = []
    for i in range(1, NUM_CUSTOMERS + 1):
        first_name = random.choice(EGYPT_FIRST_NAMES)
        last_name = random.choice(EGYPT_LAST_NAMES)
        city, governorate = random.choice(EGYPT_CITIES)
        email_name = f"{first_name}.{last_name}.{i}".lower().replace(" ", "")
        customers.append({
            'CustomerID': i,
            'FirstName': first_name,
            'LastName': last_name,
            'Email': f"{email_name}@bankmail.eg",
            'Phone': f"+20{random.randint(1000000000, 1299999999)}",
            'Address': f"{random.randint(1, 250)} Tahrir Road, {city}",
            'City': city,
            'State': governorate,
            'ZipCode': f"{random.randint(10000, 99999)}",
            'DateOfBirth': fake.date_of_birth(minimum_age=18, maximum_age=90),
            'JoinDate': fake.date_between(start_date='-5y', end_date='today')
        })
    df = pd.DataFrame(customers)
    df.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)
    return df

def generate_accounts(customers_df, branches_df):
    print("Generating Accounts...")
    accounts = []
    customer_ids = customers_df['CustomerID'].tolist()
    branch_ids = branches_df['BranchID'].tolist()

    for i in range(1, NUM_ACCOUNTS + 1):
        customer_id = random.choice(customer_ids)
        open_date = customers_df[customers_df['CustomerID'] == customer_id]['JoinDate'].values[0]
        # Ensure account open date is after join date
        if isinstance(open_date, str):
            open_date = datetime.strptime(open_date, '%Y-%m-%d').date()
        accounts.append({
            'AccountID': fake.unique.random_number(digits=10),
            'CustomerID': customer_id,
            'BranchID': random.choice(branch_ids),
            'AccountType': random.choice(['Checking', 'Savings', 'Credit']),
            'Balance': round(random.uniform(100.0, 50000.0), 2),
            'OpenDate': fake.date_between(start_date=open_date, end_date='today'),
            'Status': random.choices(['Active', 'Closed', 'Suspended'], weights=[0.9, 0.08, 0.02])[0]
        })
    df = pd.DataFrame(accounts)
    df.to_csv(f"{OUTPUT_DIR}/accounts.csv", index=False)
    return df

def generate_loans(customers_df, branches_df):
    print("Generating Loans...")
    loans = []
    customer_ids = customers_df['CustomerID'].tolist()
    branch_ids = branches_df['BranchID'].tolist()

    for i in range(1, NUM_LOANS + 1):
        principal = round(random.uniform(5000, 500000), 2)
        rate = round(random.uniform(3.5, 12.5), 2)
        term = random.choice([12, 24, 36, 48, 60, 120, 360])
        loans.append({
            'LoanID': i,
            'CustomerID': random.choice(customer_ids),
            'BranchID': random.choice(branch_ids),
            'LoanType': random.choice(['Mortgage', 'Auto', 'Personal', 'Student']),
            'PrincipalAmount': principal,
            'InterestRate': rate,
            'TermMonths': term,
            'StartDate': fake.date_between(start_date='-5y', end_date='today'),
            'Status': random.choices(['Active', 'Paid', 'Defaulted'], weights=[0.8, 0.15, 0.05])[0]
        })
    df = pd.DataFrame(loans)
    df.to_csv(f"{OUTPUT_DIR}/loans.csv", index=False)
    return df

def random_transaction_datetime(start_dt: datetime, end_dt: datetime) -> datetime:
    """Return a uniformly sampled datetime between start_dt and end_dt."""
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())
    return datetime.fromtimestamp(random.randint(start_ts, end_ts))


def generate_transactions(accounts_df):
    print("Generating Transactions...")
    transactions = []
    active_accounts = accounts_df[accounts_df['Status'] == 'Active']['AccountID'].tolist()

    for i in range(1, NUM_TRANSACTIONS + 1):
        tx_type = random.choices(['Deposit', 'Withdrawal', 'Transfer', 'Payment'], weights=[0.4, 0.3, 0.2, 0.1])[0]
        account_id = random.choice(active_accounts)
        amount = round(random.uniform(5.0, 5000.0), 2)

        related_account = None
        if tx_type == 'Transfer':
            related_account = random.choice(active_accounts)
            while related_account == account_id:
                related_account = random.choice(active_accounts)

        transactions.append({
            'TransactionID': fake.unique.uuid4(),
            'AccountID': account_id,
            'TransactionType': tx_type,
            'Amount': amount,
            'TransactionDate': random_transaction_datetime(
                TRANSACTION_START_DATE,
                TRANSACTION_END_DATE
            ).strftime('%Y-%m-%d %H:%M:%S'),
            'Description': fake.sentence(nb_words=4),
            'RelatedAccountID': related_account
        })
    df = pd.DataFrame(transactions)
    df.to_csv(f"{OUTPUT_DIR}/transactions.csv", index=False)
    return df

if __name__ == "__main__":
    print("Starting Global Horizon Bank Data Generation...")
    branches_df = generate_branches()
    employees_df = generate_employees(branches_df)
    customers_df = generate_customers()
    accounts_df = generate_accounts(customers_df, branches_df)
    loans_df = generate_loans(customers_df, branches_df)
    transactions_df = generate_transactions(accounts_df)
    print("Data Generation Complete! Files saved to data/raw/")
