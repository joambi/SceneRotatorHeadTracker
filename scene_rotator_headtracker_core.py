#!/usr/bin/env python3
"""
Platform-neutral tracking and OSC core for SceneRotator HeadTracker.
"""

from __future__ import annotations

import math
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

import cv2
import pyheadtracker as pht
from pythonosc.udp_client import SimpleUDPClient


APP_NAME = "SceneRotator HeadTracker"
APP_VERSION = "0.2"
MODEL_RELATIVE_PATH = "pyheadtracker/data/mediapipe-facelandmarker/face_landmarker_v2_with_blendshapes.task"


@dataclass
class YPRState:
    yaw: float
    pitch: float
    roll: float


class SceneRotatorOscSender:
    def __init__(self, ip: str, port: int, address_prefix: str = "/SceneRotator/"):
        self.client = SimpleUDPClient(ip, port)
        self.address_prefix = address_prefix

    def send_ypr(self, ypr: YPRState) -> None:
        self.client.send_message(
            self.address_prefix + "ypr",
            [
                float(math.degrees(ypr.yaw)),
                float(math.degrees(ypr.pitch)),
                float(math.degrees(ypr.roll)),
            ],
        )


def coerce_ypr(orientation: object) -> Optional[YPRState]:
    if orientation is None:
        return None
    if all(hasattr(orientation, attr) for attr in ("yaw", "pitch", "roll")):
        return YPRState(
            float(orientation.yaw),
            float(orientation.pitch),
            float(orientation.roll),
        )
    if isinstance(orientation, Sequence) and len(orientation) >= 3:
        return YPRState(
            float(orientation[0]),
            float(orientation[1]),
            float(orientation[2]),
        )
    return None


def smooth_pose(current: YPRState, previous: Optional[YPRState], alpha: float) -> YPRState:
    if previous is None or alpha >= 1.0:
        return current
    if alpha <= 0.0:
        return previous
    inv = 1.0 - alpha
    return YPRState(
        yaw=(alpha * current.yaw) + (inv * previous.yaw),
        pitch=(alpha * current.pitch) + (inv * previous.pitch),
        roll=(alpha * current.roll) + (inv * previous.roll),
    )


def subtract_pose(current: YPRState, offset: YPRState) -> YPRState:
    return YPRState(
        yaw=current.yaw - offset.yaw,
        pitch=current.pitch - offset.pitch,
        roll=current.roll - offset.roll,
    )


def deadzone_axis(value: float, threshold_deg: float) -> float:
    threshold = math.radians(threshold_deg)
    if abs(value) <= threshold:
        return 0.0
    return math.copysign(abs(value) - threshold, value)


def apply_deadzone(current: YPRState, threshold_deg: float) -> YPRState:
    return YPRState(
        yaw=deadzone_axis(current.yaw, threshold_deg),
        pitch=deadzone_axis(current.pitch, threshold_deg),
        roll=deadzone_axis(current.roll, threshold_deg),
    )


def apply_mode(current: YPRState, yaw_only: bool) -> YPRState:
    if not yaw_only:
        return current
    return YPRState(current.yaw, 0.0, 0.0)


def average_pose(samples: Sequence[YPRState]) -> Optional[YPRState]:
    if not samples:
        return None
    count = float(len(samples))
    return YPRState(
        yaw=sum(sample.yaw for sample in samples) / count,
        pitch=sum(sample.pitch for sample in samples) / count,
        roll=sum(sample.roll for sample in samples) / count,
    )


def available_cameras(max_index: int = 5) -> list[int]:
    indices: list[int] = []
    for index in range(max_index + 1):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ok, _frame = cap.read()
            if ok:
                indices.append(index)
        cap.release()
    return indices


def first_working_camera(max_index: int = 5) -> Optional[int]:
    cameras = available_cameras(max_index=max_index)
    if cameras:
        return cameras[0]
    return None


def resolve_model_path() -> Optional[str]:
    bundled_base = getattr(sys, "_MEIPASS", None)
    if bundled_base:
        candidate = Path(bundled_base) / MODEL_RELATIVE_PATH
        if candidate.exists():
            return str(candidate)

    try:
        import pyheadtracker

        package_candidate = (
            Path(pyheadtracker.__file__).resolve().parent
            / "data/mediapipe-facelandmarker/face_landmarker_v2_with_blendshapes.task"
        )
        if package_candidate.exists():
            return str(package_candidate)
    except Exception:
        pass

    return None


class HeadTrackerEngine:
    def __init__(
        self,
        camera_index: int,
        ip: str,
        port: int,
        smooth: float,
        deadzone_deg: float,
        yaw_only: bool,
        max_fps: float,
        status_callback: Callable[[str], None],
        pose_callback: Callable[[YPRState], None],
    ):
        self.camera_index = camera_index
        self.sender = SceneRotatorOscSender(ip, port)
        self.smooth = smooth
        self.deadzone_deg = deadzone_deg
        self.yaw_only = yaw_only
        self.max_fps = max_fps
        self.status_callback = status_callback
        self.pose_callback = pose_callback
        model_path = resolve_model_path()
        if model_path is None:
            raise RuntimeError("Could not locate the Face Landmarker model in the app bundle.")
        self.model_path = model_path
        self.tracker = pht.cam.MPFaceLandmarker(
            camera_index,
            orient_format="ypr",
            model_weights=self.model_path,
        )
        self.stop_event = threading.Event()
        self.calibrate_event = threading.Event()
        self.zero_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.neutral_offset = YPRState(0.0, 0.0, 0.0)
        self.smoothed: Optional[YPRState] = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    def zero(self) -> None:
        self.zero_event.set()

    def calibrate(self) -> None:
        self.calibrate_event.set()

    def _sample_orientation(self) -> Optional[YPRState]:
        pose = self.tracker.read_pose()
        if pose is None:
            return None
        return coerce_ypr(pose.get("orientation"))

    def _collect_calibration(self, seconds: float = 1.2) -> Optional[YPRState]:
        samples: list[YPRState] = []
        deadline = time.monotonic() + seconds
        frame_interval = 1.0 / self.max_fps
        while time.monotonic() < deadline and not self.stop_event.is_set():
            orientation = self._sample_orientation()
            if orientation is not None:
                samples.append(orientation)
            time.sleep(frame_interval)
        return average_pose(samples)

    def _run(self) -> None:
        try:
            self.status_callback(f"Opening camera {self.camera_index}...")
            self.tracker.open()
            self.tracker.zero()
            self.status_callback("Running")
            frame_interval = 1.0 / self.max_fps
            while not self.stop_event.is_set():
                loop_start = time.monotonic()

                if self.zero_event.is_set():
                    self.tracker.zero()
                    self.neutral_offset = YPRState(0.0, 0.0, 0.0)
                    self.smoothed = None
                    self.zero_event.clear()
                    self.status_callback("Recentered")

                if self.calibrate_event.is_set():
                    self.status_callback("Calibrating...")
                    calibration = self._collect_calibration()
                    if calibration is not None:
                        self.neutral_offset = calibration
                        self.smoothed = None
                        self.status_callback("Calibration stored")
                    else:
                        self.status_callback("Calibration failed")
                    self.calibrate_event.clear()

                orientation = self._sample_orientation()
                if orientation is None:
                    self.status_callback("No face detected")
                    time.sleep(0.01)
                    continue

                adjusted = subtract_pose(orientation, self.neutral_offset)
                adjusted = apply_deadzone(adjusted, self.deadzone_deg)
                adjusted = apply_mode(adjusted, self.yaw_only)
                self.smoothed = smooth_pose(adjusted, self.smoothed, self.smooth)
                self.sender.send_ypr(self.smoothed)
                self.pose_callback(self.smoothed)

                elapsed = time.monotonic() - loop_start
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
        except Exception as exc:
            self.status_callback(f"Error: {exc}")
        finally:
            try:
                self.tracker.close()
            except Exception:
                pass
