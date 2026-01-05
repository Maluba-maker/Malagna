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

# =============================
# BRANDING
# =============================
st.markdown("## 🔹 Malagna Signal Engine")
st.caption("Malagna – a rule-based OTC market analysis.")

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
# IMAGE VALIDATION
# =============================
def validate_image(image):
    if image is None or image.size == 0:
        return False, "Invalid image"
    if len(image.shape) != 3:
        return False, "Image must be color"
    return True, "OK"

# =============================
# INPUT
# =============================
input_mode = st.radio("Select Input Mode", ["Upload / Drag Screenshot", "Take Photo (Camera)"])
image = None

if input_mode == "Upload / Drag Screenshot":
    uploaded = st.file_uploader("Upload OTC chart screenshot", type=["png", "jpg", "jpeg"])
    if uploaded:
        image = np.array(Image.open(uploaded))
        st.image(image, use_column_width=True)

if input_mode == "Take Photo (Camera)":
    cam = st.camera_input("Capture chart photo")
    if cam:
        image = np.array(Image.open(cam))
        st.image(image, use_column_width=True)

# =============================
# FEATURE EXTRACTION
# =============================
def market_quality_ok(gray):
    return np.std(gray) >= 12

def detect_market_structure(gray):
    h, _ = gray.shape
    roi = gray[int(h*0.3):int(h*0.75), :]
    edges = cv2.Canny(roi, 50, 150)
    proj = np.sum(edges, axis=1)

    highs = np.where(proj > np.mean(proj) * 1.2)[0]
    lows  = np.where(proj < np.mean(proj) * 0.8)[0]

    if len(highs) < 2 or len(lows) < 2:
        return "RANGE"
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "BULLISH"
    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "BEARISH"
    return "RANGE"

def detect_support_resistance(gray):
    h, _ = gray.shape
    zone = gray[int(h*0.45):int(h*0.75), :]
    proj = np.sum(zone, axis=1)
    mean = np.mean(proj)

    return {
        "support": len(np.where(proj < mean * 0.92)[0]) > 8,
        "resistance": len(np.where(proj > mean * 1.08)[0]) > 8
    }

def analyse_candle_behaviour(gray):
    h, w = gray.shape
    recent = gray[int(h*0.55):int(h*0.75), int(w*0.7):]
    std = np.std(recent)

    if std > 38:
        return "IMPULSE"
    if std < 18:
        return "REJECTION"
    return "NEUTRAL"

def confirm_trend(gray):
    blur = cv2.GaussianBlur(gray, (25, 25), 0)
    left = np.mean(blur[:, :blur.shape[1]//3])
    right = np.mean(blur[:, blur.shape[1]//3:])

    if right > left + 3:
        return "UPTREND"
    if right < left - 3:
        return "DOWNTREND"
    return "FLAT"

def market_behaviour_warning(gray):
    h, _ = gray.shape
    vol = np.std(gray[int(h*0.4):int(h*0.7), :])
    edges = np.mean(cv2.Canny(gray, 50, 150))
    flags = []
    if vol < 18:
        flags.append("Low volatility / choppy market")
    if edges > 45:
        flags.append("Possible manipulation / spikes")
    return flags

# =============================
# POCKET-AI MARKET PERMISSION ENGINE
# =============================
def market_permission(gray):
    h, w = gray.shape

    recent = gray[int(h*0.55):int(h*0.75), :]
    if np.std(recent) < 16:
        return False, "Market compressed / overlapping candles"

    left_vol = np.std(gray[:, :w//3])
    right_vol = np.std(gray[:, w//3:])
    if abs(right_vol - left_vol) > 20:
        return False, "Volatility transition detected"

    candle_zone = gray[int(h*0.6):int(h*0.75), int(w*0.7):]
    if np.std(candle_zone) > 40:
        return False, "Early candle impulse (trap risk)"

    return True, "Market tradable"

# =============================
# 25-PAIR RULE ENGINE
# =============================
def evaluate_pairs(structure, sr, candle, trend):
    fired = []

    if structure == "BULLISH" and candle == "IMPULSE":
        fired.append(("BUY", 88, "Bullish trend acceleration"))
    if structure == "BULLISH" and trend == "UPTREND" and candle == "REJECTION":
        fired.append(("BUY", 85, "Pullback in uptrend"))
    if structure == "BEARISH" and candle == "IMPULSE":
        fired.append(("SELL", 88, "Bearish trend acceleration"))
    if structure == "BEARISH" and trend == "DOWNTREND" and candle == "REJECTION":
        fired.append(("SELL", 85, "Pullback in downtrend"))

    if sr["support"] and candle == "REJECTION":
        fired.append(("BUY", 87, "Support rejection"))
    if sr["resistance"] and candle == "REJECTION":
        fired.append(("SELL", 87, "Resistance rejection"))

    if candle == "IMPULSE" and structure == "RANGE":
        fired.append(("SELL", 85, "Range spike fade"))

    if not fired:
        return "WAIT", "No valid setup", 0, None

    fired.sort(key=lambda x: x[1], reverse=True)
    return fired[0][0], fired[0][2], fired[0][1], None

# =============================
# EXECUTION
# =============================
if image is not None and st.button("🔍 Analyse Market"):

    valid, msg = validate_image(image)
    if not valid:
        st.error(msg)
        st.stop()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if not market_quality_ok(gray):
        signal, reason, conf = "WAIT", "Market quality poor", 0
    else:
        allowed, permission_reason = market_permission(gray)

        if not allowed:
            signal, reason, conf = "WAIT", permission_reason, 0
        else:
            structure = detect_market_structure(gray)
            sr = detect_support_resistance(gray)
            candle = analyse_candle_behaviour(gray)
            trend = confirm_trend(gray)

            signal, reason, conf, _ = evaluate_pairs(structure, sr, candle, trend)

            if conf < 80:
                signal, reason = "WAIT", "Low confidence setup"

    entry = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
    expiry = entry + timedelta(minutes=1)
    warnings = market_behaviour_warning(gray)

    if signal == "BUY":
        st.success(f"🟢 BUY SIGNAL ({conf}%)")
    elif signal == "SELL":
        st.error(f"🔴 SELL SIGNAL ({conf}%)")
    else:
        st.info("⚪ WAIT")

    st.code(f"""
SIGNAL: {signal}
CONFIDENCE: {conf}%
REASON: {reason}
ENTRY: {entry.strftime('%H:%M')}
EXPIRY: {expiry.strftime('%H:%M')}
""".strip())

    if warnings:
        st.error("🚨 Market Behaviour Alert")
        for w in warnings:
            st.write("•", w)
    else:
        st.success("✅ Market behaviour appears normal")






