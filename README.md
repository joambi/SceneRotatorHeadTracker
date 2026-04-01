# SceneRotator HeadTracker

`SceneRotator HeadTracker` is a lightweight macOS utility for webcam-based head tracking with the `IEM SceneRotator`.

It sends real-time head-orientation data via OSC and was developed as a practical listening aid for head-tracked binaural Ambisonics playback in `REAPER`.

The project was created in the context of a supplementary listening package for a `JAR / Research Catalogue` submission and is intended to make head-tracked binaural listening examples easier to reproduce for reviewers and readers.

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

## Release Download

The recommended end-user path is:

1. Download the current macOS release from GitHub Releases.
2. Open `SceneRotatorHeadTracker.app`.
3. Allow camera access when macOS asks.
4. Start the listener session in `REAPER`.

The macOS release can be provided either as a zipped `.app` or as a drag-and-drop `.dmg` installer image.

For source-based builds, use the scripts in this repository.

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
- `build_headtracker_dmg.sh`
- `assets/`: icon sources and generated `.icns`
- `docs/`: build notes and paper text
- `supplementary/`: short reviewer-facing support text
- `release-assets/`: local staging area for the built macOS app

## Build

Use the working Python environment that contains `pyheadtracker`, `opencv-python`, `python-osc`, `pyobjc`, and `pyinstaller`.

```bash
./build_headtracker_icon.sh
./build_headtracker_app.sh
./build_headtracker_dmg.sh
```

The built application will appear in `dist/`. The DMG installer will appear in `release-assets/macos/`.

## Dependencies

This repository does not bundle the `IEM Plug-in Suite`.

Please install separately:
- `REAPER`
- `IEM Plug-in Suite`

## License

This repository is intended to be released under the `MIT License`.

The app source is your own code. `REAPER` and the `IEM Plug-in Suite` are external dependencies and should be obtained separately from their own sources.

## Citation And Research Use

If you reference this software in a paper, thesis, or artistic research submission, it is a good idea to cite both:

- the accompanying paper or exposition
- the GitHub repository or archived release of this software

For a stable scholarly reference, an archived GitHub release via `Zenodo` would be the cleanest next step.

## Research Context

This tool was created to support a supplementary listening package for a `JAR / Research Catalogue` submission. It is intended to help reviewers and readers compare static binaural reproduction with head-tracked binaural reproduction using the same Ambisonics source material and rendering chain discussed in the paper.

## Notes For Reviewers

- The current public build is `macOS` only.
- This is sufficient for the present supplementary listening package as long as the platform requirement is stated clearly.
- `REAPER` and the `IEM Plug-in Suite` must be installed separately.
- A static binaural reference render is recommended alongside the interactive head-tracked example.
