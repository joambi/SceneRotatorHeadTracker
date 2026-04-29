#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv-linux"
PYTHON="$VENV_DIR/bin/python"
DIST_DIR="$SCRIPT_DIR/dist-linux"
BUILD_DIR="$SCRIPT_DIR/build-linux"
APP_SCRIPT="$SCRIPT_DIR/headtracker_scenerotator_tk_app.py"
ICON_FILE="$SCRIPT_DIR/assets/SceneRotatorHeadTracker_icon.svg"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON" -c "import tkinter" >/dev/null 2>&1; then
  echo "This Python installation does not include Tkinter."
  echo "Install the Tk package for your distribution, for example:"
  echo "  sudo apt install python3-tk"
  exit 1
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install pyheadtracker opencv-python python-osc pyinstaller

SITE_PACKAGES="$("$PYTHON" -c 'import site; print(next(p for p in site.getsitepackages() if "site-packages" in p))')"

PYINSTALLER_ARGS=(
  --noconfirm
  --windowed
  --clean
  --name SceneRotatorHeadTracker
  --distpath "$DIST_DIR"
  --workpath "$BUILD_DIR"
  --specpath "$BUILD_DIR"
  --hidden-import encodings.idna
  --add-data "$SITE_PACKAGES/mediapipe:mediapipe"
  --add-data "$SITE_PACKAGES/pyheadtracker/data:pyheadtracker/data"
)

if [[ -f "$ICON_FILE" ]]; then
  PYINSTALLER_ARGS+=(--icon "$ICON_FILE")
fi

"$PYTHON" -m PyInstaller "${PYINSTALLER_ARGS[@]}" "$APP_SCRIPT"

echo
echo "Built Linux app:"
echo "  $DIST_DIR/SceneRotatorHeadTracker/SceneRotatorHeadTracker"
