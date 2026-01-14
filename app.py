import streamlit as st
import numpy as np
from datetime import datetime
import requests
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Signal Dashboard", layout="wide")

if "prices" not in st.session_state:
    st.session_state.prices = []

if "signals" not in st.session_state:
    st.session_state.signals = []

st.title("📊 Pocket Option Signal Dashboard (M1)")

st_autorefresh(interval=1000, key="refresh")

def generate_signal(prices):
    if len(prices) < 20:
        return None

    arr = np.array(prices)
    ma_fast = arr[-5:].mean()
    ma_slow = arr[-20:].mean()

    direction = "WAIT"
    confidence = 50
    reason = "No clear setup"

    if ma_fast > ma_slow:
        direction = "BUY"
        confidence = 72
        reason = "Bullish momentum (MA crossover)"

    elif ma_fast < ma_slow:
        direction = "SELL"
        confidence = 73
        reason = "Bearish momentum (MA crossover)"

    return direction, confidence, reason

# --- Sidebar manual test input ---
st.sidebar.header("Manual Test Feed")
test_price = st.sidebar.number_input("Incoming price", value=1.0000, step=0.0001)

if st.sidebar.button("Send Price"):
    st.session_state.prices.append(test_price)

    result = generate_signal(st.session_state.prices)
    if result:
        direction, confidence, reason = result
        if direction != "WAIT":
            signal = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "pair": "OTC",
                "direction": direction,
                "expiry": "1 min",
                "confidence": confidence,
                "reason": reason
            }
            st.session_state.signals.insert(0, signal)
            st.balloons()

# --- Latest Signal ---
st.subheader("📍 Latest Signal")

if st.session_state.signals:
    latest = st.session_state.signals[0]
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Direction", latest["direction"])
    col2.metric("Pair", latest["pair"])
    col3.metric("Expiry", latest["expiry"])
    col4.metric("Confidence", f"{latest['confidence']}%")
    col5.metric("Time", latest["time"])

    st.info(f"Reason: {latest['reason']}")
else:
    st.write("No signals yet.")

# --- History ---
st.subheader("📜 Signal History")

if st.session_state.signals:
    st.dataframe(st.session_state.signals, use_container_width=True)
else:
    st.write("No history yet.")











