import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Plausible seasonal cycle length per inferred pandas frequency, used only if
# the series has enough history for at least two full cycles.
_SEASONAL_PERIODS_BY_FREQ = {
    "D": 7,
    "B": 5,
    "W": 52,
    "M": 12,
    "MS": 12,
    "Q": 4,
    "QS": 4,
}


def _seasonal_periods(freq: str, n_points: int) -> int | None:
    period = _SEASONAL_PERIODS_BY_FREQ.get(freq)
    if period and n_points >= 2 * period:
        return period
    return None


def run_forecast(df: pd.DataFrame, horizon: int) -> dict:
    """Fit a Holt-Winters model on a cleaned (date, value) series.

    Returns chart-ready history + forecast points plus the params used,
    so the run can be stored verbatim on ForecastRun.result.
    """
    freq = pd.infer_freq(df["date"]) or "D"
    n_points = len(df)
    seasonal_periods = _seasonal_periods(freq, n_points)

    model = ExponentialSmoothing(
        df["value"],
        trend="add",
        seasonal="add" if seasonal_periods else None,
        seasonal_periods=seasonal_periods,
        initialization_method="estimated",
    ).fit()

    forecast_values = model.forecast(horizon)
    future_dates = pd.date_range(df["date"].iloc[-1], periods=horizon + 1, freq=freq)[1:]

    return {
        "model": "holt_winters",
        "freq": freq,
        "seasonal_periods": seasonal_periods,
        "horizon": horizon,
        "history": [
            {"date": d.isoformat(), "value": float(v)}
            for d, v in zip(df["date"], df["value"], strict=True)
        ],
        "forecast": [
            {"date": d.isoformat(), "value": float(v)}
            for d, v in zip(future_dates, forecast_values, strict=True)
        ],
    }
