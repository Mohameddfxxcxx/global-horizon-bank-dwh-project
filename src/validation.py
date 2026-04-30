"""Schema and constraint validation framework.

Lightweight, dependency-free validation aligned to the table contracts in the
data dictionary. Each validator returns a list of issue records consumable by
the ``data_quality`` scoring engine.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationIssue:
    column: str
    rule: str
    severity: str
    count: int
    detail: str = ""


@dataclass
class ValidationReport:
    table: str
    rows: int
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_dict(self) -> dict:
        return {
            "table": self.table,
            "rows": self.rows,
            "issues": [i.__dict__ for i in self.issues],
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
        }


def check_schema(
    df: pd.DataFrame,
    *,
    required_columns: Sequence[str],
    table: str,
) -> ValidationReport:
    report = ValidationReport(table=table, rows=len(df))
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        report.add(
            ValidationIssue(
                column=",".join(missing),
                rule="schema",
                severity="critical",
                count=len(missing),
                detail=f"missing columns: {missing}",
            )
        )
    return report


def check_nulls(df: pd.DataFrame, *, not_null: Iterable[str], report: ValidationReport) -> None:
    for col in not_null:
        if col not in df.columns:
            continue
        n = int(df[col].isna().sum())
        if n > 0:
            report.add(ValidationIssue(col, "not_null", "critical", n, "null values present"))


def check_unique(df: pd.DataFrame, *, unique_keys: Iterable[str], report: ValidationReport) -> None:
    for col in unique_keys:
        if col not in df.columns:
            continue
        n = int(df.duplicated(subset=[col]).sum())
        if n > 0:
            report.add(ValidationIssue(col, "unique", "critical", n, "duplicate values"))


def check_ranges(
    df: pd.DataFrame,
    *,
    ranges: Mapping[str, tuple],
    report: ValidationReport,
) -> None:
    for col, (lo, hi) in ranges.items():
        if col not in df.columns:
            continue
        bad = ((df[col] < lo) | (df[col] > hi)).sum()
        if bad > 0:
            report.add(
                ValidationIssue(
                    col, "range", "warning", int(bad), f"values outside [{lo}, {hi}]",
                )
            )


def check_referential_integrity(
    child: pd.DataFrame,
    *,
    parent: pd.DataFrame,
    fk_column: str,
    pk_column: str,
    report: ValidationReport,
) -> None:
    if fk_column not in child.columns or pk_column not in parent.columns:
        return
    orphans = ~child[fk_column].isin(parent[pk_column])
    n = int(orphans.sum())
    if n > 0:
        report.add(
            ValidationIssue(
                fk_column, "fk", "critical", n, f"orphans against {pk_column}",
            )
        )


def validate_table(
    df: pd.DataFrame,
    *,
    table: str,
    required: Sequence[str],
    not_null: Iterable[str] = (),
    unique: Iterable[str] = (),
    ranges: Mapping[str, tuple] | None = None,
) -> ValidationReport:
    report = check_schema(df, required_columns=required, table=table)
    check_nulls(df, not_null=not_null, report=report)
    check_unique(df, unique_keys=unique, report=report)
    if ranges:
        check_ranges(df, ranges=ranges, report=report)
    return report
