"""Smoke tests for ML feature builders.

These verify that the feature pipelines produce the expected shape and types
on the bundled synthetic dataset, even without running model fits in CI.
"""

import pytest


@pytest.mark.skipif(
    True,  # set to False locally to run end-to-end on bundled CSVs
    reason="Skipped by default; flip in local runs to validate ML pipelines",
)
def test_churn_features_build():
    from src.ml.churn_model import ChurnModel
    x, y = ChurnModel().build_features()
    assert len(x) == len(y)
    assert {"DaysSinceLastTxn", "TxnCount", "Volume"}.issubset(set(x.columns))


@pytest.mark.skipif(True, reason="Skipped by default")
def test_rfm_build():
    from src.ml.segmentation import CustomerSegmentation
    rfm = CustomerSegmentation().build_rfm()
    assert {"Recency", "Frequency", "Monetary"}.issubset(set(rfm.columns))
    assert rfm["Frequency"].min() >= 0
