import streamlit as st
import yfinance as yf
import ta
import pandas as pd
import time
from datetime import datetime, timedelta 

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
tv_symbol = None

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
.small { font-size:13px; color:#9ca3af; }
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div class="block">
<h1>Malagna</h1>
<div class="metric">20-Rule Dominant Engine • All Markets • True M5</div>
</div>
""", unsafe_allow_html=True)

# ================= MARKETS =================
CURRENCIES = {
    "EUR/JPY": "EURJPY=X",
    "EUR/GBP": "EURGBP=X",
    "USD/JPY": "JPY=X",
    "GBP/USD": "GBPUSD=X",
    "AUD/CAD": "AUDCAD=X",
    "AUD/CHF": "AUDCHF=X",
    "GBP/AUD": "GBPAUD=X",
    "EUR/USD": "EURUSD=X",
    "AUD/JPY": "AUDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "EUR/CHF": "EURCHF=X",
    "GBP/CHF": "GBPCHF=X",
    "CHF/JPY": "CHFJPY=X",
    "EUR/AUD": "EURAUD=X",
    "GBP/JPY": "GBPJPY=X",
    "EUR/CAD": "EURCAD=X",
    "USD/CAD": "CAD=X",
    "GBP/CAD": "GBPCAD=X",
    "USD/CHF": "CHF=X",
    "CAD/JPY": "CADJPY=X"
}

CRYPTO = {
    "BTC/USD":"BTC-USD","ETH/USD":"ETH-USD","BNB/USD":"BNB-USD",
    "SOL/USD":"SOL-USD","XRP/USD":"XRP-USD","ADA/USD":"ADA-USD",
    "DOGE/USD":"DOGE-USD","AVAX/USD":"AVAX-USD","DOT/USD":"DOT-USD",
    "LINK/USD":"LINK-USD","MATIC/USD":"MATIC-USD"
}

COMMODITIES = {
    "Gold":"GC=F","Silver":"SI=F","Crude Oil":"CL=F",
    "Brent Oil":"BZ=F","Natural Gas":"NG=F",
    "Copper":"HG=F","Corn":"ZC=F","Wheat":"ZW=F"
}

market = st.radio("Market", ["Currencies","Crypto","Commodities","Stocks"], horizontal=True)

if market == "Currencies":
    asset = st.selectbox(
    "Pair",
    list(CURRENCIES.keys()),
    key="currency_pair_select"
)
    symbol = CURRENCIES[asset]

elif market == "Crypto":
    asset = st.selectbox("Crypto", list(CRYPTO.keys()))
    symbol = CRYPTO[asset]

elif market == "Commodities":
    asset = st.selectbox("Commodity", list(COMMODITIES.keys()))
    symbol = COMMODITIES[asset]

else:
    asset = st.text_input("Stock ticker (e.g. AAPL, TSLA, MSFT)").upper()
    symbol = asset

# ================= TRADINGVIEW SYMBOL =================
TV_SYMBOLS = {}

# FX
for k in CURRENCIES.keys():
    TV_SYMBOLS[k] = f"FX:{k.replace('/','')}"

# Crypto
for k in CRYPTO.keys():
    TV_SYMBOLS[k] = f"BINANCE:{k.replace('/','').replace('USD','USDT')}"

# Commodities
TV_SYMBOLS.update({
    "Gold": "COMEX:GC1!",
    "Silver": "COMEX:SI1!",
    "Crude Oil": "NYMEX:CL1!",
    "Brent Oil": "ICEEUR:BRN1!",
    "Natural Gas": "NYMEX:NG1!",
    "Copper": "COMEX:HG1!",
    "Corn": "CBOT:ZC1!",
    "Wheat": "CBOT:ZW1!"
})

if market == "Stocks" and asset:
    tv_symbol = f"NASDAQ:{asset}"
else:
    tv_symbol = TV_SYMBOLS.get(asset)

# ================= TRADINGVIEW CHART =================
if tv_symbol:
    st.markdown("<div class='block'>", unsafe_allow_html=True)
    st.components.v1.html(
        f"""
        <iframe
            src="https://s.tradingview.com/widgetembed/?symbol={tv_symbol}&interval=5&theme=dark&style=1&locale=en"
            width="100%"
            height="420"
            frameborder="0"
            allowtransparency="true"
            scrolling="no">
        </iframe>
        """,
        height=430,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ================= DATA =================
@st.cache_data(ttl=60)
def fetch(symbol, interval, period):
    return yf.download(symbol, interval=interval, period=period, progress=False)

data_5m  = fetch(symbol, "5m", "5d")
data_15m = fetch(symbol, "15m", "10d")

def indicators(df):
    if df.empty or "Close" not in df:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:,0]
    close = close.astype(float)
    return {
        "close": close,
        "ema50": ta.trend.ema_indicator(close, 50),
        "ema200": ta.trend.ema_indicator(close, 200),
        "rsi": ta.momentum.rsi(close, 14),
        "macd": ta.trend.macd_diff(close)
    }

i5  = indicators(data_5m)
i15 = indicators(data_15m)

# ================= SUPPORT / RESISTANCE (SIMPLE & SAFE) =================
sr = {
    "support": False,
    "resistance": False
}

if i5:
    recent_low  = i5["close"].rolling(20).min().iloc[-1]
    recent_high = i5["close"].rolling(20).max().iloc[-1]
    price = i5["close"].iloc[-1]

    if abs(price - recent_low) / price < 0.002:
        sr["support"] = True
    if abs(price - recent_high) / price < 0.002:
        sr["resistance"] = True

# ================= CANDLE TYPE (M5) =================
def candle_type(df):
    if df is None or df.empty or len(df) < 2:
        return "NEUTRAL"

    try:
        o = float(df["Open"].iloc[-1])
        c = float(df["Close"].iloc[-1])
        h = float(df["High"].iloc[-1])
        l = float(df["Low"].iloc[-1])
    except Exception:
        return "NEUTRAL"

    body = abs(c - o)
    full = h - l

    if full == 0:
        return "NEUTRAL"

    ratio = body / full
    if ratio >= 0.6:
        return "IMPULSE"
    elif ratio <= 0.3:
        return "NEUTRAL"
    else:
        return "REJECTION"

candle = candle_type(data_5m)

# ================= STRUCTURE & TREND =================
structure = "RANGE"
trend = "FLAT"

if i15:
    if i15["ema50"].iloc[-1] > i15["ema200"].iloc[-1]:
        structure = "BULLISH"
        trend = "UPTREND"
    elif i15["ema50"].iloc[-1] < i15["ema200"].iloc[-1]:
        structure = "BEARISH"
        trend = "DOWNTREND"
# ================= VISUAL GATES =================
def gatekeeper(structure, trend, candle, sr):
    penalty = 0
    notes = []

    # Soft gate 1: Weak structure
    if structure == "RANGE" and trend == "FLAT":
        penalty += 12
        notes.append("Low structure clarity")

    # Soft gate 2: Neutral candle
    if candle == "NEUTRAL":
        penalty += 10
        notes.append("Weak candle")

    # Soft gate 3: Location conflict
    if structure == "BULLISH" and sr["resistance"]:
        penalty += 15
        notes.append("Near resistance")
    if structure == "BEARISH" and sr["support"]:
        penalty += 15
        notes.append("Near support")

    return penalty, ", ".join(notes) if notes else "Clean setup"

# ================= 20-RULE ENGINE =================

def evaluate_pairs(structure, sr, candle, trend):

    # --------- GATES FIRST ---------
    gates_ok, gate_reason = gatekeeper(structure, trend, sr, candle)
    if not gates_ok:
        return "WAIT", gate_reason, 0

    fired = []

    # ---- TREND CONTINUATION (HIGHEST QUALITY) ----
    if structure == "BULLISH" and trend == "UPTREND" and candle == "IMPULSE":
        fired.append(("BUY", 92, "Trend continuation breakout"))
    if structure == "BEARISH" and trend == "DOWNTREND" and candle == "IMPULSE":
        fired.append(("SELL", 92, "Trend continuation breakdown"))

    # ---- PULLBACKS FROM LEVELS ----
    if structure == "BULLISH" and trend == "UPTREND" and sr["support"] and candle == "REJECTION":
        fired.append(("BUY", 90, "Bullish pullback from support"))
    if structure == "BEARISH" and trend == "DOWNTREND" and sr["resistance"] and candle == "REJECTION":
        fired.append(("SELL", 90, "Bearish pullback from resistance"))

    # ---- SR REJECTIONS ----
    if sr["support"] and candle == "REJECTION" and structure != "BEARISH":
        fired.append(("BUY", 88, "Support rejection"))
    if sr["resistance"] and candle == "REJECTION" and structure != "BULLISH":
        fired.append(("SELL", 88, "Resistance rejection"))

    # ---- RANGE EXTREMES (LOWER PRIORITY) ----
    if structure == "RANGE" and sr["support"] and candle == "REJECTION":
        fired.append(("BUY", 84, "Range low rejection"))
    if structure == "RANGE" and sr["resistance"] and candle == "REJECTION":
        fired.append(("SELL", 84, "Range high rejection"))

    if not fired:
        return "WAIT", "No quality rule fired", 0

    # --------- DOMINANT SIDE SCORING ---------
    buys  = [r for r in fired if r[0] == "BUY"]
    sells = [r for r in fired if r[0] == "SELL"]

    buy_score  = sum(r[1] for r in buys)
    sell_score = sum(r[1] for r in sells)

    if buy_score == sell_score:
        return "WAIT", "No dominant side", 0

    dominant_rules = buys if buy_score > sell_score else sells
    dominant_rules.sort(key=lambda x: x[1], reverse=True)

    top = dominant_rules[0]

    # --------- FINAL CONFIDENCE ---------
    confidence = min(99, top[1] + (len(dominant_rules) - 1) * 3)

    return top[0], top[2], confidence
    penalty, gate_note = gatekeeper(structure, trend, candle, sr)

    signal, reason, confidence = execute_rules(fired, sr, candle)

    confidence = max(60, confidence - penalty)

 # ================= SIGNAL EVALUATION =================
signal = "WAIT"
reason = "Not evaluated"
confidence = 0

signal, reason, confidence = evaluate_pairs(structure, sr, candle, trend)

# ================= ENTRY & EXPIRY (✅ ADDED) =================
entry_time = None
expiry_time = None

if signal in ["BUY","SELL"] and not data_5m.empty:
    last_close = data_5m.index[-1].to_pydatetime()
    minute = (last_close.minute // 5 + 1) * 5
    entry_time = last_close.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minute)
    expiry_time = entry_time + timedelta(minutes=5)

# ================= DISPLAY =================
signal_class = {
    "BUY": "signal-buy",
    "SELL": "signal-sell",
    "WAIT": "signal-wait"
}[signal]

signal_class = {
    "BUY": "signal-buy",
    "SELL": "signal-sell",
    "WAIT": "signal-wait"
}[signal]

st.markdown(f"""
<div class="block center">
  <div class="{signal_class}">{signal}</div>
  <div class="metric">{asset} · {market}</div>

  {"<div class='metric'><b>Confidence:</b> " + str(confidence) + "%</div>" if signal != "WAIT" else ""}
  {"<div class='metric'><b>Entry:</b> " + entry_time.strftime('%H:%M') + "</div>" if entry_time else ""}
  {"<div class='metric'><b>Expiry:</b> " + expiry_time.strftime('%H:%M') + "</div>" if expiry_time else ""}

  <div class="small">{reason}</div>
  <div class="small">
    Bias (M15): {structure} • Trend: {trend} • Candle: {candle}
  </div>
</div>
""", unsafe_allow_html=True)














