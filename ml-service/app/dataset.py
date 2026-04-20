from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from .jobber import SERVICES
from .weather_openmeteo import DailySeries


def _week_start_monday(year: int, week: int) -> date:
    return date.fromisocalendar(year, week, 1)


def _week_date_range(year: int, week: int) -> tuple[date, date]:
    start = _week_start_monday(year, week)
    return start, start + timedelta(days=6)


def daily_indices_for_week(daily: DailySeries, year: int, week: int) -> list[int]:
    ws, we = _week_date_range(year, week)
    return [i for i, dd in enumerate(daily.dates) if ws <= dd <= we]


def week_weather_features(daily: DailySeries, year: int, week: int) -> np.ndarray:
    idx = daily_indices_for_week(daily, year, week)
    if not idx:
        return np.zeros(8, dtype=float)

    tmax = [float(daily.tmax[i]) for i in idx if daily.tmax[i] is not None]
    tmin = [float(daily.tmin[i]) for i in idx if daily.tmin[i] is not None]
    pr = [float(daily.precip[i] or 0) for i in idx]
    sn = [float(daily.snow[i] or 0) for i in idx]
    wd = [float(daily.wind[i]) for i in idx if daily.wind[i] is not None]
    rain_days = sum(1 for x in pr if x >= 0.5)

    _, woy_iso, _ = date.fromisocalendar(year, week, 1).isocalendar()
    ang = 2 * np.pi * (woy_iso - 1) / 53.0

    return np.array(
        [
            float(np.sin(ang)),
            float(np.cos(ang)),
            float(np.mean(tmax)) if tmax else 0.0,
            float(np.mean(tmin)) if tmin else 0.0,
            float(np.sum(pr)),
            float(rain_days),
            float(np.mean(wd)) if wd else 0.0,
            float(np.sum(sn)),
        ],
        dtype=float,
    )


def build_training_matrix(
    weekly_counts: dict[tuple[int, int], dict[str, int]],
    daily: DailySeries,
) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]]]:
    rows_x: list[np.ndarray] = []
    rows_y: list[np.ndarray] = []
    keys: list[tuple[int, int]] = []
    for wk in sorted(weekly_counts.keys()):
        counts = weekly_counts[wk]
        yv = np.array([counts[s] for s in SERVICES], dtype=float)
        if yv.sum() <= 0:
            continue
        share = yv / yv.sum()
        x = week_weather_features(daily, wk[0], wk[1])
        rows_x.append(x)
        rows_y.append(share)
        keys.append(wk)
    if not rows_x:
        z = len(SERVICES)
        return np.zeros((0, 8)), np.zeros((0, z)), []
    return np.vstack(rows_x), np.vstack(rows_y), keys


def baseline_by_week_of_year(
    weekly_counts: dict[tuple[int, int], dict[str, int]],
) -> dict[int, np.ndarray]:
    buckets: dict[int, list[np.ndarray]] = {}
    for (y, w), counts in weekly_counts.items():
        _, woy, _ = date.fromisocalendar(y, w, 1).isocalendar()
        vec = np.array([counts[s] for s in SERVICES], dtype=float)
        if vec.sum() <= 0:
            continue
        share = vec / vec.sum()
        buckets.setdefault(woy, []).append(share)
    return {woy: np.mean(np.stack(arrs, axis=0), axis=0) for woy, arrs in buckets.items()}


def next_iso_week_from_today(tz: ZoneInfo) -> tuple[int, int]:
    today = datetime.now(tz).date()
    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(days=7)
    y, w, _ = next_monday.isocalendar()
    return y, w
