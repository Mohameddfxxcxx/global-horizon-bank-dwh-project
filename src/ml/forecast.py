"""Branch Revenue Forecaster.

Holt-Winters (additive seasonal) forecast for monthly branch revenue. Falls
back to a deterministic moving-average projection when statsmodels is not
available, ensuring the module always returns a usable forecast.
"""

from __future__ import annotations

import pandas as pd

from ..logger import get_logger
from ._io import load_core_frames

_log = get_logger("ml.forecast")


class BranchRevenueForecaster:
    def __init__(self, horizon_months: int = 12):
        self.horizon_months = horizon_months

    def build_series(self) -> pd.DataFrame:
        frames = load_core_frames()
        tx = frames["transactions"].copy()
        acc = frames["accounts"].copy()
        br = frames["branches"].copy()

        tx["TransactionDate"] = pd.to_datetime(tx["TransactionDate"], errors="coerce")
        tx = tx.merge(acc[["AccountID", "BranchID"]], on="AccountID", how="left")
        tx = tx.merge(br[["BranchID", "BranchName"]], on="BranchID", how="left")
        tx["Month"] = tx["TransactionDate"].dt.to_period("M").dt.to_timestamp()
        monthly = (
            tx.groupby(["BranchName", "Month"])["Amount"].sum().reset_index(name="Revenue")
        )
        return monthly

    def forecast(self) -> pd.DataFrame:
        monthly = self.build_series()
        if monthly.empty:
            return monthly

        import warnings

        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            use_hw = True
        except ImportError:
            use_hw = False

        forecasts = []
        for branch, grp in monthly.groupby("BranchName"):
            grp = grp.sort_values("Month").set_index("Month").asfreq("MS")
            grp["Revenue"] = grp["Revenue"].ffill()
            if len(grp) < 6:
                continue

            if use_hw and len(grp) >= 18:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = ExponentialSmoothing(
                            grp["Revenue"], seasonal="add", seasonal_periods=12, trend="add",
                        ).fit(optimized=True)
                        f = model.forecast(self.horizon_months)
                except Exception:  # noqa: BLE001
                    f = self._naive(grp["Revenue"])
            else:
                f = self._naive(grp["Revenue"])

            future_dates = pd.date_range(
                start=grp.index.max() + pd.offsets.MonthBegin(1),
                periods=self.horizon_months,
                freq="MS",
            )
            forecasts.append(pd.DataFrame({
                "BranchName": branch,
                "Month": future_dates,
                "RevenueForecast": f.values if hasattr(f, "values") else f,
            }))

        out = pd.concat(forecasts, ignore_index=True) if forecasts else pd.DataFrame()
        _log.info("branch_forecast branches=%d horizon=%d", out["BranchName"].nunique() if not out.empty else 0, self.horizon_months)
        return out

    def _naive(self, series: pd.Series) -> pd.Series:
        last_year = series.tail(min(12, len(series)))
        avg = last_year.mean()
        trend = (series.tail(3).mean() - series.head(3).mean()) / max(len(series), 1)
        return pd.Series([avg + trend * (i + 1) for i in range(self.horizon_months)])


def main() -> None:
    df = BranchRevenueForecaster().forecast()
    if not df.empty:
        print(df.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
