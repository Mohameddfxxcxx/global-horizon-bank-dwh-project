"""Tests for the retry decorator."""

import pytest

from src.retry import retry


def test_retry_returns_value_on_success():
    @retry(attempts=3, delay=0.01, backoff=1.0, jitter=0)
    def f():
        return 42

    assert f() == 42


def test_retry_eventually_succeeds():
    counter = {"n": 0}

    @retry(attempts=4, delay=0.01, backoff=1.0, jitter=0, exceptions=(ValueError,))
    def flaky():
        counter["n"] += 1
        if counter["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert counter["n"] == 3


def test_retry_exhausts_and_raises():
    @retry(attempts=2, delay=0.01, backoff=1.0, jitter=0, exceptions=(RuntimeError,))
    def always_fails():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        always_fails()
