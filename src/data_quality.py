"""Data Quality scoring engine.

Computes a 0–100 quality score for a dataframe / report combination, using
weighted contributions from completeness, uniqueness, validity (range/format)
and referential integrity. Scores feed the ETL audit log and gate medallion
promotion.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from .validation import ValidationReport


@dataclass
class DataQualityScore:
    table: str
    score: float
    completeness: float
    uniqueness: float
    validity: float
    integrity: float
    issues: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _completeness(df: pd.DataFrame, columns: Iterable[str]) -> float:
    if df.empty:
        return 0.0
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return 100.0
    total = df[cols].size
    nulls = df[cols].isna().sum().sum()
    return float(100 * (1 - nulls / total))


def _uniqueness(df: pd.DataFrame, columns: Iterable[str]) -> float:
    if df.empty:
        return 100.0
    scores = []
    for col in columns:
        if col not in df.columns:
            continue
        if len(df) == 0:
            continue
        dupes = df.duplicated(subset=[col]).sum()
        scores.append(100 * (1 - dupes / len(df)))
    return float(sum(scores) / len(scores)) if scores else 100.0


def score_dataframe(
    df: pd.DataFrame,
    *,
    table: str,
    not_null: Iterable[str],
    unique: Iterable[str],
    report: ValidationReport,
    weights: tuple[float, float, float, float] = (0.4, 0.2, 0.3, 0.1),
) -> DataQualityScore:
    """Combine validation report into a 0–100 score.

    Weights default to: completeness 40%, uniqueness 20%, validity 30%, integrity 10%.
    """
    completeness = _completeness(df, not_null)
    uniqueness = _uniqueness(df, unique)

    rows = max(len(df), 1)
    invalid = sum(i.count for i in report.issues if i.rule in ("range", "format"))
    validity = max(0.0, 100 * (1 - invalid / rows))

    integrity_issues = sum(i.count for i in report.issues if i.rule == "fk")
    integrity = max(0.0, 100 * (1 - integrity_issues / rows))

    w_c, w_u, w_v, w_i = weights
    score = (
        completeness * w_c
        + uniqueness * w_u
        + validity * w_v
        + integrity * w_i
    )
    # Critical issues hard-cap the score
    if report.critical_count:
        score = min(score, 80)

    return DataQualityScore(
        table=table,
        score=round(score, 2),
        completeness=round(completeness, 2),
        uniqueness=round(uniqueness, 2),
        validity=round(validity, 2),
        integrity=round(integrity, 2),
        issues=len(report.issues),
    )
