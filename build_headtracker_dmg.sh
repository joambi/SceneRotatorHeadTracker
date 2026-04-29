#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RELEASE_DIR="$SCRIPT_DIR/release-assets/macos"
APP_NAME="SceneRotatorHeadTracker.app"
VERSION="v0.2"
STAGING_DIR="$RELEASE_DIR/dmg-staging"
DMG_NAME="SceneRotatorHeadTracker-macOS-${VERSION}.dmg"
DMG_PATH="$RELEASE_DIR/$DMG_NAME"
APP_PATH="$SCRIPT_DIR/dist/$APP_NAME"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app bundle: $APP_PATH"
  echo "Build the app first with build_headtracker_app.sh."
  exit 1
fi

rm -rf "$STAGING_DIR" "$DMG_PATH"
mkdir -p "$STAGING_DIR"

cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

hdiutil create \
  -volname "SceneRotator HeadTracker" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH" >/dev/null

rm -rf "$STAGING_DIR"

echo "Built DMG:"
echo "  $DMG_PATH"
