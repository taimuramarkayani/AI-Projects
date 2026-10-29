import json
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv(Path(".env"))

exports = list(Path("reports/exports").glob("bitcoin_analysis_daily_*.json"))
if not exports:
    raise SystemExit("No daily Bitcoin export found.")

path = max(exports, key=lambda p: p.stat().st_mtime)
bitcoin = json.loads(path.read_text(encoding="utf-8"))

url = os.getenv("GOOGLE_APPS_SCRIPT_URL")
if not url:
    raise SystemExit("Apps Script URL is missing from .env.")

response = requests.get(url, timeout=30)
response.raise_for_status()
fred = response.json()

if fred.get("success") is not True:
    raise SystemExit("FRED endpoint did not report success.")

btc = pd.DataFrame(bitcoin["observations"])
yields = pd.DataFrame(fred["rows"])

btc["date"] = pd.to_datetime(
    btc["timestamp_utc"], utc=True
).dt.strftime("%Y-%m-%d")

btc["return_pct"] = pd.to_numeric(btc["return_pct"], errors="coerce")
yields["yield_change_bps"] = pd.to_numeric(
    yields["yield_change_bps"], errors="coerce"
)
yields["yield_pct"] = pd.to_numeric(yields["yield_pct"], errors="coerce")

matched = btc.merge(
    yields[["observation_date", "yield_pct", "yield_change_bps"]],
    left_on="date",
    right_on="observation_date",
    how="inner",
).dropna(subset=["return_pct", "yield_change_bps"])

print("Bitcoin export:", path.name)
print("Matched observations:", len(matched))

if len(matched) < 10:
    print("Too few matching observations for a useful estimate.")
else:
    correlation = matched["return_pct"].corr(matched["yield_change_bps"])
    print("Correlation:", round(correlation, 3))

    if pd.isna(correlation):
        print("Interpretation: correlation could not be calculated.")
    elif correlation >= 0.5:
        print("Interpretation: strong positive relationship in this sample.")
    elif correlation >= 0.2:
        print("Interpretation: moderate positive relationship in this sample.")
    elif correlation > -0.2:
        print("Interpretation: weak or little linear relationship in this sample.")
    elif correlation > -0.5:
        print("Interpretation: moderate negative relationship in this sample.")
    else:
        print("Interpretation: strong negative relationship in this sample.")

valid_yields = yields.dropna(subset=["yield_pct"])
if not valid_yields.empty:
    latest = valid_yields.iloc[-1]
    print("Latest Treasury yield (%):", latest["yield_pct"])
    print("Latest yield change (bps):", latest["yield_change_bps"])