# NOTES: vizarr guide

## Versions

- shinywidgets commit: `00f90249` (2026-10-30), `main-wt` worktree
- shiny: 1.9.0
- vizarr: 0.1.1 (installed via `uv run --no-sync --with vizarr ...` overlay; not in the shared venv)
- zarr: 2.18.7 (pulled in by vizarr's `zarr<3` pin)
- Date verified: 2026-11-02 (session resumed mid-task after a scratchpad wipe; all screenshots in this
  directory were taken after the resume, against the same worktree commit)

## Install story

`vizarr` is declared in `pyproject.toml` as `vizarr = ["vizarr>=0.1.1"]` with a comment noting it pins
`zarr<3`, so it's excluded from the shared test/dev dependency groups. To run any of the examples:

```sh
uv run --no-sync --with vizarr python -m shiny run --port <port> examples/vizarr/<file>.py
```

Two gotchas specific to this extra, found while setting up:

1. **Use `python -m shiny run`, not the bare `shiny` console script.** `uv run --no-sync --with vizarr shiny
   run ...` silently ignores the overlay: `shiny` resolves to whatever's on `$PATH` first (often a different
   environment's console-script shim, which re-execs its own hardcoded interpreter), bypassing the ephemeral
   venv that `--with` builds. Routing through `python -m shiny run` forces the overlay's own interpreter.
2. **The overlay is clean.** The base worktree venv has no `zarr` at all (not partially installed), so
   `--with vizarr` resolves `vizarr>=0.1.1` and its `zarr<3` dependency without any conflict, and the
   overlay still imports the worktree's local `shinywidgets` correctly.

No fallback to `--no-project --with <path-to-worktree>` was needed -- the simple overlay worked throughout.

## Verification table

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `img/quickstart.webp` (= `img/hero.webp`) | n/a (static) | Real IDR dataset (idr0062), confocal z-stack, loads correctly with Z slider, channel colors/names from omero metadata |
| `examples/02_numpy_array.py` | yes | `img/numpy_array.webp` | n/a (static) | Plain grayscale ndarray renders correctly; channel name applied |
| `examples/03_multichannel_contrast.py` | yes | `img/multichannel_contrast.webp` | scroll-zoom to confirm pan/zoom works on a local store | 3-channel composite with correct per-channel colors from `omero` metadata |
| `examples/04_camera_view_state.py` | yes | `img/camera_before.webp`, `img/camera_after_panzoom.webp`, `img/camera_after_fly.webp` | yes: wheel-zoom + drag-pan, then button click | `reactive_read(view_state)` confirmed accurate after both gestures and a Python-side `.view_state =` set |
| `examples/05_add_layer_in_place.py` | yes | `img/addlayer_before.webp`, `img/addlayer_after.webp` | yes: zoom in, then click "Add overlay layer" | Confirmed: new layer appends, camera position identical before/after (in-place, no re-render) |
| `examples/06_channel_toggle_rerender.py` | yes | `img/contrast_before.webp`, `img/contrast_after.webp` | yes: zoom in, then drag the contrast slider | Confirmed: contrast changes, camera resets to vizarr's default fit view (see Bugs found) |
| `examples/07_linked_minimap.py` | yes | `img/minimap_before.webp`, `img/minimap_after.webp` | yes: scroll-zoom + drag-pan | Rectangle tracks the viewport correctly after interaction; before interaction the rectangle is near-degenerate (see Judgment calls) |
| `examples/08_linked_histogram.py` | yes | `img/histogram_before.webp`, `img/histogram_after.webp` | yes: scroll-zoom + drag-pan | Histogram shape changes plausibly between the full-image default and a zoomed crop |
| `gallery/template_ome_zarr_viewer.py` | yes | `img/gallery_template.webp` | yes: zoom, then "Reset view" button | Confirmed `.view_state =` reset works in place from a template-style app |
| `gallery/showcase_tissue_explorer.py` | yes | `img/gallery_showcase_before.webp`, `img/gallery_showcase_after.webp` | yes: zoom + pan | Minimap + histogram + channel selector together; verified channel selector reruns both plots correctly |

Accessor coverage: **not applicable** -- vizarr declares no accessors anywhere in `shinywidgets/_accessors.py`,
`shinywidgets/_shinywidgets.py`, or on `render_vizarr` itself (grepped for `vizarr` in both files: no hits
besides the renderer definition). Confirmed by reading `shinywidgets/_render_widget.py`'s `render_vizarr`
docstring, which documents only `reactive_read(.widget, "view_state")`.

Every gesture above was driven with real Playwright mouse/keyboard input (`mouse.wheel`, `mouse.down`/`move`/
`up`, `.click()`, keyboard arrow presses on the ion.rangeSlider handle) against a live `shiny run` process;
none were simulated by writing to the browser's widget model directly.

## Bugs found

### shinywidgets / docs

- **None found in shinywidgets itself.** `render_vizarr`'s docstring is accurate as far as we tested: the
  `view_state` debounce, the data-source handling (URL vs. local array), the `shinywidgets-vizarr` CSS marker
  class, and the fill/height interaction all matched observed behavior.

### Upstream (vizarr) -- not a shinywidgets bug, but worth flagging for the guide reader

- **A fresh `Viewer`'s camera can't be reliably set before or immediately after it's first shown.** We
  verified this directly (see the long debugging trail that produced the final, honest framing in "Updating
  the widget from Python" / "Gotchas"): vizarr's `viewer.on("viewStateChange", ...)` fires once on mount,
  reporting deck.gl's own default "fit the whole image" camera back to Python, *after* any `view_state` you
  set during construction. A naive "save camera to a reactive.Value, restore it on the new widget" pattern
  works in some runs and loses the race in others, because the restore and the browser's own default report
  can land in either order depending on timing. We built and discarded three increasingly complex workarounds
  (direct restore on mount; restore on first non-empty report; restore-once-per-widget-id with an
  ignore-first-report guard) -- the last one passed a simplified single-interaction test but still failed
  under the exact gesture sequence used in the final guide screenshot (5 rapid slider presses). We chose not
  to ship a workaround that isn't reliably reproducible and documented the reset as expected behavior
  instead. This is a genuine, reproducible finding, not a hypothetical edge case -- but per the brief's
  guidance to weigh value against complexity, we judged a timing-dependent fix not worth presenting as fact
  in a teaching document.
- **`add_image()`'s per-call config kwargs have two different, undocumented shapes.** For an OME-NGFF store
  with real channel-axis + `omero` metadata, the JS expects plural keyed-by-channel lists: `colors`,
  `contrast_limits`, `visibilities`. For a plain array with no channel axis, the same concepts are *singular*:
  `color` (a string hex or name, not a list), `contrast_limits` as one flat `[min, max]` (not nested),
  `visibility`, `opacity`. We found this by grepping the minified bundle served from
  `https://hms-dbmi.github.io/vizarr/` (not from source, since the repo wasn't cloned locally) and confirming
  it empirically: passing plural keys to a plain array is silently ignored (no error, wrong/default
  rendering), which cost significant debugging time before we identified the split. This isn't mentioned in
  vizarr's README. We recommend the guide's documented path (write real `omero` metadata) over using these
  kwargs directly, and flag the split in "Gotchas and limitations."
- **Docstring claim verified correct**: "the layer controls in the viewer's side panel (channel colors,
  contrast limits, visibility) do *not* sync back to Python" -- confirmed; we found no trait or event that
  reflects side-panel changes.

## Judgment calls

- **Dataset choice for the recurring "nuclei" examples (04-08).** Rather than reusing the shipped
  `examples/vizarr/app.py`'s exact synthetic-tissue generator in every snippet, each file regenerates a
  smaller, single- or dual-purpose synthetic image inline, to keep snippets closer to the 10-40 line target.
  The multichannel OME-NGFF generator (3 channels, `omero` metadata) is reused verbatim across
  `03_multichannel_contrast.py` and the showcase gallery app. The maintainer may prefer factoring this into a
  single `_nuclei.py`/`_tissue.py` helper imported by multiple examples instead -- we kept each file
  self-contained per the brief's "snippets must run exactly as shown" rule, which make a shared helper file
  awkward (it would need to ship alongside every example that imports it).
- **The minimap/histogram "viewport size" conversion (`CANVAS_PX`) is an approximation**, not an exact read of
  the on-screen canvas pixel size (Python doesn't have that). We call this out explicitly in the guide's
  "Coordinating multiple views" intro. The minimap's rectangle is correct in shape and roughly correct in
  position/size, but will drift from the true viewport edges if the card is resized from the hardcoded
  assumption. This is good enough to be a compelling, honest illustration of the pattern, not a
  pixel-accurate instrument.
- **`06_channel_toggle_rerender.py` deliberately does not attempt to preserve the camera.** See "Bugs found"
  above for the full investigation. We considered shipping the "restore once per widget id, ignoring the
  first report" version since it worked in an isolated test, but it failed under the actual gesture sequence
  used for the guide's own screenshot, so including it as "the pattern" would have taught something we
  couldn't verify held up. Flagging this explicitly in case the maintainer wants to revisit with more time, or
  knows a cleaner sequencing hook we missed.
- **Gallery: one template + one showcase**, both making real use of the `reactive_read(view_state)` tier
  (there being no accessors to exercise). The showcase combines both linked-view patterns from the guide body
  (minimap + histogram) plus a channel selector, rather than inventing a third pattern, to keep it reusable
  and to cross-reference the guide body directly.
- **Category**: used "3D & scientific" per the brief's roster (vizarr is explicitly listed there), even though
  the images here are strictly 2D+channel+Z, not 3D meshes/volumes like most guidefellows in that bucket.

## Editor's notes for the website

- **Strongest material**: the quick start (real IDR data, zero-config, looks great immediately) and the
  add-layer-in-place vs. re-render pair -- that contrast is the single most teachable thing about vizarr's
  current API shape, and the screenshots make the in-place camera preservation obvious at a glance.
  `04_camera_view_state.py`'s three-screenshot sequence (before / after gesture / after button) is also strong
  and could become the hero GIF candidate if the coordinator wants an animated hero later.
- **Candidate for cutting if the page needs to shrink**: the "Z-stacks and resolution pyramids" bullet under
  "What you can build" has no dedicated example/screenshot of its own (it points back to the quick start's `Z:
  118/235` slider) -- fine as a one-paragraph mention, but it's the thinnest part of the feature tour and could
  be dropped without losing a verified claim.
- **Gotchas section is unusually long** for this guide relative to its feature surface, because vizarr's
  Python API is genuinely small (one class, one real method, one synced trait) but has several sharp,
  verified edges. We'd keep all of it -- every bullet there is something we hit and confirmed, not a
  hypothetical.
- **Pairs with**: `plotly` or `matplotlib` (viewport-driven histograms/analysis, as in the linked-view
  section), `lonboard`/`maplibre` (contrast of "pixel array viewer" vs. "geospatial raster/vector viewer" for
  a cross-cutting "viewers for big imagery" article).

## Update 2026-11-11 (main @ 32ca7035)

- **Converted every `reactive_read(viewer.widget, "view_state")` to `viewer.read("view_state")`**, per the
  update brief's instruction that `.read()` replaces `reactive_read(x.widget, "trait")` as the taught fallback
  wherever a renderer output exists. Touched: `examples/04_camera_view_state.py`, `examples/07_linked_minimap.py`,
  `examples/08_linked_histogram.py`, `gallery/template_ome_zarr_viewer.py`,
  `gallery/showcase_tissue_explorer.py`, and every matching snippet in `guide.md` (the "Beyond accessors"
  section heading is now "`.read()`" instead of "`reactive_read()`", and the accessor-reference-adjacent prose
  throughout was updated to match).
- **Simplified the manual `viewer.widget is None` / `req(viewer.widget is not None)` guards away.** `.read()`
  already cancels on its own (via the `.widget` property's `req(False)`) before the viewer has rendered, so the
  separate pre-check these examples previously needed is redundant once converted -- removed it from all five
  files rather than leaving dead code next to the new call. `04` and the template still keep a `if not vs:
  return "loading..."` check for the *different* case of a widget that exists but hasn't sent its first
  `view_state` report yet (`{}`, truthy-falsy, not a `None`/not-rendered case).
- **Verified live that `.read("view_state")` fires identically to the old `reactive_read()` call**: confirmed
  `widget.has_trait("view_state")` is `True` (so `.read()` takes the same `reactive_read()` branch internally),
  then ran all five touched files end to end with real pan/zoom gestures and, for `04_camera_view_state.py`,
  the "Fly to center" button. All five produced correct, re-screenshotted output (new before/after/fly
  screenshots for `04`; new before/after for `07`, `08`, the showcase; a fresh single screenshot for the
  template). No regression versus the pre-#437 `reactive_read()` screenshots.
- vizarr was importable directly from the worktree's shared venv this pass (no `--with vizarr` overlay
  needed) -- the dependency landscape noted in "Install story" above may have changed since the original pass
  (`uv sync --all-groups --all-extras` now appears to include it); not independently investigated further
  since it isn't relevant to this update's scope.
- No accessors exist on `render_vizarr` on current `main` either (confirmed: still no hits for `vizarr` in
  `shinywidgets/_accessors.py`), so the "no accessors, `.read()` is the whole story" framing is unchanged, just
  retitled from the `reactive_read()`-era wording.
- `accessors:` front matter unchanged (`[]`).

### Bugs found (2026-11-11)

None new. The upstream camera-reset-on-re-render race and the `add_image()` kwarg-shape split documented in
the original pass are unrelated to the accessor redesign and were not re-tested this pass (no code in this
guide's examples touches either path differently than before).

## Dropped from the old report

There is no old report for vizarr in `docs/widget-reports/` (confirmed: the directory exists but is empty).
Nothing was dropped.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." This is the cleanest "only send what's visible"
example in the roster (multiscale OME-Zarr, chunk-on-demand), so the section leans on that framing and reuses
the already-measured "~33% more bytes for local arrays over the comm vs. direct browser fetch for remote URLs"
figure from "Gotchas and limitations" rather than re-measuring. No new example needed. Links forward to the
not-yet-written `../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) --
expected `check_docs.py` anchor warning.
