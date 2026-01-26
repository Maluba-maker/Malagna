import streamlit as st
import time
from datetime import datetime
import yfinance as yf
import ta
import pandas as pd

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Malagna", layout="wide")

# ================= PASSWORD PROTECTION =================
APP_PASSWORD = "malagna2026"  # 🔴 CHANGE THIS

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("""
        <div style="text-align:center; padding:40px;">
            <h2>🔐 Secure Access</h2>
            <p>Enter password to continue</p>
        </div>
        """, unsafe_allow_html=True)

        pwd = st.text_input("Password", type="password")

        if pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        elif pwd:
            st.error("Incorrect password")

        st.stop()

check_password()

# ================= STYLES =================
st.markdown("""
<style>
body { background-color:#0b0f14; color:white; }
.block { background:#121722; padding:24px; border-radius:16px; margin-bottom:20px; }
.center { text-align:center; }
.signal-buy { color:#22c55e; font-size:64px; font-weight:800; }
.signal-sell { color:#ef4444; font-size:64px; font-weight:800; }
.signal-wait { color:#9ca3af; font-size:52px; font-weight:700; }
.small { color:#9ca3af; font-size:14px; }
.metric { margin-top:6px; }
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div class="block">
  <h1>Malagna</h1>
  <div class="small">Rule-Based Multi-Timeframe Signal Engine (Real Markets Only)</div>
</div>
""", unsafe_allow_html=True)

# ================= ASSETS =================
CURRENCIES = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X",
    "USD/CHF":"CHF=X","AUD/USD":"AUDUSD=X","USD/CAD":"CAD=X",
    "NZD/USD":"NZDUSD=X","EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X",
    "EUR/GBP":"EURGBP=X"
}

CRYPTO = {
    "BTC/USD":"BTC-USD","ETH/USD":"ETH-USD","SOL/USD":"SOL-USD",
    "XRP/USD":"XRP-USD","DOGE/USD":"DOGE-USD"
}

STOCKS = {
    "Apple":"AAPL","Microsoft":"MSFT","Amazon":"AMZN","Nvidia":"NVDA",
    "Tesla":"TSLA","Meta":"META","Google":"GOOGL","Netflix":"NFLX",
    "Coca-Cola":"KO","JPMorgan":"JPM"
}

COMMODITIES = {
    "Gold":"GC=F","Silver":"SI=F","Crude Oil":"CL=F",
    "Natural Gas":"NG=F","Copper":"HG=F"
}

MARKETS = {
    "Currencies":CURRENCIES,
    "Crypto":CRYPTO,
    "Stocks":STOCKS,
    "Commodities":COMMODITIES
}

# ================= MARKET SELECTION =================
st.markdown("<div class='block'><h3>Select Market</h3></div>", unsafe_allow_html=True)

market = st.radio("Market Type", list(MARKETS.keys()), horizontal=True)
asset_name = st.selectbox("Asset", list(MARKETS[market].keys()))
symbol = MARKETS[market][asset_name]

# ================= DATA FETCH =================
@st.cache_data(ttl=30)
def fetch(symbol, interval, period):
    return yf.download(symbol, interval=interval, period=period, progress=False)

data_1m = fetch(symbol, "1m", "2d")
data_5m = fetch(symbol, "5m", "5d")
data_15m = fetch(symbol, "15m", "10d")

# ================= INDICATORS (FIXED) =================
def indicators(df):
    if df.empty or "Close" not in df:
        return None

    close = df["Close"]

    # ✅ FORCE 1-D SERIES (CRITICAL FIX)
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    close = close.astype(float)

    if len(close) < 200:
        return None

    return {
        "close": close,
        "ema50": ta.trend.ema_indicator(close=close, window=50),
        "ema200": ta.trend.ema_indicator(close=close, window=200),
        "rsi": ta.momentum.rsi(close=close, window=14),
        "macd": ta.trend.macd_diff(close=close)
    }

i1 = indicators(data_1m)
i5 = indicators(data_5m)
i15 = indicators(data_15m)

signal = "WAIT"
trend = "NO DATA"
price = 0
rsi_val = 0

if i1 and i5 and i15:
    price = round(i1["close"].iloc[-1], 5)
    rsi_val = round(i1["rsi"].iloc[-1], 1)

    # ================= RULE #2 — M15 TREND =================
    if i15["ema50"].iloc[-1] > i15["ema200"].iloc[-1]:
        trend = "BULLISH"
    elif i15["ema50"].iloc[-1] < i15["ema200"].iloc[-1]:
        trend = "BEARISH"
    else:
        trend = "RANGE"

    # ================= RULE #4 — M5 CONFIRM =================
    m5_confirm = (
        (trend == "BULLISH" and i5["close"].iloc[-1] > i5["ema50"].iloc[-1]) or
        (trend == "BEARISH" and i5["close"].iloc[-1] < i5["ema50"].iloc[-1])
    )

    # ================= RULE #5 — M1 ENTRY =================
    bullish_entry = i1["macd"].iloc[-1] > i1["macd"].iloc[-2] and i1["rsi"].iloc[-1] > 52
    bearish_entry = i1["macd"].iloc[-1] < i1["macd"].iloc[-2] and i1["rsi"].iloc[-1] < 48

    # ================= FINAL DECISION =================
    if trend == "BULLISH" and m5_confirm and bullish_entry:
        signal = "BUY"
    elif trend == "BEARISH" and m5_confirm and bearish_entry:
        signal = "SELL"
    else:
        signal = "WAIT"

# ================= DISPLAY =================
signal_class = {
    "BUY":"signal-buy",
    "SELL":"signal-sell",
    "WAIT":"signal-wait"
}[signal]

st.markdown(f"""
<div class="block center">
<div class="{signal_class}">{signal}</div>
<div class="metric">{asset_name} • {market}</div>
<div class="metric">Trend (M15): {trend}</div>
<div class="metric">RSI (M1): {rsi_val}</div>
<div class="metric">Price: {price}</div>
</div>
""", unsafe_allow_html=True)

# ================= EXECUTION GUIDE =================
st.markdown("""
<div class="block">
<h4>Execution Rules</h4>
• Trade only London / New York session<br>
• Trade WITH trend only<br>
• Enter on next candle close<br>
• M1 expiry: 30–60s<br>
• M5 expiry: 3–5min<br>
• If rules fail → WAIT
</div>
""", unsafe_allow_html=True)

time.sleep(1)
st.rerun()
