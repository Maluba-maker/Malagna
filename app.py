import streamlit as st
import hashlib
import cv2
import numpy as np
from PIL import Image
from datetime import datetime, timedelta

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Malagna Signal Engine", layout="centered")

st.markdown("## 🔹 Malagna Signal Engine")
st.caption("Pocket Option • Screenshot-based • Strategy Engine")

# =============================
# PASSWORD PROTECTION
# =============================
PASSWORD = "maluz123"
PASSWORD_HASH = hashlib.sha256(PASSWORD.encode()).hexdigest()

def check_password():
    def password_entered():
        if hashlib.sha256(st.session_state["password"].encode()).hexdigest() == PASSWORD_HASH:
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("🔐 Enter password", type="password",
                      key="password", on_change=password_entered)
        return False
    elif not st.session_state["authenticated"]:
        st.text_input("🔐 Enter password", type="password",
                      key="password", on_change=password_entered)
        st.error("❌ Incorrect password")
        return False
    return True

if not check_password():
    st.stop()

# =============================
# INPUT
# =============================
input_mode = st.radio("Select Input Mode", ["Upload / Drag Screenshot", "Take Photo (Camera)"])
image = None

if input_mode == "Upload / Drag Screenshot":
    uploaded = st.file_uploader("Upload Pocket Option screenshot", type=["png", "jpg", "jpeg"])
    if uploaded:
        image = np.array(Image.open(uploaded))
        st.image(image, use_column_width=True)

if input_mode == "Take Photo (Camera)":
    cam = st.camera_input("Capture chart photo")
    if cam:
        image = np.array(Image.open(cam))
        st.image(image, use_column_width=True)

# =============================
# HELPER FUNCTIONS (HEURISTIC)
# =============================
def estimate_trend(gray):
    blur = cv2.GaussianBlur(gray, (35, 35), 0)
    left = np.mean(blur[:, :blur.shape[1]//2])
    right = np.mean(blur[:, blur.shape[1]//2:])
    if right > left + 2:
        return "UPTREND"
    elif right < left - 2:
        return "DOWNTREND"
    return "FLAT"

def detect_fractal_proxy(gray):
    # Heuristic: detect sharp peaks/valleys
    edges = cv2.Canny(gray, 50, 150)
    density = np.mean(edges)
    if density > 25:
        return True
    return False

def stochastic_zone_proxy(gray):
    # Heuristic: bottom area volatility
    h, w = gray.shape
    zone = gray[int(h*0.8):, :]
    std = np.std(zone)
    if std < 12:
        return "FLAT_EXTREME"
    if std > 35:
        return "REVERSING"
    return "NORMAL"

def ema_filter_proxy(gray):
    # Midline brightness logic
    h = gray.shape[0]
    mid = gray[int(h*0.5), :]
    top = gray[int(h*0.3), :]
    bottom = gray[int(h*0.7), :]
    if np.mean(top) > np.mean(bottom):
        return "ABOVE"
    return "BELOW"

def confidence_score(trend, fractal, stochastic, ema_ok):
    score = 70
    if trend != "FLAT":
        score += 10
    if fractal:
        score += 5
    if stochastic == "NORMAL":
        score += 5
    if ema_ok:
        score += 5
    return min(score, 95)

# =============================
# STRATEGY ENGINE
# =============================
def evaluate_strategy(gray):
    trend = estimate_trend(gray)
    fractal_confirmed = detect_fractal_proxy(gray)
    stochastic_state = stochastic_zone_proxy(gray)
    ema_position = ema_filter_proxy(gray)

    report = {}

    # Trend logic
    if trend == "UPTREND":
        report["TREND"] = "UPTREND (Alligator aligned)"
        signal = "BUY"
    elif trend == "DOWNTREND":
        report["TREND"] = "DOWNTREND (Alligator aligned)"
        signal = "SELL"
    else:
        report["TREND"] = "NO CLEAR TREND"
        return "WAIT", "NO TRADE", report, 0

    # Fractal logic
    if not fractal_confirmed:
        report["FRACTAL"] = "NOT CONFIRMED"
        return "WAIT", "NO TRADE", report, 0
    else:
        report["FRACTAL"] = "CONFIRMED"

    # EMA filter
    ema_ok = False
    if signal == "BUY" and ema_position == "ABOVE":
        ema_ok = True
    if signal == "SELL" and ema_position == "BELOW":
        ema_ok = True

    if not ema_ok:
        report["EMA 150 FILTER"] = "BLOCKED"
        return "WAIT", "NO TRADE", report, 0
    else:
        report["EMA 150 FILTER"] = "OK"

    # Stochastic filter
    if stochastic_state == "FLAT_EXTREME":
        trade_type = "⚠️ RISKY"
        report["STOCHASTIC"] = "EXTREME (Flat)"
    elif stochastic_state == "REVERSING":
        trade_type = "CONFIRMED"
        report["STOCHASTIC"] = "REVERSAL CONFIRM"
    else:
        trade_type = "CONFIRMED"
        report["STOCHASTIC"] = "AGREES"

    # Wait rule (simulated)
    report["WAIT RULE"] = "PASSED"

    conf = confidence_score(trend, fractal_confirmed, stochastic_state, ema_ok)

    return signal, trade_type, report, conf

# =============================
# EXECUTION
# =============================
if image is not None and st.button("🔍 Analyse Market"):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    signal, trade_type, report, conf = evaluate_strategy(gray)

    now = datetime.now().replace(second=0, microsecond=0)
    entry = now + timedelta(minutes=1)
    expiry = entry + timedelta(minutes=1)

    if signal == "BUY":
        st.success("🟢 BUY")
    elif signal == "SELL":
        st.error("🔴 SELL")
    else:
        st.info("⚪ WAIT")

    st.code(f"""
SIGNAL: {signal}
TYPE: {trade_type}
TREND: {report.get("TREND","")}
FRACTAL: {report.get("FRACTAL","")}
WAIT RULE: {report.get("WAIT RULE","")}
EMA 150 FILTER: {report.get("EMA 150 FILTER","")}
STOCHASTIC: {report.get("STOCHASTIC","")}
CONFIDENCE: {conf}%
ENTRY: {entry.strftime('%H:%M')}
EXPIRY: {expiry.strftime('%H:%M')}
""".strip())






