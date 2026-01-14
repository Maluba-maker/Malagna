import streamlit as st
import numpy as np
import websocket
import threading
from datetime import datetime

st.set_page_config(page_title="Pocket Option Signals", layout="wide")

if "prices" not in st.session_state:
    st.session_state.prices = []

if "signals" not in st.session_state:
    st.session_state.signals = []

st.title("📊 Pocket Option Signal Dashboard (M1)")

BACKEND_WS = "wss://YOUR-BACKEND-URL/ws"  # <-- Replace after deploy

def on_message(ws, message):
    try:
        price = float(message)
        st.session_state.prices.append(price)
    except:
        pass

def start_ws():
    ws = websocket.WebSocketApp(BACKEND_WS, on_message=on_message)
    ws.run_forever()

if "ws_started" not in st.session_state:
    threading.Thread(target=start_ws, daemon=True).start()
    st.session_state.ws_started = True

def generate_signal(prices):
    if len(prices) < 20:
        return None

    arr = np.array(prices)
    fast = arr[-5:].mean()
    slow = arr[-20:].mean()

    if fast > slow:
        return "BUY", 72, "Bullish MA crossover"
    elif fast < slow:
        return "SELL", 73, "Bearish MA crossover"
    return None

signal = generate_signal(st.session_state.prices)

if signal:
    direction, confidence, reason = signal
    st.session_state.signals.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "direction": direction,
        "confidence": confidence,
        "reason": reason
    })

st.subheader("📍 Latest Signal")

if st.session_state.signals:
    latest = st.session_state.signals[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Direction", latest["direction"])
    col2.metric("Confidence", f"{latest['confidence']}%")
    col3.metric("Time", latest["time"])
    col4.metric("Reason", latest["reason"])
else:
    st.write("No signals yet.")

st.subheader("📜 History")
st.dataframe(st.session_state.signals, use_container_width=True)
