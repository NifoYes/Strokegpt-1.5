import os
import sys
import time
import threading
import requests
from typing import Optional, Union, Callable

Number = Union[int, float]

class HandyController:
    """
    Controller for The Handy v2 API.
    - sp/dp/rng are percentages 0..100
      * sp == relative speed
      * dp == center depth (0=base, 100=tip)
      * rng == stroke span around dp
    - No hard "30% minimum span" anymore. The minimum/preferred span are configurable:
      * HANDY_MIN_SPAN (env): absolute points (0..100). Default: 0 (disabled)
      * HANDY_PREF_SPAN (env): absolute points (0..100). Default: 0 (disabled)
    - You can also change them at runtime with set_span_policy(min_span, preferred_span).
    """

    def __init__(self, handy_key: Optional[str] = "", base_url: str = "https://www.handyfeeling.com/api/handy/v2/"):
        self.handy_key = handy_key or ""
        self.base_url = base_url.rstrip('/') + '/'

        # Runtime telemetry/state
        self.last_relative_speed: int = 50   # 0..100
        self.last_depth_pos: int = 50        # 0..100
        self.last_stroke_speed: int = 0      # physical velocity last sent

        # Calibration from app settings
        self.min_user_speed: int = 10
        self.max_user_speed: int = 80
        self.min_handy_depth: int = 0
        self.max_handy_depth: int = 100

        # Span policy (absolute points on 0..100 scale)
        # Defaults read from environment; set 0 to fully disable any floor/preference.
        self.MIN_SPAN_POINTS: int = int(os.getenv("HANDY_MIN_SPAN", "0"))
        self.PREFERRED_SPAN_POINTS: int = int(os.getenv("HANDY_PREF_SPAN", "0"))

        # Track whether manual mode has been initialised for the current batch
        self._manual_mode_active: bool = False

    # ---------------- Configuration ----------------

    def set_api_key(self, key: str):
        self.handy_key = key or ""

    def update_settings(self, min_speed: Number, max_speed: Number, min_depth: Number, max_depth: Number):
        self.min_user_speed = int(min_speed)
        self.max_user_speed = int(max_speed)
        self.min_handy_depth = int(min_depth)
        self.max_handy_depth = int(max_depth)

    def set_span_policy(self, min_span_points: Optional[int] = None, preferred_span_points: Optional[int] = None):
        """Override span policy at runtime. Use 0 to disable a given constraint."""
        if min_span_points is not None:
            self.MIN_SPAN_POINTS = max(0, min(100, int(min_span_points)))
        if preferred_span_points is not None:
            self.PREFERRED_SPAN_POINTS = max(0, min(100, int(preferred_span_points)))

    # ---------------- Internals ----------------

    def _send_command(self, path: str, body: Optional[dict] = None):
        if not self.handy_key:
            return
        headers = {
            "Content-Type": "application/json",
            "X-Connection-Key": self.handy_key
        }
        url = f"{self.base_url}{path}"
        try:
            requests.put(url, headers=headers, json=(body or {}), timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"[HANDY ERROR] PUT {path} failed: {e}", file=sys.stderr)

    @staticmethod
    def _pct(v: Number) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(100.0, v))

    # ---------------- Public API ----------------

    def stop(self):
        if not self.handy_key:
            return
        self._send_command("hamp/stop")
        self.last_stroke_speed = 0
        self.last_relative_speed = 0
        self._manual_mode_active = False

    def move(self, speed: Number, depth: Number, stroke_range: Number):
        """
        Drive the device with relative controls:
          - speed: 0..100 (relative). 0 = stop.
          - depth: 0..100 center position, mapped to calibrated [min_handy_depth, max_handy_depth].
          - stroke_range: 0..100 total span around the center.
        """
        if not self.handy_key:
            return

        # Stop
        if int(float(speed)) == 0:
            self.stop()
            return

        # Normalize
        sp_rel = self._pct(speed)
        dp_rel = self._pct(depth)
        rng_rel = self._pct(stroke_range)

        # Ensure we only initialise manual mode once per batch/script
        self._ensure_manual_mode()

        # Apply parameters immediately
        self._apply_move_parameters(sp_rel, dp_rel, rng_rel)

    def _ensure_manual_mode(self):
        """Put the device in manual mode if it is not already active."""
        if self._manual_mode_active:
            return
        self._send_command("mode", {"mode": 0})
        self._send_command("hamp/start")
        self._manual_mode_active = True

    def _apply_move_parameters(self, sp_rel: float, dp_rel: float, rng_rel: float):
        """Compute and send slide/velocity commands for the given relative values."""
        # --- Compute slide window (absolute points) ---
        calib_w = float(self.max_handy_depth - self.min_handy_depth)
        if calib_w <= 0.0:
            calib_w = 100.0

        center_abs = self.min_handy_depth + calib_w * (dp_rel / 100.0)
        requested_span_abs = int(round((rng_rel / 100.0) * calib_w))

        # Apply (optional) floors/preferences
        min_span = int(self.MIN_SPAN_POINTS or 0)
        pref_span = int(self.PREFERRED_SPAN_POINTS or 0)

        span_abs = requested_span_abs
        if pref_span > 0:
            span_abs = max(span_abs, pref_span)
        if min_span > 0:
            span_abs = max(span_abs, min_span)

        span_abs = min(span_abs, int(calib_w))

        half = span_abs / 2.0
        slide_min = int(round(center_abs - half))
        slide_max = int(round(center_abs + half))

        if slide_min < 0:
            slide_min = 0
            slide_max = min(100, slide_min + int(span_abs))
        if slide_max > 100:
            slide_max = 100
            slide_min = max(0, slide_max - int(span_abs))

        if slide_max < slide_min:
            slide_min, slide_max = slide_max, slide_min

        self._send_command("slide", {"min": slide_min, "max": slide_max})

        speed_w = float(self.max_user_speed - self.min_user_speed)
        if speed_w < 0:
            speed_w = 0
        final_vel = int(round(self.min_user_speed + speed_w * (sp_rel / 100.0)))
        self._send_command("hamp/velocity", {"velocity": final_vel})

        self.last_relative_speed = int(round(sp_rel))
        self.last_depth_pos = int(round(dp_rel))
        self.last_stroke_speed = final_vel

        try:
            print(f"[HANDY DEBUG] sp={int(sp_rel)} dp={int(dp_rel)} rng={int(rng_rel)} vel={final_vel}")
        except Exception:
            pass

    def play_move_script(
        self,
        moves: list[dict[str, Number]],
        stop_event: Optional[threading.Event] = None,
        script_changed: Optional[Callable[[], bool]] = None,
    ):
        """
        Execute a batch of moves sequentially as a single script.

        The device is put in manual mode once, the parameters of each move are
        applied in turn, and the method sleeps for the requested duration while
        periodically checking whether a stop was requested or a new script has
        been scheduled.
        """
        if not self.handy_key:
            return
        if not moves:
            return

        for move in moves:
            if stop_event and stop_event.is_set():
                break
            if script_changed and script_changed():
                break

            sp_rel = self._pct(move.get("sp", 0))
            dp_rel = self._pct(move.get("dp", 50))
            rng_rel = self._pct(move.get("rng", 50))
            duration_ms = int(move.get("duration", 0) or 0)

            if int(sp_rel) <= 0:
                self.stop()
                continue

            self._ensure_manual_mode()
            self._apply_move_parameters(sp_rel, dp_rel, rng_rel)

            remaining = duration_ms / 1000.0
            slice_size = 0.05
            while remaining > 0:
                if stop_event and stop_event.is_set():
                    return
                if script_changed and script_changed():
                    return
                t_sleep = slice_size if remaining > slice_size else remaining
                time.sleep(t_sleep)
                remaining -= t_sleep

    # Optional helpers
    def get_position_mm(self) -> Optional[float]:
        if not self.handy_key:
            return None
        headers = {"X-Connection-Key": self.handy_key}
        try:
            resp = requests.get(f"{self.base_url}slide/position/absolute", headers=headers, timeout=10)
            data = resp.json()
            return float(data.get("position", 0))
        except requests.exceptions.RequestException as e:
            print(f"[HANDY ERROR] Problem reading position: {e}", file=sys.stderr)
            return None

    def mm_to_percent(self, val: Number) -> int:
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = 0.0
        # Device travel ~110mm → map to 0..100
        return int(round(max(0.0, min(100.0, (v / 110.0) * 100.0))))

    def nudge(self, direction: str, current_min: int, current_max: int, calibration_mm: Optional[Number]):
        step = 2 if (direction or '').lower() == 'up' else -2
        new_center = max(0, min(100, int(round(self.last_depth_pos + step))))
        # Preserve current range; ensure at least 10 to make it visible
        current_span = max(10, int(current_max) - int(current_min))
        self.move(self.last_relative_speed or 10, new_center, current_span)
        return calibration_mm or 0.0
