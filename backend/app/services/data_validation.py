from io import BytesIO

import pandas as pd


class DataValidationError(ValueError):
    pass


def parse_and_clean_csv(file_bytes: bytes, date_column: str, value_column: str) -> pd.DataFrame:
    """Parse a CSV into a sorted, regularly-spaced (date, value) series.

    Raises DataValidationError on missing columns, unparseable dates, or a
    series too short to forecast.
    """
    try:
        df = pd.read_csv(BytesIO(file_bytes))
    except Exception as exc:
        raise DataValidationError(f"Could not parse file as CSV: {exc}") from exc

    missing = {date_column, value_column} - set(df.columns)
    if missing:
        raise DataValidationError(f"Columns not found in file: {sorted(missing)}")

    df = df[[date_column, value_column]].rename(columns={date_column: "date", value_column: "value"})

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise DataValidationError("Some rows have a date that could not be parsed")

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["date"]).sort_values("date")
    df = df.groupby("date", as_index=False)["value"].mean()

    if len(df) < 10:
        raise DataValidationError("Need at least 10 data points to forecast")

    inferred_freq = pd.infer_freq(df["date"]) or "D"
    full_index = pd.date_range(df["date"].min(), df["date"].max(), freq=inferred_freq)
    df = df.set_index("date").reindex(full_index)
    df["value"] = df["value"].interpolate(method="linear").ffill().bfill()
    df = df.rename_axis("date").reset_index()

    return df
