import streamlit as st
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Pocket Option Signal Dashboard", layout="wide")

# Auto refresh every second
st_autorefresh(interval=1000, key="refresh")

# State
if "prices" not in st.session_state:
    st.session_state.prices = []

if "signals" not in st.session_state:
    st.session_state.signals = []

# Read incoming price from URL
params = st.experimental_get_query_params()
if "price" in params:
    try:
        price = float(params["price"][0])
        if len(st.session_state.prices) == 0 or price != st.session_state.prices[-1]:
            st.session_state.prices.append(price)
    except:
        pass

st.title("📊 Pocket Option Signal Dashboard (M1)")

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

# Generate signal
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

        if len(st.session_state.signals) == 0 or st.session_state.signals[0]["time"] != signal["time"]:
            st.session_state.signals.insert(0, signal)

# Latest Signal
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

# History
st.subheader("📜 Signal History")

if st.session_state.signals:
    st.dataframe(st.session_state.signals, use_container_width=True)
else:
    st.write("No history yet.")













