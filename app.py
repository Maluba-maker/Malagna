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
st.caption("Malagna – a Pocket-AI style OTC market analysis.")

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
# MARKET PERMISSION (Layer 5 rules)
# =============================
def market_permission(gray):
    h, w = gray.shape

    if np.std(gray[int(h*0.55):int(h*0.75), :]) < 16:
        return False, "Market compressed"

    if abs(np.std(gray[:, :w//3]) - np.std(gray[:, w//3:])) > 20:
        return False, "Volatility transition"

    if np.std(gray[int(h*0.6):int(h*0.75), int(w*0.7):]) > 40:
        return False, "Early candle impulse"

    return True, "Market tradable"

# =============================
# 🔵 25-RULE CORE ENGINE
# =============================
def malagna_decision(structure, sr, candle, trend, gray):
    buy_score = 0
    sell_score = 0
    reasons = []

    # ===== LAYER 1: Candle Truth (Rules 1–5)
    if candle == "IMPULSE":
        buy_score += 2
        sell_score += 2
    elif candle == "REJECTION":
        buy_score += 1
        sell_score += 1

    # ===== LAYER 2: Structure & Location (Rules 6–10)
    if structure == "BULLISH":
        buy_score += 2
    elif structure == "BEARISH":
        sell_score += 2

    if sr["support"]:
        buy_score += 2
    if sr["resistance"]:
        sell_score += 2

    # ===== LAYER 3: Momentum & Trend (Rules 11–15)
    if trend == "UPTREND":
        buy_score += 2
    elif trend == "DOWNTREND":
        sell_score += 2

    # ===== LAYER 4: Liquidity & Manipulation (Rules 16–20)
    manipulation = False
    if candle == "IMPULSE" and sr["resistance"] and structure != "BULLISH":
        manipulation = True
        reasons.append("Upper liquidity sweep")
    if candle == "IMPULSE" and sr["support"] and structure != "BEARISH":
        manipulation = True
        reasons.append("Lower liquidity sweep")

    if manipulation:
        return "WAIT", "Manipulation detected", 0

    # ===== FINAL DECISION (Rules 21–25)
    diff = buy_score - sell_score
    confidence = min(95, abs(diff) * 12)

    if diff >= 3 and confidence >= 80:
        return "BUY", "Multi-layer bullish confluence", confidence
    if diff <= -3 and confidence >= 80:
        return "SELL", "Multi-layer bearish confluence", confidence

    return "WAIT", "No strong confluence", confidence

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
        signal, reason, conf = "WAIT", "Poor market quality", 0
    else:
        allowed, permission_reason = market_permission(gray)

        if not allowed:
            signal, reason, conf = "WAIT", permission_reason, 0
        else:
            structure = detect_market_structure(gray)
            sr = detect_support_resistance(gray)
            candle = analyse_candle_behaviour(gray)
            trend = confirm_trend(gray)

            signal, reason, conf = malagna_decision(
                structure, sr, candle, trend, gray
            )

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









