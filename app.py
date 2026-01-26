import streamlit as st
import yfinance as yf
import ta
import pandas as pd
import time

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Malagna", layout="wide")

# ================= PASSWORD =================
APP_PASSWORD = "malagna2026"

def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        st.markdown("<h2 style='text-align:center'>🔐 Secure Access</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password")
        if pwd == APP_PASSWORD:
            st.session_state.auth = True
            st.rerun()
        elif pwd:
            st.error("Incorrect password")
        st.stop()

check_password()

# ================= STYLES =================
st.markdown("""
<style>
body { background:#0b0f14; color:white; }
.block { background:#121722; padding:22px; border-radius:16px; margin-bottom:18px; }
.center { text-align:center; }
.signal-buy { color:#22c55e; font-size:60px; font-weight:800; }
.signal-sell { color:#ef4444; font-size:60px; font-weight:800; }
.signal-wait { color:#9ca3af; font-size:48px; font-weight:700; }
.metric { color:#9ca3af; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div class="block">
<h1>Malagna</h1>
<div class="metric">Market-State Gated M5 Signal Engine</div>
</div>
""", unsafe_allow_html=True)

# ================= ASSETS =================
MARKETS = {
    "Currencies": {
        "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X",
        "AUD/USD":"AUDUSD=X","USD/CAD":"CAD=X"
    },
    "Crypto": {
        "BTC/USD":"BTC-USD","ETH/USD":"ETH-USD"
    },
    "Stocks": {
        "Apple":"AAPL","Microsoft":"MSFT","Nvidia":"NVDA"
    },
    "Commodities": {
        "Gold":"GC=F","Crude Oil":"CL=F"
    }
}

TV_SYMBOLS = {
    "EUR/USD":"FX:EURUSD","GBP/USD":"FX:GBPUSD","USD/JPY":"FX:USDJPY",
    "AUD/USD":"FX:AUDUSD","USD/CAD":"FX:USDCAD",
    "BTC/USD":"BINANCE:BTCUSDT","ETH/USD":"BINANCE:ETHUSDT",
    "Apple":"NASDAQ:AAPL","Microsoft":"NASDAQ:MSFT","Nvidia":"NASDAQ:NVDA",
    "Gold":"COMEX:GC1!","Crude Oil":"NYMEX:CL1!"
}

market = st.radio("Market", list(MARKETS.keys()), horizontal=True)
asset = st.selectbox("Asset", list(MARKETS[market].keys()))
symbol = MARKETS[market][asset]
tv_symbol = TV_SYMBOLS.get(asset)

# ================= CHART =================
st.markdown("<div class='block'>", unsafe_allow_html=True)
st.components.v1.html(
    f"""
    <iframe src="https://s.tradingview.com/widgetembed/?symbol={tv_symbol}&interval=5&theme=dark"
    width="100%" height="450" frameborder="0"></iframe>
    """,
    height=470
)
st.markdown("</div>", unsafe_allow_html=True)

# ================= DATA =================
@st.cache_data(ttl=60)
def fetch(symbol, interval, period):
    return yf.download(symbol, interval=interval, period=period, progress=False)

data_5m = fetch(symbol, "5m", "5d")
data_15m = fetch(symbol, "15m", "10d")

def indicators(df):
    if df.empty or "Close" not in df:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.astype(float)
    if len(close) < 100:
        return None
    return {
        "close": close,
        "ema50": ta.trend.ema_indicator(close, 50),
        "ema200": ta.trend.ema_indicator(close, 200),
        "rsi": ta.momentum.rsi(close, 14),
        "macd": ta.trend.macd_diff(close)
    }

i5 = indicators(data_5m)
i15 = indicators(data_15m)

# ================= MARKET STATE DETECTION =================
signal = "WAIT"
state = "UNDEFINED"
trend = "NONE"

if i5 and i15:
    price = i5["close"].iloc[-1]

    # ---- STRUCTURE (BIAS) ----
    if i15["ema50"].iloc[-1] > i15["ema200"].iloc[-1]:
        trend = "BULLISH"
    elif i15["ema50"].iloc[-1] < i15["ema200"].iloc[-1]:
        trend = "BEARISH"
    else:
        trend = "RANGE"

    # ---- CANDLE TYPE ----
    body = abs(i5["close"].iloc[-1] - i5["close"].iloc[-2])
    full = data_5m["High"].iloc[-1] - data_5m["Low"].iloc[-1]

    if body / full > 0.6:
        candle = "IMPULSE"
    elif body / full < 0.3:
        candle = "NEUTRAL"
    else:
        candle = "REJECTION"

    # ---- MARKET STATE ----
    if trend in ["BULLISH", "BEARISH"] and candle == "IMPULSE":
        state = "TREND_EXPANSION"
    elif trend in ["BULLISH", "BEARISH"] and candle != "IMPULSE":
        state = "TREND_PULLBACK"
    elif trend == "RANGE" and candle != "IMPULSE":
        state = "RANGE_EXTREME"
    elif trend == "RANGE" and candle == "IMPULSE":
        state = "VOLATILITY_SPIKE"
    else:
        state = "RANGE_COMPRESSION"

    # ================= STATE-GATED DECISIONS =================

    # ---- TREND EXPANSION ----
    if state == "TREND_EXPANSION":
        if trend == "BULLISH" and i5["rsi"].iloc[-1] > 55 and i5["macd"].iloc[-1] > i5["macd"].iloc[-2]:
            signal = "BUY"
        elif trend == "BEARISH" and i5["rsi"].iloc[-1] < 45 and i5["macd"].iloc[-1] < i5["macd"].iloc[-2]:
            signal = "SELL"

    # ---- TREND PULLBACK ----
    elif state == "TREND_PULLBACK":
        if trend == "BULLISH" and price > i5["ema50"].iloc[-1] and i5["rsi"].iloc[-1] > 50:
            signal = "BUY"
        elif trend == "BEARISH" and price < i5["ema50"].iloc[-1] and i5["rsi"].iloc[-1] < 50:
            signal = "SELL"

    # ---- RANGE EXTREMES ----
    elif state == "RANGE_EXTREME":
        if i5["rsi"].iloc[-1] < 40:
            signal = "BUY"
        elif i5["rsi"].iloc[-1] > 60:
            signal = "SELL"

    # ---- VOLATILITY SPIKE ----
    elif state == "VOLATILITY_SPIKE":
        signal = "WAIT"

# ================= DISPLAY =================
signal_class = {"BUY":"signal-buy","SELL":"signal-sell","WAIT":"signal-wait"}[signal]

st.markdown(f"""
<div class="block center">
<div class="{signal_class}">{signal}</div>
<div class="metric">{asset} • {market}</div>
<div class="metric">Market State: {state}</div>
<div class="metric">Bias (M15): {trend}</div>
</div>
""", unsafe_allow_html=True)

time.sleep(1)
st.rerun()




