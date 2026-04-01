# SceneRotator HeadTracker

`SceneRotator HeadTracker` is a lightweight macOS utility for webcam-based head tracking with the `IEM SceneRotator`.

It sends real-time head-orientation data via OSC and was developed as a practical listening aid for head-tracked binaural Ambisonics playback in `REAPER`.

## Features

- Webcam-based markerless head tracking
- Direct OSC output to `IEM SceneRotator`
- `Yaw only` and `Full YPR` modes
- `Calibrate` and `Recenter`
- Native macOS app build

## Current Platform

The current release targets `macOS`.

For the associated research package, a macOS-only release is intentional and acceptable as long as this requirement is stated clearly. `REAPER` and the `IEM Plug-in Suite` remain external dependencies.

## Requirements

- `macOS`
- `REAPER`
- `IEM Plug-in Suite`
- A webcam
- Headphones

## Quick Start

1. Open `SceneRotatorHeadTracker.app`.
2. Allow camera access when macOS asks.
3. Open your `REAPER` session.
4. Insert `IEM SceneRotator` and enable OSC receive on the configured port.
5. Select a camera in the app and press `Start`.
6. Press `Calibrate` while looking straight ahead.

## OSC

The app sends orientation data to:

`/SceneRotator/ypr`

Default target:

- IP: `127.0.0.1`
- Port: `7000`

## Repository Layout

- `headtracker_scenerotator_cocoa_app.py`
- `build_headtracker_app.sh`
- `build_headtracker_icon.sh`
- `assets/`: icon sources and generated `.icns`
- `docs/`: build notes and paper text
- `supplementary/`: short reviewer-facing support text
- `release-assets/`: local staging area for the built macOS app

## Build

Use the working Python environment that contains `pyheadtracker`, `opencv-python`, `python-osc`, `pyobjc`, and `pyinstaller`.

```bash
./build_headtracker_icon.sh
./build_headtracker_app.sh
```

The built application will appear in `dist/`.

## Dependencies

This repository does not bundle the `IEM Plug-in Suite`.

Please install separately:
- `REAPER`
- `IEM Plug-in Suite`

## License

This repository is intended to be released under the `MIT License`.

The app source is your own code. `REAPER` and the `IEM Plug-in Suite` are external dependencies and should be obtained separately from their own sources.

## Research Context

This tool was created to support a supplementary listening package for a `JAR / Research Catalogue` submission. It is intended to help reviewers and readers compare static binaural reproduction with head-tracked binaural reproduction using the same Ambisonics source material and rendering chain discussed in the paper.
