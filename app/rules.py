# app/rules.py
from __future__ import annotations
from datetime import datetime, timezone
import os, re
from typing import Tuple

# Optional demo freeze: export EZ_DEMO_NOW_UTC="2025-11-01T12:00:00Z"
_DEMO_NOW = os.getenv("EZ_DEMO_NOW_UTC")

ISO_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

def _parse_iso_z(s: str) -> datetime:
    """
    Accept 'YYYY-MM-DDTHH:MM:SSZ' or the same with '+00:00'.
    Raises ValueError with a friendly message if invalid.
    """
    if not s:
        raise ValueError("Empty deadline string. Expected 'YYYY-MM-DDTHH:MM:SSZ'.")
    s = s.strip().upper()
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    if not ISO_Z_RE.match(s):
        raise ValueError(f"Bad ISO timestamp '{s}'. Expected 'YYYY-MM-DDTHH:MM:SSZ'.")
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

def now_utc() -> datetime:
    if _DEMO_NOW:
        return _parse_iso_z(_DEMO_NOW)
    return datetime.now(timezone.utc)

def hours_to_deadline(deadline_iso: str, now: datetime | None = None) -> float:
    if now is None:
        now = now_utc()
    dl = _parse_iso_z(deadline_iso)
    return (dl - now).total_seconds() / 3600.0

def auto_approve_beyond_48h(deadline_iso: str, now: datetime | None = None) -> Tuple[bool, float]:
    h = hours_to_deadline(deadline_iso, now)
    return (h > 48, h)

def deadline_meta(deadline_iso: str) -> dict:
    now = now_utc()
    h = hours_to_deadline(deadline_iso, now)
    dl = _parse_iso_z(deadline_iso)
    return {
        "now_utc": now.isoformat().replace("+00:00", "Z"),
        "deadline_utc": dl.isoformat().replace("+00:00", "Z"),
        "hours_to_deadline": round(h, 1),
        "within_48h": bool(0 <= h <= 48),
        "beyond_48h": bool(h > 48),
    }
