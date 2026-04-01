#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/venvs/pyheadtracker"
APP_SCRIPT="$SCRIPT_DIR/headtracker_scenerotator_cocoa_app.py"
DIST_DIR="$SCRIPT_DIR/dist"
BUILD_DIR="$SCRIPT_DIR/build"
APP_NAME="SceneRotatorHeadTracker"
DISPLAY_NAME="SceneRotator HeadTracker"
BUNDLE_ID="at.iem.SceneRotatorHeadTracker"
APP_VERSION="0.1"
MPL_DIR="$SCRIPT_DIR/.mplconfig"
ICON_FILE="$SCRIPT_DIR/assets/SceneRotatorHeadTracker.icns"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing virtual environment: $VENV_DIR"
  exit 1
fi

source "$VENV_DIR/bin/activate"

SITE_PACKAGES=$(python -c 'import site; print(next(p for p in site.getsitepackages() if "site-packages" in p))')
mkdir -p "$MPL_DIR"
export MPLCONFIGDIR="$MPL_DIR"

PYINSTALLER_ARGS=(
  --noconfirm
  --windowed
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
  --hidden-import encodings.idna
  --add-data "$SITE_PACKAGES/mediapipe:mediapipe"
  --add-data "$SITE_PACKAGES/pyheadtracker/data:pyheadtracker/data"
)

if [[ -f "$ICON_FILE" ]]; then
  PYINSTALLER_ARGS+=(--icon "$ICON_FILE")
fi

if ! python -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller is not installed in the virtual environment."
  echo "Install it with:"
  echo "  pip install pyinstaller"
  exit 1
fi

rm -rf "$DIST_DIR" "$BUILD_DIR"

pyinstaller "${PYINSTALLER_ARGS[@]}" "$APP_SCRIPT"

INFO_PLIST="$DIST_DIR/$APP_NAME.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string SceneRotatorHeadTracker uses the camera for webcam-based head tracking." "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSCameraUsageDescription SceneRotatorHeadTracker uses the camera for webcam-based head tracking." "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $DISPLAY_NAME" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $DISPLAY_NAME" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleName $DISPLAY_NAME" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleName string $DISPLAY_NAME" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $APP_VERSION" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $APP_VERSION" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $APP_VERSION" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $APP_VERSION" "$INFO_PLIST"

codesign --force --deep --sign - "$DIST_DIR/$APP_NAME.app"

echo
echo "Built app:"
echo "  $DIST_DIR/$APP_NAME.app"
echo
echo "Next steps:"
echo "  1. Test the app locally."
echo "  2. Optionally codesign it."
echo "  3. Optionally notarize it for distribution."
