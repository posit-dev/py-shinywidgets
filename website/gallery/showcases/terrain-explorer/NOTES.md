# NOTES: terrain-explorer

- Promoted from `docs/widget-guides/k3d/gallery/showcase_terrain_explorer.py`, unchanged
  except the `# Run:` header line. The k3d guide's own INVESTIGATION.md found (and later
  revised) a bug about custom widget messages sent synchronously during render being
  dropped; this showcase doesn't send any messages during render (the `click_callback` is
  attached via a constructor kwarg, and `start_auto_play()`-style calls aren't used here),
  so it isn't affected.
- Re-verified 2026-11-02 in `main-wt`: k3d 3.2.0, matplotlib (locked), numpy (locked). No
  `--with` overlay needed.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + terrain renders | yes (Playwright, swiftshader WebGL flags) | `#terrain canvas` visible, `img/hero.webp` |
| Click "Fly to highest point" | yes | `#camera_out` changes to `6.9 / 1.4 / 9.0`, a marker appears at the peak, `img/after_peak.webp` |
| Real click on the terrain surface | yes | `#picked` changes from `"None (click the terrain)"` to `"elevation: 1021 m\nrow, col: 139, 108"`, `img/after_click.webp` |

## Judgment calls

- None beyond the header-line edit.

## Update 2026-11-11 (main @ 32ca7035)

- **Narrative fix**: `camera_out()` used `reactive_read(terrain.widget, "camera")`, the old
  taught fallback. k3d now has a named `camera()` accessor (`_accessor_specs = (K3D_CAMERA,)` in
  `shinywidgets/_render_widget.py`), so switched to `terrain.camera()` (tier 1) and dropped the
  now-unused `reactive_read` import.
- Verified with Playwright (swiftshader WebGL flags): orbit-drag changed `#camera_out` from
  `16.0/-18.0/14.0` to `8.2/-25.0/8.5`; "Fly to highest point" then changed it to
  `6.9/1.4/9.0` -- the exact figures the 2026-11-02 verification table above recorded for the old
  `reactive_read()` call, confirming identical behavior. No console/server errors.
- Accessors: `terrain.camera()` -- verified with a real gesture (orbit + fly-to button), values
  read from the rendered `#camera_out` output.
