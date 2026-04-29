#!/usr/bin/env python3
"""
Minimal native macOS Cocoa app for webcam head tracking -> IEM SceneRotator OSC.
"""

from __future__ import annotations

import math
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, Optional, Sequence

import cv2
import pyheadtracker as pht
from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSColor,
    NSFont,
    NSMakeRange,
    NSMakeRect,
    NSRoundedBezelStyle,
    NSScrollView,
    NSSegmentedControl,
    NSTextAlignmentLeft,
    NSPopUpButton,
    NSRunningApplication,
    NSView,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialHUDWindow,
    NSVisualEffectStateActive,
    NSVisualEffectView,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
    NSWindowTitleHidden,
    NSWorkspace,
)
from AVFoundation import AVCaptureDevice, AVAuthorizationStatusAuthorized, AVAuthorizationStatusDenied, AVAuthorizationStatusNotDetermined, AVMediaTypeVideo
from Foundation import NSObject, NSTimer
from pythonosc.udp_client import SimpleUDPClient
import objc


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


from scene_rotator_headtracker_core import (
    APP_NAME,
    APP_VERSION,
    HeadTrackerEngine,
    available_cameras,
    first_working_camera,
)


class AppDelegate(NSObject):
    engine = objc.ivar()
    status_queue = objc.ivar()
    window = objc.ivar()

    def applicationDidFinishLaunching_(self, notification) -> None:
        self.engine = None
        self.status_queue = Queue()
        self._build_ui()
        self._refresh_cameras()
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05,
            self,
            "pollQueue:",
            None,
            True,
        )
        NSRunningApplication.currentApplication().activateWithOptions_(1 << 1)
        self._update_camera_permission_status()

    def applicationShouldTerminateAfterLastWindowClosed_(self, app) -> bool:
        return True

    def applicationWillTerminate_(self, notification) -> None:
        if self.engine is not None:
            self.engine.stop()

    @objc.python_method
    def _build_ui(self) -> None:
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 560, 780),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_(f"{APP_NAME} {APP_VERSION}")
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(NSWindowTitleHidden)
        self.window.setMovableByWindowBackground_(True)
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)
        content = self.window.contentView()

        background = NSVisualEffectView.alloc().initWithFrame_(content.bounds())
        background.setAutoresizingMask_(18)
        background.setMaterial_(NSVisualEffectMaterialHUDWindow)
        background.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        background.setState_(NSVisualEffectStateActive)
        content.addSubview_(background)

        panel = NSView.alloc().initWithFrame_(NSMakeRect(18, 18, 524, 744))
        panel.setWantsLayer_(True)
        panel.layer().setCornerRadius_(18.0)
        panel.layer().setBackgroundColor_(NSColor.colorWithCalibratedWhite_alpha_(0.12, 0.92).CGColor())
        background.addSubview_(panel)

        y = 700
        self.title_label = self._label(
            panel,
            APP_NAME,
            24,
            y - 2,
            340,
            28,
            bold=True,
            size=24,
            color=NSColor.whiteColor(),
        )
        self.subtitle_label = self._label(
            panel,
            "Webcam head tracking for IEM SceneRotator",
            24,
            y - 36,
            360,
            18,
            color=NSColor.secondaryLabelColor(),
            size=12,
        )
        y -= 122

        connection_card = self._section(panel, "Connection", 24, y - 78, 476, 148)

        self._label(connection_card, "Camera", 18, 96, 100, 20, color=NSColor.secondaryLabelColor())
        self.camera_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(134, 92, 106, 30), False)
        self._style_popup(self.camera_popup)
        connection_card.addSubview_(self.camera_popup)

        self.refresh_button = self._button(connection_card, "Refresh", 248, 92, 80, 30, "refreshCameras:")
        self.fps_field = self._text_input(connection_card, "FPS", "60", 334, 92, field_width=74)

        self.ip_field = self._text_input(connection_card, "OSC IP", "127.0.0.1", 18, 56, field_width=120)
        self.port_field = self._text_input(connection_card, "OSC Port", "7000", 18, 20, field_width=120)
        self.smooth_field = self._text_input(connection_card, "Smooth", "1.0", 254, 56, field_width=120)
        self.deadzone_field = self._text_input(connection_card, "Deadzone", "0.0", 254, 20, field_width=120)

        y -= 176

        tracking_card = self._section(panel, "Tracking", 24, y - 24, 476, 92)
        self._label(tracking_card, "Mode", 18, 42, 100, 20, color=NSColor.secondaryLabelColor())
        self.mode_control = NSSegmentedControl.alloc().initWithFrame_(NSMakeRect(134, 38, 196, 30))
        self.mode_control.setSegmentCount_(2)
        self.mode_control.setLabel_forSegment_("Yaw only", 0)
        self.mode_control.setLabel_forSegment_("Full YPR", 1)
        self.mode_control.setSelectedSegment_(0)
        tracking_card.addSubview_(self.mode_control)

        y -= 124

        controls_card = self._section(panel, "Controls", 24, y - 8, 476, 92)
        self.start_button = self._button(controls_card, "Start", 18, 10, 82, 34, "startTracking:", primary=True)
        self.stop_button = self._button(controls_card, "Stop", 108, 10, 82, 34, "stopTracking:")
        self.calibrate_button = self._button(controls_card, "Calibrate", 190, 10, 96, 34, "calibrate:")
        self.recenter_button = self._button(controls_card, "Recenter", 294, 10, 96, 34, "recenter:")
        self.quit_button = self._button(controls_card, "Quit", 398, 10, 60, 34, "quitApp:")
        self.stop_button.setEnabled_(False)
        self.calibrate_button.setEnabled_(False)
        self.recenter_button.setEnabled_(False)
        y -= 112

        status_card = self._section(panel, "Status", 24, y - 8, 476, 132)
        self.status_label = self._label(status_card, "Idle", 18, 54, 440, 20, size=13)
        self.pose_label = self._label(
            status_card,
            "Yaw 0.00 | Pitch 0.00 | Roll 0.00",
            18,
            24,
            440,
            20,
            color=NSColor.secondaryLabelColor(),
            size=12,
        )
        y -= 160

        instructions = (
            "1. Choose the camera and OSC port.\n"
            "2. Open SceneRotator and enable OSC receive.\n"
            "3. Press Start.\n"
            "4. Press Calibrate while looking straight ahead.\n"
            "5. Use Recenter for a quick neutral reset."
        )
        info_card = self._section(panel, "How to Use", 24, y + 8, 476, 132)
        self.instructions_label = self._multiline_label(
            info_card,
            instructions,
            28,
            8,
            420,
            82,
            color=NSColor.secondaryLabelColor(),
            size=12,
        )
        self.permission_button = self._button(panel, "Allow Camera Access", 326, 666, 174, 28, "requestCameraAccess:")
        self.permission_button.setHidden_(True)

    @objc.python_method
    def _section(self, parent, title: str, x: float, y: float, w: float, h: float):
        card = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        card.setWantsLayer_(True)
        card.layer().setCornerRadius_(14.0)
        card.layer().setBackgroundColor_(NSColor.colorWithCalibratedWhite_alpha_(0.17, 0.95).CGColor())
        parent.addSubview_(card)
        tag = self._label(card, title, 14, h - 24, 180, 16, color=NSColor.secondaryLabelColor(), size=11)
        return card

    @objc.python_method
    def _label(
        self,
        parent,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        bold: bool = False,
        color=None,
        size: float = 13,
    ):
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(color or NSColor.labelColor())
        label.setAlignment_(NSTextAlignmentLeft)
        if bold:
            label.setFont_(NSFont.boldSystemFontOfSize_(size))
        else:
            label.setFont_(NSFont.systemFontOfSize_(size))
        parent.addSubview_(label)
        return label

    @objc.python_method
    def _multiline_label(self, parent, text: str, x: float, y: float, w: float, h: float, color=None, size: float = 12):
        label = self._label(parent, text, x, y, w, h, color=color, size=size)
        label.setUsesSingleLineMode_(False)
        label.setLineBreakMode_(0)
        return label

    @objc.python_method
    def _button(self, parent, title: str, x: float, y: float, w: float, h: float, action: str, primary: bool = False):
        button = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        button.setTitle_(title)
        button.setBezelStyle_(NSRoundedBezelStyle)
        button.setTarget_(self)
        button.setAction_(action)
        if primary:
            button.setKeyEquivalent_("\r")
        parent.addSubview_(button)
        return button

    @objc.python_method
    def _text_input(self, parent, label_text: str, default: str, x: float, y: float, field_width: float = 104):
        self._label(parent, label_text, x, y + 4, 100, 20, color=NSColor.secondaryLabelColor())
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(x + 116, y, field_width, 26))
        field.setStringValue_(default)
        field.setBezeled_(True)
        field.setBezelStyle_(0)
        parent.addSubview_(field)
        return field

    @objc.python_method
    def _style_popup(self, popup):
        popup.setFont_(NSFont.systemFontOfSize_(13))

    @objc.python_method
    def _update_camera_permission_status(self) -> None:
        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeVideo)
        if status == AVAuthorizationStatusAuthorized:
            self.permission_button.setHidden_(True)
            return
        if status == AVAuthorizationStatusNotDetermined:
            self.status_label.setStringValue_("Camera access not granted yet. Press 'Allow Camera Access'.")
            self.permission_button.setHidden_(False)
            return
        if status == AVAuthorizationStatusDenied:
            self.status_label.setStringValue_(
                "Camera access is denied. Press 'Allow Camera Access' to open System Settings."
            )
            self.permission_button.setTitle_("Open Camera Settings")
            self.permission_button.setHidden_(False)
            return
        self.permission_button.setHidden_(False)

    @objc.python_method
    def _refresh_cameras(self) -> None:
        cameras = available_cameras()
        self.camera_popup.removeAllItems()
        if not cameras:
            for fallback in ("0", "1", "2"):
                self.camera_popup.addItemWithTitle_(fallback)
            self.camera_popup.selectItemAtIndex_(0)
            self.status_label.setStringValue_("No camera auto-detected. Defaulting to camera 0.")
            return
        for camera in cameras:
            self.camera_popup.addItemWithTitle_(str(camera))
        self.camera_popup.selectItemAtIndex_(0)
        self.status_label.setStringValue_("Available cameras: " + ", ".join(str(c) for c in cameras))

    @objc.python_method
    def _set_running(self, running: bool) -> None:
        self.start_button.setEnabled_(not running)
        self.stop_button.setEnabled_(running)
        self.calibrate_button.setEnabled_(running)
        self.recenter_button.setEnabled_(running)

    @objc.python_method
    def _parse_settings(self):
        camera = int(self.camera_popup.titleOfSelectedItem())
        ip = self.ip_field.stringValue().strip()
        port = int(self.port_field.stringValue())
        smooth = float(self.smooth_field.stringValue())
        deadzone = float(self.deadzone_field.stringValue())
        max_fps = float(self.fps_field.stringValue())
        yaw_only = self.mode_control.selectedSegment() == 0
        return camera, ip, port, smooth, deadzone, max_fps, yaw_only

    @objc.IBAction
    def refreshCameras_(self, sender) -> None:
        self._refresh_cameras()

    @objc.IBAction
    def startTracking_(self, sender) -> None:
        if self.engine is not None:
            return
        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeVideo)
        if status != AVAuthorizationStatusAuthorized:
            self._update_camera_permission_status()
            return
        try:
            camera, ip, port, smooth, deadzone, max_fps, yaw_only = self._parse_settings()
        except Exception as exc:
            self.status_label.setStringValue_(f"Invalid settings: {exc}")
            return

        selected_camera = camera
        fallback_camera = first_working_camera()
        if fallback_camera is not None:
            camera = fallback_camera if str(selected_camera) == "0" and self.camera_popup.numberOfItems() > 0 and self.camera_popup.titleOfSelectedItem() == "0" else selected_camera

        try:
            self.engine = HeadTrackerEngine(
                camera_index=camera,
                ip=ip,
                port=port,
                smooth=smooth,
                deadzone_deg=deadzone,
                yaw_only=yaw_only,
                max_fps=max_fps,
                status_callback=lambda text: self.status_queue.put(("status", text)),
                pose_callback=lambda pose: self.status_queue.put(("pose", pose)),
            )
        except Exception as exc:
            fallback = first_working_camera()
            if fallback is not None and fallback != camera:
                try:
                    self.engine = HeadTrackerEngine(
                        camera_index=fallback,
                        ip=ip,
                        port=port,
                        smooth=smooth,
                        deadzone_deg=deadzone,
                        yaw_only=yaw_only,
                        max_fps=max_fps,
                        status_callback=lambda text: self.status_queue.put(("status", text)),
                        pose_callback=lambda pose: self.status_queue.put(("pose", pose)),
                    )
                    self.status_label.setStringValue_(f"Camera {selected_camera} failed. Falling back to camera {fallback}.")
                except Exception as fallback_exc:
                    self.status_label.setStringValue_(
                        "Could not open any camera. Check macOS Camera permission for "
                        "SceneRotatorHeadTracker.app."
                    )
                    self.pose_label.setStringValue_(str(fallback_exc))
                    return
            else:
                self.status_label.setStringValue_(
                    "Could not open the selected camera. Check Camera permission or try 1 or 2."
                )
                self.pose_label.setStringValue_(str(exc))
                return

        self.engine.start()
        self._set_running(True)
        self.status_label.setStringValue_("Starting...")

    @objc.IBAction
    def stopTracking_(self, sender) -> None:
        if self.engine is None:
            return
        self.engine.stop()
        self.engine = None
        self._set_running(False)
        self.status_label.setStringValue_("Stopped")

    @objc.IBAction
    def calibrate_(self, sender) -> None:
        if self.engine is not None:
            self.engine.calibrate()

    @objc.IBAction
    def recenter_(self, sender) -> None:
        if self.engine is not None:
            self.engine.zero()

    @objc.IBAction
    def quitApp_(self, sender) -> None:
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        NSApp.terminate_(None)

    @objc.IBAction
    def requestCameraAccess_(self, sender) -> None:
        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeVideo)
        if status == AVAuthorizationStatusDenied:
            NSWorkspace.sharedWorkspace().openURL_(
                objc.lookUpClass("NSURL").URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"
                )
            )
            return

        def completion(granted):
            self.status_queue.put(
                (
                    "status",
                    "Camera access granted. You can start tracking now."
                    if granted
                    else "Camera access denied. Enable it in System Settings > Privacy & Security > Camera.",
                )
            )
            self.status_queue.put(("permission_refresh", None))

        AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVMediaTypeVideo,
            completion,
        )

    def pollQueue_(self, timer) -> None:
        try:
            while True:
                kind, payload = self.status_queue.get_nowait()
                if kind == "status":
                    self.status_label.setStringValue_(str(payload))
                    if str(payload).startswith("Error:") and self.engine is not None:
                        self.engine.stop()
                        self.engine = None
                        self._set_running(False)
                elif kind == "pose":
                    pose = payload
                    self.pose_label.setStringValue_(
                        f"Yaw {math.degrees(pose.yaw):.2f} | "
                        f"Pitch {math.degrees(pose.pitch):.2f} | "
                        f"Roll {math.degrees(pose.roll):.2f}"
                    )
                elif kind == "permission_refresh":
                    self._update_camera_permission_status()
        except Empty:
            pass


def main() -> int:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
