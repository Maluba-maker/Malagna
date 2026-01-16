# =========================================
# MALAGNA TRUE VISION — FINAL PRODUCTION SYSTEM
# PART 1 — CORE + ENGINES + MEMORY + STABILITY
# =========================================

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import tempfile
import time
from datetime import datetime, timedelta
import hashlib

# =========================================
# GLOBAL CONFIG
# =========================================

APP_NAME = "Malagna True Vision AI"
VERSION = "3.0 FINAL"
FRAME_DELAY = 0.05

# =========================================
# UTILITIES
# =========================================

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

def current_entry_and_expiry():
    now = datetime.now().replace(second=0, microsecond=0)
    entry = now + timedelta(minutes=1)
    expiry = entry + timedelta(minutes=1)
    return entry, expiry

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
# PRECISION CANDLE ENGINE (SYNCED)
# =========================================

class PrecisionCandleEngine:
    def __init__(self):
        self.last_count = 0
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

        candles = self._merge_verticals(candles)

        # Sort left to right = time order
        candles = sorted(candles, key=lambda c: c["x"])

        return candles

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
        count = len(candles)

        if self.last_count == 0:
            self.last_count = count
            return False, candles, self.candle_index

        if count > self.last_count:
            confirmed = self.flicker_filter.update(True)
            if confirmed:
                self.candle_index += 1
                self.last_count = count
                return True, candles, self.candle_index
        else:
            self.flicker_filter.update(False)

        self.last_count = count
        return False, candles, self.candle_index

# =========================================
# AUTO FRACTAL DETECTION ENGINE (PATCH 1)
# =========================================

class PrecisionFractalEngine:
    def __init__(self):
        self.candles = []
        self.last_confirmed_index = None
        self.fractal_index = None

    def update(self, candle, index):
        self.candles.append(candle)

        if len(self.candles) < 5:
            return False, None, None

        i = len(self.candles) - 3

        if self.last_confirmed_index == i:
            return False, None, None

        c0 = self.candles[i - 2]
        c1 = self.candles[i - 1]
        c2 = self.candles[i]
        c3 = self.candles[i + 1]
        c4 = self.candles[i + 2]

        if (
            c2["top"] < c1["top"] and
            c2["top"] < c0["top"] and
            c2["top"] < c3["top"] and
            c2["top"] < c4["top"]
        ):
            self.last_confirmed_index = i
            self.fractal_index = index
            return True, "UP", index

        if (
            c2["bottom"] > c1["bottom"] and
            c2["bottom"] > c0["bottom"] and
            c2["bottom"] > c3["bottom"] and
            c2["bottom"] > c4["bottom"]
        ):
            self.last_confirmed_index = i
            self.fractal_index = index
            return True, "DOWN", index

        return False, None, None

# =========================================
# PRECISION ALLIGATOR ENGINE
# =========================================

class PrecisionAlligatorEngine:
    def __init__(self):
        self.slope_history = []

    def _detect_masks(self, frame):
        hsv = to_hsv(frame)

        # Blue line (Jaws)
        blue_mask = cv2.inRange(hsv, (90, 70, 70), (130, 255, 255))

        # Red line (Teeth)
        red1 = cv2.inRange(hsv, (0, 70, 70), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 70, 70), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)

        # Green line (Lips)
        green_mask = cv2.inRange(hsv, (35, 70, 70), (85, 255, 255))

        return blue_mask, red_mask, green_mask

    def _extract_curve_points(self, mask):
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=60, minLineLength=30, maxLineGap=10
        )
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

        if not blue_pts or not red_pts or not green_pts:
            return {"direction": "FLAT", "quality": "INVALID"}

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

        # Intertwined / touching logic
        if min_sep < 8:
            return {"direction": "FLAT", "quality": "INTERTWINED"}

        # Zigzag / flat slope logic
        if not (abs(s_blue) > 0.03 and abs(s_red) > 0.03 and abs(s_green) > 0.03):
            return {"direction": "FLAT", "quality": "ZIGZAG"}

        # Direction
        if s_blue > 0 and s_red > 0 and s_green > 0:
            direction = "UPTREND"
        elif s_blue < 0 and s_red < 0 and s_green < 0:
            direction = "DOWNTREND"
        else:
            direction = "FLAT"

        return {
            "direction": direction,
            "quality": "STRONG",
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
        # White-ish / light color detection for EMA line
        return cv2.inRange(hsv, (0, 0, 200), (180, 60, 255))

    def _extract_curve_points(self, mask):
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=60, minLineLength=30, maxLineGap=10
        )
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

        position = "ABOVE" if distance < 0 else "BELOW"

        return {
            "ema_present": True,
            "slope": slope,
            "price_position": position,
            "distance": abs(distance),
            "allowed_direction": "BUY" if position == "ABOVE" else "SELL"
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
        # Blue line
        blue_mask = cv2.inRange(hsv, (90, 70, 70), (130, 255, 255))
        # Red line
        red1 = cv2.inRange(hsv, (0, 70, 70), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 70, 70), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)
        return blue_mask, red_mask

    def _extract_curve_points(self, mask):
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=50, minLineLength=20, maxLineGap=8
        )
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
            "flat": flat
        }

# =========================================
# SYSTEM STATE
# =========================================

class SystemState:
    IDLE = "IDLE"
    WAITING = "WAITING"
    READY = "READY"
    FIRED = "FIRED"

# =========================================
# MEMORY ENGINE
# =========================================

class MemoryEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = SystemState.IDLE
        self.current_candle_index = -1
        self.fractal_index = None
        self.signal_fired = False
        self.fractal_type = None

    def new_candle(self, index):
        self.current_candle_index = index

        if self.state == SystemState.WAITING:
            if self.current_candle_index - self.fractal_index >= 2:
                self.state = SystemState.READY

    def on_fractal(self, ftype, index):
        if self.state == SystemState.IDLE:
            self.fractal_index = index
            self.fractal_type = ftype
            self.state = SystemState.WAITING

    def candles_since_fractal(self):
        if self.fractal_index is None:
            return None
        return self.current_candle_index - self.fractal_index

    def can_trade(self):
        return self.state == SystemState.READY and not self.signal_fired

    def fire(self):
        self.signal_fired = True
        self.state = SystemState.FIRED

        # ---------------------------
        # 1️⃣ FRACTAL GATEKEEPER
        # ---------------------------
        if not fractal_data["confirmed"]:
            return self._wait("No confirmed fractal")

        report["FRACTAL"] = fractal_data["type"]

        # ---------------------------
        # 2️⃣ TIMING RULE (2 candles after fractal)
        # ---------------------------
        if not self.memory.can_trade():
            return self._wait("Waiting for 2-candle confirmation")

        report["WAIT RULE"] = "PASSED"

        # ---------------------------
        # 3️⃣ TREND FILTER
        # ---------------------------
        trend = alligator_data["direction"]
        quality = alligator_data["quality"]

        if trend == "FLAT":
            return self._wait("No clear trend")

        if quality in ["INTERTWINED", "ZIGZAG", "INVALID"]:
            return self._wait("Alligator not clean")

        report["TREND"] = trend

        # ---------------------------
        # 4️⃣ EMA FILTER
        # ---------------------------
        if not ema_data.get("ema_present", False):
            return self._wait("EMA not detected")

        allowed = ema_data["allowed_direction"]

        if trend == "UPTREND" and allowed != "BUY":
            return self._wait("EMA blocks BUY")

        if trend == "DOWNTREND" and allowed != "SELL":
            return self._wait("EMA blocks SELL")

        report["EMA 150 FILTER"] = "PASSED"

        # ---------------------------
        # 5️⃣ STOCHASTIC FILTER
        # ---------------------------
        if not stoch_data["valid"]:
            return self._wait("Stochastic invalid")

        risky = False

        # Contradiction logic
        if trend == "UPTREND" and stoch_data["slope_blue"] < 0 and stoch_data["slope_red"] < 0:
            return self._wait("Stochastic contradicts trend")

        if trend == "DOWNTREND" and stoch_data["slope_blue"] > 0 and stoch_data["slope_red"] > 0:
            return self._wait("Stochastic contradicts trend")

        # Flat zone = risky
        if stoch_data["flat"]:
            risky = True
            report["STOCHASTIC"] = "FLAT → RISKY"
        else:
            report["STOCHASTIC"] = "CONFIRMS"

        # ---------------------------
        # 6️⃣ FINAL DECISION
        # ---------------------------
        signal = "BUY" if trend == "UPTREND" else "SELL"
        signal_type = "RISKY" if risky else "CONFIRMED"
        confidence = 92 if not risky else 78

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
# STREAMLIT UI HELPERS
# =========================================

def draw_candle_labels(frame, candles, fractal_index=None):
    overlay = frame.copy()

    for i, c in enumerate(candles):
        x = int(c["x"])
        y = int(c["top"] - 10)

        label = f"C{i+1}"
        color = (255, 255, 255)  # white

        if fractal_index is not None:
            if i == fractal_index:
                label = "FRACTAL"
                color = (0, 255, 255)  # yellow
            elif i == fractal_index + 1:
                label = "C+1"
                color = (255, 255, 0)
            elif i == fractal_index + 2:
                label = "C+2"
                color = (255, 200, 0)
            elif i > fractal_index + 2:
                label = "ENTRY"
                color = (0, 255, 0)

        cv2.putText(
            overlay,
            label,
            (x - 20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            color,
            1,
            cv2.LINE_AA
        )
    return overlay
def draw_decision_banner(frame, text, color=(0, 255, 0)):
    banner = frame.copy()
    h, w = banner.shape[:2]

    cv2.rectangle(banner, (0, 0), (w, 40), (0, 0, 0), -1)
    cv2.putText(
        banner,
        text,
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA
    )

    return banner
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
# SCREENSHOT MODE (PATCH 6 — FULL)
# =========================================

if mode == "Screenshot":
    uploaded = st.file_uploader("Upload chart screenshot", type=["png", "jpg", "jpeg"])

    if uploaded:
        frame = np.array(Image.open(uploaded))
        frame = resize_for_processing(frame)

        mem = st.session_state.memory

        # Candle tracking
        new_candle, candles = st.session_state.candle_engine.update(frame)
        if new_candle:
            mem.new_candle()

            latest = candles[-1]
            candle_data = {
                "top": latest["top"],
                "bottom": latest["bottom"]
            }

            new_fractal, ftype = st.session_state.fractal_engine.update(candle_data)
            if new_fractal:
                mem.on_fractal(ftype)
        else:
            new_fractal = False

        # Label overlay
        fractal_idx = mem.fractal_index
        overlay = draw_candle_labels(frame, candles, fractal_idx)

        fractal_data = {
            "confirmed": new_fractal,
            "type": mem.fractal_type
        }

        alligator_data = st.session_state.alligator_engine.analyze(frame)
        ema_data = st.session_state.ema_engine.analyze(frame)
        stoch_data = st.session_state.stoch_engine.analyze(frame)

        result = st.session_state.fusion.resolve(
            fractal_data,
            alligator_data,
            ema_data,
            stoch_data
        )

        banner_text = "WAIT"
        banner_color = (255, 255, 0)

        if result["signal"] != "WAIT":
            mem.fire()
            banner_text = f"{result['signal']} — {result['type']}"
            banner_color = (0, 255, 0) if result["type"] == "CONFIRMED" else (0, 165, 255)
            text = format_signal_output(result)
            st.session_state.signal_locked = True
            st.session_state.signal_text = text
        else:
            banner_text = "WAIT — No valid setup"

        overlay = draw_decision_banner(overlay, banner_text, banner_color)
        st.image(overlay, use_column_width=True)

        if st.session_state.signal_locked:
            st.experimental_rerun()

# =========================================
# VIDEO MODE (PATCH 6 — FULL)
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

                # Candle tracking
                new_candle, candles = st.session_state.candle_engine.update(frame)
                if new_candle:
                    mem.new_candle()

                    latest = candles[-1]
                    candle_data = {
                        "top": latest["top"],
                        "bottom": latest["bottom"]
                    }

                    new_fractal, ftype = st.session_state.fractal_engine.update(candle_data)
                    if new_fractal:
                        mem.on_fractal(ftype)
                else:
                    new_fractal = False

                fractal_idx = mem.fractal_index
                overlay = draw_candle_labels(frame, candles, fractal_idx)

                fractal_data = {
                    "confirmed": new_fractal,
                    "type": mem.fractal_type
                }

                alligator_data = st.session_state.alligator_engine.analyze(frame)
                ema_data = st.session_state.ema_engine.analyze(frame)
                stoch_data = st.session_state.stoch_engine.analyze(frame)

                result = st.session_state.fusion.resolve(
                    fractal_data,
                    alligator_data,
                    ema_data,
                    stoch_data
                )

                banner_text = "WAIT"
                banner_color = (255, 255, 0)

                if result["signal"] != "WAIT":
                    mem.fire()
                    banner_text = f"{result['signal']} — {result['type']}"
                    banner_color = (0, 255, 0) if result["type"] == "CONFIRMED" else (0, 165, 255)
                    text = format_signal_output(result)
                    st.session_state.signal_locked = True
                    st.session_state.signal_text = text
                    overlay = draw_decision_banner(overlay, banner_text, banner_color)
                    frame_slot.image(overlay, channels="BGR", use_column_width=True)
                    break
                else:
                    overlay = draw_decision_banner(overlay, "WAIT — Scanning", (255, 255, 0))

                frame_slot.image(overlay, channels="BGR", use_column_width=True)
                time.sleep(FRAME_DELAY)

            cap.release()
            st.experimental_rerun()
