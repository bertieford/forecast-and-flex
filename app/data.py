from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd


OUTPUT_ENV_VAR = "FF_OUTPUT_DIR"


def _outputs_dir() -> Path:
    env_value = None
    try:
        import os

        env_value = os.getenv(OUTPUT_ENV_VAR)
    except Exception:
        env_value = None

    if env_value:
        return Path(env_value)

    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "outputs"


@lru_cache(maxsize=1)
def load_forecast_df() -> pd.DataFrame:
    path = _outputs_dir() / "sarima_weather_forecast.csv"
    if not path.exists():
        raise FileNotFoundError(f"Forecast file not found: {path}")

    df = pd.read_csv(path)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"]).dt.date
    return df


@lru_cache(maxsize=1)
def load_metrics_df() -> pd.DataFrame:
    path = _outputs_dir() / "sarima_weather_metrics.csv"
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {path}")

    return pd.read_csv(path)


def forecast_records(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    df = load_forecast_df().copy()

    if start:
        start_date = pd.to_datetime(start).date()
        df = df[df["day"] >= start_date]
    if end:
        end_date = pd.to_datetime(end).date()
        df = df[df["day"] <= end_date]

    if limit is not None:
        df = df.head(limit)

    df = df.assign(day=df["day"].astype(str))
    return df.to_dict(orient="records")


def metrics_record() -> dict:
    df = load_metrics_df()
    if df.empty:
        return {}
    return df.iloc[0].to_dict()
