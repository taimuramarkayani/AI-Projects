
"""Bitcoin Market Behaviour Analyzer.

Fetches daily or 4-hour Bitcoin OHLC data from Kraken, calculates descriptive
market metrics, applies documented rules, and generates a Markdown report.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
REPORT_PATH = REPORTS_DIR / "sample_report.md"

KRAKEN_URL = "https://api.kraken.com/0/public/OHLC"
TRADING_PAIR = "XBTUSD"
DAILY_INTERVAL_MINUTES = 1440
FOUR_HOUR_INTERVAL_MINUTES = 240
ANALYSIS_DAYS = 30
LOOKBACK_DAYS = 30
REQUEST_TIMEOUT_SECONDS = 20


# ---------------------------------------------------------
# 1. Retrieve and validate Kraken data
# ---------------------------------------------------------

def fetch_market_data(interval_minutes: int = DAILY_INTERVAL_MINUTES) -> pd.DataFrame:
    """Fetch daily or 4-hour OHLC candles and validate Kraken's response."""

    if interval_minutes not in (DAILY_INTERVAL_MINUTES, FOUR_HOUR_INTERVAL_MINUTES):
        raise ValueError("Supported intervals are 1440 (daily) and 240 (4-hour).")

    params = {
        "pair": TRADING_PAIR,
        "interval": interval_minutes,
    }

    try:
        response = requests.get(
            KRAKEN_URL,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Kraken request failed: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Kraken returned invalid JSON.") from exc

    errors = payload.get("error")
    if not isinstance(errors, list):
        raise RuntimeError("Kraken response has no valid error field.")
    if errors:
        raise RuntimeError(f"Kraken API error: {', '.join(errors)}")

    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken response has no valid result object.")

    pair_keys = [key for key in result if key != "last"]
    if len(pair_keys) != 1:
        raise RuntimeError(
            f"Expected one OHLC data key; received {pair_keys}."
        )

    candles = result[pair_keys[0]]
    if not isinstance(candles, list) or not candles:
        raise RuntimeError("Kraken returned no OHLC candles.")

    columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "vwap",
        "volume",
        "trades",
    ]

    for candle in candles:
        if not isinstance(candle, list) or len(candle) != 8:
            raise RuntimeError("Unexpected OHLC candle structure.")

    df = pd.DataFrame(candles, columns=columns)

    numeric_columns = [
        "timestamp", "open", "high", "low",
        "close", "vwap", "volume", "trades",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df[numeric_columns].isna().any().any():
        raise RuntimeError("OHLC data contains missing or invalid numbers.")

    if not (df["close"] > 0).all():
        raise RuntimeError("OHLC data contains non-positive closing prices.")

    if not (df["volume"] >= 0).all():
        raise RuntimeError("OHLC data contains negative trading volume.")

    df["timestamp"] = df["timestamp"].astype("int64")
    # Keep a timezone-aware UTC timestamp for exact chart alignment and hover details.
    df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["date"] = df["datetime_utc"].dt.date

    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    df = df.reset_index(drop=True)

    # Kraken's final candle is the current, potentially incomplete interval.
    # Exclude it rather than treating it as a completed daily observation.
    if len(df) < 2:
        raise RuntimeError("Insufficient candles to exclude the current candle.")

    df = df.iloc[:-1].copy().reset_index(drop=True)

    # Ensure enough history for rolling metrics and the first daily return.
    # Keep the same 30-day visible window for both views: 30 daily bars or
    # 180 four-hour bars. The API supplies enough history for the lookback.
    visible_observations = ANALYSIS_DAYS if interval_minutes == DAILY_INTERVAL_MINUTES else ANALYSIS_DAYS * 6
    required = visible_observations + LOOKBACK_DAYS + 1
    if len(df) < required:
        raise RuntimeError(
            f"Need at least {required} completed candles; "
            f"received {len(df)}."
        )

    return df


# ---------------------------------------------------------
# 2. Calculate metrics and apply documented rules
# ---------------------------------------------------------

def analyse_market(
    df: pd.DataFrame, interval_minutes: int = DAILY_INTERVAL_MINUTES
) -> pd.DataFrame:
    """Calculate rolling metrics without using future observations."""

    df = df.copy()

    # Return compares each close with the previous completed close.
    df["daily_return_pct"] = df["close"].pct_change() * 100

    # These averages include the current day's close.
    df["sma_7"] = df["close"].rolling(7, min_periods=7).mean()
    df["sma_30"] = df["close"].rolling(30, min_periods=30).mean()

    # Comparison baselines use only the preceding 30 completed days.
    previous_volume = df["volume"].shift(1)
    df["avg_volume_prev_30"] = previous_volume.rolling(
        LOOKBACK_DAYS, min_periods=LOOKBACK_DAYS
    ).mean()

    previous_abs_return = df["daily_return_pct"].abs().shift(1)
    df["median_abs_return_prev_30"] = previous_abs_return.rolling(
        LOOKBACK_DAYS, min_periods=LOOKBACK_DAYS
    ).median()

    df["movement_threshold_pct"] = (
        2 * df["median_abs_return_prev_30"]
    )

    df["unusual_movement"] = (
        df["daily_return_pct"].abs() > df["movement_threshold_pct"]
    )

    df["high_volume"] = df["volume"] > df["avg_volume_prev_30"]

    df["trend_comparison"] = "Insufficient data"
    valid = df["sma_7"].notna() & df["sma_30"].notna()

    df.loc[valid & (df["sma_7"] > df["sma_30"]),
           "trend_comparison"] = "7-day SMA above 30-day SMA"
    df.loc[valid & (df["sma_7"] < df["sma_30"]),
           "trend_comparison"] = "7-day SMA below 30-day SMA"
    df.loc[valid & (df["sma_7"] == df["sma_30"]),
           "trend_comparison"] = "Moving averages equal"

    # Select the last 30 completed days only after calculating
    # metrics that require the earlier historical lookback.
    visible_observations = ANALYSIS_DAYS if interval_minutes == DAILY_INTERVAL_MINUTES else ANALYSIS_DAYS * 6
    return df.tail(visible_observations).reset_index(drop=True)


# ---------------------------------------------------------
# 3. Generate a Markdown report
# ---------------------------------------------------------

def generate_report(
    df: pd.DataFrame, interval_minutes: int = DAILY_INTERVAL_MINUTES
) -> Path:
    """Write a descriptive report for the completed analysis period."""

    if df.empty:
        raise RuntimeError("Cannot generate a report from empty data.")

    latest = df.iloc[-1]
    timeframe = "Daily" if interval_minutes == DAILY_INTERVAL_MINUTES else "4-hour"
    unit = "day" if interval_minutes == DAILY_INTERVAL_MINUTES else "4-hour candle"
    first_close = df.iloc[0]["close"]
    last_close = latest["close"]
    period_change = (last_close / first_close - 1) * 100

    unusual_count = int(df["unusual_movement"].sum())
    high_volume_count = int(df["high_volume"].sum())

    generated_at = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    report = f"""# Bitcoin Market Behaviour Analyzer

**Generated:** {generated_at}

## Research question

How do Bitcoin's price movements and trading volume relate to its
short-term (7-observation) and longer-term (30-observation) price trends
over the displayed completed {timeframe.lower()} candles?

## Data source

- Exchange: Kraken
- Pair: XBT/USD
- Interval: {timeframe}
- Analysis observations: {len(df)}

## Summary

- First closing price in the period: ${first_close:,.2f}
- Latest completed closing price: ${last_close:,.2f}
- Closing-price change across the period: {period_change:+.2f}%
- Latest {unit} return: {latest['daily_return_pct']:+.2f}%
- Latest 7-day SMA: ${latest['sma_7']:,.2f}
- Latest 30-day SMA: ${latest['sma_30']:,.2f}
- Latest trend comparison: {latest['trend_comparison']}
- Days flagged for unusual movement: {unusual_count}
- Days flagged for high volume: {high_volume_count}

## {timeframe} observations

| Timestamp (UTC) | Close (USD) | Return (%) | Volume (XBT) | 7-observation SMA | 30-observation SMA | Unusual move | High volume |
|---|---:|---:|---:|---:|---:|:---:|:---:|
"""

    for _, row in df.iterrows():
        report += (
            f"| {row['datetime_utc'].strftime('%Y-%m-%d %H:%M')} UTC "
            f"| ${row['close']:,.2f} "
            f"| {row['daily_return_pct']:+.2f}% "
            f"| {row['volume']:,.4f} "
            f"| ${row['sma_7']:,.2f} "
            f"| ${row['sma_30']:,.2f} "
            f"| {'Yes' if row['unusual_movement'] else 'No'} "
            f"| {'Yes' if row['high_volume'] else 'No'} |\n"
        )

    report += """
## Rule definitions

1. **Unusual movement:** Absolute candle return exceeds twice the median
   absolute return across the preceding 30 completed candles.
2. **High volume:** Candle volume exceeds the average volume across the
   preceding 30 completed candles.
3. **Trend comparison:** The 7-observation SMA is compared with the 30-observation SMA.

## Interpretation and limitations

These rules describe historical observations. They do not establish
causation, predict future prices, or provide buy/sell recommendations.
The analysis uses historical observations before the displayed 30-day period to calculate moving averages and rolling comparison thresholds.

## Educational disclaimer

This project is for education only and is not financial advice.
"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    return REPORT_PATH


# ---------------------------------------------------------
# 4. Run the workflow
# ---------------------------------------------------------

def main() -> None:
    """Execute data retrieval, analysis and report generation."""

    try:
        print("Fetching daily Bitcoin data from Kraken...")
        market_data = fetch_market_data()

        print(f"Validated {len(market_data)} completed candles.")
        analysed = analyse_market(market_data)

        report_path = generate_report(analysed)
        print(f"Analysis complete. Report saved to: {report_path}")

    except (RuntimeError, ValueError, KeyError) as exc:
        raise SystemExit(f"Analysis stopped: {exc}") from exc


if __name__ == "__main__":
    main()