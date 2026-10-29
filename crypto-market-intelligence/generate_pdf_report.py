
"""Generate a combined Bitcoin and US Treasury yield report."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "reports" / "exports"
OUTPUT_DIR = BASE_DIR / "reports" / "pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_export(timeframe):
    files = list(EXPORT_DIR.glob(f"bitcoin_analysis_{timeframe}_*.json"))
    if not files:
        raise FileNotFoundError(
            f"No {timeframe} Bitcoin export found. Run export_analysis.py first."
        )
    return max(files, key=lambda p: p.stat().st_mtime)


def load_export(path, timeframe):
    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("timeframe") != timeframe:
        raise ValueError(f"Unexpected timeframe in {path.name}")

    data = pd.DataFrame(payload.get("observations", []))
    required = {"timestamp_utc", "close_usd", "return_pct", "volume_xbt"}
    missing = required - set(data.columns)

    if missing:
        raise ValueError(f"Missing fields in {path.name}: {sorted(missing)}")

    data["timestamp_utc"] = pd.to_datetime(
        data["timestamp_utc"], utc=True, errors="coerce"
    )

    for col in ["close_usd", "return_pct", "volume_xbt", "sma_7", "sma_30"]:
        if col in data:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["timestamp_utc", "close_usd"])
    data = data.sort_values("timestamp_utc").reset_index(drop=True)

    if data.empty:
        raise ValueError(f"No valid observations in {path.name}")

    return payload, data


def money(value):
    return "N/A" if pd.isna(value) else f"${value:,.2f}"


def pct(value):
    return "N/A" if pd.isna(value) else f"{value:+.2f}%"


def load_fred_data():
    """Read the latest FRED-backed Treasury data from the Apps Script endpoint."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except ImportError:
        pass

    url = os.getenv("GOOGLE_APPS_SCRIPT_URL")
    if not url:
        raise RuntimeError(
            "GOOGLE_APPS_SCRIPT_URL is missing. Check your local .env "
            "or GitHub Actions environment."
        )

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if payload.get("success") is not True:
        raise RuntimeError(f"Treasury data request failed: {payload.get('error')}")

    fred = pd.DataFrame(payload.get("rows", []))
    required = {"observation_date", "yield_pct", "yield_change_bps"}

    if required - set(fred.columns):
        raise ValueError("Treasury data is missing required columns.")

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
        raise RuntimeError("No valid Treasury observations were returned.")

    return fred


def build_yield_analysis(daily, fred):
    btc = daily.copy()
    btc["date"] = btc["timestamp_utc"].dt.strftime("%Y-%m-%d")
    btc["return_pct"] = pd.to_numeric(btc["return_pct"], errors="coerce")

    treasury = fred.copy()
    treasury["date"] = treasury["observation_date"].dt.strftime("%Y-%m-%d")

    matched = btc.merge(
        treasury[["date", "yield_pct", "yield_change_bps"]],
        on="date",
        how="inner",
    )
    matched = matched.dropna(subset=["return_pct", "yield_change_bps"])

    latest = fred.iloc[-1]
    correlation = float("nan")

    # Avoid calculating a misleading correlation from too little data
    # or when either variable has no variation.
    if (
        len(matched) >= 10
        and matched["return_pct"].nunique() > 1
        and matched["yield_change_bps"].nunique() > 1
    ):
        correlation = matched["return_pct"].corr(
            matched["yield_change_bps"]
        )

    if pd.isna(correlation):
        interpretation = (
            f"There are {len(matched)} matched daily observations. "
            "There is not enough usable data to estimate a dependable "
            "linear relationship."
        )
    else:
        strength = abs(correlation)

        if strength < 0.20:
            strength_text = "very weak"
        elif strength < 0.40:
            strength_text = "weak"
        elif strength < 0.60:
            strength_text = "moderate"
        elif strength < 0.80:
            strength_text = "strong"
        else:
            strength_text = "very strong"

        direction = "positive" if correlation > 0 else "negative"

        if strength < 0.20:
            interpretation = (
                f"The calculated correlation is {correlation:+.3f}, indicating "
                "little clear linear relationship in this sample."
            )
        elif correlation > 0:
            interpretation = (
                f"The calculated correlation is {correlation:+.3f}, indicating "
                f"a {strength_text} positive relationship in this sample. "
                "Bitcoin returns tended to be higher on days when Treasury "
                "yields increased, but this does not establish cause and effect."
            )
        else:
            interpretation = (
                f"The calculated correlation is {correlation:+.3f}, indicating "
                f"a {strength_text} negative relationship in this sample. "
                "Bitcoin returns tended to be lower on days when Treasury "
                "yields increased, but this does not establish cause and effect."
            )

    if not pd.isna(latest["yield_change_bps"]):
        change = float(latest["yield_change_bps"])
        if change > 0:
            latest_change_text = f"increased by {change:.1f} basis points"
        elif change < 0:
            latest_change_text = f"decreased by {abs(change):.1f} basis points"
        else:
            latest_change_text = "was unchanged"
    else:
        latest_change_text = "has no available daily change"

    # Compare the latest yield with the preceding five available observations.
    if len(fred) >= 6:
        previous_yield = float(fred.iloc[-6]["yield_pct"])
        yield_change_5 = float(latest["yield_pct"]) - previous_yield
        if yield_change_5 > 0:
            five_day_text = (
                f"Over the latest five observation intervals, the yield "
                f"rose by {yield_change_5:.2f} percentage points."
            )
        elif yield_change_5 < 0:
            five_day_text = (
                f"Over the latest five observation intervals, the yield "
                f"fell by {abs(yield_change_5):.2f} percentage points."
            )
        else:
            five_day_text = (
                "The yield was unchanged over the latest five observation intervals."
            )
    else:
        five_day_text = "There are too few yield observations for a five-interval comparison."

    return {
        "latest_date": latest["observation_date"].strftime("%Y-%m-%d"),
        "latest_yield": float(latest["yield_pct"]),
        "latest_change_text": latest_change_text,
        "five_day_text": five_day_text,
        "matched_count": len(matched),
        "correlation": correlation,
        "interpretation": interpretation,
    }


def bitcoin_insights(data, label):
    insights = []
    latest = data.iloc[-1]
    previous = data.iloc[-2] if len(data) >= 2 else None

    if pd.notna(latest["return_pct"]):
        movement = float(latest["return_pct"])
        if movement >= 2:
            insights.append(
                f"{label}: Bitcoin rose {movement:.2f}% in the latest candle, "
                "a notable increase worth comparing with trading volume."
            )
        elif movement <= -2:
            insights.append(
                f"{label}: Bitcoin fell {abs(movement):.2f}% in the latest candle, "
                "a notable decline worth comparing with trading volume."
            )
        elif movement > 0:
            insights.append(
                f"{label}: Bitcoin edged higher by {movement:.2f}% in the latest candle."
            )
        elif movement < 0:
            insights.append(
                f"{label}: Bitcoin edged lower by {abs(movement):.2f}% in the latest candle."
            )
        else:
            insights.append(f"{label}: Bitcoin's latest candle had no price change.")

    if "sma_7" in data and pd.notna(latest.get("sma_7")):
        if latest["close_usd"] > latest["sma_7"]:
            insights.append(
                f"{label}: The latest closing price is above its 7-period average, "
                "indicating stronger recent prices than that short-term benchmark."
            )
        else:
            insights.append(
                f"{label}: The latest closing price is below its 7-period average, "
                "indicating weaker recent prices than that short-term benchmark."
            )

    if "sma_30" in data and pd.notna(latest.get("sma_30")):
        if latest["close_usd"] > latest["sma_30"]:
            insights.append(
                f"{label}: The latest closing price is above its 30-period average."
            )
        else:
            insights.append(
                f"{label}: The latest closing price is below its 30-period average."
            )

    if previous is not None and pd.notna(latest["volume_xbt"]):
        earlier_volume = data["volume_xbt"].iloc[:-1].dropna()
        if not earlier_volume.empty and earlier_volume.mean() > 0:
            ratio = latest["volume_xbt"] / earlier_volume.mean()
            if ratio >= 1.5:
                insights.append(
                    f"{label}: Latest trading volume was {ratio:.1f} times the "
                    "average of earlier candles in this export. This may indicate "
                    "greater activity, but volume alone does not show market direction."
                )
            elif ratio <= 0.5:
                insights.append(
                    f"{label}: Latest trading volume was less than half the "
                    "average of earlier candles in this export."
                )
            else:
                insights.append(
                    f"{label}: Latest trading volume was close to the average "
                    "of earlier candles in this export."
                )

    return insights


def make_charts(data, timeframe, prefix):
    label = "Daily" if timeframe == "daily" else "4-hour"
    paths = [
        OUTPUT_DIR / f"{prefix}_price.png",
        OUTPUT_DIR / f"{prefix}_returns.png",
        OUTPUT_DIR / f"{prefix}_volume.png",
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["timestamp_utc"], y=data["close_usd"],
        name="Bitcoin close", mode="lines"
    ))

    for column, name in [("sma_7", "SMA 7"), ("sma_30", "SMA 30")]:
        if column in data and data[column].notna().any():
            fig.add_trace(go.Scatter(
                x=data["timestamp_utc"], y=data[column],
                name=name, mode="lines"
            ))

    fig.update_layout(
        title=f"Bitcoin Price and Moving Averages — {label} Candles",
        xaxis_title="Date (UTC)", yaxis_title="Price (USD)",
        template="plotly_white", width=1100, height=480,
    )
    fig.write_image(str(paths[0]))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["timestamp_utc"], y=data["return_pct"],
        name="Return (%)"
    ))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(
        title=f"Bitcoin Returns — {label} Candles",
        xaxis_title="Date (UTC)", yaxis_title="Return (%)",
        template="plotly_white", width=1100, height=360,
    )
    fig.write_image(str(paths[1]))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["timestamp_utc"], y=data["volume_xbt"],
        name="Volume (XBT)"
    ))
    fig.update_layout(
        title=f"Bitcoin Trading Volume — {label} Candles",
        xaxis_title="Date (UTC)", yaxis_title="Volume (XBT)",
        template="plotly_white", width=1100, height=360,
    )
    fig.write_image(str(paths[2]))

    return paths


def make_yield_chart(fred, prefix):
    path = OUTPUT_DIR / f"{prefix}_treasury_yield.png"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fred["observation_date"], y=fred["yield_pct"],
        name="US 10-year yield", mode="lines+markers"
    ))

    latest = fred.iloc[-1]
    fig.add_annotation(
        x=latest["observation_date"], y=latest["yield_pct"],
        text=f"Latest: {latest['yield_pct']:.2f}%",
        showarrow=True, arrowhead=2
    )
    fig.update_layout(
        title="US 10-year Treasury Yield",
        xaxis_title="Date", yaxis_title="Yield (%)",
        template="plotly_white", width=1100, height=420,
    )
    fig.write_image(str(path))
    return path


def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(
        18 * mm, 12 * mm,
        "Educational market analysis — not financial advice"
    )
    canvas.drawRightString(192 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf():
    daily_payload, daily = load_export(find_export("daily"), "daily")
    four_payload, four = load_export(find_export("4-hour"), "4-hour")
    fred = load_fred_data()

    analysis = build_yield_analysis(daily, fred)
    insights = bitcoin_insights(daily, "Daily candles")
    insights += bitcoin_insights(four, "4-hour candles")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    daily_charts = make_charts(daily, "daily", f"daily_{timestamp}")
    four_charts = make_charts(four, "4-hour", f"four_hour_{timestamp}")
    yield_chart = make_yield_chart(fred, timestamp)
    pdf_path = OUTPUT_DIR / f"market_intelligence_combined_{timestamp}.pdf"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=22, leading=27,
        alignment=TA_LEFT, textColor=colors.HexColor("#0f172a"),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"],
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=6, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SmallNote", parent=styles["BodyText"],
        fontSize=8, leading=11, textColor=colors.HexColor("#475569"),
    ))

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=15 * mm, bottomMargin=19 * mm,
        title="Bitcoin Market Intelligence",
        author="Bitcoin Market Behaviour Analyzer",
    )

    daily_first = daily.iloc[0]["close_usd"]
    daily_last = daily.iloc[-1]["close_usd"]
    daily_change = ((daily_last / daily_first) - 1) * 100 if daily_first else float("nan")

    four_first = four.iloc[0]["close_usd"]
    four_last = four.iloc[-1]["close_usd"]
    four_change = ((four_last / four_first) - 1) * 100 if four_first else float("nan")

    rows = [
        ["Metric", "Daily candles", "4-hour candles"],
        ["Latest close", money(daily_last), money(four_last)],
        ["Latest return", pct(daily.iloc[-1]["return_pct"]), pct(four.iloc[-1]["return_pct"])],
        ["7-period average", money(daily.iloc[-1].get("sma_7", float("nan"))), money(four.iloc[-1].get("sma_7", float("nan")))],
        ["30-period average", money(daily.iloc[-1].get("sma_30", float("nan"))), money(four.iloc[-1].get("sma_30", float("nan")))],
        ["Visible-period price change", pct(daily_change), pct(four_change)],
        ["Observations", str(len(daily)), str(len(four))],
    ]

    table = Table(rows, colWidths=[54 * mm, 57 * mm, 57 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story = [
        Paragraph("Bitcoin Market Intelligence", styles["ReportTitle"]),
        Paragraph(
            "Daily and 4-hour Bitcoin price, return and volume analysis, "
            "combined with US 10-year Treasury yield observations.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            f"Generated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
            styles["SmallNote"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Timeframe Comparison", styles["SectionHeading"]),
        table,
        Spacer(1, 3 * mm),
        Paragraph("Data-Driven Bitcoin Observations", styles["SectionHeading"]),
    ]

    story.extend(Paragraph(f"• {item}", styles["BodyText"]) for item in insights)

    story.extend([
        PageBreak(),
        Paragraph("Daily Candle Analysis", styles["SectionHeading"]),
        Image(str(daily_charts[0]), width=174 * mm, height=76 * mm),
        Image(str(daily_charts[1]), width=174 * mm, height=55 * mm),
        Image(str(daily_charts[2]), width=174 * mm, height=55 * mm),
        PageBreak(),
        Paragraph("4-hour Candle Analysis", styles["SectionHeading"]),
        Image(str(four_charts[0]), width=174 * mm, height=76 * mm),
        Image(str(four_charts[1]), width=174 * mm, height=55 * mm),
        Image(str(four_charts[2]), width=174 * mm, height=55 * mm),
        PageBreak(),
        Paragraph("Treasury Yields and Bitcoin", styles["SectionHeading"]),
        Paragraph(
            f"Latest US 10-year Treasury yield: <b>{analysis['latest_yield']:.2f}%</b> "
            f"on {analysis['latest_date']}. The latest yield change "
            f"{analysis['latest_change_text']}.",
            styles["BodyText"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(analysis["five_day_text"], styles["BodyText"]),
        Spacer(1, 2 * mm),
        Paragraph(
            f"Matched daily observations: <b>{analysis['matched_count']}</b>.",
            styles["BodyText"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            (
                f"Bitcoin returns vs daily yield changes: "
                f"<b>{analysis['correlation']:+.3f}</b>."
                if not pd.isna(analysis["correlation"])
                else "Correlation was not calculated because there was insufficient usable data."
            ),
            styles["BodyText"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(analysis["interpretation"], styles["BodyText"]),
        Spacer(1, 3 * mm),
        Image(str(yield_chart), width=174 * mm, height=66 * mm),
        Paragraph(
            "Bond prices generally move in the opposite direction to market yields. "
            "Higher yields can make bonds more attractive compared with Bitcoin, "
            "but Bitcoin may rise or fall for many other reasons. This report "
            "describes observed data and does not establish cause and effect.",
            styles["SmallNote"],
        ),
        PageBreak(),
        Paragraph("Methodology and Limitations", styles["SectionHeading"]),
        Paragraph(
            "Bitcoin data comes from saved Kraken public OHLC exports. Treasury "
            "observations come from the project's Google Apps Script endpoint "
            "using FRED-backed data. Correlation compares daily Bitcoin returns "
            "with same-date changes in the 10-year Treasury yield.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "The matched sample may be small and does not prove that yield changes "
            "cause Bitcoin price movements. A positive relationship means returns "
            "tended to be higher on days with rising yields in this sample; a "
            "negative relationship means returns tended to be lower. Results may "
            "change as new data arrives. This report is educational, not financial advice.",
            styles["SmallNote"],
        ),
    ])

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return pdf_path


if __name__ == "__main__":
    try:
        result = generate_pdf()
        print(f"Combined PDF report created: {result}")
    except Exception as exc:
        raise SystemExit(f"PDF generation failed: {exc}") from exc
