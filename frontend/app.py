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
    candle_data = load_candle_data(
        selected_ticker,
        period=candle_period,
        interval=candle_interval
    )

# ── Loading state — new ticker not yet analysed ───────────────────────────
if data.get("verdict") == "LOADING":
    st.title(f"📡 {selected_ticker} — Starting Analysis")
    st.info(
        f"⏳ PulseAI is fetching and analysing data for **{selected_ticker}** "
        f"for the first time. First signal arrives in ~60 seconds."
    )
    st.caption("Page will auto-refresh every 10 seconds until data is ready.")
    time.sleep(10)
    st.rerun()

# ── Header ────────────────────────────────────────────────────────────────
st.title(f"📊 {data['ticker']} — Market Intelligence")
st.caption(f"Last updated: {data['timestamp']}" if data['timestamp'] else "Waiting for first signal...")

# ── Combined signal banner ────────────────────────────────────────────────
verdict    = data["verdict"] or "HOLD"
confidence = data["confidence"] or "low"

COLORS = {
    "STRONG BUY":  "rgba(0, 200, 83, 0.9)",
    "WEAK BUY":    "rgba(105, 240, 174, 0.9)",
    "HOLD":        "rgba(255, 215, 64, 0.9)",
    "WEAK SELL":   "rgba(255, 109, 0, 0.9)",
    "STRONG SELL": "rgba(213, 0, 0, 0.9)",
    "LOADING":     "rgba(100, 100, 100, 0.9)",
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
m1.metric("Current Price", f"${data['current_price']}")

pct = data.get("pct_change_tomorrow", 0) or 0
m2.metric(
    f"Tomorrow ({data['predicted_tomorrow_date'] or '—'})",
    f"${data['predicted_tomorrow']}",
    f"{pct:+.2f}%"
)

sentiment_raw = data["sentiment"]
label = "Bullish 📈" if sentiment_raw > 10 else "Bearish 📉" if sentiment_raw < -10 else "Neutral ⚪"
m3.metric("Sentiment", label, f"{sentiment_raw:+.1f}")

m4.metric("Items Analysed", data["item_count"])

st.markdown(
    f"*Price range tomorrow: ${data['price_lower']} — ${data['price_upper']}*"
)
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

# ── Two column layout ─────────────────────────────────────────────────────
left, right = st.columns([2, 1])

with left:
    # Sentiment chart
    st.subheader("📈 Flagged Sentiment Scores")
    if data["time_series"]:
        df = pd.DataFrame(data["time_series"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["sentiment"],
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=8),
            hovertemplate="<b>%{text}</b><br>Score: %{y:.1f}<extra></extra>",
            text=df["source"],
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            yaxis_range=[-100, 100],
            yaxis_title="Sentiment Score",
            xaxis_title="Time",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No anomalies detected this cycle — market is quiet.")

    # Flagged headlines
    st.subheader("📰 Flagged Headlines")
    if data["news"]:
        for item in data["news"]:
            z = item.get("z_score")
            z_str = f"Z: {z:+.2f}" if z else "Isolation Forest"
            score = item.get("score", 0)
            badge = "🟢" if score > 0.3 else "🔴" if score < -0.3 else "⚪"
            st.markdown(
                f"{badge} **{item['title']}**  \n"
                f"<span style='color:gray; font-size:0.8em'>"
                f"{item['source'].upper()} · {item['time']} · "
                f"Score: {score:+.2f} · {z_str}"
                f"</span>",
                unsafe_allow_html=True
            )
            st.markdown("---")
    else:
        st.info("No flagged headlines this cycle.")

with right:
    # Anomaly alert
    if data["anomaly"]:
        signal_label = data["signal_type"].replace("_", " ").title()
        st.error(f"🚨 Anomaly Detected — {signal_label}")
    else:
        st.success("✅ No anomaly detected")

    # AI Brief
    st.subheader("🤖 AI Brief")
    if data["anomaly"] and not data["llm_brief"]:
        st.warning("Anomaly detected — brief generating, refresh in a moment.")
    elif data["llm_brief"]:
        st.markdown(f"**Summary**  \n{data['llm_brief']}")
        if data["why_it_matters"]:
            st.markdown(f"**Why it matters**  \n{data['why_it_matters']}")
        if data["what_this_means"]:
            st.markdown(f"**What this could mean for you**  \n{data['what_this_means']}")
        if data["brief_confidence"]:
            st.caption(f"Brief confidence: {data['brief_confidence']}")
    else:
        st.info("No brief — no anomaly detected this cycle.")

    # System status
    st.subheader("⚙️ System")
    st.markdown(f"**Watching:** {selected_ticker}")
    st.markdown(f"**Poll interval:** 60s")
    st.markdown(f"**Sources:** NewsAPI · Yahoo RSS · StockTwits · yfinance · SEC EDGAR · Finnhub")
    st.markdown(f"**Models:** FinBERT · Z-score · Isolation Forest · Prophet")

st.markdown("---")

# ── Backtest Section ──────────────────────────────────────────────────────
with st.expander("🧪 Model Validation — Historical Backtest", expanded=False):
    st.markdown("""
    **How accurate is PulseAI on real past events?**  
    We ran our pipeline on headlines from known market-moving events 
    and compared our signal to what actually happened.
    """)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Events Tested", "3")
    col_b.metric("Accuracy", "—")
    col_c.metric("Signals Fired", "—")

    bt_col1, bt_col2 = st.columns(2)
    run_btn = bt_col1.button("▶ Run Backtest Now", type="primary")
    event_filter = bt_col2.selectbox(
        "Filter by event",
        options=["All", "adani", "tsla_earnings", "cybertruck"],
        index=0
    )

    if run_btn:
        with st.spinner("Running backtest on historical events..."):
            try:
                import requests as req
                event_id = None if event_filter == "All" else event_filter
                params = {}
                if event_id:
                    params["event_id"] = event_id
                resp = req.get(
                    "http://127.0.0.1:8000/signals/backtest",
                    params=params,
                    timeout=120
                )
                bt = resp.json()
                summary = bt.get("summary", {})
                events = bt.get("events", [])

                # update metrics
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Events", summary.get("total_events", 0))
                m2.metric("Accuracy", f"{summary.get('accuracy_pct', 0)}%")
                m3.metric("Precision", f"{summary.get('precision_pct', 0)}%")
                m4.metric("Recall", f"{summary.get('recall_pct', 0)}%")

                st.markdown("---")

                # event cards
                for event in events:
                    p = event.get("prediction", {})
                    pl = event.get("pipeline", {})
                    pd_data = event.get("price_data", {})
                    correct = p.get("correct", False)

                    card_color = "#00c85322" if correct else "#d5000022"
                    border_color = "#00c853" if correct else "#d50000"
                    icon = "✅" if correct else "❌"

                    st.markdown(
                        f"""
                        <div style="background:{card_color}; border-left: 4px solid {border_color};
                                    padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                            <b>{icon} {event.get('label')} — {event.get('ticker')} ({event.get('date')})</b><br>
                            <span style="color:#ccc; font-size:0.85em">{event.get('description', '')}</span><br><br>
                            <b>Signal:</b> {pl.get('signal_type', '—')} &nbsp;|&nbsp;
                            <b>Avg Sentiment:</b> {pl.get('avg_sentiment', 0):+.3f} &nbsp;|&nbsp;
                            <b>Outcome:</b> {p.get('outcome', '—')}<br>
                            <b>Actual price move (day+1):</b> {pd_data.get('move_day1_pct', event.get('known_move_pct', '?')):+.1f}%
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if pl.get("top_flags"):
                        with st.expander(f"Top flagged headlines — {event.get('label')}"):
                            for flag in pl["top_flags"]:
                                score = flag.get("score", 0)
                                badge = "🟢" if score > 0 else "🔴"
                                st.markdown(f"{badge} `{score:+.3f}` {flag.get('text', '')}")

            except Exception as e:
                st.error(f"Backtest error: {e}")
                st.info("Make sure the backend is running and backtester.py is in backend/")

# ── Auto refresh ──────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.rerun()