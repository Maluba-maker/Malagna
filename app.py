import streamlit as st
import time
import yfinance as yf
import ta
import pandas as pd

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Malagna", layout="wide")

# ================= PASSWORD =================
APP_PASSWORD = "malagna2026"  # 🔴 CHANGE THIS

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
.block { background:#121722; padding:24px; border-radius:16px; margin-bottom:20px; }
.center { text-align:center; }
.signal-buy { color:#22c55e; font-size:64px; font-weight:800; }
.signal-sell { color:#ef4444; font-size:64px; font-weight:800; }
.signal-wait { color:#9ca3af; font-size:52px; font-weight:700; }
.metric { color:#9ca3af; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div class="block">
<h1>Malagna</h1>
<div class="metric">True M5 Entry Signal Engine (Real Markets Only)</div>
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

TV_SYMBOLS = {
    "EUR/USD":"FX:EURUSD","GBP/USD":"FX:GBPUSD","USD/JPY":"FX:USDJPY",
    "USD/CHF":"FX:USDCHF","AUD/USD":"FX:AUDUSD","USD/CAD":"FX:USDCAD",
    "NZD/USD":"FX:NZDUSD","EUR/JPY":"FX:EURJPY","GBP/JPY":"FX:GBPJPY",
    "EUR/GBP":"FX:EURGBP",

    "BTC/USD":"BINANCE:BTCUSDT","ETH/USD":"BINANCE:ETHUSDT",
    "SOL/USD":"BINANCE:SOLUSDT","XRP/USD":"BINANCE:XRPUSDT",
    "DOGE/USD":"BINANCE:DOGEUSDT",

    "Apple":"NASDAQ:AAPL","Microsoft":"NASDAQ:MSFT","Amazon":"NASDAQ:AMZN",
    "Nvidia":"NASDAQ:NVDA","Tesla":"NASDAQ:TSLA","Meta":"NASDAQ:META",
    "Google":"NASDAQ:GOOGL","Netflix":"NASDAQ:NFLX",
    "Coca-Cola":"NYSE:KO","JPMorgan":"NYSE:JPM",

    "Gold":"COMEX:GC1!","Silver":"COMEX:SI1!",
    "Crude Oil":"NYMEX:CL1!","Natural Gas":"NYMEX:NG1!",
    "Copper":"COMEX:HG1!"
}

# ================= CONTROLS =================
market = st.radio("Market Type", list(MARKETS.keys()), horizontal=True)
asset_name = st.selectbox("Asset", list(MARKETS[market].keys()))

symbol = MARKETS[market][asset_name]
tv_symbol = TV_SYMBOLS.get(asset_name)

# ================= TRADINGVIEW CHART =================
st.markdown("<div class='block'>", unsafe_allow_html=True)
if tv_symbol:
    st.components.v1.html(
        f"""
        <iframe src="https://s.tradingview.com/widgetembed/?symbol={tv_symbol}&interval=1&theme=dark&style=1&hideideas=1"
        width="100%" height="460" frameborder="0"></iframe>
        """,
        height=480
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
    if len(close) < 200:
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

signal, trend, price, rsi_val = "WAIT", "NO DATA", 0, 0

if i5 and i15:
    price = round(i5["close"].iloc[-1], 5)
    rsi_val = round(i5["rsi"].iloc[-1], 1)

    if i15["ema50"].iloc[-1] > i15["ema200"].iloc[-1]:
        trend = "BULLISH"
    elif i15["ema50"].iloc[-1] < i15["ema200"].iloc[-1]:
        trend = "BEARISH"
    else:
        trend = "RANGE"

    buy_entry = (
        trend == "BULLISH" and
        i5["close"].iloc[-1] > i5["ema50"].iloc[-1] and
        i5["macd"].iloc[-1] > i5["macd"].iloc[-2] and
        i5["rsi"].iloc[-1] > 50
    )

    sell_entry = (
        trend == "BEARISH" and
        i5["close"].iloc[-1] < i5["ema50"].iloc[-1] and
        i5["macd"].iloc[-1] < i5["macd"].iloc[-2] and
        i5["rsi"].iloc[-1] < 50
    )

    if buy_entry:
        signal = "BUY"
    elif sell_entry:
        signal = "SELL"

# ================= SIGNAL DISPLAY =================
signal_class = {"BUY":"signal-buy","SELL":"signal-sell","WAIT":"signal-wait"}[signal]

st.markdown(f"""
<div class="block center">
<div class="{signal_class}">{signal}</div>
<div class="metric">{asset_name} • {market}</div>
<div class="metric">Trend (M15): {trend}</div>
<div class="metric">RSI (M5): {rsi_val}</div>
<div class="metric">Price: {price}</div>
</div>
""", unsafe_allow_html=True)

time.sleep(1)
st.rerun()


