"""Fraud / Anomaly Detection.

Unsupervised Isolation Forest scorer that flags anomalous transactions across
amount, customer-window velocity, and branch concentration features. The output
is an ``anomaly_score`` per transaction (higher = more anomalous).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..logger import get_logger
from ._io import load_core_frames

_log = get_logger("ml.fraud")


class FraudDetector:
    def __init__(self, contamination: float = 0.01, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self.feature_columns: list[str] = [
            "Amount", "AmountZ", "Window5Volume", "BranchConcentration", "IsWeekend",
        ]

    def build_features(self) -> pd.DataFrame:
        frames = load_core_frames()
        tx = frames["transactions"].copy()
        acc = frames["accounts"].copy()

        tx["TransactionDate"] = pd.to_datetime(tx["TransactionDate"], errors="coerce")
        tx = tx.dropna(subset=["TransactionDate", "Amount"])
        tx = tx.merge(acc[["AccountID", "CustomerID", "BranchID"]], on="AccountID", how="left")
        tx = tx.sort_values(["CustomerID", "TransactionDate"])

        # Per-customer z-score
        cust_stats = tx.groupby("CustomerID")["Amount"].agg(["mean", "std"]).rename(columns={"mean": "muAmt", "std": "sdAmt"})
        tx = tx.join(cust_stats, on="CustomerID")
        tx["AmountZ"] = (tx["Amount"] - tx["muAmt"]) / tx["sdAmt"].replace(0, np.nan)
        tx["AmountZ"] = tx["AmountZ"].fillna(0)

        # Rolling 5-txn volume
        tx["Window5Volume"] = (
            tx.groupby("CustomerID")["Amount"]
              .rolling(5, min_periods=1).sum()
              .reset_index(level=0, drop=True)
        )

        # Branch concentration: how many distinct branches in last 5 txns
        tx["BranchConcentration"] = (
            tx.groupby("CustomerID")["BranchID"]
              .rolling(5, min_periods=1).apply(lambda s: s.nunique())
              .reset_index(level=0, drop=True)
        )

        tx["IsWeekend"] = tx["TransactionDate"].dt.dayofweek.isin([5, 6]).astype(int)
        return tx

    def fit_score(self) -> pd.DataFrame:
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as exc:
            raise RuntimeError("scikit-learn is required for FraudDetector") from exc

        df = self.build_features()
        x = df[self.feature_columns].fillna(0)
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=200,
        )
        self.model.fit(x)
        df["anomaly_score"] = -self.model.score_samples(x)  # higher = more anomalous
        df["is_anomaly"] = (self.model.predict(x) == -1).astype(int)
        flagged = int(df["is_anomaly"].sum())
        _log.info("fraud_score n=%d anomalies=%d rate=%.3f",
                  len(df), flagged, flagged / max(len(df), 1))
        return df[
            ["TransactionID", "AccountID", "CustomerID", "BranchID",
             "TransactionDate", "Amount", "AmountZ", "anomaly_score", "is_anomaly"]
        ]


def main() -> None:
    df = FraudDetector().fit_score()
    print(df.sort_values("anomaly_score", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
