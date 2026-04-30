"""Loan Default Probability Model.

Logistic regression / gradient-boosting classifier predicting loan default.
Features: principal, interest rate, term, customer demographics, branch
characteristics, and loan vintage.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..logger import get_logger
from ._io import load_core_frames

_log = get_logger("ml.default")


@dataclass
class DefaultMetrics:
    auc: float
    accuracy: float
    n_train: int
    n_test: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class LoanDefaultModel:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.feature_columns: list[str] = []

    def build_features(self) -> tuple[pd.DataFrame, pd.Series]:
        frames = load_core_frames()
        loans = frames["loans"].copy()
        cust = frames["customers"].copy()

        loans["StartDate"] = pd.to_datetime(loans["StartDate"], errors="coerce")
        cust["DateOfBirth"] = pd.to_datetime(cust["DateOfBirth"], errors="coerce")

        df = loans.merge(cust[["CustomerID", "DateOfBirth"]], on="CustomerID", how="left")
        df["AgeAtOrigination"] = ((df["StartDate"] - df["DateOfBirth"]).dt.days // 365).astype("Int64")
        df["LoanAgeDays"] = (pd.Timestamp.utcnow().tz_localize(None) - df["StartDate"]).dt.days
        df["LoanAgeDays"] = df["LoanAgeDays"].fillna(0).astype(int)

        loan_type_dummies = pd.get_dummies(df["LoanType"], prefix="LType", drop_first=True)
        df = pd.concat([df, loan_type_dummies], axis=1)

        feature_cols = (
            ["PrincipalAmount", "InterestRate", "TermMonths",
             "AgeAtOrigination", "LoanAgeDays"]
            + list(loan_type_dummies.columns)
        )
        x = df[feature_cols].fillna(0)
        y = (df["Status"] == "Defaulted").astype(int)
        self.feature_columns = feature_cols
        return x, y

    def fit(self) -> DefaultMetrics:
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.metrics import accuracy_score, roc_auc_score
            from sklearn.model_selection import train_test_split
        except ImportError as exc:
            raise RuntimeError("scikit-learn is required for LoanDefaultModel.fit()") from exc

        x, y = self.build_features()
        if y.sum() < 5:
            _log.warning("default_skip reason=insufficient_positives")
            return DefaultMetrics(auc=0.5, accuracy=float(y.mean()), n_train=0, n_test=0)

        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.25, random_state=self.random_state, stratify=y,
        )
        self.model = GradientBoostingClassifier(random_state=self.random_state)
        self.model.fit(x_tr, y_tr)
        proba = self.model.predict_proba(x_te)[:, 1]
        pred = (proba >= 0.5).astype(int)

        metrics = DefaultMetrics(
            auc=float(roc_auc_score(y_te, proba)),
            accuracy=float(accuracy_score(y_te, pred)),
            n_train=int(len(y_tr)),
            n_test=int(len(y_te)),
        )
        _log.info("default_model_fit auc=%.3f", metrics.auc)
        return metrics


def main() -> None:
    print(LoanDefaultModel().fit().to_dict())


if __name__ == "__main__":
    main()
