# Build And Verify Windows And Linux Versions

The native macOS app uses Cocoa APIs and must be built on macOS. Windows and
Linux use the cross-platform Tkinter entry point:

```text
headtracker_scenerotator_tk_app.py
```

Both variants share the platform-neutral tracking engine:

```text
scene_rotator_headtracker_core.py
```

## What Can Be Verified From macOS

If you only have a Mac, you can verify the shared Python code and the macOS
behavior, but not the final Windows or Linux executables. PyInstaller bundles
native platform libraries, so each release artifact must be built and smoke
tested on its target operating system.

On macOS, run:

```bash
cd SceneRotatorHeadTracker
.venv-tk/bin/python -m py_compile scene_rotator_headtracker_core.py headtracker_scenerotator_tk_app.py
.venv-tk/bin/python -c "from scene_rotator_headtracker_core import available_cameras; print(available_cameras(max_index=5))"
.venv-tk/bin/python headtracker_scenerotator_tk_app.py
```

Expected:

- the compile command exits without output
- the camera command prints a list such as `[0]` or `[0, 1, 2]`
- the Tkinter app opens
- pressing `Start` sends Yaw/Pitch/Roll values to IEM SceneRotator over OSC

This confirms the shared app logic. It does not confirm Windows camera access,
Linux camera permissions, or target-platform PyInstaller packaging.

## Windows

Build on a Windows machine with Python 3.11 installed. The official installer
from `python.org` includes Tkinter by default and is the recommended option.

### Windows User Steps

1. Install `REAPER`.
2. Install the `IEM Plug-in Suite`.
3. Install Python 3.11 from `python.org`.
4. Download or clone this repository.
5. Open PowerShell in the repository folder.
6. Build the app:

```powershell
.\build_headtracker_windows.ps1
```

The script creates `.venv-windows`, installs the Python dependencies, and runs
PyInstaller.

The result is:

```text
dist-windows\SceneRotatorHeadTracker\SceneRotatorHeadTracker.exe
```

Distribute the whole `SceneRotatorHeadTracker` folder, not only the `.exe`.

### Windows Verification Steps

1. Open `REAPER`.
2. Add `IEM SceneRotator` to a track.
3. Enable OSC receive in SceneRotator and set the receive port to `7000`.
4. Start:

```powershell
.\dist-windows\SceneRotatorHeadTracker\SceneRotatorHeadTracker.exe
```

5. Select camera `0`.
6. Keep OSC IP as `127.0.0.1` and OSC Port as `7000`.
7. Press `Start`.
8. Look left/right and confirm that SceneRotator's Yaw value changes.
9. Press `Calibrate` while looking straight ahead.
10. Press `Stop`, then close and reopen the app once.

Expected:

- the app opens without requiring Python from the user
- the webcam activates
- Yaw/Pitch/Roll values update in the app
- SceneRotator's Yaw/Pitch/Roll display follows head movement
- `Calibrate`, `Recenter`, `Stop`, and relaunch work

If Windows Defender warns about the app, choose "More info" and "Run anyway".
This is expected for unsigned research builds.

## Linux

Build on the target Linux distribution. The Python installation must include
Tkinter. On Debian/Ubuntu systems, install it with:

```bash
sudo apt install python3-tk
```

Then run:

```bash
./build_headtracker_linux.sh
```

The script creates `.venv-linux`, installs the dependencies, and runs
PyInstaller. The result is:

```text
dist-linux/SceneRotatorHeadTracker/SceneRotatorHeadTracker
```

Distribute the whole `SceneRotatorHeadTracker` folder.

### Linux User Steps

1. Install `REAPER`.
2. Install the `IEM Plug-in Suite`.
3. Install Python, venv, Tkinter, and common camera/GL libraries.

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk libgl1 libglib2.0-0 v4l-utils
```

4. Download or clone this repository.
5. Open a terminal in the repository folder.
6. Build the app:

```bash
./build_headtracker_linux.sh
```

### Linux Verification Steps

1. Confirm that Linux can see the webcam:

```bash
v4l2-ctl --list-devices
```

2. Open `REAPER`.
3. Add `IEM SceneRotator` to a track.
4. Enable OSC receive in SceneRotator and set the receive port to `7000`.
5. Start:

```bash
./dist-linux/SceneRotatorHeadTracker/SceneRotatorHeadTracker
```

6. Select camera `0`.
7. Keep OSC IP as `127.0.0.1` and OSC Port as `7000`.
8. Press `Start`.
9. Look left/right and confirm that SceneRotator's Yaw value changes.
10. Press `Calibrate` while looking straight ahead.
11. Press `Stop`, then close and reopen the app once.

Expected:

- the app opens without requiring Python from the user
- the webcam activates
- Yaw/Pitch/Roll values update in the app
- SceneRotator's Yaw/Pitch/Roll display follows head movement
- `Calibrate`, `Recenter`, `Stop`, and relaunch work

If the camera does not open, check that the user is allowed to access video
devices. On many distributions this means logging out and back in after adding
the user to the `video` group:

```bash
sudo usermod -aG video "$USER"
```

## SceneRotator Setup

In IEM SceneRotator, enable OSC receive and use the same port as the app. The
default is:

```text
127.0.0.1:7000
```

The app sends:

```text
/SceneRotator/ypr yaw pitch roll
```

Values are sent in degrees.

## Tester Report Template

Ask external Windows and Linux testers to send back:

```text
Operating system:
CPU architecture:
Python version used for build:
Build command completed: yes/no
App opened: yes/no
Camera list shown:
Selected camera:
SceneRotator OSC indicator active: yes/no
Yaw changes when turning head: yes/no
Pitch/Roll mode tested: yaw only/full YPR
Calibrate works: yes/no
Recenter works: yes/no
Any terminal output or error:
Screenshot:
```

## Maintainer Release Rule

Mark Windows and Linux builds as experimental until at least one real user has
completed the verification steps on each platform. A macOS-only verification is
not enough for a public Windows or Linux release.
