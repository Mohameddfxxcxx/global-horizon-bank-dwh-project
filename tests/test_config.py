"""Tests for the configuration module."""

from src.config import CONFIG, DataQualityThresholds, SQLServerConfig


def test_config_singleton_loaded():
    assert CONFIG.sql.database_dwh
    assert CONFIG.sql.host
    assert CONFIG.dq.silver_min == 95.0
    assert CONFIG.dq.gold_min == 99.0


def test_sqlalchemy_url_format():
    sql = SQLServerConfig()
    url = sql.sqlalchemy_url("test_db")
    assert url.startswith("mssql+pymssql://")
    assert "test_db" in url


def test_quality_thresholds_ordered():
    dq = DataQualityThresholds()
    assert dq.bronze_min < dq.silver_min < dq.gold_min
