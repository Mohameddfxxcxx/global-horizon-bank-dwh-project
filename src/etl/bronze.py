"""Bronze layer ETL — raw landing.

Reads source CSVs (or future API/CDC feeds), validates schema, and writes an
immutable copy to ``data/bronze/`` as parquet. The Bronze zone is the system of
record for raw data; nothing is mutated here.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import BRONZE_DIR, RAW_DATA_DIR
from .base import ETLJob

SOURCE_TABLES = {
    "branches": "branches.csv",
    "employees": "employees.csv",
    "customers": "customers.csv",
    "accounts": "accounts.csv",
    "loans": "loans.csv",
    "transactions": "transactions.csv",
}


class BronzeIngest(ETLJob):
    name = "bronze_ingest"

    def __init__(self, source_dir: Path = RAW_DATA_DIR, target_dir: Path = BRONZE_DIR):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def extract(self) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for table, fname in SOURCE_TABLES.items():
            src = self.source_dir / fname
            if not src.exists():
                self.log.warning("bronze_skip table=%s reason=missing_source path=%s", table, src)
                continue
            frames[table] = pd.read_csv(src)
            self.log.info("bronze_extract table=%s rows=%d", table, len(frames[table]))
        return frames

    def transform(self, payload: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        # Bronze: schema-faithful — only ingestion timestamp added.
        for tbl, df in payload.items():
            df["_ingested_at"] = pd.Timestamp.utcnow()
            df["_source_file"] = SOURCE_TABLES[tbl]
        return payload

    def load(self, payload: dict[str, pd.DataFrame]) -> int:
        total = 0
        for tbl, df in payload.items():
            target = self.target_dir / f"{tbl}.parquet"
            try:
                df.to_parquet(target, index=False)
            except (ImportError, ValueError):
                # Fallback: write CSV when no parquet engine is installed
                target = self.target_dir / f"{tbl}.csv"
                df.to_csv(target, index=False)
            total += len(df)
            self.log.info("bronze_load table=%s rows=%d path=%s", tbl, len(df), target)
        return total


if __name__ == "__main__":
    BronzeIngest().run()
