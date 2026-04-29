#!/usr/bin/env python3
"""
Cross-platform Tkinter app for webcam head tracking -> IEM SceneRotator OSC.
"""

from __future__ import annotations

import math
import tkinter as tk
from queue import Empty, Queue
from tkinter import messagebox, ttk

from scene_rotator_headtracker_core import (
    APP_NAME,
    APP_VERSION,
    HeadTrackerEngine,
    available_cameras,
    first_working_camera,
)


class HeadTrackerTkApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.minsize(520, 520)
        self.engine: HeadTrackerEngine | None = None
        self.status_queue: Queue[tuple[str, object]] = Queue()

        self.camera_var = tk.StringVar(value="0")
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="7000")
        self.fps_var = tk.StringVar(value="60")
        self.smooth_var = tk.StringVar(value="1.0")
        self.deadzone_var = tk.StringVar(value="0.0")
        self.mode_var = tk.StringVar(value="yaw")
        self.status_var = tk.StringVar(value="Idle")
        self.pose_var = tk.StringVar(value="Yaw 0.00 | Pitch 0.00 | Roll 0.00")

        self._build_ui()
        self.refresh_cameras()
        self.after(50, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        outer = ttk.Frame(self, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        title = ttk.Label(outer, text=APP_NAME, font=("", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(outer, text="Webcam head tracking for IEM SceneRotator")
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 16))

        connection = ttk.LabelFrame(outer, text="Connection", padding=12)
        connection.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for column in range(4):
            connection.columnconfigure(column, weight=1)

        ttk.Label(connection, text="Camera").grid(row=0, column=0, sticky="w")
        self.camera_combo = ttk.Combobox(connection, textvariable=self.camera_var, width=8, state="readonly")
        self.camera_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.refresh_button = ttk.Button(connection, text="Refresh", command=self.refresh_cameras)
        self.refresh_button.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        self._entry(connection, "OSC IP", self.ip_var, 0, 2)
        self._entry(connection, "OSC Port", self.port_var, 0, 3)
        self._entry(connection, "FPS", self.fps_var, 2, 0)
        self._entry(connection, "Smooth", self.smooth_var, 2, 1)
        self._entry(connection, "Deadzone", self.deadzone_var, 2, 2)

        tracking = ttk.LabelFrame(outer, text="Tracking", padding=12)
        tracking.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        ttk.Radiobutton(tracking, text="Yaw only", variable=self.mode_var, value="yaw").grid(
            row=0, column=0, sticky="w", padx=(0, 16)
        )
        ttk.Radiobutton(tracking, text="Full YPR", variable=self.mode_var, value="ypr").grid(
            row=0, column=1, sticky="w"
        )

        controls = ttk.LabelFrame(outer, text="Controls", padding=12)
        controls.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        for column in range(5):
            controls.columnconfigure(column, weight=1)
        self.start_button = ttk.Button(controls, text="Start", command=self.start_tracking)
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop_tracking, state="disabled")
        self.calibrate_button = ttk.Button(controls, text="Calibrate", command=self.calibrate, state="disabled")
        self.recenter_button = ttk.Button(controls, text="Recenter", command=self.recenter, state="disabled")
        self.quit_button = ttk.Button(controls, text="Quit", command=self.quit_app)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.calibrate_button.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.recenter_button.grid(row=0, column=3, sticky="ew", padx=(0, 8))
        self.quit_button.grid(row=0, column=4, sticky="ew")

        status = ttk.LabelFrame(outer, text="Status", padding=12)
        status.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.pose_var).grid(row=1, column=0, sticky="w", pady=(8, 0))

        help_text = (
            "Open IEM SceneRotator, enable OSC receive, and set the receive port to 7000. "
            "Then press Start and Calibrate while looking straight ahead."
        )
        help_label = ttk.Label(outer, text=help_text, wraplength=480, justify="left")
        help_label.grid(row=6, column=0, sticky="ew")

    def _entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, column: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0, 2))
        ttk.Entry(parent, textvariable=variable, width=12).grid(
            row=row + 1,
            column=column,
            sticky="ew",
            padx=(0, 8),
            pady=(0, 10),
        )

    def refresh_cameras(self) -> None:
        cameras = available_cameras()
        values = [str(camera) for camera in cameras] or ["0", "1", "2"]
        self.camera_combo.configure(values=values)
        if self.camera_var.get() not in values:
            self.camera_var.set(values[0])
        if cameras:
            self.status_var.set("Available cameras: " + ", ".join(values))
        else:
            self.status_var.set("No camera auto-detected. Defaulting to camera 0.")

    def _set_running(self, running: bool) -> None:
        normal = "normal"
        disabled = "disabled"
        self.start_button.configure(state=disabled if running else normal)
        self.stop_button.configure(state=normal if running else disabled)
        self.calibrate_button.configure(state=normal if running else disabled)
        self.recenter_button.configure(state=normal if running else disabled)
        self.refresh_button.configure(state=disabled if running else normal)
        self.camera_combo.configure(state=disabled if running else "readonly")

    def _parse_settings(self) -> tuple[int, str, int, float, float, float, bool]:
        camera = int(self.camera_var.get())
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get())
        smooth = float(self.smooth_var.get())
        deadzone = float(self.deadzone_var.get())
        max_fps = float(self.fps_var.get())
        yaw_only = self.mode_var.get() == "yaw"
        if not ip:
            raise ValueError("OSC IP is empty")
        if not 1 <= port <= 65535:
            raise ValueError("OSC port must be between 1 and 65535")
        if not 0.0 <= smooth <= 1.0:
            raise ValueError("Smooth must be between 0.0 and 1.0")
        if max_fps <= 0:
            raise ValueError("FPS must be greater than 0")
        return camera, ip, port, smooth, deadzone, max_fps, yaw_only

    def start_tracking(self) -> None:
        if self.engine is not None:
            return
        try:
            camera, ip, port, smooth, deadzone, max_fps, yaw_only = self._parse_settings()
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Invalid settings: {exc}")
            return

        selected_camera = camera
        fallback_camera = first_working_camera()
        if fallback_camera is not None and selected_camera == 0:
            camera = fallback_camera

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
            self.status_var.set("Could not start tracking")
            messagebox.showerror(APP_NAME, str(exc))
            return

        self.engine.start()
        self._set_running(True)
        self.status_var.set("Starting...")

    def stop_tracking(self) -> None:
        if self.engine is None:
            return
        self.engine.stop()
        self.engine = None
        self._set_running(False)
        self.status_var.set("Stopped")

    def calibrate(self) -> None:
        if self.engine is not None:
            self.engine.calibrate()

    def recenter(self) -> None:
        if self.engine is not None:
            self.engine.zero()

    def quit_app(self) -> None:
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.destroy()

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.status_queue.get_nowait()
                if kind == "status":
                    text = str(payload)
                    self.status_var.set(text)
                    if text.startswith("Error:") and self.engine is not None:
                        self.engine.stop()
                        self.engine = None
                        self._set_running(False)
                elif kind == "pose":
                    pose = payload
                    self.pose_var.set(
                        f"Yaw {math.degrees(pose.yaw):.2f} | "
                        f"Pitch {math.degrees(pose.pitch):.2f} | "
                        f"Roll {math.degrees(pose.roll):.2f}"
                    )
        except Empty:
            pass
        self.after(50, self._poll_queue)


def main() -> int:
    app = HeadTrackerTkApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
