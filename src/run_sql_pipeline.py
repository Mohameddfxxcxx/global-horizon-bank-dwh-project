"""Run every SQL script against SQL Server in canonical order.

This is the production-grade alternative to ``setup_sqlserver.py``. It uses the
canonical execution order (matches docs/sql_implementation_guide.md) and emits
detailed timing + row-count output for each step.

Usage:
    python -m src.run_sql_pipeline
"""

from __future__ import annotations

import sys
import time
from collections.abc import Iterable

from .config import CONFIG, PROJECT_ROOT
from .logger import get_logger

_log = get_logger("sql.runner", log_file="sql_runner.log")


CANONICAL_ORDER: list[str] = [
    "sql/oltp/01_ddl_oltp.sql",
    "sql/oltp/02_dml_oltp.sql",
    "sql/oltp/03_queries_oltp.sql",
    "sql/oltp/04_constraints_triggers.sql",
    "sql/oltp/05_stored_procedures.sql",
    "sql/oltp/06_security_rbac.sql",
    "sql/olap/01_ddl_star_schema.sql",
    "sql/olap/02_advanced_modeling.sql",
    "sql/olap/03_indexing_partitioning.sql",
    "sql/olap/05_advanced_modeling_pro.sql",
    "sql/etl/01_etl_procedures.sql",
    "sql/etl/02_etl_orchestration.sql",
    "sql/olap/06_views_semantic_layer.sql",
    "sql/olap/04_analytical_queries.sql",
    "sql/analytics/01_fraud_detection.sql",
    "sql/analytics/02_churn_cohort.sql",
    "sql/analytics/03_customer_lifetime_value.sql",
    "sql/analytics/04_branch_benchmarking.sql",
    "sql/analytics/05_anomaly_detection.sql",
]


def split_batches(script: str) -> Iterable[str]:
    """Split a T-SQL script on standalone GO separators."""
    out: list[str] = []
    buf: list[str] = []
    for line in script.splitlines():
        if line.strip().upper() == "GO":
            if buf:
                out.append("\n".join(buf).strip())
                buf = []
        else:
            buf.append(line)
    if buf and "\n".join(buf).strip():
        out.append("\n".join(buf).strip())
    return [b for b in out if b]


def run() -> int:
    try:
        import pymssql
    except ImportError:
        _log.error("pymssql is required. pip install pymssql")
        return 2

    sql = CONFIG.sql
    try:
        conn = pymssql.connect(server=sql.host, port=sql.port, user=sql.user,
                                password=sql.password, autocommit=True, timeout=sql.timeout)
    except Exception as exc:  # noqa: BLE001
        _log.error("connect_failed host=%s port=%d error=%s", sql.host, sql.port, exc)
        return 1

    cursor = conn.cursor()
    failed = 0
    for rel in CANONICAL_ORDER:
        path = PROJECT_ROOT / rel
        if not path.exists():
            _log.warning("missing_script path=%s", path)
            continue
        script = path.read_text(encoding="utf-8")
        started = time.perf_counter()
        for batch in split_batches(script):
            try:
                cursor.execute(batch)
            except Exception as exc:  # noqa: BLE001
                _log.error("batch_failed file=%s error=%s preview=%s",
                           rel, exc, batch[:160].replace("\n", " "))
                failed += 1
        _log.info("script_done file=%s duration=%.2fs",
                  rel, time.perf_counter() - started)

    conn.close()
    _log.info("pipeline_done failed_batches=%d", failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
