"""Daily data fetch for Teleagriculture kits.

Usage:
  python api_call.py --kit-id 1001 --format csv

Env:
  - KIT_API_KEY: optional Bearer token for the API
  - KITS_API_BASE: override base URL (default https://kits.teleagriculture.org/api)
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

# Import utility function and config
from utils import get_kit_measurements_df, BASE_URL


def get_last_day_data(kit_id: int) -> pd.DataFrame:
    """Fetches all sensor data for a given kit from the last 24 hours."""
    print(f"API base: {BASE_URL}")
    print(f"Fetching last day's measurements for kit {kit_id}...\n")

    # Fetch all data, sensors will be discovered automatically
    df = get_kit_measurements_df(kit_id)

    if df.empty or 'timestamp' not in df.columns:
        print("No data or timestamp column found.")
        return pd.DataFrame()

    # Filter for the last 24 hours
    # The timestamp column is already converted to timezone-aware datetimes in get_kit_measurements_df
    one_day_ago = pd.Timestamp.utcnow() - timedelta(days=1)
    last_day_df = df[df['timestamp'] >= one_day_ago].copy()

    print(f"Fetched rows from the last day: {len(last_day_df)}")
    if not last_day_df.empty:
        try:
            # Recalculate 'value' as numeric, coercing errors
            last_day_df['value'] = pd.to_numeric(last_day_df['value'], errors='coerce')
            
            print("Summary statistics for the last day:")
            # Group by sensor and calculate statistics
            summary = last_day_df.groupby('sensor')['value'].agg(['mean', 'min', 'max', 'count']).round(2)
            print(summary)

        except Exception as e:
            print(f"Could not generate summary statistics: {e}")

    return last_day_df


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch all measurements for a Teleagriculture kit and save to disk.")
    p.add_argument("--kit-id", type=int, required=True, help="Numeric kit id to fetch (e.g., 1001)")
    p.add_argument(
        "--sensors",
        type=str,
        default=None,
        help="Comma-separated sensor names to limit (default: discover all sensors on the kit)",
    )
    p.add_argument("--page-size", type=int, default=100, help="Page size for pagination (default: 100)")
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
    print(f"Fetching kit {args.kit_id} measurements...\n")
    df = get_kit_measurements_df(args.kit_id, sensors=sensors, page_size=args.page_size)

    print(f"Fetched rows: {len(df)}")
    if not df.empty:
        try:
            per_sensor = df.groupby("sensor").size().sort_values(ascending=False)
            print("Rows per sensor:")
            for s, n in per_sensor.items():
                print(f"  - {s}: {n}")
        except Exception:
            pass

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
    # Example of using the new function.
    # You can run this part by uncommenting it and running the script.
    # try:
    #     kit_id_to_test = 1001  # Replace with a valid kit ID
    #     last_day_data = get_last_day_data(kit_id_to_test)
    #     if not last_day_data.empty:
    #         print("\n--- Last Day Dataframe ---")
    #         print(last_day_data.head())
    #         print("--------------------------")
    # except Exception as e:
    #     print(f"An error occurred during the example run: {e}")

    raise SystemExit(main())
