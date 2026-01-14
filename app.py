import streamlit as st
import cv2
import numpy as np
import time
import hashlib
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
from streamlit_drawable_canvas import st_canvas
from datetime import datetime, timedelta

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Maluz Live Vision", layout="centered")
st.markdown("## 🔹 Maluz Signal Engine (Live)")
st.caption("Auto-capture + Continuous Vision Mode")

# =============================
# PASSWORD GATE
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
        st.text_input("🔐 Enter password", type="password", key="password", on_change=password_entered)
        return False
    elif not st.session_state["authenticated"]:
        st.text_input("🔐 Enter password", type="password", key="password", on_change=password_entered)
        st.error("❌ Incorrect password")
        return False
    return True

if not check_password():
    st.stop()

# =============================
# STATE
# =============================
if "latest_frame" not in st.session_state:
    st.session_state.latest_frame = None
if "roi" not in st.session_state:
    st.session_state.roi = None  # (x1, y1, x2, y2)
if "running" not in st.session_state:
    st.session_state.running = False
if "last_sample" not in st.session_state:
    st.session_state.last_sample = 0
if "signal" not in st.session_state:
    st.session_state.signal = "WAIT"
if "conf" not in st.session_state:
    st.session_state.conf = 0
if "reason" not in st.session_state:
    st.session_state.reason = "—"
if "warnings" not in st.session_state:
    st.session_state.warnings = []

# =============================
# MALUZ FUNCTIONS (UNCHANGED)
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

def evaluate_pairs(structure, sr, candle, trend):
    fired = []

    # A: Trend
    if structure == "BULLISH" and candle == "IMPULSE":
        fired.append(("BUY", 88, "Pair 1: Bullish trend acceleration"))
    if structure == "BULLISH" and trend == "UPTREND" and candle == "REJECTION":
        fired.append(("BUY", 85, "Pair 2: Pullback in uptrend"))
    if structure == "BULLISH" and trend == "UPTREND" and candle == "IMPULSE":
        fired.append(("BUY", 90, "Pair 3: Breakout continuation"))
    if structure == "BEARISH" and candle == "IMPULSE":
        fired.append(("SELL", 88, "Pair 4: Bearish trend acceleration"))
    if structure == "BEARISH" and trend == "DOWNTREND" and candle == "REJECTION":
        fired.append(("SELL", 85, "Pair 5: Pullback in downtrend"))

    # B: SR
    if sr["support"] and candle == "REJECTION":
        fired.append(("BUY", 87, "Pair 6: Support rejection"))
    if sr["resistance"] and candle == "REJECTION":
        fired.append(("SELL", 87, "Pair 7: Resistance rejection"))
    if sr["support"] and candle == "NEUTRAL" and structure == "BEARISH":
        fired.append(("BUY", 90, "Pair 8: Sell exhaustion / double bottom"))
    if sr["resistance"] and candle == "NEUTRAL" and structure == "BULLISH":
        fired.append(("SELL", 90, "Pair 9: Buy exhaustion / double top"))
    if sr["support"] and candle == "IMPULSE":
        fired.append(("BUY", 84, "Pair 10: Support impulse"))

    # C: Mean reversion
    if sr["support"] and candle == "NEUTRAL" and trend == "DOWNTREND":
        fired.append(("BUY", 86, "Pair 11: Mean reversion from lows"))
    if sr["resistance"] and candle == "NEUTRAL" and trend == "UPTREND":
        fired.append(("SELL", 86, "Pair 12: Mean reversion from highs"))
    if sr["support"] and candle == "REJECTION" and structure == "RANGE":
        fired.append(("BUY", 88, "Pair 13: Oversold snapback"))
    if sr["resistance"] and candle == "REJECTION" and structure == "RANGE":
        fired.append(("SELL", 88, "Pair 14: Overbought snapback"))
    if candle == "IMPULSE" and structure == "RANGE":
        fired.append(("BUY", 83, "Pair 15: Volatility release"))

    # D: Momentum + structure
    if candle == "IMPULSE" and structure == "BULLISH" and trend == "UPTREND":
        fired.append(("BUY", 84, "Pair 16: Momentum alignment up"))
    if candle == "IMPULSE" and structure == "BEARISH" and trend == "DOWNTREND":
        fired.append(("SELL", 84, "Pair 17: Momentum alignment down"))
    if sr["support"] and structure == "BULLISH" and candle == "NEUTRAL":
        fired.append(("BUY", 89, "Pair 18: Hidden accumulation"))
    if sr["resistance"] and structure == "BEARISH" and candle == "NEUTRAL":
        fired.append(("SELL", 89, "Pair 19: Distribution"))
    if candle == "REJECTION" and trend in ["UPTREND", "DOWNTREND"]:
        fired.append(("BUY" if trend == "UPTREND" else "SELL", 83, "Pair 20: Second-leg entry"))

    # E: OTC / manipulation
    if sr["support"] and candle == "IMPULSE" and structure != "BEARISH":
        fired.append(("BUY", 92, "Pair 21: Stop-hunt recovery"))
    if sr["resistance"] and candle == "IMPULSE" and structure != "BULLISH":
        fired.append(("SELL", 92, "Pair 22: Stop-hunt rejection"))
    if sr["support"] and candle == "IMPULSE" and trend == "FLAT":
        fired.append(("BUY", 94, "Pair 23: Spring pattern"))
    if sr["resistance"] and candle == "IMPULSE" and trend == "FLAT":
        fired.append(("SELL", 94, "Pair 24: Upthrust pattern"))
    if candle == "IMPULSE" and structure == "RANGE":
        fired.append(("SELL", 85, "Pair 25: Wick spike fade"))

    if not fired:
        return "WAIT", "No valid pair alignment", 0, None

    fired.sort(key=lambda x: x[1], reverse=True)
    top = fired[0]

    opposing = None
    for f in fired[1:]:
        if f[0] != top[0]:
            opposing = f
            break

    if opposing:
        return (
            top[0],
            f"{top[2]} ⚠️ Conflict with {opposing[0]} ({opposing[1]}%)",
            top[1],
            opposing[1]
        )

    return top[0], top[2], top[1], None

# =============================
# WEBRTC CAPTURE
# =============================
class VisionProcessor(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        st.session_state.latest_frame = img
        return img

st.subheader("Live Capture (Share the Pocket Option TAB)")

webrtc_streamer(
    key="maluz-live",
    video_transformer_factory=VisionProcessor,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# =============================
# ROI SELECTOR (DRAG BOX)
# =============================
st.subheader("Select Chart Region (Draw a box once)")

if st.session_state.latest_frame is not None:
    img = cv2.cvtColor(st.session_state.latest_frame, cv2.COLOR_BGR2RGB)
    canvas_result = st_canvas(
        fill_color="rgba(0, 0, 0, 0)",
        stroke_width=2,
        stroke_color="#00FF00",
        background_image=Image.fromarray(img),
        update_streamlit=True,
        height=img.shape[0]//2,
        width=img.shape[1]//2,
        drawing_mode="rect",
        key="canvas",
    )

    if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
        rect = canvas_result.json_data["objects"][-1]
        x1 = int(rect["left"])
        y1 = int(rect["top"])
        x2 = int(x1 + rect["width"])
        y2 = int(y1 + rect["height"])
        st.session_state.roi = (x1, y1, x2, y2)
        st.success("ROI set. Live analysis will use this region.")

# =============================
# CONTROLS
# =============================
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("▶ Start"):
        st.session_state.running = True
with col2:
    if st.button("⏸ Pause"):
        st.session_state.running = False
with col3:
    if st.button("🔄 Reset"):
        st.session_state.running = False
        st.session_state.signal = "WAIT"
        st.session_state.conf = 0
        st.session_state.reason = "—"
        st.session_state.warnings = []

# =============================
# CONTINUOUS ANALYSIS (2s)
# =============================
st.subheader("Live Signal")

if st.session_state.running and st.session_state.latest_frame is not None and st.session_state.roi is not None:
    now = time.time()
    if now - st.session_state.last_sample >= 2:
        st.session_state.last_sample = now

        frame = st.session_state.latest_frame
        x1, y1, x2, y2 = st.session_state.roi
        crop = frame[y1:y2, x1:x2]

        if crop.size > 0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

            if not market_quality_ok(gray):
                signal, reason, conf, _ = "WAIT", "Market quality poor", 0, None
            else:
                structure = detect_market_structure(gray)
                sr = detect_support_resistance(gray)
                candle = analyse_candle_behaviour(gray)
                trend = confirm_trend(gray)

                signal, reason, conf, _ = evaluate_pairs(structure, sr, candle, trend)

            warnings = market_behaviour_warning(gray)

            st.session_state.signal = signal
            st.session_state.conf = conf
            st.session_state.reason = reason
            st.session_state.warnings = warnings

# =============================
# DISPLAY
# =============================
if st.session_state.signal == "BUY":
    st.success(f"🟢 BUY ({st.session_state.conf}%)")
elif st.session_state.signal == "SELL":
    st.error(f"🔴 SELL ({st.session_state.conf}%)")
else:
    st.info("⚪ WAIT")

st.code(f"""
SIGNAL: {st.session_state.signal}
CONFIDENCE: {st.session_state.conf}%
REASON: {st.session_state.reason}
""".strip())

if st.session_state.warnings:
    st.warning("⚠ Market Alerts")
    for w in st.session_state.warnings:
        st.write("•", w)










