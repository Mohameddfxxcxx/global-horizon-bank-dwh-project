"""Centralized configuration for the Global Horizon Bank platform.

All environment-variable lookups, file paths, and tunable parameters live here.
The rest of the codebase imports from this module — never reads ``os.environ``
directly. This keeps configuration auditable and testable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
BRONZE_DIR: Path = DATA_DIR / "bronze"
SILVER_DIR: Path = DATA_DIR / "silver"
GOLD_DIR: Path = DATA_DIR / "gold"
LOG_DIR: Path = PROJECT_ROOT / "logs"
SQL_DIR: Path = PROJECT_ROOT / "sql"


@dataclass(frozen=True)
class SQLServerConfig:
    """SQL Server connection settings, sourced from environment variables."""

    host: str = os.getenv("SQLSERVER_HOST", "localhost")
    port: int = int(os.getenv("SQLSERVER_PORT", "21433"))
    user: str = os.getenv("SQLSERVER_USER", "sa")
    password: str = os.getenv("SQLSERVER_PASSWORD", "MyStrongPass123!")
    database_oltp: str = os.getenv("SQLSERVER_DB_OLTP", "GlobalHorizon_OLTP")
    database_dwh: str = os.getenv("SQLSERVER_DB", "GlobalHorizon_DWH")
    timeout: int = int(os.getenv("SQLSERVER_TIMEOUT", "10"))

    def sqlalchemy_url(self, db: str | None = None) -> str:
        target = db or self.database_dwh
        return f"mssql+pymssql://{self.user}:{self.password}@{self.host}:{self.port}/{target}"


@dataclass(frozen=True)
class DataGenerationConfig:
    num_customers: int = int(os.getenv("GHB_NUM_CUSTOMERS", "10000"))
    num_branches: int = int(os.getenv("GHB_NUM_BRANCHES", "50"))
    num_employees: int = int(os.getenv("GHB_NUM_EMPLOYEES", "200"))
    num_accounts: int = int(os.getenv("GHB_NUM_ACCOUNTS", "12000"))
    num_loans: int = int(os.getenv("GHB_NUM_LOANS", "3000"))
    num_transactions: int = int(os.getenv("GHB_NUM_TRANSACTIONS", "100000"))
    seed: int = int(os.getenv("GHB_SEED", "42"))


@dataclass(frozen=True)
class DataQualityThresholds:
    """Minimum DQ score to promote data to the next medallion zone."""

    bronze_min: float = 80.0
    silver_min: float = 95.0
    gold_min: float = 99.0


@dataclass(frozen=True)
class AppConfig:
    sql: SQLServerConfig = field(default_factory=SQLServerConfig)
    data_gen: DataGenerationConfig = field(default_factory=DataGenerationConfig)
    dq: DataQualityThresholds = field(default_factory=DataQualityThresholds)
    log_level: str = os.getenv("GHB_LOG_LEVEL", "INFO").upper()
    environment: str = os.getenv("GHB_ENV", "development")

    def ensure_dirs(self) -> None:
        for d in (DATA_DIR, RAW_DATA_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR, LOG_DIR):
            d.mkdir(parents=True, exist_ok=True)


CONFIG = AppConfig()
