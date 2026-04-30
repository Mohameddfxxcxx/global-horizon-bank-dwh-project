# -*- coding: utf-8 -*-
"""Global Horizon Bank — Executive Analytics Center.

A nine-tab Harvard-grade executive dashboard delivering a full banking
intelligence stack: KPIs, profitability, customer 360, risk & fraud, loan
portfolio, branch performance, operations, data quality, and forecasting.
"""

from __future__ import annotations

import os
import random
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page Configuration & Premium Theme
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Global Horizon Bank — Executive Analytics",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Premium KPI cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, var(--secondary-background-color) 0%, rgba(120, 144, 200, 0.08) 100%);
        padding: 18px 22px;
        border-radius: 14px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(128, 128, 128, 0.12);
    }
    [data-testid="stMetricValue"] {
        font-weight: 700;
        font-size: 1.7rem;
    }
    /* Section headers */
    h2, h3 { letter-spacing: -0.01em; }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--secondary-background-color);
        border-radius: 10px 10px 0 0;
        padding: 10px 18px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0E5BB5 0%, #1F77B4 100%);
        color: #ffffff !important;
    }
    /* Expander polish */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(128, 128, 128, 0.12) !important;
        border-radius: 12px !important;
    }
    /* Banner */
    .gh-banner {
        background: linear-gradient(135deg, #0E2A47 0%, #1F77B4 50%, #16A085 100%);
        color: #ffffff;
        padding: 28px 32px;
        border-radius: 16px;
        margin-bottom: 8px;
    }
    .gh-banner h1 { color: #ffffff; margin: 0 0 6px 0; font-weight: 700; }
    .gh-banner p { color: rgba(255,255,255,0.88); margin: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="gh-banner">
        <h1>🏦 Global Horizon Bank — Executive Analytics</h1>
        <p>Enterprise Data Warehouse Platform · Harvard Edition</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------
try:
    import pymssql
    _PYMSSQL_AVAILABLE = True
except ImportError:
    _PYMSSQL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _parse_date(col: pd.Series) -> pd.Series:
    return pd.to_datetime(col, errors="coerce")


def derive_agegroup(dob: pd.Series) -> pd.Series:
    today = pd.Timestamp("today")
    age = (today - dob).dt.days // 365
    bins = [0, 24, 35, 50, 150]
    labels = ["18-24", "25-35", "36-50", "51+"]
    return pd.cut(age, bins=bins, labels=labels, right=False)


def is_weekend(date_series: pd.Series) -> pd.Series:
    return date_series.dt.weekday.isin([5, 6])


def safe_pct(num: float, den: float) -> float:
    return float(num) / float(den) * 100 if den else 0.0


def delta_label(curr: float, prev: float, unit: str = "value") -> str:
    if not prev:
        return "n/a"
    pct = (curr - prev) / prev * 100
    return f"{pct:+.1f}% vs prior {unit}"


# ---------------------------------------------------------------------------
# Data Loading (CSV → SQL → Demo fallback)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
    paths = {
        "tx": os.path.join(base_path, "transactions.csv"),
        "acc": os.path.join(base_path, "accounts.csv"),
        "cust": os.path.join(base_path, "customers.csv"),
        "br": os.path.join(base_path, "branches.csv"),
        "loans": os.path.join(base_path, "loans.csv"),
    }
    source = "CSV"
    try:
        if not all(os.path.exists(p) for p in paths.values()):
            raise FileNotFoundError
        tx = pd.read_csv(paths["tx"])
        acc = pd.read_csv(paths["acc"])
        cust = pd.read_csv(paths["cust"])
        br = pd.read_csv(paths["br"])
        loans = pd.read_csv(paths["loans"])
    except Exception:
        tx = acc = cust = br = loans = None

    if any(df is None for df in [tx, acc, cust, br, loans]) and _PYMSSQL_AVAILABLE:
        try:
            source = "SQL"
            conn = pymssql.connect(
                server=os.getenv("SQLSERVER_HOST", "localhost"),
                port=int(os.getenv("SQLSERVER_PORT", "21433")),
                user=os.getenv("SQLSERVER_USER", "sa"),
                password=os.getenv("SQLSERVER_PASSWORD", "MyStrongPass123!"),
                database=os.getenv("SQLSERVER_DB", "GlobalHorizon_DWH"),
                timeout=5,
            )
            tx = pd.read_sql("SELECT * FROM dbo.Transactions", conn)
            acc = pd.read_sql("SELECT * FROM dbo.Accounts", conn)
            cust = pd.read_sql("SELECT * FROM dbo.Customers", conn)
            br = pd.read_sql("SELECT * FROM dbo.Branches", conn)
            loans = pd.read_sql("SELECT * FROM dbo.Loans", conn)
            conn.close()
        except Exception:
            tx = acc = cust = br = loans = None

    if any(df is None for df in [tx, acc, cust, br, loans]):
        merged, loans_merged = demo_dataset()
        return merged, loans_merged, pd.DataFrame(), "Demo"

    tx["TransactionDate"] = _parse_date(tx["TransactionDate"])
    acc["OpenDate"] = _parse_date(acc["OpenDate"])
    cust["DateOfBirth"] = _parse_date(cust["DateOfBirth"])
    cust["JoinDate"] = _parse_date(cust["JoinDate"]) if "JoinDate" in cust.columns else pd.NaT
    loans["StartDate"] = _parse_date(loans["StartDate"])
    acc = acc.rename(columns={"Status": "AccountStatus"})

    merged = (
        tx.merge(acc, on="AccountID", how="left")
          .merge(cust, on="CustomerID", how="left", suffixes=("", "_cust"))
          .merge(br, on="BranchID", how="left", suffixes=("", "_br"))
    )
    merged["Year"] = merged["TransactionDate"].dt.year
    merged["Quarter"] = merged["TransactionDate"].dt.quarter
    merged["MonthName"] = merged["TransactionDate"].dt.month_name()
    merged["YearMonth"] = merged["TransactionDate"].dt.to_period("M").dt.to_timestamp()
    merged["BranchState"] = merged["State_br"] if "State_br" in merged.columns else merged["State"]
    merged["AgeGroup"] = derive_agegroup(merged["DateOfBirth"])
    merged["IsWeekend"] = is_weekend(merged["TransactionDate"])
    merged["Hour"] = merged["TransactionDate"].dt.hour

    loans_merged = loans.merge(br, on="BranchID", how="left", suffixes=("", "_br"))
    loans_merged["LoanAgeDays"] = (pd.Timestamp("today") - loans_merged["StartDate"]).dt.days

    return merged, loans_merged, cust, source


def demo_dataset() -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = 3000
    date_range = pd.date_range(start="2022-01-01", end="2024-12-31", freq="D")
    transaction_types = ["Deposit", "Withdrawal", "Transfer", "Payment"]
    branches = [
        ("Mansoura Branch", "Dakahlia"), ("Port Said Branch", "PortSaid"),
        ("Alexandria Branch", "Alexandria"), ("Cairo Branch", "Cairo"),
        ("Luxor Branch", "Luxor"),
    ]
    age_groups = ["18-24", "25-35", "36-50", "51+"]
    account_types = ["Savings", "Checking", "Credit"]
    account_statuses = ["Active", "Inactive", "Dormant"]

    records = []
    for _ in range(rows):
        tx_date = random.choice(date_range)
        b, st_ = random.choice(branches)
        records.append({
            "TransactionDate": tx_date,
            "TransactionType": random.choices(transaction_types, weights=[0.4, 0.28, 0.2, 0.12])[0],
            "Amount": round(random.expovariate(1 / 1500), 2),
            "BranchName": b,
            "BranchState": st_,
            "CustomerID": random.randint(1, 1000),
            "AccountID": random.randint(1, 1200),
            "AccountType": random.choice(account_types),
            "AccountStatus": random.choice(account_statuses),
            "AgeGroup": random.choice(age_groups),
            "IsWeekend": tx_date.weekday() in (5, 6),
            "Hour": random.randint(0, 23),
        })
    df = pd.DataFrame(records)
    df["Year"] = df["TransactionDate"].dt.year
    df["Quarter"] = df["TransactionDate"].dt.quarter
    df["MonthName"] = df["TransactionDate"].dt.month_name()
    df["YearMonth"] = df["TransactionDate"].dt.to_period("M").dt.to_timestamp()

    loan_records = []
    for _ in range(300):
        sd = random.choice(date_range)
        loan_records.append({
            "LoanType": random.choice(["Mortgage", "Auto", "Personal", "Student"]),
            "PrincipalAmount": round(random.uniform(5000, 500000), 2),
            "InterestRate": round(random.uniform(3.5, 12.5), 2),
            "TermMonths": random.choice([12, 24, 36, 60, 120, 360]),
            "Status": random.choices(["Active", "Paid", "Defaulted"], weights=[0.8, 0.15, 0.05])[0],
            "StartDate": sd,
            "LoanAgeDays": (pd.Timestamp("today") - sd).days,
            "BranchID": random.randint(1, 5),
            "BranchName": random.choice(branches)[0],
            "State": random.choice(branches)[1],
        })
    return df, pd.DataFrame(loan_records)


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------
def aggregate_by(df: pd.DataFrame, group_col, mode: str, metric_label: str = "Metric") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if isinstance(group_col, str):
        group_col = [group_col]
    if mode == "Sum":
        return df.groupby(group_col, observed=False)["Amount"].sum().reset_index(name=metric_label)
    return df.groupby(group_col, observed=False).size().reset_index(name=metric_label)


def rfm_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "CustomerID" not in df.columns:
        return pd.DataFrame()
    as_of = df["TransactionDate"].max()
    rfm = (
        df.groupby("CustomerID")
          .agg(
              Recency=("TransactionDate", lambda s: (as_of - s.max()).days),
              Frequency=("TransactionID" if "TransactionID" in df.columns else "Amount", "count"),
              Monetary=("Amount", "sum"),
          )
          .reset_index()
    )
    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm["Monetary"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)

    def _segment(row):
        if row["R"] == 5 and row["F"] >= 4 and row["M"] >= 4:
            return "Champions"
        if row["R"] >= 4 and row["F"] >= 3 and row["M"] >= 3:
            return "Loyal"
        if row["R"] >= 4 and row["F"] <= 2:
            return "New / Promising"
        if row["R"] <= 2 and row["F"] >= 4 and row["M"] >= 4:
            return "At Risk — High Value"
        if row["R"] == 1 and row["F"] == 1:
            return "Hibernating"
        return "Need Attention"

    rfm["Segment"] = rfm.apply(_segment, axis=1)
    return rfm


def fraud_signals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.sort_values(["CustomerID", "TransactionDate"]).copy()
    cust_stats = out.groupby("CustomerID")["Amount"].agg(["mean", "std"]).rename(columns={"mean": "muAmt", "std": "sdAmt"})
    out = out.join(cust_stats, on="CustomerID")
    out["AmountZ"] = (out["Amount"] - out["muAmt"]) / out["sdAmt"].replace(0, np.nan)
    out["AmountZ"] = out["AmountZ"].fillna(0)
    out["NearThreshold"] = out["Amount"].between(9000, 9999).astype(int)
    out["RiskScore"] = (
        np.clip(np.abs(out["AmountZ"]) * 8, 0, 60)
        + out["NearThreshold"] * 25
        + out["IsWeekend"].astype(int) * 5
    ).clip(0, 100)
    return out


def churn_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "CustomerID" not in df.columns:
        return pd.DataFrame()
    as_of = df["TransactionDate"].max()
    out = (
        df.groupby("CustomerID")
          .agg(
              LastActivity=("TransactionDate", "max"),
              TxnCount=("Amount", "count"),
              Volume=("Amount", "sum"),
          )
          .reset_index()
    )
    out["DaysInactive"] = (as_of - out["LastActivity"]).dt.days
    out["ChurnTier"] = pd.cut(
        out["DaysInactive"],
        bins=[-1, 14, 44, 89, 179, 9999],
        labels=["Active", "Watch", "Medium", "High", "Critical"],
    )
    return out


# ---------------------------------------------------------------------------
# Sidebar — Filters & Settings
# ---------------------------------------------------------------------------
with st.spinner("Initializing executive analytics…"):
    merged_df, loans_df, customers_df, data_source = load_data()

st.sidebar.image("https://img.icons8.com/fluency/96/bank.png", width=72)
st.sidebar.header("Control Panel")
src_color = {"CSV": "green", "SQL": "blue", "Demo": "orange"}.get(data_source, "gray")
st.sidebar.markdown(f"**Data Source:** :{src_color}[{data_source}]")

with st.sidebar.expander("📅 Date Range", expanded=True):
    min_d = merged_df["TransactionDate"].min().date()
    max_d = merged_df["TransactionDate"].max().date()
    date_range = st.date_input("Select Range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_date = end_date = date_range[0]
    else:
        start_date = end_date = date_range

with st.sidebar.expander("🔍 Filters", expanded=False):
    sel_types = st.multiselect("Transaction Types",
                               options=sorted(merged_df["TransactionType"].dropna().unique().tolist()),
                               default=sorted(merged_df["TransactionType"].dropna().unique().tolist()))
    sel_states = st.multiselect("Governorates",
                                options=sorted(merged_df["BranchState"].dropna().unique().tolist()),
                                default=sorted(merged_df["BranchState"].dropna().unique().tolist()))
    sel_age = st.multiselect("Age Groups",
                             options=sorted(merged_df["AgeGroup"].dropna().unique().tolist()),
                             default=sorted(merged_df["AgeGroup"].dropna().unique().tolist()))
    sel_acc_types = st.multiselect("Account Types",
                                   options=sorted(merged_df["AccountType"].dropna().unique().tolist()),
                                   default=sorted(merged_df["AccountType"].dropna().unique().tolist()))

with st.sidebar.expander("📊 Metric Settings", expanded=False):
    max_amt = float(merged_df["Amount"].max())
    sel_amt = st.slider("Amount Range ($)", 0.0, max_amt, (0.0, max_amt))
    metric_mode = st.radio("Primary Metric", ["Sum", "Count"], index=0)
    time_grain = st.selectbox("Time Grain", ["Year", "Quarter", "Month"])
    top_n = st.slider("Top N Ranking", 3, 25, 10)

if st.sidebar.button("🔄 Refresh Data", width='stretch'):
    st.cache_data.clear()
    st.rerun()

# Apply filters ---------------------------------------------------------------
mask = (
    (merged_df["TransactionDate"] >= pd.Timestamp(start_date))
    & (merged_df["TransactionDate"] <= pd.Timestamp(end_date))
    & merged_df["TransactionType"].isin(sel_types)
    & merged_df["BranchState"].isin(sel_states)
    & merged_df["AgeGroup"].isin(sel_age)
    & merged_df["AccountType"].isin(sel_acc_types)
    & (merged_df["Amount"].between(sel_amt[0], sel_amt[1]))
)
filtered = merged_df[mask]

period_days = max((end_date - start_date).days + 1, 1)
prev_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_days - 1)
prev_filtered = merged_df[
    (merged_df["TransactionDate"] >= prev_start)
    & (merged_df["TransactionDate"] <= prev_end)
    & merged_df["TransactionType"].isin(sel_types)
    & merged_df["BranchState"].isin(sel_states)
    & merged_df["AgeGroup"].isin(sel_age)
    & merged_df["AccountType"].isin(sel_acc_types)
    & (merged_df["Amount"].between(sel_amt[0], sel_amt[1]))
]


# ---------------------------------------------------------------------------
# 9 Executive Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "🏛️ Executive Summary",
    "💵 Revenue & Profitability",
    "👥 Customer Intelligence",
    "🛡️ Risk & Fraud",
    "💰 Loan Portfolio",
    "🏢 Branch Performance",
    "⚙️ Operations & SLA",
    "🧪 Data Quality Center",
    "🔮 Forecasting Lab",
])

# ===========================================================================
# 1. EXECUTIVE SUMMARY
# ===========================================================================
with tabs[0]:
    st.subheader("C-Suite Cockpit")
    k1, k2, k3, k4, k5 = st.columns(5)
    cur_vol, cur_cnt = float(filtered["Amount"].sum()), int(len(filtered))
    cur_avg = float(filtered["Amount"].mean()) if not filtered.empty else 0.0
    cur_acc = int(filtered["AccountID"].nunique())
    cur_cust = int(filtered["CustomerID"].nunique())
    p_vol, p_cnt = float(prev_filtered["Amount"].sum()), int(len(prev_filtered))
    p_avg = float(prev_filtered["Amount"].mean()) if not prev_filtered.empty else 0.0
    p_acc = int(prev_filtered["AccountID"].nunique())
    p_cust = int(prev_filtered["CustomerID"].nunique())

    k1.metric("Volume ($)", f"${cur_vol:,.0f}", delta_label(cur_vol, p_vol, "period"))
    k2.metric("Transactions", f"{cur_cnt:,}", delta_label(cur_cnt, p_cnt, "period"))
    k3.metric("Avg Ticket", f"${cur_avg:,.2f}", delta_label(cur_avg, p_avg, "period"))
    k4.metric("Active Accounts", f"{cur_acc:,}", delta_label(cur_acc, p_acc, "period"))
    k5.metric("Active Customers", f"{cur_cust:,}", delta_label(cur_cust, p_cust, "period"))

    st.markdown("##### Net Flow & Mix")
    c1, c2, c3 = st.columns(3)
    deposits = filtered.loc[filtered["TransactionType"] == "Deposit", "Amount"].sum()
    withdrawals = filtered.loc[filtered["TransactionType"] == "Withdrawal", "Amount"].sum()
    net_flow = deposits - withdrawals
    weekend_share = filtered["IsWeekend"].mean() * 100 if not filtered.empty else 0
    c1.metric("Deposits ($)", f"${deposits:,.0f}")
    c2.metric("Withdrawals ($)", f"${withdrawals:,.0f}")
    c3.metric("Net Flow", f"${net_flow:,.0f}", "Liquidity inflow" if net_flow >= 0 else "Liquidity outflow")

    st.markdown("##### Volume Trend")
    if not filtered.empty:
        trend = filtered.groupby("YearMonth")["Amount"].sum().reset_index()
        fig = px.area(trend, x="YearMonth", y="Amount",
                      labels={"Amount": "Volume ($)", "YearMonth": "Month"},
                      color_discrete_sequence=["#1F77B4"])
        fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, width='stretch')


# ===========================================================================
# 2. REVENUE & PROFITABILITY
# ===========================================================================
with tabs[1]:
    st.subheader("Revenue & Profitability")
    c1, c2 = st.columns(2)
    with c1:
        top_br = aggregate_by(filtered, "BranchName", metric_mode).nlargest(top_n, "Metric")
        if not top_br.empty:
            fig = px.bar(top_br, x="BranchName", y="Metric", color="Metric",
                         color_continuous_scale="Blues", title=f"Top {top_n} Branches")
            fig.update_layout(height=380, xaxis_tickangle=-30)
            st.plotly_chart(fig, width='stretch')
    with c2:
        mix = aggregate_by(filtered, "TransactionType", metric_mode)
        if not mix.empty:
            fig = px.pie(mix, names="TransactionType", values="Metric", hole=0.45,
                         title="Transaction Mix",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=380)
            st.plotly_chart(fig, width='stretch')

    st.markdown("##### Profitability Ranking (Volume × Avg Ticket)")
    if not filtered.empty:
        prof = (filtered.groupby("BranchName")
                .agg(Volume=("Amount", "sum"), Avg=("Amount", "mean"),
                     Customers=("CustomerID", "nunique"))
                .reset_index())
        prof["ProfitabilityScore"] = (
            prof["Volume"].rank(pct=True) * 0.5
            + prof["Avg"].rank(pct=True) * 0.3
            + prof["Customers"].rank(pct=True) * 0.2
        ) * 100
        prof = prof.sort_values("ProfitabilityScore", ascending=False).head(top_n)
        st.dataframe(prof.round(2), width='stretch')

    st.markdown("##### Revenue by Governorate")
    if not filtered.empty:
        gov = aggregate_by(filtered, "BranchState", "Sum", metric_label="Volume")
        fig = px.bar(gov.sort_values("Volume", ascending=True), x="Volume", y="BranchState",
                     orientation="h", color="Volume", color_continuous_scale="Teal")
        fig.update_layout(height=420)
        st.plotly_chart(fig, width='stretch')


# ===========================================================================
# 3. CUSTOMER INTELLIGENCE
# ===========================================================================
with tabs[2]:
    st.subheader("Customer 360 — RFM, CLV, Cohorts")

    rfm = rfm_table(filtered)
    if rfm.empty:
        st.info("Not enough data to compute RFM segments.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Customers in slice", f"{len(rfm):,}")
        c2.metric("Median Frequency", f"{rfm['Frequency'].median():.0f}")
        c3.metric("Median Monetary", f"${rfm['Monetary'].median():,.0f}")

        seg = rfm["Segment"].value_counts().reset_index()
        seg.columns = ["Segment", "Customers"]
        fig = px.bar(seg, x="Segment", y="Customers", color="Segment",
                     title="RFM Segment Distribution",
                     color_discrete_sequence=px.colors.qualitative.Bold)
        st.plotly_chart(fig, width='stretch')

        st.markdown("##### CLV Decile Distribution")
        rfm["CLVDecile"] = pd.qcut(rfm["Monetary"], 10, labels=False, duplicates="drop") + 1
        clv = rfm.groupby("CLVDecile")["Monetary"].agg(["mean", "count"]).reset_index()
        fig = px.bar(clv, x="CLVDecile", y="mean", color="count",
                     labels={"mean": "Avg Monetary ($)", "count": "# Customers"},
                     color_continuous_scale="Viridis")
        st.plotly_chart(fig, width='stretch')

    st.markdown("##### Demographic Decomposition")
    c1, c2 = st.columns(2)
    with c1:
        age = aggregate_by(filtered, "AgeGroup", metric_mode)
        if not age.empty:
            fig = px.bar(age, x="AgeGroup", y="Metric", color="AgeGroup",
                         title="By Age Group", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, width='stretch')
    with c2:
        acc_t = aggregate_by(filtered, "AccountType", metric_mode)
        if not acc_t.empty:
            fig = px.pie(acc_t, names="AccountType", values="Metric", hole=0.4,
                         title="By Account Type")
            st.plotly_chart(fig, width='stretch')

    st.markdown("##### Acquisition Cohort Retention (Heatmap)")
    if not filtered.empty:
        cohort_first = filtered.groupby("CustomerID")["TransactionDate"].min().dt.to_period("M")
        df_c = filtered.copy()
        df_c["CohortMonth"] = df_c["CustomerID"].map(cohort_first).astype(str)
        df_c["ActivityMonth"] = df_c["TransactionDate"].dt.to_period("M").astype(str)
        coh = df_c.groupby(["CohortMonth", "ActivityMonth"])["CustomerID"].nunique().reset_index()
        coh.columns = ["CohortMonth", "ActivityMonth", "ActiveCustomers"]
        cohort_pivot = coh.pivot(index="CohortMonth", columns="ActivityMonth", values="ActiveCustomers")
        cohort_size = cohort_pivot.iloc[:, 0]
        retention = cohort_pivot.div(cohort_size, axis=0).fillna(0) * 100
        if not retention.empty:
            fig = px.imshow(retention.values, x=retention.columns, y=retention.index,
                            color_continuous_scale="Blues", aspect="auto",
                            labels={"color": "% Retained"})
            fig.update_layout(height=480, title="Retention % by Cohort Month")
            st.plotly_chart(fig, width='stretch')


# ===========================================================================
# 4. RISK & FRAUD
# ===========================================================================
with tabs[3]:
    st.subheader("Risk & Fraud Surveillance")

    fr = fraud_signals(filtered)
    if fr.empty:
        st.info("Insufficient data for fraud scoring.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Suspicious (z≥3)", f"{(fr['AmountZ'].abs() >= 3).sum():,}")
        c2.metric("Near-threshold flags", f"{int(fr['NearThreshold'].sum()):,}")
        c3.metric("Median Risk Score", f"{fr['RiskScore'].median():.1f}")
        c4.metric("High-Risk Txns", f"{(fr['RiskScore'] >= 70).sum():,}")

        st.markdown("##### Velocity Heatmap (Hour × Weekday)")
        heat = (fr.assign(Weekday=fr["TransactionDate"].dt.day_name())
                  .groupby(["Hour", "Weekday"])["Amount"].sum().reset_index())
        if not heat.empty:
            order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            heat["Weekday"] = pd.Categorical(heat["Weekday"], categories=order, ordered=True)
            heat = heat.sort_values(["Weekday", "Hour"])
            fig = px.density_heatmap(heat, x="Hour", y="Weekday", z="Amount",
                                     color_continuous_scale="Reds")
            fig.update_layout(height=380)
            st.plotly_chart(fig, width='stretch')

        st.markdown("##### Top 25 High-Risk Transactions")
        cols = [c for c in ["TransactionDate", "BranchName", "BranchState",
                            "TransactionType", "Amount", "AmountZ", "RiskScore"]
                if c in fr.columns]
        top_risk = fr.sort_values("RiskScore", ascending=False).head(25)[cols]
        st.dataframe(top_risk, width='stretch')


# ===========================================================================
# 5. LOAN PORTFOLIO
# ===========================================================================
with tabs[4]:
    st.subheader("Loan Portfolio Analytics")

    if loans_df.empty:
        st.info("No loan data available.")
    else:
        active = (loans_df["Status"] == "Active").sum()
        defaulted = (loans_df["Status"] == "Defaulted").sum()
        paid = (loans_df["Status"] == "Paid").sum()
        npl = safe_pct(defaulted, len(loans_df))
        principal = loans_df["PrincipalAmount"].sum()
        avg_rate = loans_df["InterestRate"].mean() if "InterestRate" in loans_df.columns else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Principal", f"${principal:,.0f}")
        c2.metric("Active Loans", f"{active:,}")
        c3.metric("Paid Loans", f"{paid:,}")
        c4.metric("Defaulted", f"{defaulted:,}")
        c5.metric("NPL Ratio", f"{npl:.2f}%",
                  delta_color="inverse")

        c1, c2 = st.columns(2)
        with c1:
            l_type = loans_df.groupby("LoanType")["PrincipalAmount"].sum().reset_index()
            fig = px.bar(l_type, x="LoanType", y="PrincipalAmount", color="LoanType",
                         title="Principal by Type",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig, width='stretch')
        with c2:
            l_stat = loans_df["Status"].value_counts().reset_index()
            l_stat.columns = ["Status", "Count"]
            fig = px.pie(l_stat, names="Status", values="Count", hole=0.4,
                         title="Status Distribution",
                         color_discrete_sequence=["#2ECC71", "#3498DB", "#E74C3C"])
            st.plotly_chart(fig, width='stretch')

        st.markdown("##### Loan Vintage")
        loans_df["StartYear"] = pd.to_datetime(loans_df["StartDate"]).dt.year
        vintage = loans_df.groupby(["StartYear", "Status"]).size().reset_index(name="Count")
        fig = px.bar(vintage, x="StartYear", y="Count", color="Status",
                     barmode="stack", title="Loans Originated by Year × Status")
        st.plotly_chart(fig, width='stretch')

        if "InterestRate" in loans_df.columns:
            st.markdown("##### Interest Rate Distribution by Type")
            fig = px.box(loans_df, x="LoanType", y="InterestRate", color="LoanType",
                         points="outliers")
            st.plotly_chart(fig, width='stretch')


# ===========================================================================
# 6. BRANCH PERFORMANCE
# ===========================================================================
with tabs[5]:
    st.subheader("Branch Performance & Benchmarking")

    if filtered.empty:
        st.info("Adjust filters to view branch performance.")
    else:
        bp = (filtered.groupby(["BranchName", "BranchState"])
              .agg(Volume=("Amount", "sum"), Txns=("Amount", "count"),
                   Customers=("CustomerID", "nunique"),
                   AvgTicket=("Amount", "mean"))
              .reset_index())
        bp["EfficiencyScore"] = (
            bp["Volume"].rank(pct=True) * 0.4
            + bp["Customers"].rank(pct=True) * 0.4
            + bp["AvgTicket"].rank(pct=True) * 0.2
        ) * 100

        c1, c2 = st.columns(2)
        with c1:
            top = bp.nlargest(top_n, "EfficiencyScore")
            fig = px.bar(top, x="BranchName", y="EfficiencyScore",
                         color="Volume", color_continuous_scale="Blues",
                         title=f"Top {top_n} Branches by Efficiency Score")
            fig.update_layout(xaxis_tickangle=-30, height=420)
            st.plotly_chart(fig, width='stretch')
        with c2:
            fig = px.scatter(bp, x="Volume", y="Customers", size="Txns",
                             color="EfficiencyScore", hover_name="BranchName",
                             color_continuous_scale="Viridis",
                             title="Efficiency Frontier (Volume × Customers)")
            st.plotly_chart(fig, width='stretch')

        st.markdown("##### Governorate League Table")
        league = (bp.groupby("BranchState")
                    .agg(Volume=("Volume", "sum"), Customers=("Customers", "sum"),
                         Branches=("BranchName", "nunique"))
                    .reset_index().sort_values("Volume", ascending=False))
        league["Rank"] = range(1, len(league) + 1)
        st.dataframe(league.round(2), width='stretch')


# ===========================================================================
# 7. OPERATIONS & SLA
# ===========================================================================
with tabs[6]:
    st.subheader("Operations & SLA")
    if filtered.empty:
        st.info("No data in selected window.")
    else:
        c1, c2, c3 = st.columns(3)
        weekend_pct = filtered["IsWeekend"].mean() * 100
        peak_hour = filtered.groupby("Hour").size().idxmax() if "Hour" in filtered.columns else 0
        avg_per_day = filtered.groupby(filtered["TransactionDate"].dt.date).size().mean()
        c1.metric("Weekend Share", f"{weekend_pct:.1f}%")
        c2.metric("Peak Hour", f"{int(peak_hour):02d}:00")
        c3.metric("Avg Txns / Day", f"{avg_per_day:,.0f}")

        st.markdown("##### Hourly Throughput")
        if "Hour" in filtered.columns:
            hourly = filtered.groupby("Hour").size().reset_index(name="Txns")
            fig = px.bar(hourly, x="Hour", y="Txns", color="Txns",
                         color_continuous_scale="Plasma")
            fig.update_layout(height=320)
            st.plotly_chart(fig, width='stretch')

        st.markdown("##### Weekday Distribution")
        weekday = (filtered.assign(Weekday=filtered["TransactionDate"].dt.day_name())
                   .groupby("Weekday")["Amount"].agg(["sum", "count"])
                   .reset_index())
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday["Weekday"] = pd.Categorical(weekday["Weekday"], categories=order, ordered=True)
        weekday = weekday.sort_values("Weekday")
        fig = px.bar(weekday, x="Weekday", y="sum", color="count",
                     labels={"sum": "Volume ($)", "count": "Txns"},
                     color_continuous_scale="Mint")
        fig.update_layout(height=320)
        st.plotly_chart(fig, width='stretch')


# ===========================================================================
# 8. DATA QUALITY CENTER
# ===========================================================================
with tabs[7]:
    st.subheader("Data Quality Center")

    def column_completeness(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
        comp = (1 - df.isna().mean()) * 100
        return comp.round(2).reset_index().rename(columns={"index": "Column", 0: "Completeness"})

    completeness = column_completeness(merged_df)
    if completeness.empty:
        st.info("Quality center has no data.")
    else:
        completeness.columns = ["Column", "Completeness"]
        avg_comp = completeness["Completeness"].mean()
        uniq_tx = (
            (1 - merged_df["TransactionID"].duplicated().mean()) * 100
            if "TransactionID" in merged_df.columns else 100
        )
        valid_amount = (merged_df["Amount"] > 0).mean() * 100
        score = (avg_comp * 0.5 + uniq_tx * 0.25 + valid_amount * 0.25)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall DQ Score", f"{score:.2f} / 100")
        c2.metric("Completeness", f"{avg_comp:.2f}%")
        c3.metric("TX Uniqueness", f"{uniq_tx:.2f}%")
        c4.metric("Valid Amounts", f"{valid_amount:.2f}%")

        fig = px.bar(completeness.sort_values("Completeness"),
                     x="Completeness", y="Column", orientation="h",
                     color="Completeness", color_continuous_scale="Viridis",
                     title="Column Completeness")
        fig.update_layout(height=520)
        st.plotly_chart(fig, width='stretch')

        st.markdown("##### Freshness")
        latest = merged_df["TransactionDate"].max()
        age_days = (pd.Timestamp.utcnow().tz_localize(None) - latest).days
        st.write(f"📅 Latest transaction: **{latest.date()}** — **{age_days} days** old")


# ===========================================================================
# 9. FORECASTING LAB
# ===========================================================================
with tabs[8]:
    st.subheader("Forecasting Lab")

    if filtered.empty:
        st.info("Insufficient data to project.")
    else:
        monthly = (filtered.groupby("YearMonth")["Amount"].sum().reset_index()
                   .rename(columns={"Amount": "Volume"}))
        monthly = monthly.sort_values("YearMonth")
        if len(monthly) < 3:
            st.info("Need at least 3 months of data for forecasting.")
        else:
            # Try Holt-Winters; otherwise naive
            forecast_df = None
            try:
                import warnings as _warnings
                from statsmodels.tsa.holtwinters import ExponentialSmoothing
                series = monthly.set_index("YearMonth")["Volume"].asfreq("MS").ffill()
                seasonal = "add" if len(series) >= 24 else None
                periods = 12 if seasonal else None
                with _warnings.catch_warnings():
                    _warnings.simplefilter("ignore")
                    model = ExponentialSmoothing(series, seasonal=seasonal,
                                                 seasonal_periods=periods, trend="add").fit(optimized=True)
                    horizon = 12
                    future = pd.date_range(series.index.max() + pd.offsets.MonthBegin(1),
                                           periods=horizon, freq="MS")
                    forecast = model.forecast(horizon)
                forecast_df = pd.DataFrame({"YearMonth": future, "Volume": forecast.values, "Type": "Forecast"})
            except ImportError:
                last = monthly.tail(min(6, len(monthly)))["Volume"]
                base = float(last.mean())
                future = pd.date_range(monthly["YearMonth"].max() + pd.offsets.MonthBegin(1),
                                       periods=12, freq="MS")
                forecast_df = pd.DataFrame({"YearMonth": future,
                                             "Volume": [base] * 12,
                                             "Type": "Forecast (Naive)"})

            history = monthly.assign(Type="History")
            full = pd.concat([history, forecast_df], ignore_index=True)
            fig = px.line(full, x="YearMonth", y="Volume", color="Type",
                          title="Monthly Volume — History + 12-Month Forecast",
                          color_discrete_map={"History": "#1F77B4",
                                              "Forecast": "#E74C3C",
                                              "Forecast (Naive)": "#E74C3C"})
            fig.update_traces(mode="lines+markers")
            fig.update_layout(height=440)
            st.plotly_chart(fig, width='stretch')
            st.markdown("> **Method:** Holt-Winters additive with optimized trend/seasonality. Falls back to "
                        "rolling-mean projection when statsmodels is unavailable.")

        st.markdown("##### Customer Churn Risk Distribution")
        churn = churn_table(filtered)
        if not churn.empty:
            tier = churn["ChurnTier"].value_counts().reindex(
                ["Active", "Watch", "Medium", "High", "Critical"], fill_value=0).reset_index()
            tier.columns = ["Tier", "Customers"]
            fig = px.bar(tier, x="Tier", y="Customers", color="Tier",
                         color_discrete_map={"Active": "#2ECC71", "Watch": "#F1C40F",
                                             "Medium": "#E67E22", "High": "#E74C3C",
                                             "Critical": "#7F1D1D"},
                         title="Customer Churn-Risk Tiers")
            st.plotly_chart(fig, width='stretch')


# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    f"🏛️ Global Horizon Bank · Enterprise Data Warehouse Platform "
    f"| Source: {data_source} | Snapshot: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
