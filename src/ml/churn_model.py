"""Customer Churn Model.

Trains a Gradient Boosting classifier to predict which customers are likely to
churn (defined as no transaction in the last 90 days). Inputs are constructed
from Silver/Gold-zone features: recency, frequency, monetary, demographic, and
account-mix signals.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..logger import get_logger
from ._io import load_core_frames

_log = get_logger("ml.churn")

CHURN_WINDOW_DAYS = 90


@dataclass
class ModelMetrics:
    auc: float
    accuracy: float
    precision: float
    recall: float
    n_train: int
    n_test: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class ChurnModel:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.feature_columns: list[str] = []

    def build_features(self) -> tuple[pd.DataFrame, pd.Series]:
        """Construct point-in-time features and a churn label.

        We carve out a ``CHURN_WINDOW_DAYS`` observation window at the tail of
        history. Features are built from transactions BEFORE the cutoff; the
        target is whether the customer transacts AFTER the cutoff. This avoids
        the obvious leakage of using ``days-since-last-transaction`` (which is
        the target itself) as a feature.
        """
        frames = load_core_frames()
        tx = frames["transactions"].copy()
        cust = frames["customers"].copy()
        acc = frames["accounts"].copy()

        tx["TransactionDate"] = pd.to_datetime(tx["TransactionDate"], errors="coerce")
        cust["DateOfBirth"] = pd.to_datetime(cust["DateOfBirth"], errors="coerce")
        cutoff = tx["TransactionDate"].max() - pd.Timedelta(days=CHURN_WINDOW_DAYS)

        tx_cust = tx.merge(acc[["AccountID", "CustomerID"]], on="AccountID", how="left")
        before = tx_cust[tx_cust["TransactionDate"] <= cutoff]
        after = tx_cust[tx_cust["TransactionDate"] > cutoff]

        feat = (
            before.groupby("CustomerID")
                  .agg(
                      LastActivity=("TransactionDate", "max"),
                      FirstActivity=("TransactionDate", "min"),
                      TxnCount=("TransactionID", "count"),
                      Volume=("Amount", "sum"),
                      AvgTicket=("Amount", "mean"),
                      StdTicket=("Amount", "std"),
                  )
                  .reset_index()
        )
        feat["DaysSinceLastBeforeCutoff"] = (cutoff - feat["LastActivity"]).dt.days.fillna(9999).astype(int)
        feat["TenureDays"] = (feat["LastActivity"] - feat["FirstActivity"]).dt.days.fillna(0).astype(int)

        df = cust.merge(feat, on="CustomerID", how="left")
        df["AgeYears"] = ((pd.Timestamp.utcnow().tz_localize(None) - df["DateOfBirth"]).dt.days // 365).astype("Int64")
        for col, default in [("TxnCount", 0), ("Volume", 0.0), ("AvgTicket", 0.0),
                             ("StdTicket", 0.0), ("TenureDays", 0),
                             ("DaysSinceLastBeforeCutoff", 9999)]:
            df[col] = df[col].fillna(default)
        df["TxnCount"] = df["TxnCount"].astype(int)

        acc_count = acc.groupby("CustomerID").size().rename("AccountCount").reset_index()
        df = df.merge(acc_count, on="CustomerID", how="left")
        df["AccountCount"] = df["AccountCount"].fillna(0).astype(int)

        # Target = no transactions in the tail window
        active_after = set(after["CustomerID"].unique())
        y = (~df["CustomerID"].isin(active_after)).astype(int)

        feature_cols = ["TxnCount", "Volume", "AvgTicket", "StdTicket",
                        "DaysSinceLastBeforeCutoff", "TenureDays",
                        "AgeYears", "AccountCount"]
        x = df[feature_cols].fillna(0)
        self.feature_columns = feature_cols
        return x, y

    def fit(self) -> ModelMetrics:
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.metrics import (
                accuracy_score,
                precision_score,
                recall_score,
                roc_auc_score,
            )
            from sklearn.model_selection import train_test_split
        except ImportError as exc:
            raise RuntimeError("scikit-learn is required for ChurnModel.fit()") from exc

        x, y = self.build_features()
        if y.sum() == 0 or y.sum() == len(y):
            _log.warning("churn_skip reason=monoclass churn_rate=%.3f", y.mean())
            return ModelMetrics(auc=0.5, accuracy=float(y.mean()), precision=0,
                                recall=0, n_train=0, n_test=0)

        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.25, random_state=self.random_state, stratify=y,
        )
        self.model = GradientBoostingClassifier(random_state=self.random_state)
        self.model.fit(x_tr, y_tr)
        proba = self.model.predict_proba(x_te)[:, 1]
        pred = (proba >= 0.5).astype(int)

        metrics = ModelMetrics(
            auc=float(roc_auc_score(y_te, proba)),
            accuracy=float(accuracy_score(y_te, pred)),
            precision=float(precision_score(y_te, pred, zero_division=0)),
            recall=float(recall_score(y_te, pred, zero_division=0)),
            n_train=int(len(y_tr)),
            n_test=int(len(y_te)),
        )
        _log.info("churn_model_fit auc=%.3f acc=%.3f", metrics.auc, metrics.accuracy)
        return metrics

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not fit. Call fit() first.")
        return self.model.predict_proba(df[self.feature_columns])[:, 1]


def main() -> None:
    metrics = ChurnModel().fit()
    print(metrics.to_dict())


if __name__ == "__main__":
    main()
