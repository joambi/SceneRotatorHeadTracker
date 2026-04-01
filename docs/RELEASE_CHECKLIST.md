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

- Create tag `v0.1`
- Create GitHub Release titled `SceneRotator HeadTracker v0.1`
- Upload `SceneRotatorHeadTracker.app` or a zipped macOS app bundle
- Paste the contents of `RELEASE_NOTES_v0.1.md`

## Optional Research Archiving

- Archive the GitHub release with `Zenodo`
- Add DOI to the paper and repository README

