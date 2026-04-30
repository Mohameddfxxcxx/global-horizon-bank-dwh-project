"""Silver layer ETL — cleansed and conformed.

Reads from Bronze, applies type coercion, deduplication, key validation, and
writes a quality-scored output to ``data/silver/``. Bridge to the Gold star
schema.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import BRONZE_DIR, SILVER_DIR
from ..data_quality import score_dataframe
from ..validation import (
    check_referential_integrity,
    validate_table,
)
from .base import ETLJob


class SilverTransform(ETLJob):
    name = "silver_transform"

    def __init__(self, source_dir: Path = BRONZE_DIR, target_dir: Path = SILVER_DIR):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.target_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def _read(self, table: str) -> pd.DataFrame:
        for ext in (".parquet", ".csv"):
            path = self.source_dir / f"{table}{ext}"
            if path.exists():
                if ext == ".parquet":
                    try:
                        return pd.read_parquet(path)
                    except (ImportError, ValueError):
                        continue
                return pd.read_csv(path)
        return pd.DataFrame()

    def extract(self) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for table in ("branches", "employees", "customers", "accounts", "loans", "transactions"):
            frames[table] = self._read(table)
            self.log.info("silver_extract table=%s rows=%d", table, len(frames[table]))
        return frames

    def transform(self, payload: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        # 1. Type coercion + deduplication
        if "transactions" in payload and not payload["transactions"].empty:
            tx = payload["transactions"]
            tx["TransactionDate"] = pd.to_datetime(tx["TransactionDate"], errors="coerce")
            tx["Amount"] = pd.to_numeric(tx["Amount"], errors="coerce")
            tx = tx.dropna(subset=["TransactionDate", "Amount", "AccountID"])
            tx = tx.drop_duplicates(subset=["TransactionID"], keep="first")
            payload["transactions"] = tx

        for date_col, table in (("OpenDate", "accounts"), ("StartDate", "loans"),
                                 ("DateOfBirth", "customers"), ("JoinDate", "customers"),
                                 ("HireDate", "employees")):
            df = payload.get(table)
            if df is None or df.empty or date_col not in df.columns:
                continue
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # 2. Validation reports
        if not payload.get("transactions", pd.DataFrame()).empty:
            r = validate_table(
                payload["transactions"],
                table="transactions",
                required=["TransactionID", "AccountID", "Amount", "TransactionType", "TransactionDate"],
                not_null=["TransactionID", "AccountID", "Amount"],
                unique=["TransactionID"],
                ranges={"Amount": (0.01, 1e9)},
            )
            if not payload.get("accounts", pd.DataFrame()).empty:
                check_referential_integrity(
                    payload["transactions"], parent=payload["accounts"],
                    fk_column="AccountID", pk_column="AccountID", report=r,
                )
            score = score_dataframe(
                payload["transactions"], table="transactions",
                not_null=["TransactionID", "AccountID", "Amount"],
                unique=["TransactionID"], report=r,
            )
            self.log.info("silver_dq table=transactions score=%.2f issues=%d", score.score, score.issues)

        return payload

    def load(self, payload: dict[str, pd.DataFrame]) -> int:
        total = 0
        for table, df in payload.items():
            if df.empty:
                continue
            target = self.target_dir / f"{table}.parquet"
            try:
                df.to_parquet(target, index=False)
            except (ImportError, ValueError):
                target = self.target_dir / f"{table}.csv"
                df.to_csv(target, index=False)
            total += len(df)
            self.log.info("silver_load table=%s rows=%d path=%s", table, len(df), target)
        return total


if __name__ == "__main__":
    SilverTransform().run()
