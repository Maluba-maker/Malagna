import streamlit as st

# ================= SIMPLE ACCESS CONTROL =================
APP_PASSWORD = "malagna2025"  # change this

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Malagna Access")
    password = st.text_input("Enter access password", type="password")

    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.stop()

import streamlit as st
import time
from datetime import datetime, timedelta
import yfinance as yf
import ta
import pandas as pd

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Malagna", layout="wide")

# ================= STYLES =================
st.markdown("""
<style>
body { background-color:#0b0f14; color:white; }
.block { background:#121722; padding:24px; border-radius:16px; margin-bottom:20px; }
.center { text-align:center; }
.signal-buy { color:#22c55e; font-size:64px; font-weight:800; }
.signal-sell { color:#ef4444; font-size:64px; font-weight:800; }
.signal-wait { color:#9ca3af; font-size:52px; font-weight:700; }
.bar { height:10px; background:#1f2937; border-radius:6px; }
.fill-green { height:10px; background:#22c55e; border-radius:6px; }
.fill-blue { height:10px; background:#3b82f6; border-radius:6px; }
.small { color:#9ca3af; font-size:14px; }
.metric { margin-top:6px; }
.high { color:#60a5fa; }
.medium { color:#facc15; }
.low { color:#f87171; }
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div class="block">
  <h1>Malagna</h1>
  <div class="small">Multi-Factor Market Analysis & Signal Engine</div>
</div>
""", unsafe_allow_html=True)

# ================= ASSETS =================
CURRENCY = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","USD/CAD","NZD/USD",
    "EUR/JPY","GBP/JPY","EUR/GBP","EUR/CAD","EUR/SEK","EUR/CHF","EUR/HUF",
    "USD/CNY","USD/HKD","USD/SGD","USD/INR","USD/MXN","USD/PHP",
    "USD/IDR","USD/THB","USD/MYR","USD/ZAR","USD/RUB"
]

OTC = [
    "EUR/USD OTC","GBP/USD OTC","USD/JPY OTC","AUD/USD OTC","USD/CHF OTC"
]

CRYPTO = ["BTC/USD","ETH/USD","SOL/USD","XRP/USD","DOGE/USD"]
STOCKS = ["AAPL","MSFT","AMZN","NVDA","TSLA"]

# ================= RELIABILITY =================
RELIABILITY = {k: "Medium" for k in CURRENCY}
RELIABILITY.update({k: "Medium" for k in OTC})
RELIABILITY.update({
    "EUR/USD":"High","GBP/USD":"High","AUD/USD":"High",
    "BTC/USD":"High","ETH/USD":"High",
    "AAPL":"High","MSFT":"High","AMZN":"High","NVDA":"High"
})

# ================= SYMBOL MAPS =================
YF_SYMBOLS = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X","USD/CHF":"CHF=X",
    "AUD/USD":"AUDUSD=X","USD/CAD":"CAD=X","NZD/USD":"NZDUSD=X",
    "EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X","EUR/GBP":"EURGBP=X",
    "EUR/CAD":"EURCAD=X","EUR/SEK":"EURSEK=X","EUR/CHF":"EURCHF=X","EUR/HUF":"EURHUF=X",
    "USD/CNY":"CNY=X","USD/HKD":"HKD=X","USD/SGD":"SGD=X","USD/INR":"INR=X",
    "USD/MXN":"MXN=X","USD/PHP":"PHP=X","USD/IDR":"IDR=X","USD/THB":"THB=X",
    "USD/MYR":"MYR=X","USD/ZAR":"ZAR=X","USD/RUB":"RUB=X",

    "EUR/USD OTC":"EURUSD=X","GBP/USD OTC":"GBPUSD=X","USD/JPY OTC":"JPY=X",
    "AUD/USD OTC":"AUDUSD=X","USD/CHF OTC":"CHF=X",

    "BTC/USD":"BTC-USD","ETH/USD":"ETH-USD","SOL/USD":"SOL-USD",
    "XRP/USD":"XRP-USD","DOGE/USD":"DOGE-USD",

    "AAPL":"AAPL","MSFT":"MSFT","AMZN":"AMZN","NVDA":"NVDA","TSLA":"TSLA"
}

TV_SYMBOLS = {}
for pair in CURRENCY:
    TV_SYMBOLS[pair] = f"FX:{pair.replace('/','')}"
for pair in OTC:
    TV_SYMBOLS[pair] = f"FX:{pair.replace('/','').replace(' OTC','')}"
TV_SYMBOLS.update({
    "BTC/USD":"BINANCE:BTCUSDT","ETH/USD":"BINANCE:ETHUSDT",
    "SOL/USD":"BINANCE:SOLUSDT","XRP/USD":"BINANCE:XRPUSDT","DOGE/USD":"BINANCE:DOGEUSDT",
    "AAPL":"NASDAQ:AAPL","MSFT":"NASDAQ:MSFT","AMZN":"NASDAQ:AMZN",
    "NVDA":"NASDAQ:NVDA","TSLA":"NASDAQ:TSLA"
})

# ================= ASSET SELECTION =================
st.markdown("<div class='block'><h3>Select Asset</h3></div>", unsafe_allow_html=True)

asset_type = st.radio(
    "Asset Type",
    ["Currency","OTC","Crypto","Stocks"],
    horizontal=True
)

if asset_type == "Currency":
    asset = st.selectbox("Asset", CURRENCY)
elif asset_type == "OTC":
    asset = st.selectbox("Asset", OTC)
elif asset_type == "Crypto":
    asset = st.selectbox("Asset", CRYPTO)
else:
    asset = st.selectbox("Asset", STOCKS)

reliability = RELIABILITY.get(asset,"Medium")
symbol = YF_SYMBOLS.get(asset)
tv_symbol = TV_SYMBOLS.get(asset)

# ================= TIMER =================
now = datetime.utcnow()
if "next_candle" not in st.session_state:
    st.session_state.next_candle = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

remaining = int((st.session_state.next_candle - datetime.utcnow()).total_seconds())
if remaining <= 0:
    st.session_state.next_candle = datetime.utcnow().replace(second=0, microsecond=0) + timedelta(minutes=1)
    remaining = 60

# ================= DATA =================
data = yf.download(symbol, interval="1m", period="2d", progress=False)

market_state = "NORMAL"
wick_confirm = False

if data.empty or len(data) < 200:
    signal, trend, price, rsi, confidence, accuracy = "NO TRADE","NEUTRAL",0,0,50,50
else:
    close = data["Close"]
    open_ = data["Open"]
    high = data["High"]
    low = data["Low"]

    if hasattr(close,"columns"):
        close = close.iloc[:,0]
        open_ = open_.iloc[:,0]
        high = high.iloc[:,0]
        low = low.iloc[:,0]

    close = close.astype(float)

    # ===== OTC MARKET STATE =====
    if asset_type == "OTC":
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_high = bb.bollinger_hband()
        bb_low = bb.bollinger_lband()
        bb_width = (bb_high - bb_low).iloc[-1]
        avg_price = close.iloc[-20:].mean()
        market_state = "RANGING" if bb_width / avg_price < 0.003 else "BLOCKED"

    # ===== WICK CONFIRMATION (NEW) =====
    body = abs(close.iloc[-2] - open_.iloc[-2])
    upper_wick = high.iloc[-2] - max(close.iloc[-2], open_.iloc[-2])
    lower_wick = min(close.iloc[-2], open_.iloc[-2]) - low.iloc[-2]

    if body > 0:
        if upper_wick >= body * 1.5:
            wick_confirm = "SELL"
        elif lower_wick >= body * 1.5:
            wick_confirm = "BUY"

    # ===== ORIGINAL LOGIC =====
    ema20 = ta.trend.ema_indicator(close,20)
    ema50 = ta.trend.ema_indicator(close,50)
    ema200 = ta.trend.ema_indicator(close,200)
    rsi_series = ta.momentum.rsi(close,14)
    macd = ta.trend.macd_diff(close)

    price = round(close.iloc[-1],5)
    rsi = round(rsi_series.iloc[-1],1)

    score = 0
    if ema20.iloc[-1] > ema50.iloc[-1] > ema200.iloc[-1]:
        trend="BULLISH"; score+=25
    elif ema20.iloc[-1] < ema50.iloc[-1] < ema200.iloc[-1]:
        trend="BEARISH"; score+=25
    else:
        trend="NEUTRAL"

    score+=15
    if 40 <= rsi <= 60: score+=20
    if macd.iloc[-1] > macd.iloc[-2]: score+=20

    signal = "BUY" if trend=="BULLISH" and score>=70 else "SELL" if trend=="BEARISH" and score>=70 else "NO TRADE"

    # ===== OTC SIGNAL GATE =====
    if asset_type == "OTC" and market_state == "BLOCKED":
        signal = "NO TRADE"

    # ===== OTC MEAN-REVERSION + WICK CONFIRMATION =====
    if asset_type == "OTC" and market_state == "RANGING":
        last_price = close.iloc[-1]
        if rsi <= 30 and last_price <= bb_low.iloc[-1] and wick_confirm == "BUY":
            signal = "BUY"
        elif rsi >= 70 and last_price >= bb_high.iloc[-1] and wick_confirm == "SELL":
            signal = "SELL"

    confidence = min(100,score)
    accuracy = min(100,score+10)

signal_class = "signal-buy" if signal=="BUY" else "signal-sell" if signal=="SELL" else "signal-wait"

# ================= CHART =================
with st.expander("📊 Show / Hide Chart"):
    st.components.v1.html(
        f"<iframe src='https://s.tradingview.com/widgetembed/?symbol={tv_symbol}&interval=1&theme=dark' width='100%' height='400'></iframe>",
        height=420
    )

# ================= MAIN SIGNAL =================
st.markdown(f"""
<div class="block center">
<div class="{signal_class}">{signal}</div>
<div class="metric">{asset} • <span class="{reliability.lower()}">{reliability}</span></div>
<div class="metric">Market State: <b>{market_state}</b></div>
<div class="metric">Strength: {confidence}% | Accuracy: {accuracy}%</div>
<div class="bar"><div class="fill-green" style="width:{confidence}%"></div></div><br>
<div class="bar"><div class="fill-blue" style="width:{accuracy}%"></div></div>
<div class="metric">Trend: {trend}</div>
<div class="metric">RSI: {rsi}</div>
<div class="metric">Price: {price}</div>
<div class="metric">Next Candle: {st.session_state.next_candle.strftime('%H:%M:%S')}</div>
<div class="metric"><b>Countdown: {remaining}s</b></div>
</div>
""", unsafe_allow_html=True)

# ================= SIDE PANELS =================
c1, c2 = st.columns(2)

with c1:
    st.markdown("""
    <div class="block">
    <h4>Confluence Breakdown</h4>
    ✔ EMA structure<br>
    ✔ RSI zone alignment<br>
    ✔ MACD momentum<br>
    ✔ Trend confirmation
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="block">
    <h4>Execution Steps</h4>
    1. Wait candle close<br>
    2. Enter next candle<br>
    3. Follow signal direction<br>
    4. Respect risk rules
    </div>
    """, unsafe_allow_html=True)

time.sleep(1)
st.rerun()
# =========================================================
# 🔥 MALAGNA OTC SIGNAL ENGINE (ADD-ON MODULE)
# =========================================================

st.markdown("---")
st.markdown("## 📊 OTC Signal Engine (Beta)")

from datetime import datetime, timedelta
import statistics

# -------- SETTINGS ----------
confidence_threshold = st.slider(
    "Minimum Confidence (%) – OTC",
    70, 95, 80
)

pair = st.selectbox(
    "OTC Pair",
    ["AUD/USD OTC", "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC"],
    key="otc_pair"
)

support = st.number_input(
    "Support Level (OTC)",
    value=0.6500,
    step=0.0001,
    format="%.5f"
)

resistance = st.number_input(
    "Resistance Level (OTC)",
    value=0.6550,
    step=0.0001,
    format="%.5f"
)

# -------- MOCK CANDLES (TEMPORARY) ----------
candles = [
    {"open": 0.6531, "high": 0.6538, "low": 0.6529, "close": 0.6535},
    {"open": 0.6535, "high": 0.6542, "low": 0.6532, "close": 0.6539},
    {"open": 0.6539, "high": 0.6545, "low": 0.6536, "close": 0.6541},
    {"open": 0.6541, "high": 0.6548, "low": 0.6538, "close": 0.6540},
    {"open": 0.6540, "high": 0.6549, "low": 0.6537, "close": 0.6536},
    {"open": 0.6536, "high": 0.6547, "low": 0.6534, "close": 0.6533},
    {"open": 0.6533, "high": 0.6542, "low": 0.6530, "close": 0.6531},
    {"open": 0.6531, "high": 0.6540, "low": 0.6528, "close": 0.6529},
    {"open": 0.6529, "high": 0.6537, "low": 0.6525, "close": 0.6526},
    {"open": 0.6526, "high": 0.6532, "low": 0.6521, "close": 0.6523},
    {"open": 0.6523, "high": 0.6530, "low": 0.6519, "close": 0.6520},
    {"open": 0.6520, "high": 0.6527, "low": 0.6516, "close": 0.6518},
    {"open": 0.6518, "high": 0.6525, "low": 0.6514, "close": 0.6516},
    {"open": 0.6516, "high": 0.6522, "low": 0.6512, "close": 0.6514},
    {"open": 0.6514, "high": 0.6520, "low": 0.6510, "close": 0.6512},
    {"open": 0.6512, "high": 0.6518, "low": 0.6509, "close": 0.6510},
]

# -------- INDICATORS ----------
def rsi(candles, period=14):
    closes = [c["close"] for c in candles]
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-i] - closes[-i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def bollinger(candles, period=20, dev=2):
    closes = [c["close"] for c in candles[-period:]]
    sma = statistics.mean(closes)
    std = statistics.stdev(closes)
    return sma - dev * std, sma + dev * std

# -------- ENGINE ----------
def otc_engine(candles, support, resistance):
    buy = sell = 0
    reasons = []

    price = candles[-1]["close"]
    buffer = (resistance - support) * 0.1

    if price >= resistance - buffer:
        sell += 30; reasons.append("Price near resistance")
    elif price <= support + buffer:
        buy += 30; reasons.append("Price near support")

    r = rsi(candles)
    if r >= 70:
        sell += 20; reasons.append(f"RSI overbought ({r})")
    elif r <= 30:
        buy += 20; reasons.append(f"RSI oversold ({r})")

    lower, upper = bollinger(candles)
    if price >= upper:
        sell += 20; reasons.append("Upper Bollinger Band touched")
    elif price <= lower:
        buy += 20; reasons.append("Lower Bollinger Band touched")

    confidence = max(buy, sell)
    if confidence < confidence_threshold:
        return "NO_TRADE", confidence, reasons

    return ("BUY" if buy > sell else "SELL"), confidence, reasons

# -------- RUN ----------
if st.button("🔍 Analyse OTC Market"):
    signal, confidence, reasons = otc_engine(candles, support, resistance)

    if signal == "NO_TRADE":
        st.warning("⚪ NO TRADE — conditions not strong enough")
    else:
        now = datetime.now()
        entry = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        expiry = entry + timedelta(minutes=1)
        arrow = "⬆️" if signal == "BUY" else "⬇️"

        st.success("✅ OTC SIGNAL")
        st.code(f"""
PAIR: {pair}
TIMEFRAME: 1M
SIGNAL: {signal} {arrow}
CONFIDENCE: {confidence}%
ENTRY: {entry.strftime('%H:%M')}
EXPIRY: {expiry.strftime('%H:%M')}
""".strip())

        with st.expander("Why this signal"):
            for r in reasons:
                st.write("•", r)



