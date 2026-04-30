"""Base class for ETL jobs.

Defines the lifecycle hooks (extract → transform → load) and standard logging,
timing, and audit emission. Concrete jobs override the three primitive methods.
"""

from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..logger import get_logger


@dataclass
class JobResult:
    job_name: str
    run_id: str
    rows_in: int = 0
    rows_out: int = 0
    duration_seconds: float = 0.0
    status: str = "PENDING"
    error: str | None = None
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class ETLJob(abc.ABC):
    """Abstract base for an ETL job.

    Implementers override ``extract``, ``transform``, and ``load``. The base
    ``run`` method coordinates the lifecycle and ensures every run produces a
    deterministic ``JobResult``.
    """

    name: str = "etl_job"

    def __init__(self) -> None:
        self.log = get_logger(f"etl.{self.name}", log_file=f"etl_{self.name}.log")

    # ------------------------------------------------------------------
    # Lifecycle primitives — override in subclasses
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def extract(self) -> Any: ...

    @abc.abstractmethod
    def transform(self, payload: Any) -> Any: ...

    @abc.abstractmethod
    def load(self, payload: Any) -> int:
        """Return the number of rows persisted."""

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------
    def run(self) -> JobResult:
        run_id = str(uuid.uuid4())
        result = JobResult(job_name=self.name, run_id=run_id, status="RUNNING")
        started = time.perf_counter()
        self.log.info("etl_start job=%s run_id=%s", self.name, run_id)

        try:
            payload = self.extract()
            try:
                result.rows_in = len(payload)  # type: ignore[arg-type]
            except TypeError:
                pass
            payload = self.transform(payload)
            rows_loaded = self.load(payload)
            result.rows_out = rows_loaded
            result.status = "SUCCESS"
        except Exception as exc:  # noqa: BLE001 — top-level orchestrator
            result.status = "FAILED"
            result.error = str(exc)
            self.log.exception("etl_failed job=%s run_id=%s", self.name, run_id)
            raise
        finally:
            result.duration_seconds = round(time.perf_counter() - started, 3)
            self.log.info(
                "etl_end job=%s run_id=%s status=%s rows_in=%d rows_out=%d duration=%ss",
                self.name, run_id, result.status,
                result.rows_in, result.rows_out, result.duration_seconds,
            )

        return result
