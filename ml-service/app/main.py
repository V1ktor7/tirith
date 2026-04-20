from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .dataset import (
    baseline_by_week_of_year,
    build_training_matrix,
    next_iso_week_from_today,
    week_weather_features,
)
from .jobber import SERVICES, unwrap_payload, weekly_service_counts
from .model_service_mix import multinomial_log_loss, predict_shares, train_ridge_shares
from .weather_openmeteo import DailySeries, fetch_archive, fetch_forecast_horizon

app = FastAPI(title="QuickClean ML")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT = DATA_PATH / "last_snapshot.json"


def _ensure_data_dir() -> None:
    DATA_PATH.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "snapshot_exists": SNAPSHOT.is_file(),
        "webhook_configured": bool(settings.webhook_url),
        "min_weeks_ml": settings.min_weeks_ml,
    }


@app.get("/ingest")
def ingest_get() -> dict[str, Any]:
    if not settings.webhook_url:
        raise HTTPException(500, "Set WEBHOOK_URL in environment")
    _ensure_data_dir()
    with httpx.Client(timeout=120.0) as c:
        r = c.get(settings.webhook_url, headers={"Accept": "application/json"})
        r.raise_for_status()
        raw = r.json()
    SNAPSHOT.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    payload = unwrap_payload(raw)
    return {"ok": True, "jobs": len(payload.get("jobs") or []), "path": str(SNAPSHOT)}


@app.post("/ingest")
def ingest_post(body: Any) -> dict[str, Any]:
    _ensure_data_dir()
    SNAPSHOT.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    payload = unwrap_payload(body)
    return {"ok": True, "jobs": len(payload.get("jobs") or [])}


@app.get("/predict/service-mix")
def predict_service_mix(horizon: int = 1) -> dict[str, Any]:
    _ = horizon  # reserved for multi-week output
    if not SNAPSHOT.is_file():
        raise HTTPException(400, "No snapshot — call GET /ingest or POST /ingest first")
    raw = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    payload = unwrap_payload(raw)
    jobs = payload.get("jobs") or []
    tz = ZoneInfo(settings.timezone)

    weekly = weekly_service_counts(jobs, tz)
    if not weekly:
        raise HTTPException(400, "No jobs with parsable dates in snapshot")

    min_d = min(date.fromisocalendar(y, w, 1) for y, w in weekly.keys())
    max_d = max(date.fromisocalendar(y, w, 7) for y, w in weekly.keys())
    pad_start = min_d - timedelta(days=7)
    pad_end = max_d + timedelta(days=7)

    daily_hist = fetch_archive(settings.mtl_lat, settings.mtl_lon, pad_start, pad_end, settings.timezone)
    X, Y, _keys = build_training_matrix(weekly, daily_hist)
    baseline_map = baseline_by_week_of_year(weekly)

    n_weeks = X.shape[0]
    note = "ok"
    model = None
    val_loss: float | None = None

    if n_weeks >= settings.min_weeks_ml:
        hold = max(1, int(round(0.2 * n_weeks)))
        X_tr, Y_tr = X[:-hold], Y[:-hold]
        X_va, Y_va = X[-hold:], Y[-hold:]
        if X_tr.shape[0] >= 4:
            model = train_ridge_shares(X_tr, Y_tr)
            pred_va = predict_shares(model, X_va)
            val_loss = multinomial_log_loss(Y_va, pred_va)

    ny, nw = next_iso_week_from_today(tz)
    ws = date.fromisocalendar(ny, nw, 1)
    we = ws + timedelta(days=6)

    daily_fc = fetch_forecast_horizon(settings.mtl_lat, settings.mtl_lon, settings.timezone, forecast_days=16)
    idx_fc = [i for i, d in enumerate(daily_fc.dates) if ws <= d <= we]
    if not idx_fc:
        note = "forecast_missing_days_for_target_week"
        x_next = week_weather_features(daily_hist, ny, nw).reshape(1, -1)
    else:
        sub = DailySeries(
            dates=[daily_fc.dates[i] for i in idx_fc],
            tmax=[daily_fc.tmax[i] for i in idx_fc],
            tmin=[daily_fc.tmin[i] for i in idx_fc],
            precip=[daily_fc.precip[i] for i in idx_fc],
            rain=[daily_fc.rain[i] for i in idx_fc],
            wind=[daily_fc.wind[i] for i in idx_fc],
            snow=[daily_fc.snow[i] for i in idx_fc],
        )
        x_next = week_weather_features(sub, ny, nw).reshape(1, -1)

    if model is not None:
        ml_p = predict_shares(model, x_next)[0]
    else:
        ml_p = None
        note = f"insufficient_weeks_need_{settings.min_weeks_ml}_got_{n_weeks}"

    _, woy, _ = ws.isocalendar()
    bvec = baseline_map.get(woy)
    if bvec is None:
        bvec = np.ones(len(SERVICES)) / len(SERVICES)
        note = (note + ";baseline_week_fallback_uniform").strip(";")

    out_ml = {SERVICES[i]: float(ml_p[i]) for i in range(len(SERVICES))} if ml_p is not None else None
    out_base = {SERVICES[i]: float(bvec[i]) for i in range(len(SERVICES))}

    top = max((out_ml or out_base).values())
    high_demand = {s: bool(abs((out_ml or out_base)[s] - top) < 1e-9) for s in SERVICES}

    weeks_out = [
        {
            "weekStart": ws.isoformat(),
            "weekEnd": we.isoformat(),
            "isoYear": ny,
            "isoWeek": nw,
            "predicted_mix_ml": out_ml,
            "predicted_mix_baseline": out_base,
            "high_demand": high_demand,
        }
    ]

    safe_loss: float | None = None
    if val_loss is not None and math.isfinite(val_loss):
        safe_loss = round(float(val_loss), 6)

    return {
        "model": "ridge_multioutput_shares" if model else "baseline_only",
        "trained_weeks": n_weeks,
        "validation_log_loss": safe_loss,
        "note": note,
        "services": SERVICES,
        "weeks": weeks_out,
    }
