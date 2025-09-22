"""
Utility helpers for Teleagriculture kits API

Provides:
- BASE_URL, HEADERS (with optional Bearer from KIT_API_KEY env)
- get_kit_info(kit_id)
- get_kit_measurements_df(kit_id, sensors=None, page_size=100)
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Optional

import pandas as pd
import requests

# API configuration
BASE_URL = os.getenv("KITS_API_BASE", "https://kits.teleagriculture.org/api")
KIT_API_KEY = os.getenv("KIT_API_KEY")

HEADERS: dict[str, str] = {
    "Accept": "application/json",
}
if KIT_API_KEY:
    HEADERS["Authorization"] = f"Bearer {KIT_API_KEY}"


def get_kit_info(kit_id: int) -> Optional[dict]:
    """Fetch metadata for a kit (board).

    Returns the JSON 'data' object or None if not found / error.
    """
    url = f"{BASE_URL}/kits/{kit_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            body = r.json()
            return body.get("data")
        return None
    except requests.RequestException:
        return None


def _paginate(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    page_size: int = 100,
    max_pages: int = 500,
):
    """Cursor pagination helper yielding lists of items from {'data': [...]} pages.

    Stops when no next_cursor is provided or on any non-200/parse error.
    """
    q = dict(params or {})
    q["page[size]"] = str(page_size)
    cursor = None
    pages = 0
    while pages < max_pages:
        if cursor:
            q["page[cursor]"] = cursor
        try:
            r = requests.get(url, headers=headers, params=q, timeout=30)
        except requests.RequestException:
            break
        if r.status_code != 200:
            break
        try:
            payload = r.json()
        except Exception:
            break
        data = payload.get("data")
        meta = payload.get("meta", {})
        yield data if isinstance(data, list) else []
        cursor = meta.get("next_cursor")
        pages += 1
        if not cursor:
            break


def get_kit_measurements_df(
    kit_id: int,
    sensors: Optional[Iterable[str]] = None,
    *,
    page_size: int = 100,
) -> pd.DataFrame:
    """Fetch all measurements for the given kit across its sensors as a DataFrame.

    - If sensors is None, discover sensors via get_kit_info(kit_id).
    - Returns columns: kit_id, sensor, timestamp, value, unit, _raw
      (depending on API, some fields may be None/NaT)
    """
    # Determine sensor list
    if sensors is None:
        kit = get_kit_info(kit_id)
        if not kit:
            return pd.DataFrame(columns=["kit_id", "sensor", "timestamp", "value", "unit", "_raw"])
        sensor_list = [
            s.get("name")
            for s in (kit.get("sensors") or [])
            if isinstance(s, dict) and s.get("name")
        ]
    else:
        sensor_list = [s for s in sensors if s]

    rows: list[dict[str, Any]] = []

    for sname in sensor_list:
        endpoint = f"{BASE_URL}/kits/{kit_id}/{sname}/measurements"
        for page in _paginate(endpoint, headers=HEADERS, page_size=page_size):
            for item in page:
                if not isinstance(item, dict):
                    continue
                
                # Some APIs nest details under 'attributes'
                rec = item.get("attributes", {})
                rec.update({k: v for k, v in item.items() if k != "attributes"})

                ts = rec.get("timestamp") or rec.get("time") or rec.get("created_at") or rec.get("datetime")
                val = rec.get("value") or rec.get("reading") or rec.get("measurement") or rec.get("val")
                unit = rec.get("unit") or rec.get("units")
                rows.append(
                    {
                        "kit_id": kit_id,
                        "sensor": sname,
                        "timestamp": ts,
                        "value": val,
                        "unit": unit,
                        "_raw": item,  # preserve original
                    }
                )

    df = pd.DataFrame(rows)
    if not df.empty and "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df.sort_values(["sensor", "timestamp"], kind="stable")
        except Exception:
            pass
    return df


def fetch_kit_dataframe(kit_id: int) -> pd.DataFrame:
    """Simplest API: return all measurements for the given kit as a DataFrame.

    Equivalent to get_kit_measurements_df(kit_id) with sensible defaults.
    """
    return get_kit_measurements_df(kit_id)
