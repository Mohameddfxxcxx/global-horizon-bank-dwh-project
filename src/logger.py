"""Structured logging for the Global Horizon Bank platform.

Emits ISO-timestamped, key=value records to stderr by default and to a rotating
file under ``logs/`` when invoked from a long-running pipeline. Designed to be
machine-parseable for downstream observability tooling.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import CONFIG, LOG_DIR

_LOG_FORMAT = (
    "%(asctime)sZ level=%(levelname)s logger=%(name)s "
    "module=%(module)s line=%(lineno)d msg=%(message)s"
)


def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """Return a configured logger.

    Each logger is configured exactly once; subsequent calls return the cached
    instance with the existing handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(CONFIG.log_level)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S")

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if log_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = Path(log_file)
        if not path.is_absolute():
            path = LOG_DIR / log_file
        rotating = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
        rotating.setFormatter(formatter)
        logger.addHandler(rotating)

    return logger
