
"""Bitcoin Market Behaviour Analyzer.

Fetches daily Bitcoin OHLC data from Kraken, calculates descriptive
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
INTERVAL_MINUTES = 1440

ANALYSIS_DAYS = 30
LOOKBACK_DAYS = 30
REQUEST_TIMEOUT_SECONDS = 20


# ---------------------------------------------------------
# 1. Retrieve and validate Kraken data
# ---------------------------------------------------------

def fetch_market_data() -> pd.DataFrame:
    """Fetch daily OHLC candles and validate Kraken's response."""

    params = {
        "pair": TRADING_PAIR,
        "interval": INTERVAL_MINUTES,
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
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.date

    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    df = df.reset_index(drop=True)

    # Kraken's final candle is the current, potentially incomplete interval.
    # Exclude it rather than treating it as a completed daily observation.
    if len(df) < 2:
        raise RuntimeError("Insufficient candles to exclude the current candle.")

    df = df.iloc[:-1].copy().reset_index(drop=True)

    # Ensure enough history for rolling metrics and the first daily return.
    required = ANALYSIS_DAYS + LOOKBACK_DAYS + 1
    if len(df) < required:
        raise RuntimeError(
            f"Need at least {required} completed candles; "
            f"received {len(df)}."
        )

    return df


# ---------------------------------------------------------
# 2. Calculate metrics and apply documented rules
# ---------------------------------------------------------

def analyse_market(df: pd.DataFrame) -> pd.DataFrame:
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
    return df.tail(ANALYSIS_DAYS).reset_index(drop=True)


# ---------------------------------------------------------
# 3. Generate a Markdown report
# ---------------------------------------------------------

def generate_report(df: pd.DataFrame) -> Path:
    """Write a descriptive report for the completed analysis period."""

    if df.empty:
        raise RuntimeError("Cannot generate a report from empty data.")

    latest = df.iloc[-1]
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

How do Bitcoin's daily price movements and trading volume relate to its
short-term (7-day) and longer-term (30-day) price trends over the last
30 completed daily candles?

## Data source

- Exchange: Kraken
- Pair: XBT/USD
- Interval: Daily
- Analysis observations: {len(df)}

## Summary

- First closing price in the period: ${first_close:,.2f}
- Latest completed closing price: ${last_close:,.2f}
- Closing-price change across the period: {period_change:+.2f}%
- Latest daily return: {latest['daily_return_pct']:+.2f}%
- Latest 7-day SMA: ${latest['sma_7']:,.2f}
- Latest 30-day SMA: ${latest['sma_30']:,.2f}
- Latest trend comparison: {latest['trend_comparison']}
- Days flagged for unusual movement: {unusual_count}
- Days flagged for high volume: {high_volume_count}

## Daily observations

| Date | Close (USD) | Return (%) | Volume (XBT) | 7-day SMA | 30-day SMA | Unusual move | High volume |
|---|---:|---:|---:|---:|---:|:---:|:---:|
"""

    for _, row in df.iterrows():
        report += (
            f"| {row['date']} "
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

1. **Unusual movement:** Absolute daily return exceeds twice the median
   absolute daily return across the preceding 30 completed days.
2. **High volume:** Daily volume exceeds the average volume across the
   preceding 30 completed days.
3. **Trend comparison:** The 7-day SMA is compared with the 30-day SMA.

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
