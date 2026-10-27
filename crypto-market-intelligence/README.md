# Bitcoin Market Behaviour Analyzer

## Research Question

How do Bitcoin's daily price movements and trading volume relate to its short-term (7-day) and longer-term (30-day) price trends over the last 30 days?

## Project Objective

The objective of this project is to analyse Bitcoin market data using Python. The workflow will retrieve daily market data from Kraken, calculate financial metrics, apply documented rules, and automatically generate a report explaining the observed market behaviour.

## Data Source

- **Exchange:** Kraken
- **API:** Public OHLC endpoint
- **Trading pair:** XBT/USD
- **Candle interval:** Daily (1,440 minutes)
- **Analysis period:** Last 30 completed daily candles

## API Exploration Notes

- The Kraken public OHLC endpoint returned a JSON response with an empty `error` list and market data under the `XXBTZUSD` key.
- Each OHLC candle contains eight fields in this order: Unix timestamp, open, high, low, close, volume-weighted average price (VWAP), trading volume, and trade count.
- Price and volume values are returned as strings, so the Python workflow must convert them to numeric types before calculations. Timestamps and trade counts appear as numbers.
- The endpoint can return up to 720 candles. The final candle represents the current, incomplete interval and must be excluded from completed-daily analysis.
- Historical candles are needed to calculate the 7-day and 30-day moving averages and the rolling comparison thresholds before selecting the last 30 completed days.
- The API request succeeded after the primary Wi-Fi adapter's DNS configuration was changed to Google DNS.



## Planned Analysis

The project will investigate:

1. Daily Bitcoin price changes and their relationship with trading volume.
2. Days with unusually large price movements relative to recent historical behaviour.
3. Days with higher-than-usual trading volume.
4. The relationship between the 7-day and 30-day moving averages.
5. The overall market behaviour observed during the analysis period.

## Planned Workflow

1. Retrieve Bitcoin OHLC data from Kraken.
2. Inspect, clean, and validate the returned data.
3. Exclude incomplete candles from the analysis.
4. Calculate price changes, trading volume metrics, and moving averages.
5. Apply documented rules to identify notable observations.
6. Verify at least one calculated value manually.
7. Generate a Markdown report in the `reports/` folder.

## Project Status

Initial setup — research question confirmed. API exploration, implementation, testing, and report generation are pending.

## Educational Disclaimer

This project is for education only and is not financial advice.