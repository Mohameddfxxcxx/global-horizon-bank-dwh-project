"""Tests for the validation framework."""

import pandas as pd

from src.validation import (
    ValidationReport,
    check_referential_integrity,
    validate_table,
)


def test_validate_table_flags_missing_columns():
    df = pd.DataFrame({"a": [1, 2, 3]})
    report = validate_table(df, table="t", required=["a", "b"])
    assert report.critical_count >= 1
    assert any(i.rule == "schema" for i in report.issues)


def test_validate_table_flags_nulls_and_duplicates():
    df = pd.DataFrame({"id": [1, 1, None, 3], "v": [10, 20, 30, 40]})
    report = validate_table(
        df, table="t", required=["id", "v"], not_null=["id"], unique=["id"],
    )
    rules = {i.rule for i in report.issues}
    assert "not_null" in rules
    assert "unique" in rules


def test_referential_integrity_detects_orphans():
    parent = pd.DataFrame({"pk": [1, 2, 3]})
    child = pd.DataFrame({"fk": [1, 2, 99]})
    rep = ValidationReport(table="child", rows=len(child))
    check_referential_integrity(child, parent=parent, fk_column="fk", pk_column="pk", report=rep)
    assert rep.critical_count == 1
    assert rep.issues[0].rule == "fk"
    assert rep.issues[0].count == 1


def test_validate_table_range_warnings():
    df = pd.DataFrame({"a": [1, 5, -10, 1000]})
    rep = validate_table(
        df, table="t", required=["a"], ranges={"a": (0, 100)},
    )
    assert any(i.rule == "range" for i in rep.issues)
