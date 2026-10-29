
"""Export Bitcoin market analysis to a local JSON file."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from main import (
    ANALYSIS_DAYS,
    DAILY_INTERVAL_MINUTES,
    FOUR_HOUR_INTERVAL_MINUTES,
    analyse_market,
    fetch_market_data,
)

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "reports" / "exports"


def build_export(interval_minutes: int = DAILY_INTERVAL_MINUTES) -> dict:
    """Fetch and analyse market data, then return JSON-compatible results."""
    if interval_minutes not in (
        DAILY_INTERVAL_MINUTES,
        FOUR_HOUR_INTERVAL_MINUTES,
    ):
        raise ValueError("Interval must be 1440 (daily) or 240 (4-hour).")

    market_data = fetch_market_data(interval_minutes)
    analysed = analyse_market(market_data, interval_minutes)

    if analysed.empty:
        raise RuntimeError("Cannot export an empty market analysis.")

    def clean_number(value):
        if pd.isna(value):
            return None
        return float(value)

    observations = []
    for _, row in analysed.iterrows():
        observations.append({
            "timestamp_utc": row["datetime_utc"].isoformat(),
            "close_usd": clean_number(row["close"]),
            "return_pct": clean_number(row["daily_return_pct"]),
            "volume_xbt": clean_number(row["volume"]),
            "sma_7": clean_number(row["sma_7"]),
            "sma_30": clean_number(row["sma_30"]),
            "unusual_movement": bool(row["unusual_movement"]),
            "high_volume": bool(row["high_volume"]),
            "trend_comparison": str(row["trend_comparison"]),
        })

    latest = analysed.iloc[-1]
    timeframe = (
        "daily"
        if interval_minutes == DAILY_INTERVAL_MINUTES
        else "4-hour"
    )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Kraken",
        "pair": "XBT/USD",
        "timeframe": timeframe,
        "interval_minutes": interval_minutes,
        "return_definition": (
            "daily candle return"
            if interval_minutes == DAILY_INTERVAL_MINUTES
            else "4-hour candle return"
        ),
        "analysis_days": ANALYSIS_DAYS,
        "observation_count": len(observations),
        "latest": {
            "timestamp_utc": latest["datetime_utc"].isoformat(),
            "close_usd": clean_number(latest["close"]),
            "return_pct": clean_number(latest["daily_return_pct"]),
            "sma_7": clean_number(latest["sma_7"]),
            "sma_30": clean_number(latest["sma_30"]),
            "trend_comparison": str(latest["trend_comparison"]),
            "unusual_movement": bool(latest["unusual_movement"]),
            "high_volume": bool(latest["high_volume"]),
        },
        "observations": observations,
    }


def save_export(data: dict) -> Path:
    """Save export data to a timestamped JSON file."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = EXPORT_DIR / f"bitcoin_analysis_{data['timeframe']}_{timestamp}.json"
    path.write_text(
        json.dumps(data, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return path


def main() -> None:
    for interval in (DAILY_INTERVAL_MINUTES, FOUR_HOUR_INTERVAL_MINUTES):
        data = build_export(interval)
        path = save_export(data)
        print(
            f"Saved {data['timeframe']} export with "
            f"{data['observation_count']} observations: {path}"
        )


if __name__ == "__main__":
    main()
