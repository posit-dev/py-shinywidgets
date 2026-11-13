# NOTES: pyvista guide

## Versions used

- pyvista 0.49.2
- **trame-pyvista: 0.3.4** (Python 3.12, resolved by `uv sync --all-groups` against current `main`'s lockfile --
  the lockfile pins 0.2.3 only for `python_full_version < '3.11' or >= '3.15'`; 3.11-3.14 get 0.3.4). This matters:
  0.3.x is a rewrite of `EmbeddableWidget` from a plain `ipywidgets.HTML` subclass to an `anywidget.AnyWidget`
  with a process-wide shared "viewer page" widget, carrying real behavioral differences from what an older
  venv/report would show (see Bugs found #1).
- shiny 1.9.0, shinywidgets @ main (00f90249), Python 3.12.13
- Dates: most verification 2026-10-30; the multi-session investigation and final write-up 2026-11-02, after a
  session restart recreated the worktree with a fresh `uv sync` (which is how the trame-pyvista version bump was
  discovered -- the pre-restart venv had 0.2.3 installed, stale relative to the current lockfile).

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | drag-rotate verified in k3d-style smoke test (not re-screenshotted) | re-verified visually identical after the trame-pyvista version bump |
| examples/02_scalar_coloring.py | yes | yes | n/a (static) | |
| examples/03_isosurface_contour.py | yes | yes | n/a (static) | CT download + downsample verified fast (cached after first run) |
| examples/04_glyphs_streamlines.py | yes | yes | n/a (static) | kitchen CFD dataset + split multiblock geometry for context |
| examples/05_glyphs.py | yes | yes | n/a (static) | iterated twice to get a readable vortex field (first attempt had a degenerate center spike) |
| examples/06_multiblock.py | yes | yes | n/a (static) | switched from the kitchen furniture multiblock (visually abstract) to a synthetic 3-part assembly |
| examples/07_coordinate_threshold_stats.py | yes | yes (before/after) | yes -- real slider drag via Playwright, stats text changed (38,748 -> 5,340 triangles) | |
| examples/08_coordinate_clip_stats.py | yes | yes (before/after) | yes -- real slider drag, stats text changed (76,588 -> 31,289 points) | |
| examples/09_coordinate_scalar_choice.py | yes | yes (before/after) | yes -- real `select_option()`, stats + colorbar changed | |
| examples/10_camera_presets.py | yes | yes (before/after) | yes -- real drag-rotate + button click, confirmed camera resets to the clicked preset, not the dragged angle | also found: clicking the *same* preset twice is a no-op (reactive.value.set() short-circuits on equal value) |
| examples/11_layout_sizing.py | yes | yes | n/a | confirmed via JS measurement (`offsetWidth/Height`) that `height="250px"` constrains both the output and the iframe to exactly 250px -- the full-page screenshot's apparent extra whitespace is just an empty fillable page below a short card, not a sizing bug |
| examples/12_multisession_workaround.py | yes | yes (renders) + two dedicated multi-session Playwright drivers | n/a | see Bugs found #1; verified to fix both the concurrent-session and reconnect-after-close failure modes |
| gallery/template_isosurface_explorer.py | yes | yes | n/a (reuses 07's verified interaction) | |
| gallery/showcase_terrain_explorer.py | yes | yes (before/after) | yes -- slider drag + select_option together, stats/histogram/colors all updated in the after screenshot | |

No accessors exist for this renderer (confirmed: zero entries reference `pyvista` in `shinywidgets/_accessors.py`
or any `_accessor_specs`), so the brief's "drive a real gesture, confirm the accessor fired" requirement doesn't
apply; instead every "Coordinating multiple views" and "Updating the widget" example was gesture-driven (real
Playwright slider drags / `select_option()` / button clicks / mouse-drag rotation) with before/after screenshots
and, where applicable, a text readout confirming the server-side value actually changed.

## Bugs found

### 1. Multi-session breakage with current-main's resolved trame-pyvista (shinywidgets + trame-pyvista interaction) -- **regression, high severity**

Confirmed, reproducible, not a flake (ran each scenario twice). Root cause: trame-pyvista >= 0.3 renders through
an `anywidget`-based `EmbeddableWidget` whose `_viewer_page` trait references a **process-wide singleton**
(`trame_pyvista.jupyter._ViewerPage`, caching the ~400 KB vtk.js runtime so it isn't resent on every render --
itself a nice improvement, see Judgment calls). shinywidgets' session-ownership model (`_shinywidgets.py`) treats
that singleton like any other widget: owned by whichever session first constructs it. Verified two failure modes
with a Playwright driver running two `BrowserContext`s against one `shiny run` process:

- **Concurrent**: session A renders a pyvista plot; session B (opened while A is still connected) gets
  `RuntimeError: _ViewerPage belongs to another Shiny session, so it can't be displayed here.` in that one output.
- **Sequential**: session A renders, then **disconnects**; session B connects afterward and gets
  `RuntimeError: _ViewerPage was closed (its render was invalidated, or it was closed explicitly), so it can't be
  displayed again.` -- i.e. the app is broken for every visitor after the first one leaves, until the server
  process restarts. This is the more important case: it doesn't require true concurrency, just two sequential
  visits, which is the normal lifecycle of almost any deployed Shiny app.

**Workaround found and verified (Shiny Core only):** construct one throwaway `Plotter`, coerce it with
`as_widget()`, inside `shinywidgets.shared_lifetime()`, at true top-level module scope (i.e. before `App(ui,
server)` -- see `examples/12_multisession_workaround.py`). This runs with no Shiny session active at all, so
`shared_lifetime()`'s `constructing_shared` contextvar reaches the branch in `init_shiny_widget()` that registers
a sessionless, shared-context widget straight into `SHARED_WIDGETS` -- the same path that gives `ipyvue`/
`ipyvuetify`/`lonboard`/`ipycanvas`/`nglview` their import-time singletons. Verified fixed: both the concurrent
and the reconnect-after-close scenarios pass with this file.

**Does not reliably work in Shiny Express.** Traced why: an Express script's top-level code always runs with
`get_current_session()` returning a **non-`None` `ExpressStubSession`**, even for the very first statement
executed (confirmed by printing `get_current_session()` from inside the warm-up block) -- so the `if session is
None:` branch in `init_shiny_widget()` (the one that actually does the `SHARED_WIDGETS` registration for
sessionless construction) is never reached; execution instead hits `if session.is_stub_session(): return` and
exits having registered nothing, regardless of `shared_lifetime()`. I also tried moving the warm-up into a
`@reactive.effect` (which does run with a real, non-stub session) -- this fixed the sequential reconnect case but
**not** the true-concurrent case, because success then depends on which session's code happens to touch
`trame_pyvista`'s internal cache first process-wide, a race the app has no control over. I did not find a
reliable Express-side fix and say so plainly in the guide rather than recommend something flaky.

**Suggested fix location**: `shinywidgets/_shinywidgets.py` already has exactly the right abstraction for this
(`IMPORT_TIME_WIDGET_PACKAGES`, `EAGERLY_SHARED_PACKAGES`, `is_import_time_singleton()` -- see the comment there:
"packages with process-global registry widgets"). Adding trame-pyvista's `_ViewerPage` to that list (keyed by,
e.g., `type(w).__module__ == "trame_pyvista.jupyter"` and `type(w).__name__ == "_ViewerPage"`) would make it
process-global automatically regardless of which session or app style first constructs it, with no user-facing
workaround needed. I did not attempt this fix myself per the brief's "report, don't fix" instruction.

**Why this wasn't in the old report** (`docs/widget-reports/pyvista/report.md`, dated 2026-10-22, scorecard says
"Multi-session: fully isolated, verified"): that review's venv had trame-pyvista 0.2.3 (the pre-rewrite,
plain-`ipywidgets.HTML` version with no shared internal widget), so the bug class didn't exist yet. I only found
this because the coordinator's session-restart recreated the worktree with a fresh `uv sync`, which resolved a
newer trame-pyvista for this Python version than my original (stale) venv had -- this is worth flagging to the
maintainer as exactly the kind of "stale local venv passes, fresh install doesn't" gap called out in CLAUDE.md.

### 2. Performance characterization in the old report is stale (not a bug, but corrects prior documentation)

The old report's "~1.1 MB floor + ~19 KB/1000 cells, every render" framing was accurate for trame-pyvista 0.2.3
but is now misleading for 0.3.4 (the version current `main` actually resolves for Python 3.11-3.14): the ~400 KB-
1.2 MB "floor" (the vtk.js runtime) is now sent once per browser session, not once per render. A tiny unchanged
mesh re-renders for ~12 KB; a 39k-triangle isosurface re-renders for ~800 KB (consistent with the old per-cell
rate, just without the extra floor stacked on each time). Measured via Playwright's `framereceived` websocket
events, summed over an initial render and a subsequent re-render, repeated to confirm stability. This is a
genuine improvement worth documenting accurately rather than carrying the stale number forward -- see the
Performance note in "Reacting to user interaction."

### 3. Docstring is accurate (no doc bugs found)

`render_pyvista`'s docstring in `_render_widget.py` holds up on every claim I checked: `.show()` returning `None`
outside Jupyter, the closed-`Plotter` pre-check and its message, `pyvista_layout_defaults`'s `isinstance` guard,
the "no accessors / no reactive_read target" framing. No corrections needed here (contrast with the brief's
warning that docstrings can be wrong elsewhere in this project).

## Judgment calls

- **Chose a synthetic 3-part assembly (cylinder/cylinder/sphere) over the kitchen-furniture `MultiBlock`** for
  the dedicated "multi-block" highlight, after rendering the furniture version and finding it visually abstract
  (disconnected colored planes/boxes, hard to read as "a kitchen" without walls or a floor). The kitchen
  `MultiBlock` is still used, combined and made translucent, as context geometry in the streamlines highlight,
  where it reads fine as "the room" behind the flow. Worth revisiting if the maintainer wants a single dataset to
  carry both the multi-block and streamlines stories.
- **Did not add a dedicated "camera/picks come back to Python" exploration beyond what's in the guide.** The
  assignment asked me to verify this if I found any way. I inspected the actual `EmbeddableWidget` instance
  (traits: `scene`, `iframe_style`, `_viewer_page`, none set by the browser) and the `window.widgetManager`
  model for it in Chromium -- confirmed there is nothing writable from the browser side at all, not even in
  principle (no JS code in `_SCENE_ESM` ever calls `model.set()`/`model.save_changes()`). I'm confident this is a
  structural "no," not a gap in my search.
- **Treated the multi-session bug as a "report, don't fix" finding** per the brief, even though I found and
  verified a workaround. I spent real effort characterizing exactly when the workaround does and doesn't apply
  (Core vs. Express) rather than just linking the gotcha, since a half-right workaround recommendation would be
  worse than a precise one. Flagging in case the maintainer wants this trimmed for length in the public guide --
  it's long for a "gotcha," but I think the severity (breaks after the first visitor leaves) justifies the space.
- **Performance numbers are approximate and environment-dependent** (machine load, exact mesh), stated as such
  in the guide ("roughly," "measured fresh against current main"). I did not try to pin down tighter bounds.

## What I dropped from the old report and why

- The detailed "scorecard" table (stars per dimension) -- doesn't fit this guide's format, and multi-session is
  now a real asterisk rather than a clean 5-star row.
- Exact payload-math constants ("~1.1 MB floor + ~19 KB/1000 cells") -- superseded by fresh 0.3.4 numbers (see
  Bugs found #2).
- `as_widget_pyvista` nits about `TypeError` message wording and `isinstance` guards in `pyvista_layout_defaults`
  -- both already fixed on current `main` (verified by reading `_as_widget.py` and `_render_widget_base.py`
  directly; the type-name-only error and the `isinstance(widget, EmbeddableWidget)` guard are both present).
- The gallery "parametric surface explorer" app (six `pv.Parametric*` surfaces + resolution/colormap/style
  controls) -- solid app, but didn't demonstrate a coordination pattern (no paired Python-computed output), which
  this pass of the roster treats as the higher-value thing to show. Replaced with the terrain explorer showcase,
  which demonstrates three coordination patterns on one real dataset instead.

## Pairs with

- **k3d, ipyvolume, pythreejs** (3D & scientific siblings) -- all three keep a live browser-to-Python connection
  and expose a `camera()` accessor (pythreejs and k3d) or `reactive_read()` target (ipyvolume); pyvista's html
  backend is the one 3D renderer in the roster with no such channel at all. Good material for a cross-cutting
  "which 3D renderer" article.
- No cross-widget linked-view pairing built (map/table driving the 3D view) -- didn't find a natural, non-forced
  pairing given the one-way data flow; the "Coordinating multiple views" patterns pair the 3D view with plain
  Shiny outputs (`@render.code`, `@render.plot`) instead, which is the more honest story for this renderer.

## Update 2026-11-11 (main @ 32ca7035)

Versions: shinywidgets `main` @ `32ca7035`, pyvista 0.49.2, **trame-pyvista 0.3.6** (confirmed with
`uv pip list` in the worktree -- the `trame-pyvista<0.3` pin this guide's "Bugs found #1" and `FIX.md`
describe is gone; `pyproject.toml` now floors `trame-pyvista>=0.3` for Python 3.11-3.14 only, and pyvista is
excluded from the extra entirely below 3.11), shiny 1.9.0, Python 3.13, shared `main-wt` worktree. Playwright:
Chromium headless with `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`.

**What changed in the guide and why:**

- **The multi-session regression (this guide's `FIX.md` and "Bugs found #1") is fixed on current main (PR
  #410) -- removed the Gotchas bullet and the `shared_lifetime()` workaround entirely**, per the brief
  ("workarounds for this can go"). Re-verified end to end with **two separate Playwright browser contexts**
  (separate cookies/sessions, not just two tabs) against the plain quick-start app:
  - **Concurrent**: context A and context B both open the app while both stay connected. Before the fix,
    B's output showed `RuntimeError: _ViewerPage belongs to another Shiny session`. Now: both render the
    sphere, zero console errors, zero `RuntimeError` text in either page.
  - **Sequential (the more realistic case -- no concurrency needed)**: context A opens and renders, then A
    closes (simulating a tab close), then a **new** context C opens the app afterward. Before the fix, C's
    output showed `RuntimeError: _ViewerPage was closed ... can't be displayed again`. Now: C renders
    correctly (screenshot confirms a visible, correctly shaded sphere), zero errors.
  - Probe files (not committed): `scratchpad/agents/threed/probe/pyvista_multisession.py` +
    `check_multisession.py`.
- **Deleted `examples/12_multisession_workaround.py`** -- it existed solely to work around the now-fixed bug,
  recommended a pattern that didn't even reliably work in Shiny Express, and would actively mislead a reader
  into adding unneeded, Core-only boilerplate. No replacement example needed; nothing to work around.
- **Installation section**: added the Python 3.11-3.14 floor (`trame-pyvista>=0.3` requires 3.11+; `vtk`
  still lacks 3.15+ wheels) -- this guide previously mentioned only the 3.15+ upper bound, not the new 3.11+
  lower one that came with dropping the 0.2.3 pin.
- Updated the trame-pyvista version references (0.3.4 -> 0.3.6/0.3.x) and the Gotchas verification-date line.
- Left the performance note's re-render payload sizes (~12 KB unchanged mesh, ~800 KB isosurface) as the
  original author measured them: the fix in this update's range changes *session ownership*, not export
  size, and a spot re-measurement (quick-start sphere, websocket frame capture) showed the same
  order-of-magnitude payload on a re-render with no 400 KB-plus runtime re-send, consistent with the existing
  numbers.

**Re-verified claims (all with a real browser, this pass):**

- Multi-session fix (#410): see above, two-context concurrent + sequential-reconnect, both clean.
- Quick-start sphere's re-render payload stays small (no vtk.js runtime re-send): spot-checked via websocket
  frame-size capture, largest re-render frame ~30 KB vs. ~414 KB for the runtime on first load.

## Bugs found (2026-11-11)

None. The one bug this guide tracked (`FIX.md`, "Bugs found #1") is confirmed fixed, closing it out.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views," reusing the already-measured re-render payload
numbers from "Performance: cache the mesh, gate expensive re-renders" (~12 KB unchanged mesh, ~800 KB for a
39k-triangle isosurface) rather than re-measuring. Classified as "summarize on the server" (decimate/downsample
before export) since pyvista's html backend has no GPU-streamed or viewport-culled path. No new example needed.
Links forward to the not-yet-written `../articles/performance/article.md#three-approaches-to-large-data` (Task
7, same wave) -- expected `check_docs.py` anchor warning.
