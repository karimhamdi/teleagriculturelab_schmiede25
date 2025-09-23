"""Teleagriculture kits API client + CLI.

Usage: python api_call.py --kit-id 1001 --format csv

Env:
    - KIT_API_KEY    optional Bearer token
    - KITS_API_BASE  base URL (default https://kits.teleagriculture.org/api)
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

# --- API configuration ---
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

def load_cached_kit_dataframe(kit_id: int, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load the most recent cached kit dataframe from data/ as a fallback.

    Looks for files like data/kit_<id>_*.csv or .parquet. Returns empty DataFrame if none.
    """
    base = data_dir or (Path(__file__).parent / "data")
    if not base.exists():
        return pd.DataFrame(columns=["kit_id", "sensor", "timestamp", "value", "unit"])

    candidates = list(base.glob(f"kit_{kit_id}_*.csv")) + list(base.glob(f"kit_{kit_id}_*.parquet"))
    if not candidates:
        return pd.DataFrame(columns=["kit_id", "sensor", "timestamp", "value", "unit"])

    # pick the most recently modified
    path = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        if path.suffix == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_parquet(path)
    except Exception:
        return pd.DataFrame(columns=["kit_id", "sensor", "timestamp", "value", "unit"])

    # normalize columns
    need_cols = {"kit_id", "sensor", "timestamp", "value", "unit"}
    missing = need_cols - set(df.columns)
    for col in missing:
        df[col] = None
    df = df[["kit_id", "sensor", "timestamp", "value", "unit"]]
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df = df.dropna(subset=["timestamp"])  # enforce valid timestamps
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["sensor"] = df["sensor"].astype(str)
        df = df.sort_values(["sensor", "timestamp"], kind="stable")
    except Exception:
        pass
    return df


def get_kit_measurements_df(
    kit_id: int,
    sensors: Optional[list[str]] | None = None,
    *,
    page_size: int = 100,
    max_pages: int = 500,
) -> pd.DataFrame:
    """Return a concise DataFrame for the kit's sensors.

    Columns: [kit_id, sensor, timestamp, value, unit]
    """
    # discover sensors if not provided
    sensor_list: List[str] = [s for s in (sensors or []) if s]
    if not sensor_list:
        kit = get_kit_info(kit_id) or {}
        sensor_list = [
            (s.get("name") or s.get("slug") or s.get("sensor"))
            for s in (kit.get("sensors") or [])
            if isinstance(s, dict) and (s.get("name") or s.get("slug") or s.get("sensor"))
        ]
    # Env override or last-resort default if discovery fails (keeps app working without auth)
    if not sensor_list:
        env_sensors = (os.getenv("KITS_SENSORS") or "").strip()
        if env_sensors:
            sensor_list = [s.strip() for s in env_sensors.split(",") if s.strip()]
    if not sensor_list:
        sensor_list = ["ftTemp", "gbHum", "NH3", "C3H8", "CO"]

    rows: list[dict] = []
    for sname in sensor_list:
        endpoint = f"{BASE_URL}/kits/{kit_id}/{sname}/measurements"
        for page in _paginate(endpoint, headers=HEADERS, page_size=page_size, max_pages=max_pages):
            for item in page:
                if not isinstance(item, dict):
                    continue
                attrs = item.get("attributes") or {}
                # tolerate common alternative keys while keeping output schema tight
                ts = (
                    attrs.get("timestamp")
                    or item.get("timestamp")
                    or item.get("time")
                    or item.get("created_at")
                    or item.get("datetime")
                )
                val = (
                    attrs.get("value")
                    or item.get("value")
                    or item.get("reading")
                    or item.get("measurement")
                    or item.get("val")
                )
                unit = attrs.get("unit") or item.get("unit") or item.get("units")
                if ts is None or val is None:
                    continue
                rows.append(
                    {
                        "kit_id": kit_id,
                        "sensor": sname,
                        "timestamp": ts,
                        "value": val,
                        "unit": unit,
                    }
                )
    df = pd.DataFrame(rows, columns=["kit_id", "sensor", "timestamp", "value", "unit"])
    if not df.empty:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df.dropna(subset=["timestamp"])  # enforce valid timestamps
            # numeric value if possible (keeps visualization robust)
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df["sensor"] = df["sensor"].astype(str)
            df = df.sort_values(["sensor", "timestamp"], kind="stable")
        except Exception:
            pass
    # Fallback to cached data if API yielded nothing
    if df.empty:
        cached = load_cached_kit_dataframe(kit_id)
        if not cached.empty:
            return cached
    return df


def fetch_kit_dataframe(kit_id: int) -> pd.DataFrame:
    """Simplest API: return all measurements for the given kit as a DataFrame.

    Equivalent to get_kit_measurements_df(kit_id) with sensible defaults.
    """
    return get_kit_measurements_df(kit_id)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch kit measurements and save to disk.")
    p.add_argument("--kit-id", type=int, required=True, help="Numeric kit id to fetch (e.g., 1001)")
    p.add_argument(
        "--sensors",
        type=str,
        default=None,
        help="Comma-separated sensor names to limit (default: discover all sensors on the kit)",
    )
    p.add_argument("--page-size", type=int, default=100, help="Page size for pagination (default: 100)")
    p.add_argument(
        "--max-pages",
        type=int,
        default=500,
        help="Maximum number of pages to paginate per sensor (default: 500)",
    )
    p.add_argument(
        "--format",
        choices=["csv", "parquet"],
        default="csv",
        help="Output format (default: csv)",
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output file path. If not provided, saves under teleagriculture/data/kit_<id>_<YYYY-MM-DD>.<ext>",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    sensors: Optional[List[str]] = None
    if args.sensors:
        sensors = [s.strip() for s in args.sensors.split(",") if s.strip()]

    print(f"API base: {BASE_URL}")
    print(f"Fetching kit {args.kit_id} measurements...")
    df = get_kit_measurements_df(
        args.kit_id,
        sensors=sensors,
        page_size=args.page_size,
        max_pages=args.max_pages,
    )
    print(f"Fetched rows: {len(df)}")

    # Determine output path
    ext = args.format
    if args.out:
        out_path = Path(args.out)
    else:
        dt = datetime.utcnow().strftime("%Y-%m-%d")
        out_dir = Path(__file__).parent / "data"
        out_path = out_dir / f"kit_{args.kit_id}_{dt}.{ext}"
    
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "csv":
        df.to_csv(out_path, index=False)
        print(f"\nSaved CSV -> {out_path.resolve()}")
    elif args.format == "parquet":
        try:
            df.to_parquet(out_path, index=False)
            print(f"\nSaved Parquet -> {out_path.resolve()}")
        except ImportError:
            print("\nParquet write failed. Please install pyarrow or fastparquet.")
            return 1
        except Exception as e:
            print(f"\nAn error occurred while saving the Parquet file: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
