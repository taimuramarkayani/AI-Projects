
"""Send Bitcoin analysis, Treasury-yield findings, and PDF to Apps Script."""

from __future__ import annotations

import base64
import json
import math
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "reports" / "exports"
PDF_DIR = BASE_DIR / "reports" / "pdf"

load_dotenv(BASE_DIR / ".env")


def newest_file(pattern: str, directory: Path) -> Path:
    files = list(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No file matching {pattern!r} in {directory}. "
            "Generate the required export/report first."
        )
    return max(files, key=lambda path: path.stat().st_mtime)


def load_treasury_data(url: str) -> pd.DataFrame:
    """Retrieve the latest Treasury observations from the Apps Script GET endpoint."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if payload.get("success") is not True:
        raise RuntimeError(
            f"Treasury endpoint failed: {payload.get('error', 'Unknown error')}"
        )

    fred = pd.DataFrame(payload.get("rows", []))
    required = {"observation_date", "yield_pct", "yield_change_bps"}

    missing = required - set(fred.columns)
    if missing:
        raise ValueError(f"Treasury data is missing fields: {sorted(missing)}")

    fred["observation_date"] = pd.to_datetime(
        fred["observation_date"], errors="coerce"
    )
    fred["yield_pct"] = pd.to_numeric(fred["yield_pct"], errors="coerce")
    fred["yield_change_bps"] = pd.to_numeric(
        fred["yield_change_bps"], errors="coerce"
    )

    fred = (
        fred.dropna(subset=["observation_date", "yield_pct"])
        .sort_values("observation_date")
        .drop_duplicates("observation_date", keep="last")
        .reset_index(drop=True)
    )

    if fred.empty:
        raise RuntimeError("The Treasury endpoint returned no valid observations.")

    return fred


def build_macro_analysis(
    bitcoin_export: dict, treasury: pd.DataFrame
) -> dict:
    """Calculate a fresh Bitcoin-return versus Treasury-yield-change comparison."""
    observations = pd.DataFrame(bitcoin_export.get("observations", []))

    required = {"timestamp_utc", "return_pct"}
    if required - set(observations.columns):
        raise ValueError("Bitcoin export lacks timestamp_utc or return_pct.")

    observations["timestamp_utc"] = pd.to_datetime(
        observations["timestamp_utc"], utc=True, errors="coerce"
    )
    observations["return_pct"] = pd.to_numeric(
        observations["return_pct"], errors="coerce"
    )
    observations["date"] = observations["timestamp_utc"].dt.strftime("%Y-%m-%d")

    yields = treasury.copy()
    yields["date"] = yields["observation_date"].dt.strftime("%Y-%m-%d")

    matched = observations.merge(
        yields[["date", "yield_pct", "yield_change_bps"]],
        on="date",
        how="inner",
    ).dropna(subset=["return_pct", "yield_change_bps"])

    correlation = None
    if (
        len(matched) >= 10
        and matched["return_pct"].nunique() > 1
        and matched["yield_change_bps"].nunique() > 1
    ):
        value = matched["return_pct"].corr(matched["yield_change_bps"])
        if pd.notna(value):
            correlation = round(float(value), 3)

    latest = treasury.iloc[-1]
    latest_yield = float(latest["yield_pct"])
    latest_date = latest["observation_date"].strftime("%Y-%m-%d")

    latest_change = latest["yield_change_bps"]
    if pd.isna(latest_change):
        change_text = "The latest daily yield change is unavailable."
        change_value = None
    else:
        change_value = float(latest_change)
        if change_value > 0:
            change_text = (
                f"The yield increased by {change_value:.1f} basis points "
                "on the latest observation."
            )
        elif change_value < 0:
            change_text = (
                f"The yield decreased by {abs(change_value):.1f} basis points "
                "on the latest observation."
            )
        else:
            change_text = "The yield was unchanged on the latest observation."

    if correlation is None:
        interpretation = (
            f"There are {len(matched)} matched daily observations. "
            "There is not enough usable data to calculate a dependable "
            "correlation. No directional conclusion is drawn."
        )
    else:
        strength = abs(correlation)
        if strength < 0.20:
            interpretation = (
                f"The correlation is {correlation:+.3f}, showing little clear "
                "linear relationship in this sample."
            )
        else:
            if strength < 0.40:
                strength_text = "weak"
            elif strength < 0.60:
                strength_text = "moderate"
            elif strength < 0.80:
                strength_text = "strong"
            else:
                strength_text = "very strong"

            if correlation > 0:
                interpretation = (
                    f"The correlation is {correlation:+.3f}, indicating a "
                    f"{strength_text} positive relationship in this sample. "
                    "Bitcoin returns tended to be higher on days when yields "
                    "increased."
                )
            else:
                interpretation = (
                    f"The correlation is {correlation:+.3f}, indicating a "
                    f"{strength_text} negative relationship in this sample. "
                    "Bitcoin returns tended to be lower on days when yields "
                    "increased."
                )

    email_text = (
        "US 10-year Treasury yield and Bitcoin\n"
        f"Latest Treasury yield: {latest_yield:.2f}% ({latest_date}).\n"
        f"{change_text}\n"
        f"Matched daily observations: {len(matched)}.\n"
        f"Bitcoin-return/yield-change correlation: "
        f"{correlation if correlation is not None else 'Not calculated'}.\n"
        f"{interpretation}\n\n"
        "Plain-English context: When market yields rise, existing fixed-rate "
        "bond prices generally fall. Higher yields can make bonds more attractive "
        "than Bitcoin, which does not pay interest just for holding it. This "
        "can put pressure on Bitcoin, but it is not a rule and other market "
        "forces may dominate.\n\n"
        "Limitations: Correlation does not prove causation. This calculation "
        "uses same-date daily Bitcoin returns and daily Treasury-yield changes; "
        "the sample may be small and the relationship can change over time."
    )

    return {
        "latest_yield_pct": latest_yield,
        "yield_observation_date": latest_date,
        "latest_yield_change_bps": change_value,
        "matched_observations": int(len(matched)),
        "btc_yield_correlation": correlation,
        "macro_analysis_text": email_text,
    }


def build_payload(analysis: dict) -> dict:
    secret = os.getenv("BITCOIN_API_SECRET")
    if not secret:
        raise RuntimeError("BITCOIN_API_SECRET is not configured.")

    if analysis.get("timeframe") != "daily":
        raise ValueError("Only a daily export can be sent.")

    latest = analysis.get("latest")
    observations = analysis.get("observations")

    if not isinstance(latest, dict):
        raise ValueError("The export has no valid latest metrics.")
    if not isinstance(observations, list) or not observations:
        raise ValueError("The export has no observations.")

    for field in ("close_usd", "return_pct", "sma_7", "sma_30"):
        if latest.get(field) is None:
            raise ValueError(f"Latest analysis is missing {field}.")

    return {
        "secret": secret,
        "run_timestamp_utc": analysis.get("generated_at_utc"),
        "pair": analysis.get("pair", "XBT/USD"),
        "latest_close_usd": latest["close_usd"],
        "daily_return_pct": latest["return_pct"],
        "sma_7_usd": latest["sma_7"],
        "sma_30_usd": latest["sma_30"],
        "unusual_movement_count": sum(
            bool(row.get("unusual_movement")) for row in observations
        ),
        "high_volume_count": sum(
            bool(row.get("high_volume")) for row in observations
        ),
    }


def send_daily_analysis() -> None:
    url = os.getenv("GOOGLE_APPS_SCRIPT_URL")
    if not url or not url.startswith("https://script.google.com/"):
        raise RuntimeError("GOOGLE_APPS_SCRIPT_URL is missing or invalid.")

    export_path = newest_file("bitcoin_analysis_daily_*.json", EXPORT_DIR)
    pdf_path = newest_file("market_intelligence_combined_*.pdf", PDF_DIR)

    with export_path.open("r", encoding="utf-8") as file:
        analysis = json.load(file)

    # Recalculate the macro analysis on every run.
    treasury = load_treasury_data(url)
    macro = build_macro_analysis(analysis, treasury)

    payload = build_payload(analysis)
    payload.update(macro)
    payload["pdf_filename"] = pdf_path.name
    payload["pdf_base64"] = base64.b64encode(
        pdf_path.read_bytes()
    ).decode("ascii")

    # Never print the URL, payload, PDF contents, or secret.
    response = requests.post(
        url,
        json=payload,
        timeout=60,
        allow_redirects=True,
    )
    response.raise_for_status()

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            "Apps Script returned a non-JSON response. "
            "Check the web app deployment."
        ) from None

    if not isinstance(result, dict) or result.get("success") is not True:
        error = (
            result.get("error", "Unknown Apps Script error")
            if isinstance(result, dict)
            else "Unexpected response"
        )
        raise RuntimeError(f"Apps Script did not confirm success: {error}")

    if result.get("email_sent") is not True:
        raise RuntimeError(
            "Google Sheets may have been updated, but Apps Script "
            "did not confirm that the email was sent."
        )

    print("Google Sheets submission confirmed.")
    print(f"Source export: {export_path.name}")
    print(f"PDF selected: {pdf_path.name}")
    print(f"Treasury yield: {macro['latest_yield_pct']:.2f}%")
    print(f"Matched observations: {macro['matched_observations']}")
    print(f"Correlation: {macro['btc_yield_correlation']}")
    print("Email sending confirmed by Apps Script.")
    print(f"Recipient: {result.get('recipient', 'configured recipient')}")


if __name__ == "__main__":
    send_daily_analysis()
