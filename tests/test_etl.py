"""Tests for the ETL framework."""

from typing import Any

from src.etl.base import ETLJob, JobResult


class _FakeJob(ETLJob):
    name = "fake"

    def __init__(self):
        super().__init__()
        self.calls = []

    def extract(self) -> Any:
        self.calls.append("extract")
        return [1, 2, 3]

    def transform(self, payload: Any) -> Any:
        self.calls.append("transform")
        return [x * 2 for x in payload]

    def load(self, payload: Any) -> int:
        self.calls.append("load")
        return len(payload)


def test_etl_lifecycle_runs_in_order():
    job = _FakeJob()
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.status == "SUCCESS"
    assert result.rows_in == 3
    assert result.rows_out == 3
    assert job.calls == ["extract", "transform", "load"]


def test_etl_failure_sets_status():
    class _BoomJob(_FakeJob):
        def transform(self, payload):
            raise RuntimeError("boom")

    import pytest
    job = _BoomJob()
    with pytest.raises(RuntimeError):
        job.run()
