
"""Interactive dashboard for Bitcoin Market Behaviour Analyzer."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from main import fetch_market_data, analyse_market


# ---------------------------------------------------------
# Page setup
# ---------------------------------------------------------

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
        color: #a9b8cc;
    }
    h1, h2, h3 {
        color: #f8fafc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Header and data refresh
# ---------------------------------------------------------

st.title("₿ Bitcoin Market Behaviour Analyzer")
st.caption(
    "Kraken XBT/USD · Daily market data · "
    "30 completed observations · Educational analysis only"
)

with st.sidebar:
    st.header("Controls")
    st.write("Data source: Kraken public OHLC API")
    st.write("Pair: XBT/USD")
    st.write("Interval: Daily")

    refresh = st.button("Refresh market data", use_container_width=True)

    st.divider()
    st.caption(
        "Rule flags describe historical observations. "
        "They are not buy/sell signals or price predictions."
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_analysis():
    """Retrieve and calculate market data."""
    raw_data = fetch_market_data()
    return analyse_market(raw_data)


if refresh:
    load_analysis.clear()

try:
    with st.spinner("Retrieving and analysing Kraken market data..."):
        data = load_analysis()
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


# ---------------------------------------------------------
# KPI cards
# ---------------------------------------------------------

st.subheader("Market overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Latest completed close",
    f"${latest['close']:,.2f}",
    f"{latest_return:+.2f}% daily",
)

c2.metric(
    "30-observation change",
    f"{period_change:+.2f}%",
    "First close to last close",
)

c3.metric(
    "7-day SMA",
    f"${latest['sma_7']:,.2f}",
    "Short-term trend",
)

c4.metric(
    "30-day SMA",
    f"${latest['sma_30']:,.2f}",
    "Longer-term trend",
)

trend = latest["trend_comparison"]
st.info(f"Latest moving-average comparison: **{trend}**")


# ---------------------------------------------------------
# Candlestick and moving-average chart
# ---------------------------------------------------------

st.subheader("Price action and moving averages")

price_chart = go.Figure()

price_chart.add_trace(
    go.Candlestick(
        x=data["date"],
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        name="Daily OHLC",
        increasing_line_color="#22c55e",
        decreasing_line_color="#f87171",
    )
)

price_chart.add_trace(
    go.Scatter(
        x=data["date"],
        y=data["sma_7"],
        mode="lines",
        name="7-day SMA",
        line=dict(color="#38bdf8", width=2),
    )
)

price_chart.add_trace(
    go.Scatter(
        x=data["date"],
        y=data["sma_30"],
        mode="lines",
        name="30-day SMA",
        line=dict(color="#fbbf24", width=2),
    )
)

price_chart.update_layout(
    template="plotly_dark",
    height=520,
    xaxis_title="Date",
    yaxis_title="Price (USD)",
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.08, x=0),
    margin=dict(l=15, r=15, t=55, b=15),
)

st.plotly_chart(price_chart, use_container_width=True)


# ---------------------------------------------------------
# Volume and daily returns
# ---------------------------------------------------------

left, right = st.columns(2)

with left:
    st.subheader("Trading volume")

    volume_chart = go.Figure()

    volume_chart.add_trace(
        go.Bar(
            x=data["date"],
            y=data["volume"],
            name="Daily volume",
            marker_color="#64748b",
            hovertemplate="Date: %{x}<br>Volume: %{y:,.4f} XBT<extra></extra>",
        )
    )

    volume_chart.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["avg_volume_prev_30"],
            mode="lines",
            name="Previous 30-day average",
            line=dict(color="#fbbf24", width=2),
        )
    )

    high_volume = data[data["high_volume"]]

    volume_chart.add_trace(
        go.Scatter(
            x=high_volume["date"],
            y=high_volume["volume"],
            mode="markers",
            name="High-volume flag",
            marker=dict(color="#fb923c", size=10, symbol="diamond"),
        )
    )

    volume_chart.update_layout(
        template="plotly_dark",
        height=380,
        xaxis_title="Date",
        yaxis_title="Volume (XBT)",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )

    st.plotly_chart(volume_chart, use_container_width=True)

with right:
    st.subheader("Daily price returns")

    return_colors = [
        "#22c55e" if value >= 0 else "#f87171"
        for value in data["daily_return_pct"]
    ]

    returns_chart = go.Figure()

    returns_chart.add_trace(
        go.Bar(
            x=data["date"],
            y=data["daily_return_pct"],
            marker_color=return_colors,
            name="Daily return",
            hovertemplate="Date: %{x}<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    unusual = data[data["unusual_movement"]]

    returns_chart.add_trace(
        go.Scatter(
            x=unusual["date"],
            y=unusual["daily_return_pct"],
            mode="markers",
            name="Unusual-movement flag",
            marker=dict(color="#fbbf24", size=11, symbol="diamond"),
        )
    )

    returns_chart.add_hline(y=0, line_color="#94a3b8", line_width=1)

    returns_chart.update_layout(
        template="plotly_dark",
        height=380,
        xaxis_title="Date",
        yaxis_title="Daily return (%)",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )

    st.plotly_chart(returns_chart, use_container_width=True)


# ---------------------------------------------------------
# Rule summary and detailed data
# ---------------------------------------------------------

st.subheader("Rule-based observations")

r1, r2, r3 = st.columns(3)

r1.metric(
    "Unusual-movement days",
    int(data["unusual_movement"].sum()),
)

r2.metric(
    "High-volume days",
    int(data["high_volume"].sum()),
)

r3.metric(
    "Latest daily volume",
    f"{latest_volume:,.2f} XBT",
)

st.caption(
    "Unusual movement = absolute daily return greater than twice "
    "the median absolute return over the preceding 30 completed days. "
    "High volume = daily volume above the preceding 30-day average."
)

with st.expander("View daily analysis data"):
    display_columns = [
        "date",
        "close",
        "daily_return_pct",
        "volume",
        "sma_7",
        "sma_30",
        "unusual_movement",
        "high_volume",
    ]

    display_data = data[display_columns].copy()
    display_data = display_data.rename(
        columns={
            "date": "Date",
            "close": "Close (USD)",
            "daily_return_pct": "Daily Return (%)",
            "volume": "Volume (XBT)",
            "sma_7": "7-day SMA",
            "sma_30": "30-day SMA",
            "unusual_movement": "Unusual Movement",
            "high_volume": "High Volume",
        }
    )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = display_data.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download analysis as CSV",
        data=csv_data,
        file_name="bitcoin_market_analysis.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.caption(
    f"Data source: Kraken public OHLC API · "
    f"Last observation: {latest['date']} · "
    "Metrics are descriptive and based on completed daily candles."
)

st.caption("This project is for education only and is not financial advice.")
