# -*- coding: utf-8 -*-
"""Global Horizon Bank Dashboard

This Streamlit app loads the banking data warehouse either from CSV files (local
fallback) or from a SQL Server database. It builds a merged dataframe that
contains transactions, accounts, customers and branches. Additional derived
features – age groups, weekend flag and time‑grain columns – are calculated on
the fly. A dedicated **Loans** tab visualises loan portfolios.

The app is designed to run both locally (`streamlit run dashboard/app.py`) and
on Streamlit Cloud (the CSV files are bundled with the repo; the SQL connection
will be skipped when the driver is unavailable).
"""

import os
import random
from datetime import datetime
from typing import Tuple, List, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

# Optional SQL driver – will be used only if available
try:
    import pymssql
    _PYMSSQL_AVAILABLE = True
except ImportError:
    _PYMSSQL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Global Horizon Bank Dashboard",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for theme-aware premium feel
st.markdown("""
    <style>
    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    
    /* Expander styling */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(128, 128, 128, 0.1) !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important;
        background-color: var(--secondary-background-color) !important;
        margin-bottom: 10px !important;
        border-radius: 12px !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--secondary-background-color);
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏦 Global Horizon Bank Analytics")
st.markdown("### Data Warehouse Executive Dashboard")

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _parse_date(col: pd.Series) -> pd.Series:
    """Parse a date column safely, returning a datetime dtype."""
    return pd.to_datetime(col, errors="coerce")

def derive_agegroup(dob: pd.Series) -> pd.Series:
    """Derive an age‑group label from a date‑of‑birth series.
    Groups: 18‑24, 25‑35, 36‑50, 51+ (based on today).
    """
    today = pd.Timestamp("today")
    age = (today - dob).dt.days // 365
    bins = [0, 24, 35, 50, 150]
    labels = ["18-24", "25-35", "36-50", "51+"]
    return pd.cut(age, bins=bins, labels=labels, right=False)

def is_weekend(date_series: pd.Series) -> pd.Series:
    """Return True for Saturday / Sunday values."""
    return date_series.dt.weekday.isin([5, 6])

def delta_label(current_value: float, previous_value: float, mode: str) -> str:
    if previous_value == 0:
        return "n/a"
    delta_pct = ((current_value - previous_value) / previous_value) * 100
    unit = "amount" if mode == "Sum" else "count"
    return f"{delta_pct:+.1f}% vs previous {unit}"

def generate_recommendations(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    full_df: pd.DataFrame,
    mode: str,
) -> List[Dict]:
    recommendations = []
    
    current_sum = current_df["Amount"].sum() if not current_df.empty else 0.0
    previous_sum = previous_df["Amount"].sum() if not previous_df.empty else 0.0
    current_count = len(current_df)
    previous_count = len(previous_df)
    
    current_metric = current_sum if mode == "Sum" else float(current_count)
    previous_metric = previous_sum if mode == "Sum" else float(previous_count)

    global_avg_ticket = full_df["Amount"].mean() if not full_df.empty else 0.0
    current_avg_ticket = current_df["Amount"].mean() if not current_df.empty else 0.0

    if current_df.empty:
        return [{
            "severity": "Low",
            "title": "Insufficient data under current filters",
            "why": "The current selection has no transactions to evaluate.",
            "action": "Expand date, branch, or transaction filters to generate recommendations."
        }]

    weekend_share = float(current_df["IsWeekend"].mean() * 100)
    if weekend_share >= 40:
        recommendations.append({
            "severity": "High",
            "title": "Rebalance weekend staffing and liquidity windows",
            "why": f"Weekend activity is {weekend_share:.1f}% of selected transactions.",
            "action": "Increase weekend support coverage and adjust branch cash planning."
        })

    branch_metric = aggregate_by(current_df, "BranchName", mode, metric_label="Metric")
    if not branch_metric.empty and current_metric > 0:
        top_branch = branch_metric.sort_values("Metric", ascending=False).iloc[0]
        concentration = float((top_branch["Metric"] / current_metric) * 100)
        if concentration >= 35:
            recommendations.append({
                "severity": "High",
                "title": "Reduce branch concentration risk",
                "why": f"{top_branch['BranchName']} contributes {concentration:.1f}% of selected {mode.lower()} volume.",
                "action": "Transfer successful branch practices to nearby branches and monitor dependency."
            })

    if previous_metric > 0:
        trend_change = ((current_metric - previous_metric) / previous_metric) * 100
        if trend_change <= -10:
            recommendations.append({
                "severity": "High",
                "title": "Address declining momentum",
                "why": f"Selected period {mode.lower()} is down {abs(trend_change):.1f}% versus prior period.",
                "action": "Deploy retention campaigns for impacted customer/account segments."
            })
        elif trend_change >= 10:
            recommendations.append({
                "severity": "Medium",
                "title": "Scale capacity for growth areas",
                "why": f"Selected period {mode.lower()} is up {trend_change:.1f}% versus prior period.",
                "action": "Allocate service capacity to high-growth governorates and transaction types."
            })

    if current_avg_ticket > 0 and global_avg_ticket > 0 and current_avg_ticket >= (global_avg_ticket * 1.2):
        recommendations.append({
            "severity": "Medium",
            "title": "Launch premium offers for high-value segments",
            "why": f"Average ticket (${current_avg_ticket:,.2f}) exceeds global baseline (${global_avg_ticket:,.2f}).",
            "action": "Promote premium bundles and relationship-driven products for this segment."
        })

    tx_mix = aggregate_by(current_df, "TransactionType", "Count", metric_label="TxCount")
    if not tx_mix.empty and tx_mix["TxCount"].sum() > 0:
        tx_mix = tx_mix.sort_values("TxCount", ascending=False)
        top_tx = tx_mix.iloc[0]
        tx_share = float((top_tx["TxCount"] / tx_mix["TxCount"].sum()) * 100)
        if tx_share >= 50:
            recommendations.append({
                "severity": "Low",
                "title": "Diversify transaction mix",
                "why": f"{top_tx['TransactionType']} represents {tx_share:.1f}% of transaction count.",
                "action": "Bundle adjacent services to diversify customer transaction behavior."
            })

    if not recommendations:
        recommendations.append({
            "severity": "Low",
            "title": "Performance appears balanced",
            "why": "No major concentration or trend anomalies were detected for this slice.",
            "action": "Continue monitoring with branch and account-level drill-downs."
        })

    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    recommendations.sort(key=lambda item: severity_order.get(item["severity"], 3))
    return recommendations

# ---------------------------------------------------------------------------
# Data loading – CSV with SQL fallback (CACHED)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Load the core fact table and a backup demo dataframe.

    Returns:
        merged_df: The fully joined dataframe used throughout the app.
        loans_merged: A merged loan dataframe.
        source: A string indicating the data source ("CSV", "SQL", or "Demo").
    """
    # Paths to raw CSV files
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
    tx_path = os.path.join(base_path, "transactions.csv")
    acc_path = os.path.join(base_path, "accounts.csv")
    cust_path = os.path.join(base_path, "customers.csv")
    branch_path = os.path.join(base_path, "branches.csv")
    loans_path = os.path.join(base_path, "loans.csv")

    source = "CSV"
    
    # -------------------------------------------------------------------
    # Attempt CSV loading first
    # -------------------------------------------------------------------
    try:
        if not all(os.path.exists(p) for p in [tx_path, acc_path, cust_path, branch_path, loans_path]):
            raise FileNotFoundError("One or more CSV files missing.")
        
        tx = pd.read_csv(tx_path)
        acc = pd.read_csv(acc_path)
        cust = pd.read_csv(cust_path)
        br = pd.read_csv(branch_path)
        loans = pd.read_csv(loans_path)
    except Exception:
        tx = acc = cust = br = loans = None

    # -------------------------------------------------------------------
    # If any CSV failed, try SQL (only when driver is present)
    # -------------------------------------------------------------------
    if any(df is None for df in [tx, acc, cust, br]):
        if not _PYMSSQL_AVAILABLE:
            df, l_df = demo_dataset()
            return df, l_df, "Demo"
        
        try:
            source = "SQL"
            # Build connection string from env vars (matching docker-compose defaults)
            server = os.getenv("SQLSERVER_HOST", "localhost")
            port = int(os.getenv("SQLSERVER_PORT", "21433"))
            user = os.getenv("SQLSERVER_USER", "sa")
            password = os.getenv("SQLSERVER_PASSWORD", "MyStrongPass123!")
            database = os.getenv("SQLSERVER_DB", "GlobalHorizon_DWH")
            
            conn = pymssql.connect(
                server=server,
                port=port,
                user=user,
                password=password,
                database=database,
                timeout=5
            )
            tx = pd.read_sql("SELECT * FROM dbo.Transactions", conn)
            acc = pd.read_sql("SELECT * FROM dbo.Accounts", conn)
            cust = pd.read_sql("SELECT * FROM dbo.Customers", conn)
            br = pd.read_sql("SELECT * FROM dbo.Branches", conn)
            loans = pd.read_sql("SELECT * FROM dbo.Loans", conn)
            conn.close()
        except Exception:
            df, l_df = demo_dataset()
            return df, l_df, "Demo"

    # -------------------------------------------------------------------
    # Merge all tables
    # -------------------------------------------------------------------
    # Parse dates
    tx["TransactionDate"] = _parse_date(tx["TransactionDate"])
    acc["OpenDate"] = _parse_date(acc["OpenDate"])
    cust["DateOfBirth"] = _parse_date(cust["DateOfBirth"])
    loans["StartDate"] = _parse_date(loans["StartDate"])

    # Rename accounts Status -> AccountStatus before merge
    acc = acc.rename(columns={"Status": "AccountStatus"})

    # Join transaction tables
    merged = (
        tx.merge(acc, on="AccountID", how="left")
        .merge(cust, on="CustomerID", how="left", suffixes=("", "_cust"))
        .merge(br, on="BranchID", how="left", suffixes=("", "_br"))
    )

    # Derive helper columns
    merged["Year"] = merged["TransactionDate"].dt.year
    merged["Quarter"] = merged["TransactionDate"].dt.quarter
    merged["MonthName"] = merged["TransactionDate"].dt.month_name()
    merged["BranchState"] = merged["State_br"] if "State_br" in merged.columns else merged["State"]
    merged["AgeGroup"] = derive_agegroup(merged["DateOfBirth"])
    merged["IsWeekend"] = is_weekend(merged["TransactionDate"])

    # Pre-merge loans
    loans_merged = loans.merge(br, on="BranchID", how="left", suffixes=("", "_br"))
    loans_merged["LoanAgeDays"] = (pd.Timestamp("today") - loans_merged["StartDate"]).dt.days

    return merged, loans_merged, source

# ---------------------------------------------------------------------------
# Demo dataset – fallback
# ---------------------------------------------------------------------------

def demo_dataset() -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = 2000
    date_range = pd.date_range(start="2022-01-01", end="2024-12-31", freq="D")
    transaction_types = ["Deposit", "Withdrawal", "Transfer", "Payment"]
    branches = [
        ("Mansoura Branch", "Dakahlia"),
        ("Port Said Branch", "PortSaid"),
        ("Alexandria Branch", "Alexandria"),
        ("Cairo Branch", "Cairo"),
        ("Luxor Branch", "Luxor"),
    ]
    age_groups = ["18-24", "25-35", "36-50", "51+"]
    account_types = ["Savings", "Checking", "Business", "Credit"]
    account_statuses = ["Active", "Inactive", "Dormant"]
    loan_types = ["Personal", "Mortgage", "Auto", "Student"]
    loan_statuses = ["Active", "Paid", "Defaulted"]

    records = []
    for _ in range(rows):
        tx_date = random.choice(date_range)
        branch_name, branch_state = random.choice(branches)
        tx_type = random.choices(transaction_types, weights=[0.30, 0.28, 0.24, 0.18], k=1)[0]
        amount = round(random.expovariate(1 / 1500), 2)
        records.append({
            "TransactionDate": tx_date,
            "TransactionType": tx_type,
            "Amount": amount,
            "BranchName": branch_name,
            "BranchState": branch_state,
            "CustomerID": random.randint(1, 1000),
            "AccountID": random.randint(1, 1200),
            "AccountType": random.choice(account_types),
            "AccountStatus": random.choice(account_statuses),
            "AgeGroup": random.choice(age_groups),
            "IsWeekend": tx_date.weekday() in (5, 6),
        })
    df = pd.DataFrame.from_records(records)
    df["Year"] = df["TransactionDate"].dt.year
    df["Quarter"] = df["TransactionDate"].dt.quarter
    df["MonthName"] = df["TransactionDate"].dt.month_name()
    
    loan_records = []
    for _ in range(rows // 10):
        start_date = random.choice(date_range)
        loan_records.append({
            "LoanType": random.choice(loan_types),
            "PrincipalAmount": round(random.uniform(5000, 500000), 2),
            "Status": random.choice(loan_statuses),
            "StartDate": start_date,
            "LoanAgeDays": (pd.Timestamp("today") - start_date).days,
            "BranchID": random.randint(1, 5)
        })
    loans_df = pd.DataFrame.from_records(loan_records)
    
    return df, loans_df

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

# Load Data
with st.spinner("Loading Data Warehouse..."):
    merged_df, loans_df, data_source = load_data()

# Sidebar
st.sidebar.image("https://img.icons8.com/fluency/96/bank.png", width=80)
st.sidebar.header("Control Panel")

# Data Source Info
source_color = {"CSV": "green", "SQL": "blue", "Demo": "orange"}.get(data_source, "gray")
st.sidebar.markdown(f"**Data Source:** :{source_color}[{data_source}]")

# Filters
with st.sidebar.expander("📅 Date Range", expanded=True):
    min_date = merged_df["TransactionDate"].min().date()
    max_date = merged_df["TransactionDate"].max().date()
    date_range = st.date_input(
        "Select Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # Handle single date selection vs range selection
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_date = end_date = date_range[0]
    else:
        start_date = end_date = date_range

with st.sidebar.expander("🔍 Filters", expanded=False):
    selected_types = st.multiselect(
        "Transaction Types",
        options=sorted(merged_df["TransactionType"].unique().tolist()),
        default=merged_df["TransactionType"].unique().tolist(),
    )
    selected_states = st.multiselect(
        "Governorates",
        options=sorted(merged_df["BranchState"].unique().tolist()),
        default=merged_df["BranchState"].unique().tolist(),
    )
    selected_age_groups = st.multiselect(
        "Age Groups",
        options=sorted(merged_df["AgeGroup"].dropna().unique().tolist()),
        default=merged_df["AgeGroup"].dropna().unique().tolist(),
    )
    selected_account_types = st.multiselect(
        "Account Types",
        options=sorted(merged_df["AccountType"].unique().tolist()),
        default=merged_df["AccountType"].unique().tolist(),
    )

with st.sidebar.expander("📊 Metric Settings", expanded=False):
    max_amt = float(merged_df["Amount"].max())
    selected_amount = st.slider(
        "Amount Range ($)",
        0.0, max_amt, (0.0, max_amt)
    )
    metric_mode = st.radio("Primary Metric", ["Sum", "Count"], index=0)
    time_grain = st.selectbox("Time Grain", ["Year", "Quarter", "Month"]) 
    top_n = st.slider("Top N Ranking", 3, 20, 10)

if st.sidebar.button("🔄 Refresh Data", width='stretch'):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Filter Data
# ---------------------------------------------------------------------------
mask = (
    (merged_df["TransactionDate"] >= pd.Timestamp(start_date))
    & (merged_df["TransactionDate"] <= pd.Timestamp(end_date))
    & merged_df["TransactionType"].isin(selected_types)
    & merged_df["BranchState"].isin(selected_states)
    & merged_df["AgeGroup"].isin(selected_age_groups)
    & merged_df["AccountType"].isin(selected_account_types)
    & (merged_df["Amount"] >= selected_amount[0])
    & (merged_df["Amount"] <= selected_amount[1])
)
filtered_df = merged_df[mask]

# Delta period
period_days = max((end_date - start_date).days + 1, 1)
prev_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_days - 1)

prev_mask = (
    (merged_df["TransactionDate"] >= prev_start)
    & (merged_df["TransactionDate"] <= prev_end)
    & merged_df["TransactionType"].isin(selected_types)
    & merged_df["BranchState"].isin(selected_states)
    & merged_df["AgeGroup"].isin(selected_age_groups)
    & merged_df["AccountType"].isin(selected_account_types)
    & (merged_df["Amount"] >= selected_amount[0])
    & (merged_df["Amount"] <= selected_amount[1])
)
previous_df = merged_df[prev_mask]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def aggregate_by(df: pd.DataFrame, group_col: str, mode: str, metric_label: str = "Metric") -> pd.DataFrame:
    if mode == "Sum":
        agg = df.groupby(group_col, observed=False)["Amount"].sum().reset_index(name=metric_label)
    else:
        agg = df.groupby(group_col, observed=False).size().reset_index(name=metric_label)
    return agg

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_loans, tab_recommendations, tab_data = st.tabs([
    "📈 Overview",
    "💰 Loans",
    "💡 Recommendations",
    "📋 Raw Data",
])

with tab_overview:
    # KPI Metrics
    st.subheader("Key Performance Indicators")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    curr_tx = float(len(filtered_df))
    curr_vol = float(filtered_df["Amount"].sum())
    curr_avg = float(filtered_df["Amount"].mean()) if not filtered_df.empty else 0.0
    curr_acc = float(filtered_df["AccountID"].nunique())
    curr_wknd = float(filtered_df["IsWeekend"].mean() * 100) if not filtered_df.empty else 0.0

    prev_tx = float(len(previous_df))
    prev_vol = float(previous_df["Amount"].sum())
    prev_avg = float(previous_df["Amount"].mean()) if not previous_df.empty else 0.0
    prev_acc = float(previous_df["AccountID"].nunique())
    prev_wknd = float(previous_df["IsWeekend"].mean() * 100) if not previous_df.empty else 0.0

    k1.metric("Transactions", f"{curr_tx:,.0f}", delta_label(curr_tx, prev_tx, "Count"))
    k2.metric("Volume ($)", f"${curr_vol:,.0f}", delta_label(curr_vol, prev_vol, "Sum"))
    k3.metric("Avg Ticket", f"${curr_avg:,.2f}", delta_label(curr_avg, prev_avg, "Sum"))
    k4.metric("Active Accounts", f"{curr_acc:,.0f}", delta_label(curr_acc, prev_acc, "Count"))
    k5.metric("Weekend Share", f"{curr_wknd:,.1f}%", f"{(curr_wknd - prev_wknd):+.1f}%" if prev_wknd > 0 else None)

    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Top {top_n} Branches")
        top_br = aggregate_by(filtered_df, "BranchName", metric_mode).nlargest(top_n, "Metric")
        fig1 = px.bar(top_br, x="BranchName", y="Metric", color="Metric", color_continuous_scale="Viridis", height=400)
        st.plotly_chart(fig1, width='stretch')
    with c2:
        st.subheader("Transaction Mix")
        mix = aggregate_by(filtered_df, "TransactionType", metric_mode)
        fig2 = px.pie(mix, names="TransactionType", values="Metric", hole=0.4, height=400)
        st.plotly_chart(fig2, width='stretch')

    st.subheader(f"Transaction Trend ({time_grain})")
    if time_grain == "Year":
        trend = filtered_df.groupby("Year")["Amount"].sum().reset_index(name="Metric")
        trend["Label"] = trend["Year"].astype(str)
    elif time_grain == "Quarter":
        trend = filtered_df.groupby(["Year", "Quarter"])["Amount"].sum().reset_index(name="Metric")
        trend["Label"] = trend["Year"].astype(str) + " Q" + trend["Quarter"].astype(str)
    else:
        trend = filtered_df.groupby(["Year", "MonthName"])["Amount"].sum().reset_index(name="Metric")
        trend["Label"] = trend["MonthName"] + " " + trend["Year"].astype(str)
    
    fig3 = px.line(trend, x="Label", y="Metric", markers=True)
    st.plotly_chart(fig3, width='stretch')

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Age Group Distribution")
        age_dist = aggregate_by(filtered_df, "AgeGroup", metric_mode)
        fig4 = px.bar(age_dist, x="AgeGroup", y="Metric", color="AgeGroup", height=350)
        st.plotly_chart(fig4, width='stretch')
    with c4:
        st.subheader("Weekend vs Weekday")
        w_dist = aggregate_by(filtered_df, "IsWeekend", metric_mode)
        w_dist["Label"] = w_dist["IsWeekend"].map({True: "Weekend", False: "Weekday"})
        fig5 = px.pie(w_dist, names="Label", values="Metric", height=350)
        st.plotly_chart(fig5, width='stretch')

with tab_loans:
    if loans_df.empty:
        st.info("No loan data available.")
    else:
        st.subheader("Loan Portfolio Analysis")
        l1, l2 = st.columns(2)
        with l1:
            l_type = loans_df.groupby("LoanType")["PrincipalAmount"].sum().reset_index()
            fig_l1 = px.bar(l_type, x="LoanType", y="PrincipalAmount", color="LoanType", title="Principal by Type")
            st.plotly_chart(fig_l1, width='stretch')
        with l2:
            l_stat = loans_df["Status"].value_counts().reset_index()
            l_stat.columns = ["Status", "Count"]
            fig_l2 = px.pie(l_stat, names="Status", values="Count", title="Status Distribution")
            st.plotly_chart(fig_l2, width='stretch')

with tab_recommendations:
    st.subheader("Strategic Insights")
    recs = generate_recommendations(filtered_df, previous_df, merged_df, metric_mode)
    icons = {"High": "🚨", "Medium": "⚠️", "Low": "✅"}
    for r in recs:
        with st.expander(f"{icons.get(r['severity'], 'ℹ️')} {r['severity']} - {r['title']}", expanded=(r["severity"] == "High")):
            st.markdown(f"**Insight:** {r['why']}")
            st.markdown(f"**Action:** {r['action']}")

with tab_data:
    st.subheader("Filtered Dataset")
    cols = ["TransactionDate", "BranchName", "TransactionType", "Amount", "AccountType", "AccountStatus", "AgeGroup"]
    st.dataframe(filtered_df[cols].sort_values("TransactionDate", ascending=False), width='stretch')
    
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Filtered CSV", data=csv, file_name="bank_data.csv", mime="text/csv")

st.markdown("---")
st.caption(f"Global Horizon Bank DW Dashboard | Connected via {data_source} | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
