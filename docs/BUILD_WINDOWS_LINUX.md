# Build Windows And Linux Versions

The native macOS app uses Cocoa APIs and must be built on macOS. Windows and
Linux use the cross-platform Tkinter entry point:

```text
headtracker_scenerotator_tk_app.py
```

Both variants share the platform-neutral tracking engine:

```text
scene_rotator_headtracker_core.py
```

## Windows

Build on a Windows machine with Python 3.11 installed. The official installer
from `python.org` includes Tkinter by default and is the recommended option.

```powershell
.\build_headtracker_windows.ps1
```

The script creates `.venv-windows`, installs the dependencies, and runs
PyInstaller. The result is:

```text
dist-windows\SceneRotatorHeadTracker\SceneRotatorHeadTracker.exe
```

Distribute the whole `SceneRotatorHeadTracker` folder, not only the `.exe`.

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
