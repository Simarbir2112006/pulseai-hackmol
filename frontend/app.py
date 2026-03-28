import streamlit as st
import pandas as pd
import plotly.express as px
import time
from loader import load_data   # ✅ NEW

# Page config
st.set_page_config(page_title="Real-Time Sentiment Dashboard", layout="wide")

# Initialize session state
if "ticker" not in st.session_state:
    st.session_state.ticker = ""
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "anomaly" not in st.session_state:
    st.session_state.anomaly = False

# -----------------
# 1. INPUT PANEL
# -----------------
st.sidebar.title("Input Panel")

ticker_input = st.sidebar.text_input("Stock Ticker", value=st.session_state.ticker).upper()

if st.sidebar.button("Start Monitoring"):
    if ticker_input:
        st.session_state.ticker = ticker_input
        st.session_state.monitoring = True
        st.session_state.anomaly = False
        st.rerun()

st.sidebar.markdown("---")

if st.sidebar.button("Stop Monitoring"):
    st.session_state.monitoring = False
    st.session_state.ticker = ""
    st.session_state.anomaly = False
    st.rerun()

st.sidebar.subheader("Status")
if st.session_state.monitoring and st.session_state.ticker:
    st.sidebar.info(f"Watching {st.session_state.ticker}")
else:
    st.sidebar.warning("Idle")

# -----------------
# 2 & 3. MAIN DASHBOARD / ANOMALY ALERT
# -----------------
if st.session_state.monitoring and st.session_state.ticker:

    # ✅ REPLACED MOCK WITH BACKEND
    data = load_data(st.session_state.ticker)

    st.session_state.anomaly = data["anomaly"]

    st.sidebar.metric("Current Sentiment Score", f"{data['sentiment']:.2f}")
    st.sidebar.metric("Signal", data.get("signal", "HOLD"))   # ✅ NEW

    # -----------------
    # ANOMALY VIEW
    # -----------------
    if st.session_state.anomaly:
        st.markdown(
            """
            <div style="background-color: #ffcccc; padding: 20px; border-radius: 10px; border: 2px solid red;">
                <h1 style="color: red; text-align: center;">🚨 ANOMALY DETECTED 🚨</h1>
            </div>
            <br>
            """,
            unsafe_allow_html=True
        )

        st.error(f"Anomaly detected for stock: {st.session_state.ticker}")

        st.subheader("💡 LLM Explanation")
        st.write(data["llm_brief"])

        st.subheader("📊 Signal Details")
        st.json(data)

    # -----------------
    # NORMAL DASHBOARD
    # -----------------
    else:
        st.title("Live Monitoring")

        if not data["time_series"]:
            st.warning("No data available yet...")
        else:
            df = pd.DataFrame(data["time_series"])

            fig = px.line(
                df,
                x="time",
                y="sentiment",
                title=f"{st.session_state.ticker} Sentiment Over Time",
                markers=True
            )

            fig.update_traces(line_color="green")
            fig.update_layout(
                yaxis_range=[0, 100],
                xaxis_title="Time",
                yaxis_title="Sentiment"
            )

            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Live Feed")
            for article in data["news"]:
                st.markdown(f"**{article['title']}**")
                st.caption(f"{article['source']} - {article['time']}")
                st.markdown("---")

        with col2:
            st.subheader("System Status")
            st.success("🟢 No anomaly detected")
            st.metric("System Health", "Optimal")

    # Refresh
    time.sleep(3)
    st.rerun()

else:
    st.title("Dashboard")
    st.write("Please enter a stock ticker in the sidebar and click **Start Monitoring** to begin.")