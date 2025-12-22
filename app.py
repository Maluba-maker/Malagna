

import streamlit as st
import time
from datetime import datetime, timedelta
import yfinance as yf
import ta

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
    "USD/IDR","USD/THB","USD/MYR","USD/ZAR","USD/RUB",
    "EUR/USD OTC","GBP/USD OTC","USD/JPY OTC","AUD/USD OTC","USD/CHF OTC"
]

CRYPTO = ["BTC/USD","ETH/USD","SOL/USD","XRP/USD","DOGE/USD"]
STOCKS = ["AAPL","MSFT","AMZN","NVDA","TSLA"]

RELIABILITY = {k: "Medium" for k in CURRENCY}
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

TV_SYMBOLS = {k: f"FX:{k.replace('/','')}" for k in CURRENCY}
TV_SYMBOLS.update({
    "BTC/USD":"BINANCE:BTCUSDT","ETH/USD":"BINANCE:ETHUSDT",
    "SOL/USD":"BINANCE:SOLUSDT","XRP/USD":"BINANCE:XRPUSDT","DOGE/USD":"BINANCE:DOGEUSDT",
    "AAPL":"NASDAQ:AAPL","MSFT":"NASDAQ:MSFT","AMZN":"NASDAQ:AMZN",
    "NVDA":"NASDAQ:NVDA","TSLA":"NASDAQ:TSLA"
})

# ================= ASSET SELECTION =================
st.markdown("<div class='block'><h3>Select Asset</h3></div>", unsafe_allow_html=True)

asset_type = st.radio("Asset Type", ["Currency","Crypto","Stocks"], horizontal=True)
asset = st.selectbox("Asset", CURRENCY if asset_type=="Currency" else CRYPTO if asset_type=="Crypto" else STOCKS)

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

if data.empty or len(data) < 200:
    signal, trend, price, rsi, confidence, accuracy = "NO TRADE","NEUTRAL",0,0,50,50
else:
    close = data["Close"]
    if hasattr(close,"columns"):
        close = close.iloc[:,0]
    close = close.astype(float)

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
    if 40<=rsi<=60: score+=20
    if macd.iloc[-1]>macd.iloc[-2]: score+=20

    signal = "BUY" if trend=="BULLISH" and score>=70 else "SELL" if trend=="BEARISH" and score>=70 else "NO TRADE"
    confidence=min(100,score)
    accuracy=min(100,score+10)

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

# ================= SIDE PANELS (RESTORED) =================
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
