# NOTES: aoi-workbench

- Promoted from `docs/widget-guides/leafmap/gallery/showcase_aoi_workbench.py`, unchanged
  except the `# Run` header (now points at this directory's own `app.py`, and drops
  `scipy`/`shapely`/`plotly` from the `--with` list since those three are already in the
  shared worktree's base venv -- only `leafmap`, `rioxarray`, and `localtileserver` are
  genuinely missing there).
- Re-verified 2026-11-02 in `main-wt`: leafmap 0.64.0 (resolved fresh via `--with leafmap`;
  the leafmap guide's own NOTES.md used 0.63.1 and found no leafmap-version-sensitive
  behavior, so the bump is not expected to matter here), ipyleaflet 0.20.0, rioxarray/xarray/
  scipy/shapely (already-locked versions), localtileserver (fresh via `--with`).

## Bugs found

- **[authoring note, not a shinywidgets bug]** The first run failed with
  `localtileserver is not installed` even though the app's own imports never mention
  `localtileserver` -- `leafmap.Map.add_raster()` uses it internally for local COG files.
  The original guide's run-command header already listed `localtileserver` in its `--with`
  list; I had trimmed it along with the genuinely-redundant `scipy`/`shapely`/`plotly` and
  had to add it back. Recorded here so a future promotion of this app doesn't repeat the
  same trim-too-far mistake.
- One transient `uv` install failure (`Failed to read directory .../archive-v0/...: No such
  file or directory`) on the first launch attempt, consistent with concurrent agents
  contending for the shared `uv` cache under load; resolved on an immediate retry per the
  brief's "re-run once in isolation before calling it a bug" guidance. Not a shinywidgets or
  leafmap bug.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + raster renders | yes (Playwright) | `#map .leaflet-container` visible, `img/hero.webp` |
| Draw a rectangle AOI | yes (real mouse down/move/up on the leaflet-draw rectangle tool) | `#stats_table` goes from empty to `aoi=1, mean=471.7, min=290.1, max=734.3, pixels=11880`, and `#stats_chart` shows a populated bar -- `img/after_draw.webp` |

## Judgment calls

- Did not re-verify the `band` radio recompute (switching Elevation/Slope/Moisture for an
  already-drawn AOI) in this pass; the leafmap guide's own verification already covers the
  per-band raster restyle, and this promotion's gesture budget went to the drawn_features()
  accessor itself, which is the showcase's headline feature.
