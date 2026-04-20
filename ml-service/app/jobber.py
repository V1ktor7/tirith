from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

SERVICES = ["Windows", "Gutters", "Spider", "Pressure", "Roof", "Other"]


def unwrap_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, list) and raw:
        raw = raw[0]
    if not isinstance(raw, dict):
        raise ValueError("Payload must be a JSON object or singleton array")
    return raw


def detect_svc(title: str | None) -> str:
    if not title:
        return "Other"
    t = title.lower()
    if "vitre" in t or "window" in t:
        return "Windows"
    if "goutti" in t or "gutter" in t:
        return "Gutters"
    if "araign" in t or "spider" in t:
        return "Spider"
    if "pression" in t or "pressure" in t or "power wash" in t:
        return "Pressure"
    if "toit" in t or "roof" in t:
        return "Roof"
    return "Other"


def job_date_mtl(iso: str | None, tz: ZoneInfo) -> datetime | None:
    if not iso:
        return None
    s = iso.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(tz)
    except ValueError:
        return None


def iso_week_key(dt: datetime) -> tuple[int, int]:
    y, w, _ = dt.isocalendar()
    return y, w


def weekly_service_counts(jobs: list[dict], tz: ZoneInfo) -> dict[tuple[int, int], dict[str, int]]:
    per: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: {s: 0 for s in SERVICES})
    for j in jobs:
        dt = job_date_mtl(j.get("startAt") or j.get("createdAt"), tz)
        if not dt:
            continue
        wk = iso_week_key(dt)
        svc = detect_svc(j.get("title"))
        per[wk][svc] += 1
    return dict(per)
