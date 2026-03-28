import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from loader import load_data, get_watchlist, add_ticker, remove_ticker, get_trending_tickers

st.set_page_config(page_title="PulseAI", layout="wide", page_icon="📡")

# ── Sidebar ───────────────────────────────────────────────────────────────
st.sidebar.title("📡 PulseAI")
st.sidebar.markdown("*Autonomous market intelligence*")
st.sidebar.markdown("---")

# Load trending tickers once per session (cached for 5 minutes)
@st.cache_data(ttl=300)
def cached_trending():
    return get_trending_tickers(limit=10)

trending = cached_trending()

st.sidebar.subheader("🔥 Trending Stocks")
st.sidebar.caption("Top 10 most active on Yahoo Finance — refreshes every 5 min")

selected_ticker = st.sidebar.selectbox(
    "Select a stock to monitor",
    options=trending,
    format_func=lambda t: f"{t}"
)

# Optional: still allow manual ticker entry
st.sidebar.markdown("---")
st.sidebar.subheader("Or enter any ticker")
manual_ticker = st.sidebar.text_input("Custom ticker", placeholder="e.g. INFY, RELIANCE.NS").upper().strip()
if manual_ticker:
    selected_ticker = manual_ticker
    st.sidebar.success(f"Monitoring: {manual_ticker}")

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto refresh (60s)", value=True)

# Show which ticker is being monitored
st.sidebar.info(f"**Now watching:** {selected_ticker}")

# ── Load data ─────────────────────────────────────────────────────────────
with st.spinner(f"Fetching latest signal for {selected_ticker}..."):
    data = load_data(selected_ticker)

# ── Header ────────────────────────────────────────────────────────────────
st.title(f"📊 {data['ticker']} — Market Intelligence")
st.caption(f"Last updated: {data['timestamp']}")

# ── Combined signal banner ────────────────────────────────────────────────
verdict = data["verdict"]
confidence = data["confidence"]

COLORS = {
    "STRONG BUY": "#00c853",
    "WEAK BUY": "#69f0ae",
    "HOLD": "#ffd740",
    "WEAK SELL": "#ff6d00",
    "STRONG SELL": "#d50000",
}
color = COLORS.get(verdict, "#888888")

st.markdown(
    f"""
    <div style="background:{color}22; border-left: 6px solid {color};
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
m2.metric(
    f"Tomorrow ({data['predicted_tomorrow_date']})",
    f"${data['predicted_tomorrow']}",
    f"{data['pct_change_tomorrow']:+.2f}%"
)
m3.metric("Sentiment Score", f"{data['sentiment']:.1f}/100")
m4.metric("Items Analysed", data["item_count"])

st.markdown(f"*Price range tomorrow: ${data['price_lower']} — ${data['price_upper']}*")

st.markdown("---")

# ── Two column layout ─────────────────────────────────────────────────────
left, right = st.columns([2, 1])

with left:
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

    st.subheader("📰 Flagged Headlines")
    if data["news"]:
        for item in data["news"]:
            z = item.get("z_score")
            z_str = f"Z: {z:+.2f}" if z else "Isolation Forest"
            score = item.get("score", 0)
            badge_color = "🟢" if score > 0.3 else "🔴" if score < -0.3 else "⚪"
            st.markdown(
                f"{badge_color} **{item['title']}**  \n"
                f"<span style='color:gray; font-size:0.8em'>"
                f"{item['source'].upper()} · {item['time']} · Score: {score:+.2f} · {z_str}"
                f"</span>",
                unsafe_allow_html=True
            )
            st.markdown("---")
    else:
        st.info("No flagged headlines this cycle.")

with right:
    if data["anomaly"]:
        st.error(f"🚨 Anomaly Detected — {data['signal_type'].replace('_', ' ').title()}")
    else:
        st.success("✅ No anomaly detected")

    st.subheader("🤖 AI Brief")
    if data["llm_brief"]:
        st.markdown(f"**Summary**  \n{data['llm_brief']}")
        if data["why_it_matters"]:
            st.markdown(f"**Why it matters**  \n{data['why_it_matters']}")
        if data["what_this_means"]:
            st.markdown(f"**What this could mean for you**  \n{data['what_this_means']}")
        if data["brief_confidence"]:
            st.caption(f"Brief confidence: {data['brief_confidence']}")
    else:
        st.info("No brief generated — no anomaly detected.")

    st.subheader("⚙️ System")
    st.markdown(f"**Monitoring:** {selected_ticker}")
    st.markdown(f"**Trending tickers loaded:** {len(trending)}")
    st.markdown(f"**Poll interval:** 60s")
    st.markdown(f"**Sources active:** NewsAPI, Yahoo RSS, StockTwits, yfinance, SEC EDGAR")

# ── Auto refresh ──────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.rerun()
