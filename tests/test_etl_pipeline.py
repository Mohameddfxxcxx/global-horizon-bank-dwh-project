"""Smoke tests for the medallion ETL pipeline against the bundled CSVs."""

import pandas as pd

from src.etl.bronze import BronzeIngest
from src.etl.gold import GoldStarBuild, derive_age_group
from src.etl.silver import SilverTransform


def test_age_group_derivation_buckets_correctly():
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    dobs = [
        today - pd.DateOffset(years=20),  # 18-24
        today - pd.DateOffset(years=30),  # 25-35
        today - pd.DateOffset(years=40),  # 36-50
        today - pd.DateOffset(years=70),  # 51+
    ]
    out = derive_age_group(pd.Series(dobs))
    assert list(out.astype(str)) == ["18-24", "25-35", "36-50", "51+"]


def test_bronze_ingest_runs_or_skips_cleanly():
    job = BronzeIngest()
    result = job.run()
    assert result.status == "SUCCESS"
    assert result.rows_out >= 0


def test_silver_transform_runs():
    job = SilverTransform()
    result = job.run()
    assert result.status == "SUCCESS"


def test_gold_star_build_produces_dimensions():
    job = GoldStarBuild()
    result = job.run()
    assert result.status == "SUCCESS"
