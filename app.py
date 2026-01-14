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
st.caption("Malagna – a safety-based OTC market analysis.")

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
# OTC SAFE LOGIC ENGINE
# =============================
def evaluate_pairs(structure, sr, candle, trend, warnings):
    if warnings:
        return "WAIT", "Market instability detected", 0, None

    if structure != "RANGE" and trend != "FLAT":
        return "WAIT", "Market not in safe ranging condition", 0, None

    # BUY logic
    if (
        sr["support"]
        and candle == "REJECTION"
        and trend in ["FLAT", "UPTREND"]
    ):
        return "BUY", "Support rejection in ranging market", 87, None

    # SELL logic
    if (
        sr["resistance"]
        and candle == "REJECTION"
        and trend in ["FLAT", "DOWNTREND"]
    ):
        return "SELL", "Resistance rejection in ranging market", 87, None

    return "WAIT", "No high-probability OTC setup", 0, None

# =============================
# EXECUTION
# =============================
if image is not None and st.button("🔍 Analyse Market"):

    valid, msg = validate_image(image)
    if not valid:
        st.error(msg)
        st.stop()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    warnings = market_behaviour_warning(gray)

    if not market_quality_ok(gray):
        signal, reason, conf, opposing_conf = "WAIT", "Market quality poor", 0, None
    else:
        structure = detect_market_structure(gray)
        sr = detect_support_resistance(gray)
        candle = analyse_candle_behaviour(gray)
        trend = confirm_trend(gray)

        signal, reason, conf, opposing_conf = evaluate_pairs(
            structure, sr, candle, trend, warnings
        )

    entry = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
    expiry = entry + timedelta(minutes=1)

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




