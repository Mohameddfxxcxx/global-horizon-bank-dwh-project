"""Run all ML pipelines as a single CLI command.

Usage:
    python -m src.ml          # all models
    python -m src.ml churn    # only churn
    python -m src.ml fraud
    python -m src.ml seg
    python -m src.ml forecast
    python -m src.ml default
"""

from __future__ import annotations

import sys

from .churn_model import ChurnModel
from .default_model import LoanDefaultModel
from .forecast import BranchRevenueForecaster
from .fraud_model import FraudDetector
from .segmentation import CustomerSegmentation


def _churn() -> None:
    print("Churn:", ChurnModel().fit().to_dict())


def _default() -> None:
    print("Default:", LoanDefaultModel().fit().to_dict())


def _fraud() -> None:
    df = FraudDetector().fit_score()
    print(f"Fraud: scored={len(df)} anomalies={int(df['is_anomaly'].sum())}")


def _seg() -> None:
    seg = CustomerSegmentation()
    rfm = seg.fit()
    rfm = seg.next_best_offer(rfm)
    print("Segments:", rfm["Segment"].value_counts().to_dict())


def _forecast() -> None:
    df = BranchRevenueForecaster().forecast()
    print(f"Forecast: branches={df['BranchName'].nunique()} rows={len(df)}")


_RUNNERS = {"churn": _churn, "default": _default, "fraud": _fraud,
            "seg": _seg, "forecast": _forecast}


def main(argv: list[str]) -> None:
    if not argv:
        for fn in _RUNNERS.values():
            fn()
        return
    for name in argv:
        fn = _RUNNERS.get(name.lower())
        if fn is None:
            print(f"unknown model: {name} (choose: {', '.join(_RUNNERS)})")
            continue
        fn()


if __name__ == "__main__":
    main(sys.argv[1:])
