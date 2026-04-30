"""Gold layer ETL — business-ready star schema.

Builds the dimensional model from Silver, computes derived attributes (age
groups, weekend flags, surrogate keys) and writes Gold-zone outputs that mirror
the Kimball star schema. The output of this layer is what the executive
dashboard and ML models consume.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import GOLD_DIR, SILVER_DIR
from .base import ETLJob


def derive_age_group(dob: pd.Series) -> pd.Series:
    today = pd.Timestamp.utcnow().tz_localize(None)
    age_years = (today - pd.to_datetime(dob, errors="coerce")).dt.days // 365
    bins = [0, 24, 35, 50, 150]
    labels = ["18-24", "25-35", "36-50", "51+"]
    return pd.cut(age_years, bins=bins, labels=labels, right=False)


class GoldStarBuild(ETLJob):
    name = "gold_star_build"

    def __init__(self, source_dir: Path = SILVER_DIR, target_dir: Path = GOLD_DIR):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def _read(self, table: str) -> pd.DataFrame:
        for ext in (".parquet", ".csv"):
            p = self.source_dir / f"{table}{ext}"
            if p.exists():
                if ext == ".parquet":
                    try:
                        return pd.read_parquet(p)
                    except (ImportError, ValueError):
                        continue
                return pd.read_csv(p, parse_dates=True)
        return pd.DataFrame()

    def extract(self) -> dict[str, pd.DataFrame]:
        return {
            "transactions": self._read("transactions"),
            "accounts": self._read("accounts"),
            "customers": self._read("customers"),
            "branches": self._read("branches"),
            "loans": self._read("loans"),
        }

    def transform(self, payload: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        cust, br, acc, tx, loans = (
            payload["customers"], payload["branches"], payload["accounts"],
            payload["transactions"], payload["loans"],
        )
        if cust.empty or br.empty or acc.empty:
            self.log.warning("gold_skip reason=missing_inputs")
            return {}

        # Dimensions ------------------------------------------------------
        dim_branch = br.assign(BranchKey=range(1, len(br) + 1))[
            ["BranchKey", "BranchID", "BranchName", "City", "State", "ZipCode"]
        ]

        dim_customer = cust.copy()
        dim_customer["AgeGroup"] = derive_age_group(dim_customer["DateOfBirth"])
        dim_customer["CustomerKey"] = range(1, len(dim_customer) + 1)
        dim_customer["EffectiveDate"] = pd.Timestamp.utcnow().normalize()
        dim_customer["ExpirationDate"] = pd.NaT
        dim_customer["IsCurrent"] = 1
        dim_customer = dim_customer[
            ["CustomerKey", "CustomerID", "FirstName", "LastName", "AgeGroup",
             "City", "State", "EffectiveDate", "ExpirationDate", "IsCurrent"]
        ]

        dim_account = acc.assign(AccountKey=range(1, len(acc) + 1))[
            ["AccountKey", "AccountID", "AccountType", "OpenDate", "Status"]
        ]

        # Date dimension --------------------------------------------------
        if not tx.empty:
            tx["TransactionDate"] = pd.to_datetime(tx["TransactionDate"], errors="coerce")
            tx = tx.dropna(subset=["TransactionDate"])
            date_range = pd.date_range(
                start=tx["TransactionDate"].min().normalize(),
                end=tx["TransactionDate"].max().normalize(),
                freq="D",
            )
            dim_date = pd.DataFrame({"FullDate": date_range})
            dim_date["DateKey"] = dim_date["FullDate"].dt.strftime("%Y%m%d").astype(int)
            dim_date["Year"] = dim_date["FullDate"].dt.year
            dim_date["Quarter"] = dim_date["FullDate"].dt.quarter
            dim_date["Month"] = dim_date["FullDate"].dt.month
            dim_date["MonthName"] = dim_date["FullDate"].dt.month_name()
            dim_date["DayOfMonth"] = dim_date["FullDate"].dt.day
            dim_date["DayOfWeek"] = dim_date["FullDate"].dt.dayofweek + 1
            dim_date["DayName"] = dim_date["FullDate"].dt.day_name()
            dim_date["IsWeekend"] = dim_date["FullDate"].dt.dayofweek.isin([5, 6]).astype(int)
        else:
            dim_date = pd.DataFrame()

        # Fact table ------------------------------------------------------
        fact = pd.DataFrame()
        if not tx.empty and not acc.empty:
            fact = (
                tx.merge(acc[["AccountID", "CustomerID", "BranchID"]], on="AccountID", how="left")
                  .merge(dim_customer[["CustomerKey", "CustomerID"]], on="CustomerID", how="left")
                  .merge(dim_account[["AccountKey", "AccountID"]], on="AccountID", how="left")
                  .merge(dim_branch[["BranchKey", "BranchID"]], on="BranchID", how="left")
            )
            fact["DateKey"] = fact["TransactionDate"].dt.strftime("%Y%m%d").astype("Int64")
            fact["TransactionKey"] = range(1, len(fact) + 1)
            fact = fact[
                ["TransactionKey", "TransactionID", "DateKey", "CustomerKey",
                 "AccountKey", "BranchKey", "TransactionType", "Amount"]
            ]

        return {
            "dim_branch": dim_branch,
            "dim_customer": dim_customer,
            "dim_account": dim_account,
            "dim_date": dim_date,
            "fact_transaction": fact,
            "loans": loans,
        }

    def load(self, payload: dict[str, pd.DataFrame]) -> int:
        total = 0
        for table, df in payload.items():
            if df is None or df.empty:
                continue
            target = self.target_dir / f"{table}.parquet"
            try:
                df.to_parquet(target, index=False)
            except (ImportError, ValueError):
                target = self.target_dir / f"{table}.csv"
                df.to_csv(target, index=False)
            total += len(df)
            self.log.info("gold_load table=%s rows=%d path=%s", table, len(df), target)
        return total


if __name__ == "__main__":
    GoldStarBuild().run()
