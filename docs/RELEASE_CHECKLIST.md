# Release Checklist

## Before Release

- Verify the app launches correctly on macOS
- Confirm camera permission prompt appears as expected
- Confirm tracking works with `IEM SceneRotator` on port `7000`
- Confirm `Calibrate` and `Recenter` behave as intended
- Rebuild icon if needed
- Rebuild `.app`
- Check README for current wording and links

## GitHub Release

- Create or update tag `v0.2-beta`
- Create GitHub Release titled `SceneRotator HeadTracker v0.2`
- Upload `SceneRotatorHeadTracker-macOS-v0.2.dmg`
- Verify the download URL:
  `https://github.com/joambi/SceneRotatorHeadTracker/releases/download/v0.2-beta/SceneRotatorHeadTracker-macOS-v0.2.dmg`
- Keep large `.dmg` and `.zip` files out of the normal Git repository

## Optional Research Archiving

- Archive the GitHub release with `Zenodo`
- Add DOI to the paper and repository README
