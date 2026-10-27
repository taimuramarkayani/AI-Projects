# Bitcoin Market Behaviour Analyzer

## Research Question

How do Bitcoin's daily price movements and trading volume relate to its short-term (7-day) and longer-term (30-day) price trends over the last 30 days?

## Project Objective

This project analyses Bitcoin market data using Python. It retrieves daily market data from Kraken, calculates financial metrics, applies documented rules, generates a Markdown report, and presents interactive charts through a Streamlit dashboard.

The project is designed for educational purposes and uses public market data.

## Features

- Retrieve Bitcoin daily OHLC data from Kraken's public API.
- Validate and clean market data, including handling API errors.
- Exclude the latest incomplete daily candle.
- Calculate daily percentage returns and 7-day and 30-day simple moving averages.
- Identify unusually large price movements using a documented historical comparison rule.
- Identify days with higher-than-usual trading volume.
- Generate a Markdown analysis report.
- Display interactive price, volume, and daily-return charts.
- Run automated tests using pytest.

## Data Source

- **Exchange:** Kraken
- **API:** Public OHLC endpoint
- **Trading pair:** XBT/USD
- **Candle interval:** Daily (1,440 minutes)
- **Analysis period:** Last 30 completed daily candles, with historical data used for calculations.

## API Exploration Notes

- Kraken returned market data under the `XXBTZUSD` result key with an empty `error` list for a valid request.
- Each OHLC candle contains eight fields: Unix timestamp, open, high, low, close, VWAP, volume, and trade count.
- Price and volume values are converted to numeric types before calculations.
- The latest incomplete candle is excluded from completed-daily analysis.
- Historical candles are used to calculate moving averages and rolling comparison thresholds.
- An invalid-pair test returned `EQuery:Unknown asset pair`. The program checks Kraken's error response and handles unsuccessful requests.

## Analysis Rules

- **Daily return:** Percentage change between consecutive closing prices.
- **7-day moving average:** Mean closing price over the latest seven daily observations, including the current observation.
- **30-day moving average:** Mean closing price over the latest 30 daily observations, including the current observation.
- **Unusual price movement:** A daily return is flagged when its absolute value exceeds twice the median absolute daily return across the preceding 30 completed days.
- **High trading volume:** A day's trading volume is flagged when it exceeds the average volume across the preceding 30 completed days.
- **Trend comparison:** The 7-day simple moving average (SMA) is compared with the 30-day SMA to describe the short-term trend relative to the longer-term trend.

## Project Structure

```text
crypto-market-intelligence/
├── .github/
│   └── workflows/
│       └── ci.yml
├── reports/
│   └── sample_report.md
├── tests/
│   └── test_analysis.py
├── .gitignore
├── AI_LOG.md
├── dashboard.py
├── main.py
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.12 or another compatible Python version.
- An internet connection to retrieve public market data from Kraken.

The project dependencies are listed in `requirements.txt`.

## Installation and Setup

Clone the repository:

```powershell
git clone https://github.com/taimuramarkayani/AI-Projects.git
cd AI-Projects/crypto-market-intelligence
```

Create and activate a virtual environment if you do not already have one:

```powershell
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run the Analyzer

Generate the latest analysis report:

```powershell
python main.py
```

The generated report is saved to `reports/sample_report.md`.

## Run the Dashboard

Start the interactive dashboard locally:

```powershell
python -m streamlit run dashboard.py
```

Streamlit will provide a local URL to open in your browser. Stop the dashboard with `Ctrl+C` in the terminal.

## Run the Tests

Execute the automated tests:

```powershell
python -m pytest -v
```

The tests cover the 30-day analysis period, daily returns, moving averages, high-volume detection, invalid trading pairs, and unusual price movements.

## Continuous Integration

The GitHub Actions workflow in `.github/workflows/ci.yml` installs the dependencies and runs the automated tests on pushes and pull requests targeting the `main` branch.

The workflow should be confirmed in GitHub after the project is pushed.

## AI Use and Verification

`AI_LOG.md` documents the use of AI assistance, review decisions, and verification work. The project uses explicit Python calculations and rules; an AI model is not part of the market-analysis workflow.

## Limitations

- Historical price and volume patterns do not predict future prices reliably.
- The unusual-movement and high-volume thresholds are simple educational rules, not validated trading signals.
- Public API availability and returned data may change.
- Automated tests verify selected behaviours but cannot guarantee that every possible input or market condition is handled correctly.

## Disclaimer

This project is for education only and is not financial advice.