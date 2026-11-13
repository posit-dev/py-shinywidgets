# Verification notes

- Source: promoted from `docs/widget-guides/k3d/gallery/template_point_cloud_explorer.py`. Header
  reformatted to the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync --with scikit-learn
  shiny run app.py`, port 10081, Chromium launched with
  `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` (WebGL needs
  software rendering in this headless environment).
- First click attempts at fractional canvas coordinates landed in empty space ("None (click a
  point)", `img/hero.webp`). Recalibrated against a reference screenshot of the dense red cluster
  and clicked the exact page pixel: produced "setosa (#43) [5, 3.5, 1.6]" (`img/after.webp`).
  `plot.camera()` populated correctly in both screenshots.
- `--with scikit-learn` is unpinned (not in the locked venv); used only for `load_iris`, a stable,
  low-risk dependency for this purpose.

## Update 2026-11-11 (main @ 32ca7035)

- **Doc-only fix**: the app's `# Pattern:` comment and the README front matter's `pattern:` field
  both said `reactive_read(camera)`, but the code already called `plot.camera()` (k3d's named
  accessor) -- stale label, not stale code. Corrected both to `plot.camera()`.
- Re-verified with Playwright (swiftshader WebGL flags): `#camera_out` read
  `"12.4, -6.2, 4.6, 6.1, 3.2, 4.0, 0.0, 0.0, 1.0"` on load, no console/server errors. Did not
  re-drive the click gesture (code path unchanged; already verified 2026-11-02).
- Accessors: `plot.camera()` -- re-verified (boot only, label fix); not previously mislabeled in
  code, only in the comment/front-matter text.
