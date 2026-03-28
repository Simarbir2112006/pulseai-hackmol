import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from loader import load_data, load_candle_data

st.set_page_config(page_title="PulseAI", layout="wide", page_icon="📡")

# ── Sidebar ───────────────────────────────────────────────────────────────
st.sidebar.title("📡 PulseAI")
st.sidebar.markdown("*Autonomous market intelligence*")
st.sidebar.markdown("---")

st.sidebar.subheader("Target Stock")
ticker_input = st.sidebar.text_input(
    "Enter ticker symbol",
    value="TSLA",
    placeholder="e.g. TSLA, NVDA, AAPL"
).upper().strip()

selected_ticker = ticker_input if ticker_input else "TSLA"

# Candlestick controls
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Chart Settings")
candle_period = st.sidebar.selectbox(
    "Period",
    options=["5d", "1mo", "3mo", "6mo", "1y"],
    index=1
)
candle_interval = st.sidebar.selectbox(
    "Interval",
    options=["15m", "30m", "1h", "1d"],
    index=3
)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto refresh (60s)", value=True)
st.sidebar.info(f"**Now watching:** {selected_ticker}")

# ── Load data ─────────────────────────────────────────────────────────────
with st.spinner(f"Fetching latest signal for {selected_ticker}..."):
    data        = load_data(selected_ticker)
    candle_data = load_candle_data(selected_ticker, period=candle_period, interval=candle_interval)

# ── Header ────────────────────────────────────────────────────────────────
st.title(f"📊 {data['ticker']} — Market Intelligence")
st.caption(f"Last updated: {data['timestamp']}")

# ── Combined signal banner ────────────────────────────────────────────────
verdict    = data["verdict"]
confidence = data["confidence"]

COLORS = {
    "STRONG BUY": "rgba(0, 200, 83, 0.9)",
    "WEAK BUY": "rgba(105, 240, 174, 0.9)",
    "HOLD": "rgba(255, 215, 64, 0.9)",
    "WEAK SELL": "rgba(255, 109, 0, 0.9)",
    "STRONG SELL": "rgba(213, 0, 0, 0.9)"
}

color = COLORS.get(verdict, "rgba(136,136,136,0.9)")

st.markdown(
    f"""
    <div style="background:rgba(255,255,255,0.05); border-left: 6px solid {color};
                padding: 16px; border-radius: 8px; margin-bottom: 16px;">
        <h2 style="color:{color}; margin:0">
            {verdict} &nbsp;·&nbsp;
            <span style="font-size:0.7em">Confidence: {confidence.upper()}</span>
        </h2>
        <p style="margin:4px 0 0 0; color:#ccc; font-size:0.85em">
            Sentiment aligned: {"✅" if data["sentiment_aligned"] else "❌"} &nbsp;|&nbsp;
            Price model aligned: {"✅" if data["price_aligned"] else "❌"} &nbsp;|&nbsp;
            Sources: {", ".join(data["sources_used"]) if data["sources_used"] else "—"}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ── Metrics row ───────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Current Price",    f"${data['current_price']}")
m2.metric(
    f"Tomorrow ({data['predicted_tomorrow_date']})",
    f"${data['predicted_tomorrow']}",
    f"{data['pct_change_tomorrow']:+.2f}%"
)
m3.metric("Sentiment Score",  f"{data['sentiment']:.1f}/100")
m4.metric("Items Analysed",   data["item_count"])

st.markdown(f"*Price range tomorrow: ${data['price_lower']} — ${data['price_upper']}*")
st.markdown("---")

# ── Candlestick chart ─────────────────────────────────────────────────────
st.subheader(f"🕯️ {selected_ticker} Price Chart — {candle_period} / {candle_interval}")

if candle_data:
    candle_fig = go.Figure()

    candle_fig.add_trace(go.Candlestick(
        x=candle_data["dates"],
        open=candle_data["opens"],
        high=candle_data["highs"],
        low=candle_data["lows"],
        close=candle_data["closes"],
        name="Price",
        increasing_line_color="#00c853",
        decreasing_line_color="#d50000",
        increasing_fillcolor="rgba(0,200,83,0.3)",
        decreasing_fillcolor="rgba(213,0,0,0.3)",
    ))

    # ✅ FIXED HERE
    candle_fig.add_trace(go.Bar(
        x=candle_data["dates"],
        y=candle_data["volumes"],
        name="Volume",
        marker_color=[
            "rgba(0, 200, 83, 0.2)" if c >= o else "rgba(213, 0, 0, 0.2)"
            for c, o in zip(candle_data["closes"], candle_data["opens"])
        ],
        yaxis="y2",
    ))

    candle_fig.update_layout(
        xaxis_rangeslider_visible=False,
        yaxis=dict(
            title="Price (USD)",
            side="left",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
        ),
        yaxis2=dict(
            title="Volume",
            side="right",
            overlaying="y",
            showgrid=False,
            range=[0, max(candle_data["volumes"]) * 5],
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.02, x=1),
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
    )

    st.plotly_chart(candle_fig, use_container_width=True)
else:
    st.info("No price data available.")

st.markdown("---")

# ── Auto refresh ──────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.rerun()