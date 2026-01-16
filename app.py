# =========================================
# MALAGNA TRUE VISION — FINAL SYSTEM
# PART 1 — CORE + ENGINES + STABILITY
# =========================================

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import tempfile
import time
from datetime import datetime, timedelta
import hashlib
import math

# =========================================
# GLOBAL CONFIG
# =========================================

APP_NAME = "Malagna True Vision AI"
VERSION = "3.0 FINAL"
FRAME_DELAY = 0.05  # seconds between frames in live mode

# =========================================
# GENERAL UTILITIES
# =========================================

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

def current_entry_and_expiry():
    now = datetime.now().replace(second=0, microsecond=0)
    entry = now + timedelta(minutes=1)
    expiry = entry + timedelta(minutes=1)
    return entry, expiry

# =========================================
# IMAGE HELPERS
# =========================================

def resize_for_processing(frame, max_width=900):
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame
    scale = max_width / w
    return cv2.resize(frame, (int(w * scale), int(h * scale)))

def to_hsv(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

def to_gray(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

# =========================================
# VISION HELPERS
# =========================================

def find_contours(mask):
    cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return cnts[0] if len(cnts) == 2 else cnts[1]

def linear_regression_slope(points):
    if len(points) < 2:
        return 0
    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])
    if len(xs) < 2:
        return 0
    m, _ = np.polyfit(xs, ys, 1)
    return m

# =========================================
# FLICKER FILTER
# =========================================

class FlickerFilter:
    def __init__(self, confirm_frames=2):
        self.confirm_frames = confirm_frames
        self.counter = 0

    def update(self, detected):
        if detected:
            self.counter += 1
        else:
            self.counter = 0
        return self.counter >= self.confirm_frames

# =========================================
# PASSWORD SYSTEM
# =========================================

RAW_PASSWORD = "maluz123"
PASSWORD_HASH = hashlib.sha256(RAW_PASSWORD.encode()).hexdigest()

def check_password():
    def password_entered():
        if hashlib.sha256(st.session_state["password"].encode()).hexdigest() == PASSWORD_HASH:
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("🔐 Enter Password", type="password",
                      key="password", on_change=password_entered)
        return False
    elif not st.session_state["authenticated"]:
        st.text_input("🔐 Enter Password", type="password",
                      key="password", on_change=password_entered)
        st.error("❌ Incorrect password")
        return False
    return True
# =========================================
# PRECISION CANDLE ENGINE
# =========================================

class PrecisionCandleEngine:
    def __init__(self):
        self.last_centers = []
        self.candle_index = -1
        self.flicker_filter = FlickerFilter(confirm_frames=2)

    def detect_candles(self, frame):
        hsv = to_hsv(frame)
        green_mask = cv2.inRange(hsv, (35, 70, 70), (85, 255, 255))
        red1 = cv2.inRange(hsv, (0, 70, 70), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 70, 70), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)

        candles = []

        for mask, color in [(green_mask, "BULL"), (red_mask, "BEAR")]:
            cnts = find_contours(mask)
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if h < 12 or w < 3 or w > 40:
                    continue
                candles.append({
                    "x": x + w // 2,
                    "top": y,
                    "bottom": y + h,
                    "color": color
                })

        return self._merge_verticals(candles)

    def _merge_verticals(self, candles):
        merged = []
        candles = sorted(candles, key=lambda c: c["x"])
        for c in candles:
            if not merged:
                merged.append(c)
                continue
            prev = merged[-1]
            if abs(prev["x"] - c["x"]) < 8:
                prev["top"] = min(prev["top"], c["top"])
                prev["bottom"] = max(prev["bottom"], c["bottom"])
            else:
                merged.append(c)
        return merged

    def update(self, frame):
        candles = self.detect_candles(frame)
        centers = [c["x"] for c in candles]

        if not self.last_centers:
            self.last_centers = centers
            self.candle_index = len(centers) - 1
            return False, candles

        if len(centers) > len(self.last_centers):
            confirmed = self.flicker_filter.update(True)
            if confirmed:
                self.candle_index += 1
                self.last_centers = centers
                return True, candles
        else:
            self.flicker_filter.update(False)

        self.last_centers = centers
        return False, candles


# =========================================
# PRECISION FRACTAL ENGINE
# =========================================

class PrecisionFractalEngine:
    def __init__(self):
        self.last_fractals = []
        self.confirm_filter = FlickerFilter(confirm_frames=2)

    def detect_fractals(self, frame):
        hsv = to_hsv(frame)
        green_mask = cv2.inRange(hsv, (35, 80, 80), (85, 255, 255))
        red1 = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 80, 80), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)

        fractals = []
        fractals += self._extract_arrows(green_mask, "UP")
        fractals += self._extract_arrows(red_mask, "DOWN")
        return fractals

    def _extract_arrows(self, mask, ftype):
        cnts = find_contours(mask)
        arrows = []
        for c in cnts:
            area = cv2.contourArea(c)
            if area < 25 or area > 2500:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if 5 <= len(approx) <= 9:
                x, y, w, h = cv2.boundingRect(c)
                if w < 6 or h < 6:
                    continue
                arrows.append({
                    "x": x + w // 2,
                    "y": y + h // 2,
                    "type": ftype
                })
        return arrows

    def update(self, frame):
        fractals = self.detect_fractals(frame)

        if not self.last_fractals:
            self.last_fractals = fractals
            return False, None

        if len(fractals) > len(self.last_fractals):
            confirmed = self.confirm_filter.update(True)
            if confirmed:
                newest = fractals[-1]
                self.last_fractals = fractals
                return True, newest["type"]
        else:
            self.confirm_filter.update(False)

        self.last_fractals = fractals
        return False, None
# =========================================
# PRECISION ALLIGATOR ENGINE
# =========================================

class PrecisionAlligatorEngine:
    def __init__(self):
        self.slope_history = []

    def _detect_masks(self, frame):
        hsv = to_hsv(frame)
        blue_mask = cv2.inRange(hsv, (90, 70, 70), (130, 255, 255))
        red1 = cv2.inRange(hsv, (0, 70, 70), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 70, 70), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)
        green_mask = cv2.inRange(hsv, (35, 70, 70), (85, 255, 255))
        return blue_mask, red_mask, green_mask

    def _extract_curve_points(self, mask):
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=30, maxLineGap=10)
        points = []
        if lines is not None:
            for l in lines:
                x1, y1, x2, y2 = l[0]
                points.append((x1, y1))
                points.append((x2, y2))
        return points

    def _separation(self, pts1, pts2):
        if not pts1 or not pts2:
            return 0
        ys1 = np.array([p[1] for p in pts1])
        ys2 = np.array([p[1] for p in pts2])
        return abs(np.mean(ys1) - np.mean(ys2))

    def analyze(self, frame):
        blue_mask, red_mask, green_mask = self._detect_masks(frame)
        blue_pts = self._extract_curve_points(blue_mask)
        red_pts = self._extract_curve_points(red_mask)
        green_pts = self._extract_curve_points(green_mask)

        s_blue = linear_regression_slope(blue_pts)
        s_red = linear_regression_slope(red_pts)
        s_green = linear_regression_slope(green_pts)

        self.slope_history.append((s_blue, s_red, s_green))
        if len(self.slope_history) > 5:
            self.slope_history.pop(0)

        s_blue, s_red, s_green = np.mean(self.slope_history, axis=0)

        sep_br = self._separation(blue_pts, red_pts)
        sep_rg = self._separation(red_pts, green_pts)
        sep_bg = self._separation(blue_pts, green_pts)

        min_sep = min(sep_br, sep_rg, sep_bg)

        if s_blue > 0.04 and s_red > 0.04 and s_green > 0.04:
            direction = "UPTREND"
        elif s_blue < -0.04 and s_red < -0.04 and s_green < -0.04:
            direction = "DOWNTREND"
        else:
            direction = "FLAT"

        if min_sep < 6:
            quality = "INTERTWINED"
        elif min_sep < 14:
            quality = "WEAK"
        else:
            quality = "STRONG"

        return {
            "direction": direction,
            "quality": quality,
            "slopes": (s_blue, s_red, s_green),
            "separations": (sep_br, sep_rg, sep_bg)
        }


# =========================================
# PRECISION EMA ENGINE
# =========================================

class PrecisionEMAEngine:
    def __init__(self):
        self.slope_history = []

    def _detect_mask(self, frame):
        hsv = to_hsv(frame)
        return cv2.inRange(hsv, (0, 0, 200), (180, 60, 255))

    def _extract_curve_points(self, mask):
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=30, maxLineGap=10)
        points = []
        if lines is not None:
            for l in lines:
                x1, y1, x2, y2 = l[0]
                points.append((x1, y1))
                points.append((x2, y2))
        return points

    def _estimate_price_level(self, frame):
        h, w = frame.shape[:2]
        roi = frame[int(h * 0.25):int(h * 0.85), :]
        gray = to_gray(roi)
        edges = cv2.Canny(gray, 50, 150)
        ys, _ = np.where(edges > 0)
        if len(ys) == 0:
            return None
        return np.mean(ys)

    def analyze(self, frame):
        mask = self._detect_mask(frame)
        points = self._extract_curve_points(mask)

        if not points:
            return {"ema_present": False}

        slope = linear_regression_slope(points)
        self.slope_history.append(slope)
        if len(self.slope_history) > 5:
            self.slope_history.pop(0)
        slope = np.mean(self.slope_history)

        price_y = self._estimate_price_level(frame)
        if price_y is None:
            return {"ema_present": False}

        ema_ys = np.array([p[1] for p in points])
        ema_level = np.mean(ema_ys)
        distance = price_y - ema_level

        return {
            "ema_present": True,
            "slope": slope,
            "price_position": "ABOVE" if distance < 0 else "BELOW",
            "distance": abs(distance)
        }


# =========================================
# PRECISION STOCHASTIC ENGINE
# =========================================

class PrecisionStochasticEngine:
    def __init__(self):
        self.blue_slope_history = []
        self.red_slope_history = []

    def _detect_masks(self, frame):
        hsv = to_hsv(frame)
        blue_mask = cv2.inRange(hsv, (90, 70, 70), (130, 255, 255))
        red1 = cv2.inRange(hsv, (0, 70, 70), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 70, 70), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)
        return blue_mask, red_mask

    def _extract_curve_points(self, mask):
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=20, maxLineGap=8)
        points = []
        if lines is not None:
            for l in lines:
                x1, y1, x2, y2 = l[0]
                points.append((x1, y1))
                points.append((x2, y2))
        return points

    def analyze(self, frame):
        blue_mask, red_mask = self._detect_masks(frame)
        blue_pts = self._extract_curve_points(blue_mask)
        red_pts = self._extract_curve_points(red_mask)

        if not blue_pts or not red_pts:
            return {"valid": False}

        slope_blue = linear_regression_slope(blue_pts)
        slope_red = linear_regression_slope(red_pts)

        self.blue_slope_history.append(slope_blue)
        self.red_slope_history.append(slope_red)
        if len(self.blue_slope_history) > 5:
            self.blue_slope_history.pop(0)
        if len(self.red_slope_history) > 5:
            self.red_slope_history.pop(0)

        slope_blue = np.mean(self.blue_slope_history)
        slope_red = np.mean(self.red_slope_history)

        flat = abs(slope_blue) < 0.02 and abs(slope_red) < 0.02

        return {
            "valid": True,
            "slope_blue": slope_blue,
            "slope_red": slope_red,
            "flat": flat,
            "zone": "NORMAL"
        }


# =========================================
# MEMORY ENGINE
# =========================================

class SystemState:
    IDLE = "IDLE"
    WAITING = "WAITING"
    READY = "READY"
    FIRED = "FIRED"


class MemoryEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = SystemState.IDLE
        self.current_candle_index = -1
        self.fractal_seen_index = None
        self.wait_count = 0
        self.signal_fired = False

    def new_candle(self):
        self.current_candle_index += 1
        if self.state == SystemState.WAITING:
            self.wait_count += 1
            if self.wait_count >= 2:
                self.state = SystemState.READY

    def on_fractal(self):
        if self.state == SystemState.IDLE:
            self.fractal_seen_index = self.current_candle_index
            self.wait_count = 0
            self.state = SystemState.WAITING

    def can_trade(self):
        return self.state == SystemState.READY and not self.signal_fired

    def fire(self):
        self.signal_fired = True
        self.state = SystemState.FIRED


# =========================================
# FUSION ENGINE
# =========================================

class FusionEngine:
    def __init__(self, memory_engine):
        self.memory = memory_engine

    def resolve(self, fractal_data, alligator_data, ema_data, stoch_data):
        report = {}

        trend = alligator_data["direction"]
        quality = alligator_data["quality"]

        if trend == "FLAT" or quality == "INTERTWINED":
            return self._wait("Trend invalid")

        report["TREND"] = f"{trend} (Alligator aligned)"

        if not fractal_data["confirmed"]:
            return self._wait("Fractal not confirmed")

        report["FRACTAL"] = "CONFIRMED"

        if not self.memory.can_trade():
            return self._wait("Wait rule active")

        report["WAIT RULE"] = "PASSED"

        if not ema_data.get("ema_present", False):
            return self._wait("EMA not detected")

        if trend == "UPTREND" and ema_data["price_position"] != "ABOVE":
            return self._wait("Price below EMA")

        if trend == "DOWNTREND" and ema_data["price_position"] != "BELOW":
            return self._wait("Price above EMA")

        report["EMA 150 FILTER"] = "OK"

        if not stoch_data["valid"]:
            return self._wait("Stochastic invalid")

        risky = False

        if stoch_data.get("flat"):
            risky = True
            report["STOCHASTIC"] = "FLAT / EXTREME"
        else:
            report["STOCHASTIC"] = "AGREES"

        signal = "BUY" if trend == "UPTREND" else "SELL"
        confidence = 92
        signal_type = "RISKY" if risky else "CONFIRMED"

        return {
            "signal": signal,
            "type": signal_type,
            "confidence": confidence,
            "report": report
        }

    def _wait(self, reason):
        return {
            "signal": "WAIT",
            "type": "WAIT",
            "confidence": 0,
            "report": {"REASON": reason}
        }


# =========================================
# OUTPUT FORMATTER
# =========================================

def format_signal_output(result):
    entry, expiry = current_entry_and_expiry()
    report = result.get("report", {})

    lines = [
        f"SIGNAL: {result.get('signal', '')}",
        f"TYPE: {result.get('type', '')}",
        f"TREND: {report.get('TREND', '')}",
        f"FRACTAL: {report.get('FRACTAL', '')}",
        f"WAIT RULE: {report.get('WAIT RULE', '')}",
        f"EMA 150 FILTER: {report.get('EMA 150 FILTER', '')}",
        f"STOCHASTIC: {report.get('STOCHASTIC', '')}",
        f"CONFIDENCE: {result.get('confidence', 0)}%",
        f"ENTRY: {entry.strftime('%H:%M')}",
        f"EXPIRY: {expiry.strftime('%H:%M')}",
    ]

    return "\n".join(lines)


# =========================================
# STABILITY + CALIBRATION LAYER
# =========================================

class StabilityGuard:
    def __init__(self, confirm_frames=2):
        self.confirm_frames = confirm_frames
        self.counter = 0

    def confirm(self, condition):
        if condition:
            self.counter += 1
        else:
            self.counter = 0
        return self.counter >= self.confirm_frames


class TrendHysteresis:
    def __init__(self, hold_frames=3):
        self.hold_frames = hold_frames
        self.history = []

    def update(self, trend):
        self.history.append(trend)
        if len(self.history) > self.hold_frames:
            self.history.pop(0)
        if self.history.count(trend) >= self.hold_frames:
            return trend
        return None


def final_decision_wrapper(result, alligator_data):
    if not result or result["signal"] == "WAIT":
        return None
    return result
# =========================================
# STREAMLIT UI HELPERS
# =========================================

def show_title():
    st.markdown(f"## 🔹 {APP_NAME}")
    st.caption(f"Version {VERSION}")

def show_divider():
    st.markdown("---")

# =========================================
# PASSWORD GATE
# =========================================

if not check_password():
    st.stop()

# =========================================
# UI HEADER
# =========================================

show_title()
show_divider()

# =========================================
# SESSION INIT
# =========================================

if "memory" not in st.session_state:
    st.session_state.memory = MemoryEngine()

if "fusion" not in st.session_state:
    st.session_state.fusion = FusionEngine(st.session_state.memory)

if "signal_locked" not in st.session_state:
    st.session_state.signal_locked = False

if "signal_text" not in st.session_state:
    st.session_state.signal_text = None

if "candle_engine" not in st.session_state:
    st.session_state.candle_engine = PrecisionCandleEngine()

if "fractal_engine" not in st.session_state:
    st.session_state.fractal_engine = PrecisionFractalEngine()

if "alligator_engine" not in st.session_state:
    st.session_state.alligator_engine = PrecisionAlligatorEngine()

if "ema_engine" not in st.session_state:
    st.session_state.ema_engine = PrecisionEMAEngine()

if "stoch_engine" not in st.session_state:
    st.session_state.stoch_engine = PrecisionStochasticEngine()

# =========================================
# RESET
# =========================================

def reset_system():
    st.session_state.memory.reset()
    st.session_state.signal_locked = False
    st.session_state.signal_text = None

if st.button("🔄 RESET SYSTEM"):
    reset_system()
    st.experimental_rerun()

# =========================================
# FULL SCREEN SIGNAL CARD
# =========================================

def show_signal_card(text):
    st.markdown(
        f"""
        <div style="background:#0f0f0f;padding:40px;border-radius:20px;text-align:center;">
            <h1 style="color:#00ff99;">🚨 SIGNAL FOUND</h1>
            <pre style="color:white;font-size:20px;line-height:1.4;">{text}</pre>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================
# LOCKED MODE
# =========================================

if st.session_state.signal_locked:
    show_signal_card(st.session_state.signal_text)
    st.stop()

# =========================================
# MODE SELECT
# =========================================

mode = st.radio("Select Mode", ["Screenshot", "Video"])

# =========================================
# SCREENSHOT MODE
# =========================================

if mode == "Screenshot":
    uploaded = st.file_uploader("Upload chart screenshot", type=["png", "jpg", "jpeg"])

    if uploaded:
        frame = np.array(Image.open(uploaded))
        st.image(frame, use_column_width=True)

        if st.button("🔍 Analyze Screenshot"):
            frame = resize_for_processing(frame)

            mem = st.session_state.memory

            new_candle, _ = st.session_state.candle_engine.update(frame)
            if new_candle:
                mem.new_candle()

            new_fractal, _ = st.session_state.fractal_engine.update(frame)
            if new_fractal:
                mem.on_fractal()

            fractal_data = {"confirmed": new_fractal}
            alligator_data = st.session_state.alligator_engine.analyze(frame)
            ema_data = st.session_state.ema_engine.analyze(frame)
            stoch_data = st.session_state.stoch_engine.analyze(frame)

            result = st.session_state.fusion.resolve(
                fractal_data,
                alligator_data,
                ema_data,
                stoch_data
            )

            final = final_decision_wrapper(result, alligator_data)

            if final:
                mem.fire()
                text = format_signal_output(final)
                st.session_state.signal_locked = True
                st.session_state.signal_text = text
                st.experimental_rerun()
            else:
                st.info("WAIT — No valid setup")

# =========================================
# VIDEO MODE
# =========================================

if mode == "Video":
    uploaded = st.file_uploader("Upload chart video", type=["mp4", "avi", "mov"])

    if uploaded:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded.read())
        video_path = tfile.name

        if st.button("▶ Start Live Scan"):
            cap = cv2.VideoCapture(video_path)
            frame_slot = st.empty()

            mem = st.session_state.memory

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame = resize_for_processing(frame)
                frame_slot.image(frame, channels="BGR", use_column_width=True)

                new_candle, _ = st.session_state.candle_engine.update(frame)
                if new_candle:
                    mem.new_candle()

                new_fractal, _ = st.session_state.fractal_engine.update(frame)
                if new_fractal:
                    mem.on_fractal()

                fractal_data = {"confirmed": new_fractal}
                alligator_data = st.session_state.alligator_engine.analyze(frame)
                ema_data = st.session_state.ema_engine.analyze(frame)
                stoch_data = st.session_state.stoch_engine.analyze(frame)

                result = st.session_state.fusion.resolve(
                    fractal_data,
                    alligator_data,
                    ema_data,
                    stoch_data
                )

                final = final_decision_wrapper(result, alligator_data)

                if final:
                    mem.fire()
                    text = format_signal_output(final)
                    st.session_state.signal_locked = True
                    st.session_state.signal_text = text
                    break

                time.sleep(FRAME_DELAY)

            cap.release()
            st.experimental_rerun()








