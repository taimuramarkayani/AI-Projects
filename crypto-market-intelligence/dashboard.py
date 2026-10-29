"""Interactive dashboard for Bitcoin Market Behaviour Analyzer."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from main import (
    DAILY_INTERVAL_MINUTES,
    FOUR_HOUR_INTERVAL_MINUTES,
    fetch_market_data,
    analyse_market,
)

st.set_page_config(
    page_title="Bitcoin Market Behaviour Analyzer",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)



st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(145deg, #0b1220 0%, #111827 100%);
        color: #f1f5f9;
    }

    [data-testid="stMetric"] {
        background: #172235;
        border: 1px solid #28384f;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-size: 0.9rem !important;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 1.65rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }

    h1, h2, h3 {
        color: #f8fafc;
    }

    .stMarkdown p,
    [data-testid="stCaptionContainer"] {
        color: #e2e8f0;
        font-size: 0.95rem;
        line-height: 1.65;
    }

    [data-testid="stCaptionContainer"] p {
        color: #cbd5e1 !important;
    }
    /* Gold text for the longer-term reference */
    .gold-reference {
    color: #fbbf24 !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("₿ Bitcoin Market Behaviour Analyzer")
st.caption("Market structure, returns, volume and historical rule-based observations")

with st.sidebar:
    st.header("Controls")
    timeframe_label = st.radio("Analysis timeframe", ["Daily", "4-hour"], index=0)
    interval_minutes = (
        DAILY_INTERVAL_MINUTES
        if timeframe_label == "Daily"
        else FOUR_HOUR_INTERVAL_MINUTES
    )
    st.write("Data source: Kraken public OHLC API")
    st.write("Pair: XBT/USD")
    st.write(f"Interval: {timeframe_label}")
    refresh = st.button("Refresh market data", width="stretch")
    st.divider()
    st.caption(
        "Rule flags describe historical observations. They are not buy/sell "
        "signals or price predictions."
    )

@st.cache_data(ttl=300, show_spinner=False)
def load_analysis(interval: int):
    raw_data = fetch_market_data(interval_minutes=interval)
    return analyse_market(raw_data, interval_minutes=interval)

if refresh:
    load_analysis.clear()

try:
    with st.spinner(
        f"Retrieving and analysing Kraken {timeframe_label} market data..."
    ):
        data = load_analysis(interval_minutes)
except Exception as exc:
    st.error(f"Unable to load market data: {exc}")
    st.info(
        "Check your internet connection and try refreshing. "
        "The dashboard will not display fabricated market values."
    )
    st.stop()

if data.empty:
    st.error("No analysis observations are available.")
    st.stop()

latest = data.iloc[-1]
first = data.iloc[0]
period_change = (latest["close"] / first["close"] - 1) * 100
latest_return = latest["daily_return_pct"]
latest_volume = latest["volume"]

# Compare the latest candle's volume with its reference.
if timeframe_label.lower() == "daily":
    reference_volume = (
        float(data["volume"].iloc[-2])
        if len(data) >= 2
        else float("nan")
    )
    reference_label = "previous daily candle"
else:
    reference_volume = (
        float(data["volume"].iloc[-7:-1].mean())
        if len(data) >= 7
        else float("nan")
    )
    reference_label = "previous 6-candle average"

if (
    pd.notna(latest_volume)
    and pd.notna(reference_volume)
    and reference_volume > 0
):
    volume_change_pct = (
        (latest_volume / reference_volume) - 1
    ) * 100
else:
    volume_change_pct = float("nan")


# Risk statistics for the displayed window.
returns = pd.to_numeric(data["daily_return_pct"], errors="coerce").dropna()
return_volatility = returns.std() if len(returns) > 1 else float("nan")

# Compare with the volatility estimate one day earlier.
volatility_lookback = 1 if timeframe_label.lower() == "daily" else 6

previous_returns = pd.to_numeric(
    data["daily_return_pct"], errors="coerce"
).shift(volatility_lookback).dropna()

previous_volatility = (
    previous_returns.std()
    if len(previous_returns) > 1
    else float("nan")
)
running_peak = data["close"].cummax()
drawdown_pct = (data["close"] / running_peak - 1) * 100
max_drawdown = drawdown_pct.min()

st.caption(
    f"Kraken XBT/USD . {timeframe_label} market data . Completed candles only "
    ". Educational analysis only"
)
st.subheader("Market overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Latest completed close",
    f"${latest['close']:,.2f}",
    f"{latest_return:+.2f}% per candle"
    if pd.notna(latest_return)
    else "Return unavailable",
    delta_color="normal",
)
c2.metric(
    "Visible-period change",
    f"{period_change:+.2f}%",
    (
        "- Bearish period"
        if period_change < 0
        else "+ Bullish period"
        if period_change > 0
        else "Flat period"
    ),
    delta_color="normal",
)
# Compare the short-term SMA with the longer-term SMA.
sma_7 = latest["sma_7"]
sma_30 = latest["sma_30"]

if pd.isna(sma_7) or pd.isna(sma_30):
    sma_trend = "Trend unavailable"
    sma_delta_color = "off"
elif sma_7 < sma_30:
    sma_trend = "- Bearish trend"
    sma_delta_color = "normal"
elif sma_7 > sma_30:
    sma_trend = "+ Bullish trend"
    sma_delta_color = "normal"
else:
    sma_trend = "Neutral trend"
    sma_delta_color = "off"

c3.metric(
    "7-observation SMA",
    f"${sma_7:,.2f}" if pd.notna(sma_7) else "—",
    sma_trend,
    delta_color=sma_delta_color,
)


with c4:
    st.markdown(
        f"""
        <div style="
            box-sizing: border-box;
            width: 100%;
            height: 100%;
            min-height: 0;
            background: #172235;
            border: 1px solid #28384f;
            padding: 18px;
            border-radius: 12px;
            font-family: inherit;
        ">
            <div style="
                color: #cbd5e1;
                font-size: 0.9rem;
                line-height: 1.3;
            ">
                30-observation SMA
            </div>
            <div style="
                color: #f8fafc;
                font-size: 1.65rem;
                line-height: 1.4;
                font-weight: 600;
                margin-top: 8px;
            ">
                {f"${sma_30:,.2f}" if pd.notna(sma_30) else "—"}
            </div>
            <div style="
                color: #fbbf24;
                font-size: 0.85rem;
                line-height: 1.3;
                font-weight: 500;
                margin-top: 8px;
            ">
                Longer-term reference
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

r1, r2, r3 = st.columns(3)
if pd.isna(return_volatility) or pd.isna(previous_volatility):
    volatility_delta = "Comparison unavailable"
    volatility_color = "off"
elif return_volatility > previous_volatility:
    volatility_delta = "+ Increased"
    volatility_color = "normal"
elif return_volatility < previous_volatility:
    volatility_delta = "- Reduced"
    volatility_color = "normal"
else:
    volatility_delta = "Unchanged"
    volatility_color = "off"

r1.metric(
    "Return volatility",
    f"{return_volatility:.2f}% per candle"
    if pd.notna(return_volatility)
    else "Not available",
    volatility_delta,
    delta_color=volatility_color,
)
r2.metric(
    "Maximum drawdown",
    f"{max_drawdown:.2f}%",
    "- Drawdown risk",
    delta_color="normal",
)

if pd.isna(volume_change_pct):
    volume_delta = "Comparison unavailable"
    volume_delta_color = "off"
elif volume_change_pct > 0:
    volume_delta = f"+{volume_change_pct:.1f}% vs reference"
    volume_delta_color = "normal"
elif volume_change_pct < 0:
    volume_delta = f"{volume_change_pct:.1f}% vs reference"
    volume_delta_color = "normal"
else:
    volume_delta = "Same as reference"
    volume_delta_color = "off"

r3.metric(
    "Latest candle volume",
    f"{latest_volume:,.2f} XBT",
    volume_delta,
    delta_color=volume_delta_color,
)


st.info(f"Latest moving-average comparison: **{latest['trend_comparison']}**")

st.subheader("What the current window shows")

# Interpret the moving-average relationship descriptively.
sma_short = latest["sma_7"]
sma_long = latest["sma_30"]

if pd.isna(sma_short) or pd.isna(sma_long):
    trend_explanation = (
        "There is insufficient data to compare both moving averages."
    )
elif sma_short > sma_long:
    trend_explanation = (
        "The short-term average is above the longer-term average. "
        "Recent prices have been relatively stronger within this window."
    )
elif sma_short < sma_long:
    trend_explanation = (
        "The short-term average is below the longer-term average. "
        "Recent prices have been relatively weaker within this window."
    )
else:
    trend_explanation = (
        "The two moving averages are equal, showing no separation "
        "between these averages at the latest candle."
    )

if pd.isna(return_volatility):
    volatility_explanation = (
        "There are not enough valid candle returns to estimate volatility."
    )
else:
    volatility_explanation = (
        f"Return volatility is {return_volatility:.2f}% per candle, "
        "measured as the standard deviation of returns in the displayed window. "
        "This measures variation, not the direction of price movement."
    )

if pd.isna(max_drawdown):
    drawdown_explanation = "Drawdown is unavailable for this window."
elif max_drawdown < 0:
    drawdown_explanation = (
        f"The largest peak-to-trough decline in this window was "
        f"{abs(max_drawdown):.2f}%. This is measured from the highest "
        "close reached within the displayed window."
    )
else:
    drawdown_explanation = (
        "No peak-to-trough decline was recorded in the displayed window."
    )
# Combine existing observations into a concise historical summary.
if pd.isna(sma_short) or pd.isna(sma_long):
    trend_label = "Trend unclear"
elif sma_short > sma_long:
    trend_label = "Relatively stronger"
elif sma_short < sma_long:
    trend_label = "Relatively weaker"
else:
    trend_label = "Moving averages aligned"

if pd.isna(return_volatility):
    volatility_label = "Volatility unavailable"
else:
    volatility_label = f"Return volatility: {return_volatility:.2f}% per candle"

if pd.isna(period_change):
    performance_label = "Period performance unavailable"
else:
    performance_label = f"Window return: {period_change:+.2f}%"

st.markdown("### Market context summary")
st.markdown(
    f"""
    <div style="
        background-color: #1e293b;
        border: 1px solid #475569;
        border-radius: 8px;
        padding: 16px;
        color: #f1f5f9;
        line-height: 1.8;
    ">
        <strong>Trend:</strong> {trend_label}.<br>
        <strong>Volatility:</strong> {volatility_label}.<br>
        <strong>Performance:</strong> {performance_label}.<br><br>
        <span style="color: #cbd5e1;">
            These describe the selected historical window and do not
            predict future price movements.
        </span>
    </div>
    </style>
    """,
    unsafe_allow_html=True,
)


interpretation_col1, interpretation_col2 = st.columns(2)

with interpretation_col1:
    st.markdown("**Trend context**")
    st.write(trend_explanation)

    st.markdown("**Volatility context**")
    st.write(volatility_explanation)

with interpretation_col2:
    st.markdown("**Drawdown context**")
    st.write(drawdown_explanation)

    st.markdown("**Period performance**")
    st.write(
        f"Across {len(data)} displayed candles, the first-to-last "
        f"close change was {period_change:+.2f}%. "
        "This describes the selected window, not a forecast."
    )

st.caption(
    "Interpretations are descriptive summaries of historical data, "
    "not predictions or buy/sell recommendations."
)

# Keep timestamps exact so each event marker aligns with its completed candle.
up = data["close"] >= data["open"]
hover_time = data["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")

st.subheader("Price action and moving averages")
price_chart = go.Figure()
price_chart.add_trace(
    go.Candlestick(
        x=data["datetime_utc"],
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        name=f"{timeframe_label} OHLC",
        increasing_line_color="#15803d",
        increasing_fillcolor="#166534",
        decreasing_line_color="#f87171",
        decreasing_fillcolor="#991b1b",
        customdata=hover_time,
        hovertemplate=(
            "Time: %{customdata}<br>Open: $%{open:,.2f}"
            "<br>High: $%{high:,.2f}<br>Low: $%{low:,.2f}"
            "<br>Close: $%{close:,.2f}<extra></extra>"
        ),
    )
)
price_chart.add_trace(
    go.Scatter(
        x=data["datetime_utc"],
        y=data["sma_7"],
        mode="lines",
        name="7-observation SMA",
        line=dict(color="#38bdf8", width=2),
    )
)
price_chart.add_trace(
    go.Scatter(
        x=data["datetime_utc"],
        y=data["sma_30"],
        mode="lines",
        name="30-observation SMA",
        line=dict(color="#fbbf24", width=2),
    )
)

# Mark candles that triggered either historical rule.
flagged = data[data["high_volume"] | data["unusual_movement"]].copy()
if not flagged.empty:
    flagged["is_bullish"] = flagged["close"] >= flagged["open"]
    flagged["flag_code"] = "!"
    flagged.loc[
        flagged["high_volume"] & ~flagged["unusual_movement"], "flag_code"
    ] = "V"
    flagged.loc[
        flagged["high_volume"] & flagged["unusual_movement"], "flag_code"
    ] = "V!"

    def flag_style(row):
        if row["flag_code"] == "V!":
            return (
                "#0F766E" if row["is_bullish"] else "#7f1d1d",
                "V! . High volume + unusual movement",
            )
        if row["flag_code"] == "V":
            return (
                "#86efac" if row["is_bullish"] else "#fca5a5",
                "V . High volume only",
            )
        return (
            "#38bdf8" if row["is_bullish"] else "#c084fc",
            "! . Unusual movement only",
        )

    styles = flagged.apply(flag_style, axis=1)
    flagged["flag_color"] = [item[0] for item in styles]
    flagged["flag_meaning"] = [item[1] for item in styles]
    flagged["hover_time"] = flagged["datetime_utc"].dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    price_chart.add_trace(
        go.Scatter(
            x=flagged["datetime_utc"],
            y=(flagged["open"] + flagged["close"]) / 2,
            mode="markers",
            name="Detected events",
            showlegend=False,
            marker=dict(
                symbol="diamond",
                size=9,
                color=flagged["flag_color"],
                line=dict(color="#f8fafc", width=0.8),
            ),
            customdata=flagged[
                [
                    "hover_time",
                    "daily_return_pct",
                    "volume",
                    "high_volume",
                    "unusual_movement",
                    "flag_meaning",
                ]
            ].to_numpy(),
            hovertemplate=(
                "Time: %{customdata[0]}<br>"
                "Return: %{customdata[1]:+.2f}%<br>"
                "Volume: %{customdata[2]:,.4f} XBT<br>"
                "High volume: %{customdata[3]}<br>"
                "Unusual movement: %{customdata[4]}<br>"
                "Event: %{customdata[5]}<extra></extra>"
            ),
        )
    )

# Keep all six flag keys visible, even if a flag is absent in this window.
legend_items = [
    ("#0F766E", "V! . Bullish: high volume + unusual move"),
    ("#f87171", "V! . Bearish: high volume + unusual move"),
    ("#86efac", "V . Bullish: high volume only"),
    ("#fca5a5", "V . Bearish: high volume only"),
    ("#38bdf8", "! . Bullish: unusual move only"),
    ("#c084fc", "! . Bearish: unusual move only"),
]

for color, label in legend_items:
    price_chart.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            name=label,
            marker=dict(
                symbol="diamond",
                size=10,
                color=color,
                line=dict(color="#ffffff", width=1),
            ),
            hoverinfo="skip",
        )
    )

price_chart.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=560,
    xaxis_title="Time (UTC)",
    yaxis_title="Price (USD)",
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
    legend=dict(
        orientation="h",
        y=-0.22,
        x=0,
        font=dict(size=11, color="#FFFFFF"),
        bgcolor="rgba(36,52,73,0.95)",
        bordercolor="#52657D",
        borderwidth=1,
        tracegroupgap=6,
    ),
    margin=dict(l=15, r=15, t=55, b=125),
)
st.plotly_chart(price_chart, width="stretch")


st.markdown(
    """
    <div style="
        background-color: #243449;
        border: 1px solid #52657d;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 4px;
        color: #ffffff;
        font-size: 14px;
        line-height: 1.8;
    ">
        <strong>How to read the flags</strong><br>
        <strong>V</strong> = volume exceeds the preceding 30-candle average.
        <strong>!</strong> = unusual price movement.
        <strong>V!</strong> = both rules triggered.<br>
        <strong>Candle direction:</strong>
        Green = close at or above open.
        Red = close below open.<br>
        <strong>Marker colours:</strong>
        Green/red shades identify high-volume events;
        blue/purple identify unusual movements without high volume.
        Hover over a diamond for the timestamp, return, volume, and triggered rules.
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns(2)
with left:
    st.subheader("Trading volume")
    volume_chart = go.Figure()
    volume_chart.add_trace(
        go.Bar(
            x=data["datetime_utc"],
            y=data["volume"],
            name=f"{timeframe_label} volume",
            marker_color=[
                "#166534" if is_up else "#991b1b" for is_up in up
            ],
            customdata=hover_time,
            hovertemplate=(
                "Time: %{customdata}<br>"
                "Volume: %{y:,.4f} XBT<extra></extra>"
            ),
        )
    )
    volume_chart.add_trace(
        go.Scatter(
            x=data["datetime_utc"],
            y=data["avg_volume_prev_30"],
            mode="lines",
            name="Previous 30-candle average",
            line=dict(color="#fbbf24", width=2),
        )
    )
    volume_chart.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        xaxis_title="Time (UTC)",
        yaxis_title="Volume (XBT)",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(volume_chart, width="stretch")

with right:
    st.subheader("Returns per candle")
    return_colors = [
        "#15803d" if value >= 0 else "#f87171"
        for value in data["daily_return_pct"].fillna(0)
    ]
    returns_chart = go.Figure()
    returns_chart.add_trace(
        go.Bar(
            x=data["datetime_utc"],
            y=data["daily_return_pct"],
            marker_color=return_colors,
            name="Return per candle",
            customdata=hover_time,
            hovertemplate=(
                "Time: %{customdata}<br>"
                "Return: %{y:+.2f}%<extra></extra>"
            ),
        )
    )
    returns_chart.add_hline(
        y=0, line_color="#e2e8f0", line_width=1.5
    )
    returns_chart.update_layout(
        template="plotly_dark",
        height=380,
        xaxis_title="Time (UTC)",
        yaxis_title="Price change per candle (%)",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(returns_chart, width="stretch")
    st.markdown(
        f"**Visible-period price change ({len(data)} candles):** "
        f"{period_change:+.2f}%"
    )
    st.caption(
        "The bars show individual candle returns; the period change compares "
        "the first displayed close with the last displayed close."
    )

# Indexed performance and drawdown add context beyond the raw price level.
st.subheader("Performance and risk")
perf_left, perf_right = st.columns(2)

with perf_left:
    st.markdown("**Indexed price performance**")
    indexed_price = data["close"] / data["close"].iloc[0] * 100
    performance_chart = go.Figure()
    performance_chart.add_trace(
        go.Scatter(
            x=data["datetime_utc"],
            y=indexed_price,
            mode="lines",
            name="Price index (first close = 100)",
            line=dict(color="#38bdf8", width=2.5),
            customdata=hover_time,
            hovertemplate=(
                "Time: %{customdata}<br>"
                "Price index: %{y:.2f}<extra></extra>"
            ),
        )
    )
    performance_chart.add_hline(
        y=100, line_dash="dash", line_color="#94a3b8"
    )
    performance_chart.update_layout(
        template="plotly_dark",
        height=330,
        xaxis_title="Time (UTC)",
        yaxis_title="Index (100 = first close)",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=25, b=10),
    )
    st.plotly_chart(performance_chart, width="stretch")

with perf_right:
    st.markdown("**Drawdown from the displayed-window peak**")
    drawdown_chart = go.Figure()
    drawdown_chart.add_trace(
        go.Scatter(
            x=data["datetime_utc"],
            y=drawdown_pct,
            mode="lines",
            name="Drawdown (%)",
            line=dict(color="#f87171", width=2),
            fill="tozeroy",
            fillcolor="rgba(248,113,113,0.18)",
            customdata=hover_time,
            hovertemplate=(
                "Time: %{customdata}<br>"
                "Drawdown: %{y:.2f}%<extra></extra>"
            ),
        )
    )
    drawdown_chart.update_layout(
        template="plotly_dark",
        height=330,
        xaxis_title="Time (UTC)",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=25, b=10),
    )
    st.plotly_chart(drawdown_chart, width="stretch")
    st.caption(
        "Drawdown is measured against the highest closing price within the "
        "displayed window; it is not a full-history or future-risk estimate."
    )

st.subheader("Rule-based observations")
r1, r2, r3 = st.columns(3)
r1.metric("Unusual-movement candles", int(data["unusual_movement"].sum()))
r2.metric("High-volume candles", int(data["high_volume"].sum()))
r3.metric(
    "Candles with either flag",
    int((data["unusual_movement"] | data["high_volume"]).sum()),
)
st.caption(
    "Unusual movement = absolute return greater than twice the median "
    "absolute return across the preceding 30 completed candles. High volume "
    "= volume above the preceding 30-candle average. Moving averages use "
    "7 and 30 observations. These are descriptive rules, not trade signals."
)

unusual_count = int(data["unusual_movement"].sum())
volume_count = int(data["high_volume"].sum())
either_count = int(
    (data["unusual_movement"] | data["high_volume"]).sum()
)

if either_count == 0:
    st.info(
        "No candles in the displayed window triggered either rule. "
        "This does not mean the market is risk-free."
    )
else:
    st.info(
        f"In the displayed {timeframe_label.lower()} window, "
        f"{unusual_count} candles showed unusual price movement, "
        f"{volume_count} showed high volume, and "
        f"{either_count} triggered at least one rule. "
        "These observations identify historical activity, not future direction."
    )

with st.expander(f"View {timeframe_label.lower()} analysis data"):
    display_columns = [
        "datetime_utc",
        "open",
        "high",
        "low",
        "close",
        "daily_return_pct",
        "volume",
        "sma_7",
        "sma_30",
        "unusual_movement",
        "high_volume",
    ]
    display_data = data[display_columns].copy().rename(
        columns={
            "datetime_utc": "Timestamp (UTC)",
            "open": "Open (USD)",
            "high": "High (USD)",
            "low": "Low (USD)",
            "close": "Close (USD)",
            "daily_return_pct": "Return per Candle (%)",
            "volume": "Volume (XBT)",
            "sma_7": "7-observation SMA",
            "sma_30": "30-observation SMA",
            "unusual_movement": "Unusual Movement",
            "high_volume": "High Volume",
        }
    )

    display_data["Unusual Movement"] = (
        display_data["Unusual Movement"].map({True: "Yes", False: "No"})
    )
    display_data["High Volume"] = (
        display_data["High Volume"].map({True: "Yes", False: "No"})
    )

    st.dataframe(
        display_data,
        width="stretch",
        hide_index=True,
        height=420,
        column_config={
            "Timestamp (UTC)": st.column_config.DatetimeColumn(
                "Timestamp (UTC)", format="YYYY-MM-DD HH:mm"
            ),
            "Unusual Movement": st.column_config.TextColumn("Unusual Move"),
            "High Volume": st.column_config.TextColumn("High Volume"),
        },
    )

    st.download_button(
        "Download analysis as CSV",
        data=display_data.to_csv(index=False).encode("utf-8"),
        file_name=(
            "bitcoin_market_analysis_"
            f"{timeframe_label.lower().replace('-', '_')}.csv"
        ),
        mime="text/csv",
    )

st.divider()
st.caption(
    f"Data source: Kraken public OHLC API . Latest completed candle: "
    f"{latest['datetime_utc'].strftime('%Y-%m-%d %H:%M UTC')} . "
    f"Metrics use completed {timeframe_label.lower()} candles."
)
st.caption("This project is for education only and is not financial advice.")