from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import httpx

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "rain_sum",
    "wind_speed_10m_max",
    "snowfall_sum",
]


@dataclass
class DailySeries:
    dates: list[date]
    tmax: list[float | None]
    tmin: list[float | None]
    precip: list[float | None]
    rain: list[float | None]
    wind: list[float | None]
    snow: list[float | None]


def _parse_daily(data: dict) -> DailySeries:
    d = data.get("daily") or {}
    raw_dates = d.get("time") or []
    dates = [date.fromisoformat(str(x)) for x in raw_dates]
    return DailySeries(
        dates=dates,
        tmax=list(d.get("temperature_2m_max") or []),
        tmin=list(d.get("temperature_2m_min") or []),
        precip=list(d.get("precipitation_sum") or []),
        rain=list(d.get("rain_sum") or []),
        wind=list(d.get("wind_speed_10m_max") or []),
        snow=list(d.get("snowfall_sum") or []),
    )


def fetch_archive(lat: float, lon: float, start: date, end: date, timezone: str) -> DailySeries:
    params: dict = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": timezone,
        "daily": DAILY_VARS,
    }
    with httpx.Client(timeout=90.0) as c:
        r = c.get(ARCHIVE, params=params)
        r.raise_for_status()
    return _parse_daily(r.json())


def fetch_forecast_horizon(lat: float, lon: float, timezone: str, forecast_days: int = 16) -> DailySeries:
    """Past + near-future daily rows; caller filters to the ISO week of interest."""
    params: dict = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone,
        "forecast_days": forecast_days,
        "daily": DAILY_VARS,
    }
    with httpx.Client(timeout=60.0) as c:
        r = c.get(FORECAST, params=params)
        r.raise_for_status()
    return _parse_daily(r.json())
