#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SVG_FILE="$SCRIPT_DIR/assets/SceneRotatorHeadTracker_icon.svg"
ICONSET_DIR="$SCRIPT_DIR/assets/SceneRotatorHeadTracker.iconset"
PNG_BASE="$SCRIPT_DIR/assets/SceneRotatorHeadTracker_icon.png"
ICNS_FILE="$SCRIPT_DIR/assets/SceneRotatorHeadTracker.icns"

if [[ ! -f "$SVG_FILE" ]]; then
  echo "Missing SVG icon source: $SVG_FILE"
  exit 1
fi

rm -rf "$ICONSET_DIR" "$PNG_BASE" "$ICNS_FILE"
mkdir -p "$ICONSET_DIR"

qlmanage -t -s 1024 -o "$SCRIPT_DIR/assets" "$SVG_FILE" >/dev/null 2>&1
mv "$SCRIPT_DIR/assets/SceneRotatorHeadTracker_icon.svg.png" "$PNG_BASE"

sizes=(
  "16 icon_16x16.png"
  "32 icon_16x16@2x.png"
  "32 icon_32x32.png"
  "64 icon_32x32@2x.png"
  "128 icon_128x128.png"
  "256 icon_128x128@2x.png"
  "256 icon_256x256.png"
  "512 icon_256x256@2x.png"
  "512 icon_512x512.png"
  "1024 icon_512x512@2x.png"
)

for item in "${sizes[@]}"; do
  size="${item%% *}"
  file="${item#* }"
  sips -z "$size" "$size" "$PNG_BASE" --out "$ICONSET_DIR/$file" >/dev/null
done

iconutil -c icns "$ICONSET_DIR" -o "$ICNS_FILE"

echo "Built icon:"
echo "  $ICNS_FILE"
