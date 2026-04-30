"""Shared loaders for ML modules."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import RAW_DATA_DIR


def load_csv(name: str, base: Path = RAW_DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(base / f"{name}.csv")


def load_core_frames(base: Path = RAW_DATA_DIR) -> dict[str, pd.DataFrame]:
    return {
        "transactions": load_csv("transactions", base),
        "accounts": load_csv("accounts", base),
        "customers": load_csv("customers", base),
        "branches": load_csv("branches", base),
        "loans": load_csv("loans", base),
    }
