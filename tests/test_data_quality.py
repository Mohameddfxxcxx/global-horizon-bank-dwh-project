"""Tests for the DQ scoring engine."""

import pandas as pd

from src.data_quality import score_dataframe
from src.validation import validate_table


def test_perfect_dataframe_scores_high():
    df = pd.DataFrame({"id": [1, 2, 3, 4], "amount": [10.0, 20.0, 30.0, 40.0]})
    report = validate_table(
        df, table="t", required=["id", "amount"],
        not_null=["id", "amount"], unique=["id"],
        ranges={"amount": (0, 1000)},
    )
    score = score_dataframe(
        df, table="t", not_null=["id", "amount"], unique=["id"], report=report,
    )
    assert score.score >= 95
    assert score.completeness == 100.0
    assert score.uniqueness == 100.0


def test_dataframe_with_nulls_loses_completeness():
    df = pd.DataFrame({"id": [1, None, 3], "amount": [10.0, 20.0, None]})
    report = validate_table(
        df, table="t", required=["id", "amount"],
        not_null=["id", "amount"], unique=["id"],
    )
    score = score_dataframe(
        df, table="t", not_null=["id", "amount"], unique=["id"], report=report,
    )
    assert score.completeness < 100
    assert score.score < 95
