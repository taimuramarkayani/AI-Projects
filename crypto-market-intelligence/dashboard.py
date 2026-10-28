"""Interactive dashboard for Bitcoin Market Behaviour Analyzer."""

import streamlit as st
import plotly.graph_objects as go

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
    .stApp { background: linear-gradient(145deg, #0b1220 0%, #111827 100%); color: #f1f5f9; }
    [data-testid="stMetric"] { background: #172235; border: 1px solid #28384f; padding: 18px; border-radius: 12px; }
    [data-testid="stMetricLabel"] { color: #a9b8cc; }
    h1, h2, h3 { color: #f8fafc; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("₿ Bitcoin Market Behaviour Analyzer")

with st.sidebar:
    st.header("Controls")
    timeframe_label = st.radio("Analysis timeframe", ["Daily", "4-hour"], index=0)
    interval_minutes = DAILY_INTERVAL_MINUTES if timeframe_label == "Daily" else FOUR_HOUR_INTERVAL_MINUTES
    st.write("Data source: Kraken public OHLC API")
    st.write("Pair: XBT/USD")
    st.write(f"Interval: {timeframe_label}")
    refresh = st.button("Refresh market data", width="stretch")
    st.divider()
    st.caption("Rule flags describe historical observations. They are not buy/sell signals or price predictions.")

@st.cache_data(ttl=300, show_spinner=False)
def load_analysis(interval: int):
    raw_data = fetch_market_data(interval_minutes=interval)
    return analyse_market(raw_data, interval_minutes=interval)

if refresh:
    load_analysis.clear()

try:
    with st.spinner(f"Retrieving and analysing Kraken {timeframe_label} market data..."):
        data = load_analysis(interval_minutes)
except Exception as exc:
    st.error(f"Unable to load market data: {exc}")
    st.info("Check your internet connection and try refreshing. The dashboard will not display fabricated market values.")
    st.stop()

if data.empty:
    st.error("No analysis observations are available.")
    st.stop()

latest = data.iloc[-1]
first = data.iloc[0]
period_change = (latest["close"] / first["close"] - 1) * 100
latest_return = latest["daily_return_pct"]
latest_volume = latest["volume"]

st.caption(f"Kraken XBT/USD · {timeframe_label} market data · Completed candles only · Educational analysis only")
st.subheader("Market overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest completed close", f"${latest['close']:,.2f}", f"{latest_return:+.2f}% per candle")
c2.metric(f"Visible-period change", f"{period_change:+.2f}%", f"First to last close ({len(data)} candles)")
c3.metric("7-observation SMA", f"${latest['sma_7']:,.2f}", "Short-term trend")
c4.metric("30-observation SMA", f"${latest['sma_30']:,.2f}", "Longer-term trend")
st.info(f"Latest moving-average comparison: **{latest['trend_comparison']}**")

# Keep timestamps exact so each event marker aligns with its completed candle.
up = data["close"] >= data["open"]
hover_time = data["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")

st.subheader("Price action and moving averages")
price_chart = go.Figure()
price_chart.add_trace(go.Candlestick(
    x=data["datetime_utc"],
    open=data["open"],
    high=data["high"],
    low=data["low"],
    close=data["close"],
    name=f"{timeframe_label} OHLC",
    increasing_line_color="#22c55e",
    increasing_fillcolor="#166534",
    decreasing_line_color="#f87171",
    decreasing_fillcolor="#991b1b",
    customdata=hover_time,
    hovertemplate=(
        "Time: %{customdata}<br>Open: $%{open:,.2f}"
        "<br>High: $%{high:,.2f}<br>Low: $%{low:,.2f}"
        "<br>Close: $%{close:,.2f}<extra></extra>"
    ),
))
price_chart.add_trace(go.Scatter(
    x=data["datetime_utc"], y=data["sma_7"], mode="lines",
    name="7-observation SMA",
    line=dict(color="#38bdf8", width=2),
))
price_chart.add_trace(go.Scatter(
    x=data["datetime_utc"], y=data["sma_30"], mode="lines",
    name="30-observation SMA",
    line=dict(color="#fbbf24", width=2),
))

# Small diamond markers are shown only on the candlestick chart.
# Colour encodes candle direction plus which rule(s) triggered.
flagged = data[data["high_volume"] | data["unusual_movement"]].copy()
if not flagged.empty:
    flagged["is_bullish"] = flagged["close"] >= flagged["open"]
    flagged["flag_code"] = "!"
    flagged.loc[flagged["high_volume"] & ~flagged["unusual_movement"], "flag_code"] = "V"
    flagged.loc[flagged["high_volume"] & flagged["unusual_movement"], "flag_code"] = "V!"

    def flag_style(row):
        if row["flag_code"] == "V!":
            return ("#14532d" if row["is_bullish"] else "#7f1d1d",
                    "V! · High volume + unusual movement")
        if row["flag_code"] == "V":
            return ("#86efac" if row["is_bullish"] else "#fca5a5",
                    "V · High volume only")
        return ("#38bdf8" if row["is_bullish"] else "#c084fc",
                "! · Unusual movement only")

    styles = flagged.apply(flag_style, axis=1)
    flagged["flag_color"] = [item[0] for item in styles]
    flagged["flag_meaning"] = [item[1] for item in styles]

    flagged["hover_time"] = flagged["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")
    price_chart.add_trace(go.Scatter(
        x=flagged["datetime_utc"],
        y=(flagged["open"] + flagged["close"]) / 2,
        mode="markers",
        name="Rule-event diamonds",
        marker=dict(
            symbol="diamond",
            size=9,
            color=flagged["flag_color"],
            line=dict(color="#f8fafc", width=0.8),
        ),
        customdata=flagged[[
            "hover_time", "daily_return_pct", "volume",
            "high_volume", "unusual_movement", "flag_meaning"
        ]].to_numpy(),
        hovertemplate=(
            "Time: %{customdata[0]}<br>"
            "Return: %{customdata[1]:+.2f}%<br>"
            "Volume: %{customdata[2]:,.4f} XBT<br>"
            "High volume: %{customdata[3]}<br>"
            "Unusual movement: %{customdata[4]}<br>"
            "Event: %{customdata[5]}<extra></extra>"
        ),
    ))

# Add explicit legend-only entries so the colour key is always visible,
# including when a particular event type does not occur in the selected window.
legend_items = [
    ("#14532d", "V! · Bullish: high volume + unusual move"),
    ("#86efac", "V · Bullish: high volume only"),
    ("#7f1d1d", "V! · Bearish: high volume + unusual move"),
    ("#fca5a5", "V · Bearish: high volume only"),
    ("#38bdf8", "! · Bullish: unusual move only"),
    ("#c084fc", "! · Bearish: unusual move only"),
]
for color, label in legend_items:
    price_chart.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name=label,
        marker=dict(symbol="diamond", size=9, color=color,
                    line=dict(color="#f8fafc", width=0.8)),
        hoverinfo="skip",
    ))

price_chart.update_layout(
    template="plotly_dark",
    height=560,
    xaxis_title="Time (UTC)",
    yaxis_title="Price (USD)",
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10)),
    margin=dict(l=15, r=15, t=55, b=125),
)
st.plotly_chart(price_chart, width="stretch")
st.caption(
    "Diamond key: V = high volume; ! = unusual price movement; V! = both. "
    "Green shades indicate a bullish candle; red shades indicate a bearish candle. "
    "Blue/purple indicate unusual movement without high volume. Hover over a diamond "
    "for its UTC timestamp, return, volume and rule details."
)

left, right = st.columns(2)
with left:
    st.subheader("Trading volume")
    volume_chart = go.Figure()
    volume_chart.add_trace(go.Bar(
        x=data["datetime_utc"],
        y=data["volume"],
        name=f"{timeframe_label} volume",
        marker_color=["#166534" if is_up else "#991b1b" for is_up in up],
        customdata=hover_time,
        hovertemplate="Time: %{customdata}<br>Volume: %{y:,.4f} XBT<extra></extra>",
    ))
    volume_chart.add_trace(go.Scatter(
        x=data["datetime_utc"],
        y=data["avg_volume_prev_30"],
        mode="lines",
        name="Previous 30-candle average volume",
        line=dict(color="#fbbf24", width=2),
    ))
    volume_chart.update_layout(
        template="plotly_dark", height=380, xaxis_title="Time (UTC)",
        yaxis_title="Volume (XBT)", hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(volume_chart, width="stretch")

with right:
    st.subheader("Price returns")
    return_colors = [
        "#22c55e" if value >= 0 else "#f87171"
        for value in data["daily_return_pct"]
    ]
    returns_chart = go.Figure()
    returns_chart.add_trace(go.Bar(
        x=data["datetime_utc"],
        y=data["daily_return_pct"],
        marker_color=return_colors,
        name="Return per candle",
        customdata=hover_time,
        hovertemplate="Time: %{customdata}<br>Return: %{y:+.2f}%<extra></extra>",
    ))
    # The zero line is the easiest reference for reading gains and losses.
    # Show the overall visible-period change, not the arithmetic mean of candles.
    zero_line_color = "#e2e8f0"
    returns_chart.add_hline(y=0, line_color=zero_line_color, line_width=1.5)
    returns_chart.update_layout(
        template="plotly_dark", height=380, xaxis_title="Time (UTC)",
        yaxis_title="Price change per candle (%)", hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(returns_chart, width="stretch")
    st.markdown(
        f"**Visible-period price change ({len(data)} candles):** "
        f"{period_change:+.2f}%"
    )
    st.caption(
        "This is the change from the first displayed candle's close "
        "to the last displayed candle's close. The bars show individual "
        "candle returns, which are different from the total period change."
    )
    st.caption(
        "Methodology reference: CFA Institute, *Rates and Returns* (2026 "
        "CFA Program Level I) and *Statistical Analysis of Returns* "
        "(SBBI Summary Edition, 2021), which distinguish period returns "
        "from arithmetic and geometric average returns."
    )

st.subheader("Rule-based observations")
r1, r2, r3 = st.columns(3)
r1.metric("Unusual-movement candles", int(data["unusual_movement"].sum()))
r2.metric("High-volume candles", int(data["high_volume"].sum()))
r3.metric("Latest candle volume", f"{latest_volume:,.2f} XBT")
st.caption("Unusual movement = absolute return greater than twice the median absolute return across the preceding 30 completed candles. High volume = volume above the preceding 30-candle average. SMA windows use 7 and 30 observations.")

with st.expander(f"View {timeframe_label.lower()} analysis data"):
    display_columns = ["datetime_utc", "open", "high", "low", "close", "daily_return_pct", "volume", "sma_7", "sma_30", "unusual_movement", "high_volume"]
    display_data = data[display_columns].copy().rename(columns={
        "datetime_utc": "Timestamp (UTC)", "open": "Open (USD)", "high": "High (USD)", "low": "Low (USD)", "close": "Close (USD)",
        "daily_return_pct": "Return per Candle (%)", "volume": "Volume (XBT)", "sma_7": "7-observation SMA", "sma_30": "30-observation SMA",
        "unusual_movement": "Unusual Movement", "high_volume": "High Volume"
    })
    st.dataframe(display_data, width="stretch", hide_index=True)
    st.download_button("Download analysis as CSV", data=display_data.to_csv(index=False).encode("utf-8"), file_name=f"bitcoin_market_analysis_{timeframe_label.lower().replace('-', '_')}.csv", mime="text/csv")

st.divider()
st.caption(f"Data source: Kraken public OHLC API · Latest completed candle: {latest['datetime_utc'].strftime('%Y-%m-%d %H:%M UTC')} · Metrics use completed {timeframe_label.lower()} candles.")
st.caption("This project is for education only and is not financial advice.")
