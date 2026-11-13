# NOTES: k3d guide

## Versions

- shinywidgets: `main` @ `00f90249` (2026-10-30/11-02; the run worktree was detached at this commit throughout,
  including after a mid-task scratchpad/worktree reset -- same commit both times, so all findings are against one
  consistent state of `main`).
- k3d: 3.2.0 (the anywidget-based release)
- shiny: 1.9.0
- matplotlib: whatever version ships in the `test` dependency group (used only for its bundled sample DEM data and
  colormaps, not for plotting)
- scikit-learn: **not** in the project venv; examples that use `sklearn.datasets.load_iris` (01, 12, and the
  template gallery app) were run with `uv run --no-sync --with scikit-learn ...` (an ephemeral overlay, not added to
  the lockfile). Per the coordinator's mid-run note, I double-checked this was the right call: scikit-learn was
  confirmed absent from the worktree venv (`ModuleNotFoundError`) before reaching for `--with`, so this did not
  silently override a pinned version the way an unpinned `--with duckdb` did in another guide's run.
- Playwright: Chromium, headless, default SwiftShader software rendering -- **no special launch flags were needed**
  for WebGL (confirmed: a stock `chromium.launch(headless=True)` renders k3d scenes correctly, including 1M-point
  clouds). This matches the old report's finding.
- Screenshots: 1280x800 (narrower for some gallery/accessor shots), `device_scale_factor=2` unless noted.

## Operating note: mid-task environment reset

Partway through this run, the coordinator's session restarted and the scratchpad (my scratch dir and all throwaway
probe scripts) was wiped; the run worktree (`main-wt`) was recreated fresh at the same commit (`00f90249`) with a
newly-synced venv. I verified my assigned port range (9580-9599) was free, recreated my scratch helpers, and
resumed from the already-written `docs/widget-guides/k3d/` output (which survived, since it's outside the
scratchpad). Examples 01 through roughly 13 (click-to-table) were built and screenshotted before the reset; I
re-verified the ones most likely to be affected by subtle timing bugs (anything using a widget callback or an
early-running effect) after the reset, and built the remaining examples, both gallery apps, and this NOTES.md
afterward. No content in `guide.md` depends on anything that didn't survive the reset.

A second pass, after the guide and these notes were first handed back, corrected two findings against an
independent follow-up investigation (`docs/widget-guides/k3d/INVESTIGATION.md`, provided by the coordinator): the
"input-gated effect is safe" claim under Bugs item 1 below was wrong and has been fixed, and the
`render.data_frame`-patch-from-callback bug was not reproducible and has been removed (see "Unreproduced" under
Bugs found). `examples/14_click_to_table.py` was re-verified without its former `asyncio.sleep(0)` workaround as
part of this pass.

## Verification table

Every file was run with `uv run --no-sync python -m shiny run <file> --port <N>` from the worktree (note:
`shiny run`, the installed console script, ignores a `--with` overlay venv; `python -m shiny run` resolves it
correctly -- this cost some time to discover) and driven with Playwright Chromium; every screenshot was read back
with the Read tool before being referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Accessor/claim confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `img/01_quickstart.webp` | n/a (static) | n/a |
| `examples/02_point_cloud_scale.py` | yes | `img/02_point_cloud_scale.webp` | n/a | 1M points render and stay orbitable |
| `examples/03_terrain_surface.py` | yes | `img/03_terrain_surface.webp` | n/a | real DEM renders; `is_html=True` text fix confirmed |
| `examples/04_mesh_isosurface.py` | yes | `img/04_mesh_isosurface.webp` | n/a | `marching_cubes` unit-cube output confirmed |
| `examples/05_volume.py` | yes | `img/05_volume.webp` | n/a | volumetric render confirmed |
| `examples/06_lines_vectors.py` | yes | `img/06_lines_vectors.webp` | n/a | `k3d.line`/`k3d.vectors` confirmed |
| `examples/07_animation.py` | yes | `img/07_animation.webp` | Play button click | time-keyed animation + `time` trait readout confirmed; comm-race bug found here (see Bugs) |
| `examples/08_camera_accessor.py` | yes | before/after | orbit-drag | `camera()` changes on orbit, confirmed |
| `examples/09_picking_callback.py` | yes | before/after | click (pixel-detected, real mouse down/up) | `click_callback` index+position confirmed; highlight marker moved in place |
| `examples/10_rate_limiting.py` | yes | combined | Play button + wait | 105 unthrottled vs. 12 throttled `reactive_read()` fires |
| `examples/11_update_in_place.py` | yes | before/after | orbit-drag + slider (ion.rangeSlider JS API) | camera survives point_size change, confirmed |
| `examples/12_fly_to.py` | yes | before/after | button click | camera jumps to centroid, confirmed |
| `examples/13_sync_cameras.py` | yes | before/after | orbit-drag on left canvas | right plot's camera mirrors left's, confirmed; initial-sync-drop bug found and worked around (see Bugs) |
| `examples/14_click_to_table.py` | yes | before/after | click (pixel-detected), 6 clicks in a re-verification run | row selection reaches browser on every click, confirmed (no workaround needed -- see "Unreproduced" below) |
| `examples/15_table_to_fly_to.py` | yes | before/after | row click (`get_by_text`) | camera flies + highlight moves, confirmed |
| `examples/16_layout_sizing.py` | yes | combined | n/a | fill (exact), `height=250` (exact 250px canvas), `Layout(height="250px")` (exact 250px canvas, not clipped) all measured |
| `gallery/template_point_cloud_explorer.py` | yes | before/after | click (pixel-detected) | click_callback + camera() both confirmed |
| `gallery/showcase_terrain_explorer.py` | yes | initial/clicked/peak/wireframe | click, 2 button clicks, 1 checkbox click | surface `click_callback` (position/elevation), fly-to-peak, in-place wireframe toggle, camera readout -- all confirmed |

All click gestures on WebGL canvases were driven as real `page.mouse.move()` + `.down()` + a short wait (~80ms) +
`.up()`, not a single `.click()` call -- a bare `.click()` intermittently missed in early testing (see Judgment
calls). Pixel targets were found by screenshotting the canvas, searching for the marker's known RGB color, and
converting from the (possibly `device_scale_factor`-scaled) screenshot's pixel coordinates back to CSS pixels
before adding to the canvas's bounding box -- getting this scaling wrong was a second, separate testing bug I hit
and fixed (see Judgment calls).

## Accessor coverage summary

k3d has exactly one accessor on `render_k3d`, from `_render_widget.py`'s `render_k3d` class and `_k3d.py`'s
`CAMERA` spec (not the stale design-doc lists, which I didn't use for scope):

- `camera()` -- yes, verified with a real orbit-drag gesture (`examples/08_camera_accessor.py`, and reused as the
  driving signal in `examples/13_sync_cameras.py` and the showcase gallery app). Its "cancels instead of returning
  `None`" not-ready semantics (`len(raw) == 0` before auto-fit reports) is also exercised by k3d's own existing
  Playwright test (`tests/playwright/k3d_accessors/test_k3d_accessors.py`), which I read but did not re-run
  separately -- the sentinel path is inherently a narrow timing window (auto-fit reports almost immediately with
  the default `camera_auto_fit=True`), and the existing test already asserts it end-to-end.

k3d's docstring explicitly explains why there's no `clicked()`: picking requires `plot.mode = "callback"`, a
user-visible change to the plot, which the accessor design's anti-goals forbid. I verified this reasoning is still
accurate on current main (`mode` is a plain synced trait; nothing else exposes clicks) and devoted a full
"Beyond the accessors" subsection plus two full examples (`09_picking_callback.py`, and the click-to-table/
click-to-highlight patterns) to the `click_callback`/`hover_callback` alternative, since the brief specifically
asked me to check this.

## Bugs found

### shinywidgets (confirmed, with minimal repros)

1. **A widget method or message sent synchronously inside the render function is dropped. Confirmed general: it
   also happens from a `@reactive.effect` that runs during the initial reactive flush, regardless of what (if
   anything) that effect depends on.** `scene.start_auto_play()` called directly inside `@render_k3d`'s function
   body, right before `return plot`, sends nothing: I confirmed via a browser websocket-frame capture that no
   `start_auto_play` custom message is ever transmitted, even after waiting 12+ seconds. Root cause (read in
   `_shinywidgets.py`/`_comm.py`): the widget is constructed with a placeholder `OrphanedShinyComm` (whose
   `.send()` is a no-op) until a *separate*, deferred `@reactive.effect(priority=99999)` swaps in the real
   `ShinyComm` -- and that swap hasn't happened yet while the render function that *constructed* the widget is
   still running. Minimal repro: build a k3d plot with a time-keyed trait and call `.start_auto_play()` before
   `return`ing it; `reactive_read(widget, "time")` never advances.
   **Correction from a follow-up investigation (`INVESTIGATION.md`, provided by the coordinator):** my original
   write-up claimed an effect gated on a plain UI input "reliably runs late enough" even at that input's default
   value, and treated that as safe. That claim is **wrong** and has been removed from the guide and this file.
   The investigation tested a bare effect and an input-gated effect (both against a k3d time-keyed plot) head to
   head: **both** failed to start the animation when run during the initial flush, identically to the render-
   function case. The only pattern that reliably worked, in every test, was a genuine user action after the page
   loaded (a real Playwright click on an action button). **Fix used throughout this guide (now accurate):** call
   such methods from a separate `@reactive.effect` gated on `@reactive.event(input.some_button)` (ignore_init's
   default means the effect only runs on an actual later click, not at startup) -- see `examples/07_animation.py`'s
   Play/Pause buttons and `examples/12_fly_to.py`'s fly-to buttons, both of which already used this correct pattern
   and needed no code changes, only the surrounding prose's claim about *why* it works.
2. **(Already fixed on `main`, re-confirmed rather than newly found)** The old report's two blockers --
   `Plot.close()` not calling `Widget.close()` (comm/model leak on re-render) and `Layout(height=...)` clipping the
   scene -- are both fixed. The first has a k3d-specific shim, `close_comm_on_close()` in `_shinywidgets.py`
   (confirmed by reading the code: it patches `widget.close` to also call `Widget.close(w)`); I did not re-run the
   old report's exact 8-re-render-plus-comm-count repro, since the fix is a straightforward, narrowly-targeted
   code change that's easy to read and verify by inspection. The second I *did* independently re-measure
   (`examples/16_layout_sizing.py`): a `Layout(height="250px")` plot now renders at exactly 250px, matching
   `k3d.plot(height=250)` pixel-for-pixel, with no overflow or clipping either way.

### Upstream k3d (not shinywidgets' doing)

3. **`k3d.text()`'s default LaTeX rendering drops spaces.** `k3d.text("Highest point (1068 m)")` renders as
   "Highestpoint(1068m)" in the browser -- confirmed in `examples/03_terrain_surface.py`'s "before" state, fixed
   with `is_html=True`. This matches the old report's finding exactly and is still present in k3d 3.2.0.
4. **`fetch_screenshot()` causes ~dozens of HTTP 404s for KaTeX font files** (`fonts/KaTeX_*.woff`/`.ttf`, requested
   relative to the Shiny app's origin instead of k3d's bundled assets). Confirmed via browser console capture
   during a screenshot call. Harmless -- the fonts are already loaded as inline data URLs for live rendering -- but
   it will show up in anyone's server/browser logs. Matches the old report.

### Unreproduced (removed from the published guide)

**`render.data_frame`'s row-selection/`styles` patches failing when triggered from inside a widget's `on_msg`
callback (e.g. k3d's `click_callback`)** -- my original write-up claimed `update_cell_selection()` (and a
`styles=` re-render) called synchronously from `click_callback` updated server-side state correctly but never
reached the browser, and that `await asyncio.sleep(0)` before the call fixed it reliably. A follow-up
investigation (`INVESTIGATION.md`, provided by the coordinator) rebuilt the exact scenario twice -- both the
`update_cell_selection()` form and the `styles=` form -- and drove 12 real clicks (6 per run) across both. All 12
updated the DOM correctly, with no sleep and no retries. The investigation also traced the dispatch path
(`_comm.py`'s `dispatch_client_msg`, `_shinywidgets.py`'s `init_session()`) and found nothing that would gate or
delay a `DataGrid` patch based on what triggered it -- a click-driven update goes through the same plain
reactive-effect/websocket-send path as any other input-driven update. I re-ran `examples/14_click_to_table.py`
myself without the `asyncio.sleep(0)` (6 clicks, varied screen positions) and it worked every time; the workaround
and the bug write-up have been removed from `guide.md` and the example. My best guess, per the investigation, is
that the original observation was a one-off flake (possibly stale browser state from an earlier click attempt,
given how finicky k3d picking's gesture shape already is) misattributed to the trigger source, rather than a real,
reliably-reproducing bug. See `INVESTIGATION.md` for the full methodology.

## Judgment calls

- **Picking needs a real down/wait/up, not a single `.click()`.** In early testing, `page.mouse.click(x, y)` on a
  k3d canvas intermittently failed to register with `click_callback` (`clicked_index` stayed `None`); separating it
  into `.move()` + `.down()` + `page.wait_for_timeout(80)` + `.up()` worked reliably every time afterward. I did
  not dig into why (plausibly a raycaster/pointer-event timing detail in k3d's interaction code), since the
  working pattern is simple and the brief only asks me to get a real gesture working, not to debug k3d's input
  handling. I'd flag this for anyone writing further Playwright tests against k3d picking.
- **Pixel-coordinate scaling with `device_scale_factor`.** `page.locator(...).screenshot()` returns an image sized
  at `device_scale_factor` times the element's CSS bounding box. I initially forgot to divide by that scale factor
  before adding a detected pixel offset to the bounding box's `x`/`y` (both are in CSS pixels), which silently
  clicked the wrong spot (still inside the canvas, so no error, just a different/sometimes-empty point) when
  `device_scale_factor=2` was set for a sharper screenshot. Fixed by computing `scale = rgb.shape[1] /
  box['width']` and dividing. Noting this since it's an easy mistake to repeat.
- **`examples/14_click_to_table.py` uses `render.DataGrid(..., selection_mode="row")` and
  `update_cell_selection()`, not a `styles=` highlight.** I tried `styles=` first and initially suspected (and then
  retracted, per the "Unreproduced" note above) a click-callback-specific bug with it. Kept `update_cell_selection`
  regardless, since row selection is arguably the better UX anyway (built-in highlight style, keyboard-navigable).
- **Dataset choice:** real data wherever the brief's guidance applies -- `sklearn.datasets.load_iris` in 3D for the
  quickstart, the fly-to example, and the template gallery app (recognizable, small, and the species clusters make
  a legible 3D story); the Jacksboro Fault DEM bundled inside matplotlib's sample data for the terrain surface
  example and the showcase gallery app (a real, if small, geographic elevation grid -- not a toy function).
  Synthetic data only where the point is specifically scale (`02_point_cloud_scale.py`, 1M points), a classic
  reference object with no natural "real" dataset (the Lorenz attractor in `06_lines_vectors.py`; the implicit
  torus in `04_mesh_isosurface.py`; the Gaussian-blob "nebula" in `05_volume.py`), or a deliberately small/abstract
  example where the point is the mechanism, not the data (`07_animation.py`'s toy orbits; the landmark table in
  `15_table_to_fly_to.py`).
- **`examples/12_fly_to.py` and `examples/13_sync_cameras.py` needed an explicit, shared starting camera** rather
  than each plot auto-fitting independently, specifically to avoid bug #1 above being *visible* (the first,
  possibly-dropped camera copy between two plots would otherwise show a wrong initial frame on the second plot).
  This is a real workaround for a real bug, not just a stylistic choice -- flagged in both the example's own
  comment and in Gotchas.
- I did not exhaustively test every k3d object type the old report covered (it listed 12: points, mesh, surface,
  line, volume, mip, marching_cubes, voxels, vectors, text/text2d/label, texture). I covered points, surface, mesh
  (via `marching_cubes`), volume, line, vectors, and text -- the ones the brief's "Cover:" list asked for plus text
  labels, which is 7 of the 12. I deliberately skipped voxels, mip (maximum intensity projection, a volume
  variant), texture-mapped objects, and a standalone `text2d`/`label` demo (text appears once, embedded in the
  terrain example) as lower-value for a teaching guide that's already covering the structurally distinct
  categories; a second opinion on whether voxels specifically deserve a slot (they're visually distinctive and
  simple to demo) would be welcome if the page has room.

## Pairs with (for cross-cutting articles)

- **itables / reactable**: `examples/14_click_to_table.py` and `examples/15_table_to_fly_to.py` both use a plain
  `render.DataGrid` as a stand-in (the brief's "keep the other widget simple" guidance); either pattern drops in
  directly with `render_itables`/`render_reactable` instead, same `selection_mode="row"` /
  `update_cell_selection()` API.
- **plotly**: both guides cover 3D scatter (`scatter_3d` vs. k3d points); worth a line in a cross-cutting "which 3D
  option" article pointing out k3d's scale advantage (millions of points) vs. plotly's lighter weight and 2D/3D
  consistency.

## Editor's notes for the website

- Strongest sections: the terrain showcase gallery app (4 screenshots: initial, clicked, flown-to-peak, wireframe)
  is the best single demonstration of "this is a real, in-place-editable 3D scene" -- I'd lead with it if the
  website wants one hero beyond `hero.webp` (which is in fact the "flown to peak" shot from that same app). The
  "camera() drives a second view" pattern (`examples/13_sync_cameras.py`) is a clean, visually obvious accessor
  demo that other 3D-ish guides (pythreejs, ipyvolume) could point to instead of re-explaining the idea.
- Candidates to cut for a shorter page: the isosurface (`04`) and volume (`05`) examples are the most "generic 3D
  graphics demo" feeling of the six feature-tour items (less specific to *k3d in Shiny* than the terrain/point-
  cloud/animation examples); if the page needs to shrink, these two are the ones I'd drop first, keeping the real
  DEM, the scale demo, and the animation.
- The effect-timing-race writeup in Gotchas is the most implementation-detail-heavy part of the page. It's accurate
  (re-verified by a follow-up investigation; see `INVESTIGATION.md`) and I stand behind it, but a website editor
  might want to compress it to one or two sentences with a link to a longer explanation elsewhere, since the full
  mechanism (`OrphanedShinyComm`, the deferred `priority=99999` comm-opening effect) is more "how shinywidgets
  works" than "how to use k3d."
- Extra verification screenshots exist in `img/` that aren't referenced from `guide.md` but were used to confirm
  claims along the way: none left over in this case -- every screenshot taken ended up referenced, since I re-shot
  rather than kept intermediate failed attempts.

## Update 2026-11-11 (main @ 32ca7035)

Versions: shinywidgets `main` @ `32ca7035`, k3d 3.2.0, shiny 1.9.0, Python 3.13, run in the shared
`main-wt` worktree. Playwright: Chromium headless with `--use-angle=swiftshader
--enable-unsafe-swiftshader --ignore-gpu-blocklist` (not strictly required for k3d, as the original NOTES
found, but used throughout for consistency with the other 3D guides in this batch).

**What changed in the guide and why:**

- Reworded the `07_animation.py` comment, the prose right after it, and one Gotchas bullet to describe
  **#415's actual effect on k3d** precisely (see "Re-verified" below) -- the old text ("the comm is still a
  placeholder, so the message sends nothing") is no longer true and was replaced, but the guide's
  button-wiring *pattern* is unchanged because it is still required.
- Rewrote the `camera()` accessor section to drop the "state accessor" / "event accessor" terminology
  (removed project-wide per #437) in favor of plain before/after-re-render language, and added an explicit,
  verified statement that `camera()` **re-seeds from the new plot on every re-render** (not stated this
  plainly before).
- Replaced the accessor reference table's columns with the new standard ones (`before any interaction` /
  `across re-render` instead of `Fires when` / `None means`).
- Added a one-line mention that `scene.read("camera")` is equivalent to `scene.camera()` (verified).
- No other sections needed changes: #405 (browser-created-model leak fix) doesn't apply to k3d (that's a
  pythreejs/bqplot finding); #437's re-render rules were already correctly described for `camera()`
  (it's "inherent widget state" per the PR's own classification, and the original NOTES already verified
  re-seeding implicitly via the sync-cameras example, just hadn't stated the rule explicitly in prose).

**Re-verified claims (all with a real browser, this pass):**

- `camera()` cancels (blank/no update) before the first auto-fit report, and **re-seeds from the new plot
  on re-render** rather than keeping the pre-re-render orbit: built a probe app
  (`scratchpad/agents/threed/probe/camera_reseed.py`, not committed) that orbits, re-renders with wider
  data, and reads `scene.camera()` after each step. Confirmed: cancels before first report; the orbited
  camera (`[4.12, -16.77, 2.95, ...]`) is replaced by the new plot's own auto-fit framing
  (`[24.74, -36.60, 1.79, ...]`) after re-render, not kept.
- `scene.read("camera")` returns the same 9-float list as `scene.camera()` (`scratchpad/agents/threed/probe/read_test.py`).
- **#415, re-verified in depth (see "Bugs found" below for the full finding):** a widget method's message
  (`scene.start_auto_play()`) called synchronously inside the render function, a bare startup effect, or an
  effect delayed with `reactive.invalidate_later()`/`asyncio.sleep()`, now reliably reaches the browser --
  confirmed by capturing raw websocket frames and seeing the `start_auto_play` custom message arrive, which
  on pre-#415 `main` never happened at all (per the original `INVESTIGATION.md`). This part of #415 is real
  and is reflected in the guide. But reading `scene.widget.time` directly afterward (not just through
  `reactive_read()`) shows the trait never advances unless the call follows a genuine later user action; see
  below.

## Follow-up 2026-11-11b: reactive_read(x.widget, ...) -> x.read() for the output's own widget

Coordinator flagged that the first pass still taught `reactive_read(x.widget, "trait")` for traits on the
renderer's *own* widget, where tier 2 (`x.read("trait")`) now applies. Converted every instance:

- `guide.md`/`examples/07_animation.py`: `reactive_read(orbits.widget, 'time')` -> `orbits.read('time')`.
  Re-verified: Play button click, `plot.time` readout still advances (`0.43` after 1.5s).
- `guide.md` "Beyond the accessors" section (`time`, `screenshot`, `grid_visible` bullets): converted to
  `plot.read("trait")`, retitled the section `### Beyond the accessors: picking, and \`.read()\``. Re-verified
  all three with a fresh probe app (`scratchpad/agents/threed/probe/k3d_misc_reads.py`): `grid_visible` reads
  `True` at start; `fetch_screenshot()` + `plot.read("screenshot")` returns a ~291 KB base64 string (same order
  of magnitude as the existing "~400 KB" claim, which I left as-is -- different scene content, not a
  contradiction).
- `guide.md`'s camera() prose (line ~443): now shows both `plot.read("camera")` and
  `reactive_read(plot.widget, "camera")` as equivalent (kept the latter only as "or" context, not as the
  taught primary).
- `examples/10_rate_limiting.py` + `guide.md`'s copy: converted both `reactive_read(...)` calls to
  `.read("time")`, renamed the `"reactive_read fired N times"` labels to `"read() fired N times"`, dropped the
  now-unused `reactive_read` import. **Re-verified the rate policy is still honored through `.read()`**: 5s of
  autoplay now fires ~200 times unthrottled vs. 11 times at `rate_delay=0.5` (two independent runs, both
  199-200 vs. 11) -- a new, re-measured number, not the original guide's "105 vs. 12" (machine-load/timer
  variance between sessions, not a behavior change; the ~18x throttling ratio is the point, not the absolute
  counts). Re-screenshotted `img/10_rate_limiting.webp`.
- `gallery/showcase_terrain_explorer.py`: `reactive_read(terrain.widget, "camera")` -> `terrain.camera()` (the
  renderer already has a named `camera()` accessor -- using the raw trait read here was never necessary, not
  just a tier choice). Re-verified with a real orbit-drag and a "Fly to highest point" click: camera readout
  changed correctly both times, zero console errors. Re-screenshotted
  `img/gallery_showcase_terrain_peak.webp`.
- Left two prose mentions of `reactive_read()` as explanatory "or" alternatives (camera() section, rate
  limiting's closing paragraph) -- not teaching it as the primary pattern, just noting the plain-trait
  equivalent exists.

## Bugs found (2026-11-11)

### shinywidgets / k3d interaction -- a narrower remaining gap under #415 (not a regression; new finding)

**`start_auto_play()` reaching the browser (#415) is necessary but not sufficient for K3D to actually start
playing, unless the call follows a real user-triggered event.** I re-verified the exact scenario #415's PR
description calls out ("k3d's `start_auto_play()` in the render function") across several variants, reading
`orbits.widget.time` directly (not through `reactive_read()`, to rule out a read-side issue):

1. `scene.start_auto_play()` called synchronously inside `@render_k3d`'s function body, before `return`.
2. The same call from a bare `@reactive.effect` with no dependencies (runs once at startup).
3. The same call from a `@reactive.effect` delayed with `reactive.invalidate_later(5.0)`, guarded so the
   send genuinely happens on the later, re-invoked run rather than immediately (an easy mistake: calling
   `invalidate_later()` only schedules a future re-run, it doesn't block the current one).
4. The same call from an `async def` effect after `await asyncio.sleep(5.0)` and again after `sleep(8.0)`.

**In all four, `time` stayed at `0.0` for the full observation window (6-13s), confirmed by direct attribute
reads on the server, not just `reactive_read()`.** In every case I also confirmed via a raw websocket-frame
capture that the `start_auto_play` custom message *did* reach the browser (this is the #415 fix working
correctly) -- the browser receives it but K3D's playback loop doesn't start.

By contrast, **a real Playwright click on a "Play" button always worked**, including a click fired as early
as the button existed in the DOM (well before the 5-8s delays above) -- ruling out "needs more real elapsed
time for K3D's JS module to load" as the explanation; a `fetch_widget_module`/`snapshot_source` round trip
(k3d's own two-phase module loading, confirmed by reading `k3d/_widget.py`) was already complete in the
failing cases too. The distinguishing factor, as far as I could pin down without going deeper into
py-shiny's or anywidget's internals, is specifically **whether the call happens in a reactive flush that was
itself triggered by an incoming client message** (a click) versus a server-initiated push (render, startup
effect, or timer). I did not chase the root cause further than that -- it's plausibly in py-shiny's
flush/message-batching rather than shinywidgets, and is out of scope to fix per the brief.

Minimal repro (not committed; left in scratch): `scratchpad/agents/threed/probe/send_from_render.py` (case
1), `bare_effect.py` (case 2), `combo3.py` (case 3, with the correct delayed-effect pattern),
`combo2.py`/`delayed_effect2.py` (case 4, with direct trait reads), `early_click.py` (the working control
case). All run against `shinywidgets` `main` @ `32ca7035`, k3d 3.2.0, re-run multiple times given the
"machine is loaded" caveat (another agent, `noacc-b`, was independently probing the same #415 question on
this machine at the same time, which is reassuring corroboration that this is a real area of interest, not
noise).

**Severity / guide impact:** Low-to-moderate. The guide's existing button-wiring pattern (`07_animation.py`,
`12_fly_to.py`) already does the one thing that reliably works, so no example needed to change behavior --
only the prose explaining *why*, which I corrected to be accurate rather than oversimplified. I did not
"simplify the guide to call `start_auto_play()` from the render function," per the brief's suggestion, because
that change would ship a broken example (confirmed broken, not hypothetically). Recommend the maintainer
treat this as a scoped follow-up to #415 if k3d's render-function case is meant to fully work, or accept the
narrower framing in the guide if a button-click requirement is acceptable for autoplay specifically.

## What I dropped from the old report and why

- The full scorecard/star-ratings format: replaced with concrete, verified Gotchas, per this guide's format.
- "Every widget stays in Python memory until session end" (finding 3.4, a generic shinywidgets/py-shiny retention
  issue): I read the current `_shinywidgets.py` and found it now uses a weak reference (`w_ref = ref(w)`) in the
  comm-opening effect specifically to address this class of problem; a full re-measurement of the old report's
  8-re-render gc repro is a cross-renderer architecture question, not k3d-specific content, so I left it for a
  cross-cutting article rather than this guide.
- The "about 16 WebGL plots per page is a browser limit" finding: real, but a browser/hardware limit that applies
  to any WebGL-heavy page, not a k3d-in-Shiny-specific gotcha worth a slot in an already-long Gotchas list.
- "Point sprites look about half as big in screenshots" (a `fetch_screenshot()` vs. live-view sprite-scaling
  quirk): I didn't re-verify this one (it would need a careful side-by-side pixel measurement I didn't have time
  for) and didn't want to repeat an unverified claim; the KaTeX-font-404 screenshot quirk I *did* re-verify is
  the one I kept.
- The merge-conflict/PR-review material (the old report was reviewing an in-flight PR; `render_k3d` and its
  accessor are already on `main` here, so none of that applies).

## Update 2026-11-11 (smoke follow-up: item 2 reinvestigation)

- Re-ran the `start_auto_play()` question with a fresh instrumented probe (server logs `widget.time` every
  second). New finding that **corrects** the 2026-11-11 "needs a genuine user action" conclusion: an effect
  delayed ~5 s with `reactive.invalidate_later()` starts playback with no user gesture (time ticks from 0.98
  downward right after the send). The render-function call still never plays (verified: `time` stays 0.0 for
  10+ s, then the Play button works). The real distinguishing factor is **whether the k3d view has connected
  when the message arrives**: k3d's `widget.mjs` registers its `msg:custom` handler per view inside
  `whenConnected(el).then(...)`, so earlier messages are dropped silently with no queue or replay. The earlier
  session's failing delayed cases were on a heavily loaded machine (slow view connect); their "user action"
  correlation was really a "view connected by then" correlation. Updated `guide.md` (07_animation comment,
  following prose, and the Gotcha) to the view-connect framing; button wiring stays the taught pattern as the
  robust form of "later". No code change recommended: a shinywidgets-side "send after view connects" would be
  widget-specific plumbing for a niche call; the upstream fix (queue/replay in k3d's JS) is k3d's.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views," reusing the existing
`examples/02_point_cloud_scale.py` (1M points, already verified and screenshotted) rather than writing a new
example -- no new measurement needed. Classified as "draw it with the GPU in the browser" in the new performance
article's three-approaches framing; linked forward to
`../articles/performance/article.md#three-approaches-to-large-data`, which doesn't exist yet (Task 7 runs in the
same wave) -- `check_docs.py` flags it as an unresolved anchor, expected per the task block.
