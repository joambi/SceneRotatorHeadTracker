# Build SceneRotator HeadTracker.app

This document describes the recommended way to bundle the working head tracker
into a native macOS `.app` so that readers do not need to install Python
manually.

## Important Recommendation

Use the official macOS Python installer from `python.org`, not the current
`pyenv`-based Python environment.

Reason:

The GUI app uses `tkinter`, and the current `pyenv` Python on this machine does
not provide a healthy Tcl/Tk setup for PyInstaller bundling. During the build,
PyInstaller reports:

`tkinter installation is broken. It will be excluded from the application`

For a reliable `.app` build, the safest route is:

1. install official Python from python.org
2. create a fresh virtual environment with that Python
3. reinstall the app dependencies
4. run the build script from that clean environment

## Current App Source

The GUI app entry point is:

- [headtracker_scenerotator_app.py](/Users/jschuet1/Mac_Support/headtracker_scenerotator_app.py)

It provides:

- camera selection
- OSC IP and port fields
- yaw-only or full YPR mode
- start / stop
- calibrate / recenter
- live pose status

## Step 1: Install Official Python

Download and install the current macOS universal installer from:

- [python.org macOS downloads](https://www.python.org/downloads/macos/)

After installation, verify:

```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m tkinter
```

If a small Tk window opens, the GUI foundation is healthy.

## Step 2: Create a Fresh Build Environment

```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv ~/venvs/scene-rotator-app
source ~/venvs/scene-rotator-app/bin/activate
pip install --upgrade pip
pip install pyheadtracker opencv-python python-osc pyinstaller
```

## Step 3: Point the Build Script to the New Environment

Edit:

- [build_headtracker_app.sh](/Users/jschuet1/Mac_Support/build_headtracker_app.sh)

and change:

```bash
VENV_DIR="$HOME/venvs/pyheadtracker"
```

to:

```bash
VENV_DIR="$HOME/venvs/scene-rotator-app"
```

## Step 4: Run the Build

```bash
/Users/jschuet1/Mac_Support/build_headtracker_app.sh
```

Expected output:

```text
/Users/jschuet1/Mac_Support/dist/SceneRotatorHeadTracker.app
```

## Step 5: Local Test Checklist

After building, test:

1. app launches by double click
2. macOS asks for camera permission
3. camera opens successfully
4. head tracking updates the GUI values
5. OSC reaches SceneRotator
6. app can be closed and reopened cleanly

## Camera Permission

The app must contain a camera usage description in its `Info.plist`.

The build script adds:

`NSCameraUsageDescription = "SceneRotatorHeadTracker uses the camera for webcam-based head tracking."`

Without this key, camera access may fail.

## Distribution Notes

For informal sharing, the unsigned `.app` may be sufficient.

For reviewer-facing or public sharing, the better path is:

1. codesign the app
2. notarize the app
3. distribute as a `.zip` or `.dmg`

## Suggested Supplementary Package Placement

Place the final app here:

```text
JAR_Supplement/headtracker_app/SceneRotatorHeadTracker.app
```

## Practical Summary

The app code itself is already in place. The remaining blocker is not the head
tracking logic, but the local Python GUI runtime used for bundling. Switching to
the official python.org build is the recommended path to a stable native macOS
application.
