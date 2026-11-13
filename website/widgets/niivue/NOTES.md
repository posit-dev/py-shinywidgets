# NOTES: niivue guide

## Versions

- `ipyniivue` 2.4.4 (NiiVue frontend bundle 0.65.0), `nibabel` 5.x (via ephemeral `--with nibabel` overlay --
  not in the project's locked venv), `shinywidgets` @ `origin/main` detached worktree (commit `00f90249`),
  `shiny` 1.9.0.
- Browser: headless Chromium via Playwright, launched with `--use-angle=swiftshader
  --enable-unsafe-swiftshader --ignore-gpu-blocklist` -- required; plain headless Chromium renders a blank
  canvas for this widget (confirmed; matches the old report's finding).
- Dates: initial pass 2026-10-30; resumed and re-verified after an environment reset on 2026-11-02 (same
  worktree commit, fresh venv -- re-ran `01_quickstart.py` end-to-end with a real screenshot to confirm nothing
  regressed).

## Verification table

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a | n/a |
| `examples/02_slice_types.py` | yes | yes (both views) | radio click | n/a |
| `examples/03_stat_overlay.py` | yes | yes (before/after) | slider (via ionRangeSlider JS API) | n/a |
| `examples/04_mesh.py` | yes | yes | n/a | n/a |
| `examples/05_numpy_volume.py` | yes | yes | n/a | n/a |
| `examples/06_frame4d.py` | yes | yes (frame 0 vs 8) | slider | n/a |
| `examples/07_location_accessor.py` | yes | yes (before/after) | real click | yes -- `location()` |
| `examples/08_rate_limiting.py` | yes | yes | real click | yes -- `location()` with `rate_delay=0` |
| `examples/09_atlas_label.py` | yes | yes (before/after) | real click | yes -- `location()` |
| `examples/10_timeseries_4d.py` | yes | yes (before/after) | real click | yes -- `location()` |
| `examples/11_jump_crosshair.py` | yes | yes (before/after) | select dropdown | n/a (Python-to-widget, not an accessor read) |
| `gallery/template_mri_viewer.py` | yes | yes (default + clicked) | real click | yes -- `location()` |
| `gallery/showcase_atlas_explorer.py` | yes | yes (before/after jump) | select dropdown | n/a (confirms jump does *not* fire `location()`, as documented) |

The only accessor on this renderer is `location()`. It was driven with a real Playwright mouse click in five
different apps (07, 08, 09, 10, template) and with a synthetic burst is *not* retested here (already covered by
the existing Playwright test `tests/playwright/niivue_accessors/test_niivue_accessors.py`, which this guide
leans on for the debounce-coalescing claim rather than re-deriving it).

## Bugs found

None in shinywidgets on current `main`. Every `render_niivue` behavior documented in this guide matched its
docstring once checked in a browser; the one place the docstring's language is slightly looser than ideal is
`frac2mm()`/`mm2frac()`, where it says they "don't work" without naming the failure mode -- verified exactly:
`RuntimeError: Volume coordinate transformation matrices are not available...` once a volume is loaded, but a
silent, meaningless identity-based answer (`[0.0, 0.0, 0.0, 1.0]`) if called *before* any volume is loaded. Noted
in the Gotchas section since a user could hit either path depending on call order. This is a pre-existing
ipyniivue upstream quirk, not a shinywidgets regression, and not worth flagging as a "bug" exactly -- just
something to document precisely.

Judgment call: I verified (not just trusted) the docstring's claim that `scene.crosshair_pos` never reflects a
browser click server-side, by reading `reactive_read(nv.widget.scene, "crosshair_pos")` before/after a real click
and a real drag in a throwaway app -- it stayed `[0.5, 0.5, 0.5]` throughout. Confirmed correct.

## Judgment calls for the maintainer

1. **`frame_4d` screenshots (06) look nearly identical.** The pcasl ASL perfusion demo volume's frame-to-frame
   differences are genuinely subtle to the eye (noisy low-contrast signal, not a dramatic structural change). I
   kept it anyway because `frame_4d` is a real, useful trait and I didn't find a better public demo 4D volume on
   niivue.com with more visually obvious frame differences. If a punchier screenshot matters more than exact data
   provenance, consider synthesizing a 4D volume with a clearly animated feature instead.
2. **Atlas-label lookup does its own label-array indexing** (`AAL_LABELS[round(value)]`) rather than relying on
   ipyniivue's `LUT`/`colormap_label` + `atlas_labels` machinery on `MeshLayer`/`Volume`. I chose this because (a)
   it's fewer moving parts for a guide snippet, (b) it sidesteps needing to convert the AAL JSON's `R`/`G`/`B`
   flat-list format into ipyniivue's `LUT(lut=...)` flat RGBA format, and (c) I could verify it end-to-end in one
   pass. If the "real" way (loading a proper `colormap_label` so NiiVue's own `string` field includes the label)
   is more idiomatic, that's worth a second pass, but I did not find existing example code using it to confirm
   its exact shape.
3. **`nibabel` is not in the project's dependency groups for this directory's examples** (it's a general project
   test dependency, but I didn't rely on that — I added it as an ephemeral `--with nibabel` overlay per-run, per
   the coordinator's warning about not overlaying packages already pinned in the shared venv). Three examples (05,
   10, 11) and one gallery app need it; the guide prose calls this out at first use ("Installation" section) and
   each snippet's lead-in.
4. **Gallery `showcase_atlas_explorer.py` reuses the atlas-label and landmark-jump patterns from examples 09 and
   11 nearly verbatim**, combined into one app. This was a deliberate choice to keep the showcase demonstrating
   patterns already explained in the guide body, rather than inventing new behavior -- but it does mean the
   showcase isn't testing anything the examples don't already cover. If the maintainer wants the showcase to be
   more clearly differentiated, the most natural addition would be the 4D time-series pattern (10) too, which I
   left out to keep the showcase under ~100 lines.

## What I dropped from the old report and why

- **Transport/wire-weight benchmarking (exact MB figures per render).** The old report measured ~25 MB of
  websocket traffic per render in detail. I kept the qualitative finding ("every render sends the bundle plus
  every volume, and the browser re-uploads voxels afterward -- prefer in-place updates and `Volume(url=...)`") in
  Gotchas and "Updating the widget from Python," but dropped the exact byte-counting: it's a snapshot of one
  machine's measurement, not something a user can act on precisely, and the qualitative guidance is the
  actionable part.
- **Scorecard / star ratings.** Out of place for a teaching-focused guide aimed at "what's possible," not a PR
  review.
- **Re-render lifecycle / multi-session isolation / WebGL leak testing.** These were PR-readiness checks for a
  renderer that didn't exist yet; `render_niivue` is now a shipped, tested renderer (it has its own
  `tests/playwright/niivue_accessors/` suite), so re-deriving this from scratch would be redundant with existing
  test coverage rather than new guide content.
- **Upstream issue filing suggestions** (re-upload overhead, non-synced crosshair trait, swallowed callback
  exceptions). Still true and still worth filing upstream, but out of scope for a user-facing guide; the swallowed-
  exception behavior is already called out in Gotchas since a user can actually hit it.
- **The `download_dataset()`-based gallery app from the old report** was rewritten from scratch rather than
  adapted, since the old report predates the accessor API and predates `render_niivue`/`render_widget` as it
  exists on `main` today (it used the generic `render_widget`).

## Update 2026-11-11 (main @ 32ca7035)

- **`location()` is re-seeded at every render, not reset to `None` (#437).** The old guide (written against
  `00f90249`, before #437 landed) claimed `location()` is `None` until the user's first click and resets to
  `None` on re-render. Verified live this is now wrong on both counts: `NiiVue()` constructs with
  `scene.crosshair_pos == [0.5, 0.5, 0.5]` (confirmed directly), so `location()` is seeded from render with
  `{"frac": [0.5, 0.5, 0.5], "seeded": True}` -- a dict, never `None` -- and a re-render re-seeds back to that
  same center value rather than erasing to `None`. Fixed: the accessor reference table (new
  `before any interaction` / `across re-render` columns), the `location()` prose, and every `if loc is None`
  check in `examples/07_location_accessor.py`, `08_rate_limiting.py`, `09_atlas_label.py`,
  `10_timeseries_4d.py`, `gallery/template_mri_viewer.py`, and `gallery/showcase_atlas_explorer.py` (all
  switched to `loc.get("seeded")`).
- **New section "Reading on demand: bookmark the crosshair"** (`examples/12_save_location.py`): a button handler
  reads `brain.location()` with no prior reader anywhere in the app, demonstrating the no-warm-up headline
  capability from #437. Verified: two real clicks + two button presses produced two correctly formatted mm
  bookmarks in the rendered list.
- No other behavioral changes landed for `render_niivue` between `00f90249` and `32ca7035` (`shinywidgets/_niivue.py`
  and the `render_niivue` class in `_render_widget.py` are otherwise unchanged from what the original guide
  documented); everything else in the guide (slice types, overlays, meshes, numpy volumes, 4D frames, rate
  limiting mechanics, in-place updates, `frac2mm`/`mm2flat` failure, layout/sizing) was re-read against current
  `main` and still matches.
- `accessors:` front matter unchanged (`[location]`).

### Verification table (this update)

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/07_location_accessor.py` | yes | yes, refreshed (before/after) | real click | yes -- seeded dict before click, full payload after |
| `examples/08_rate_limiting.py` | yes | yes, refreshed | real click | yes |
| `examples/09_atlas_label.py` | yes | yes, refreshed (before/after) | real click | yes -- region card shows "Hippocampus R" |
| `examples/10_timeseries_4d.py` | yes (`--with nibabel`) | yes, refreshed (before/after) | real click | n/a (reads `vox`, same accessor) |
| `examples/12_save_location.py` (new) | yes | yes | real click x2 + button click x2 | yes -- two bookmarks recorded correctly |
| `gallery/template_mri_viewer.py` | yes | yes, refreshed (before/after) | real click | yes |
| `gallery/showcase_atlas_explorer.py` | yes (`--with nibabel`) | yes, refreshed (before/after jump) | select dropdown (landmark jump) | confirms jump still does not fire `location()` (region card unchanged after jump) |

Everything else in the directory (01-06, 11) is unaffected by this pass -- their code and screenshots were not
touched since they don't read `location()`.

### Bugs found (2026-11-11)

None. `location()`'s current behavior matches its docstring exactly (seed-at-render,
re-seed-on-re-render, debounce 250 ms); the old guide's claims were accurate for `00f90249` but stale against
`32ca7035`, which is a guide bug, not a shinywidgets bug.

## Editor's notes for the website

- Strongest sections: "Voxel value to atlas label" and "Jumping the crosshair from Python" -- both have clean
  before/after screenshots with an obvious, legible change (region name changes; crosshair visibly jumps to a
  different brain area). These are the best candidates for a hero GIF if the maintainer wants one later (a
  recorded drag on the quickstart app, or the landmark-jump dropdown, would both work).
- The hero image (`img/02_slice_types_render.webp`, the 3D cortical render) reads well at a glance and doesn't need
  a caption to be recognizable as "neuroimaging."
- Candidate to cut for a shorter page: the "4D volumes" highlight under "What you can build" (06_frame4d) is the
  weakest visual (see judgment call 1 above) -- if the page needs to shrink, cut that highlight and keep the 4D
  *time-series* pattern under "Coordinating multiple views" instead, since that one has a legible, convincing
  before/after (a plotted line appearing).
- `pairs with`: itables, reactable (table row selection could drive the landmark-jump pattern instead of a
  dropdown -- noted inline in "Coordinating multiple views").

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views," reusing the already-measured "~5 MB bundle +
base64-encoded volumes, every re-render" figure from "Gotchas and limitations" rather than re-measuring.
Classified primarily as GPU-in-the-browser (WebGL2), with `Volume(url=...)` and in-place updates called out as
the "only send what's visible"-adjacent mitigations this guide already teaches. No new example needed. Links
forward to the not-yet-written `../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same
wave) -- expected `check_docs.py` anchor warning.
