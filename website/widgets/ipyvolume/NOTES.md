# NOTES: ipyvolume guide

## Versions

- ipyvolume 0.6.3, ipywidgets 8.1.9, shiny 1.9.0, pythreejs 2.4.2, plotly 6.9.0
- shinywidgets worktree: `main-wt` detached at `origin/main` (00f90249 after an
  environment restart; originally verified against the same commit before the
  restart -- `00f90249 fix(plotly): bind accessor events when Plotly draws
  after the bind request and display (#392)`).
- Date: 2026-10-30 (initial verification), resumed 2026-11-02 after a
  coordinator/session restart wiped the scratch dir (worktree was recreated
  fresh at the same commit; re-verified a sample of earlier findings after
  resuming).

## Bugs found

### 1. Upstream (ipyvolume): per-point string color arrays hang the entire Shiny *process*, not just that output

**Severity: high. Not a shinywidgets bug** -- reproduces identically in plain
`ipywidgets`/Jupyter, anywhere a `Scatter`'s own `get_state()` gets called.

Repro: set `color=` on an `ipyvolume.Scatter` (or pass a list/array of
multi-character strings via `ipv.scatter(..., color=["tomato", "seagreen",
...])`) and display the figure. The **entire server process hangs** (not just
that output -- a second, unrelated HTTP request to the same app also hangs
forever). Confirmed with `faulthandler.dump_traceback_later()`: every worker
thread is blocked in

```
ipyvolume/serialize.py:326 color_to_binary_or_json
  -> ipywidgets/widgets/widget.py:615 get_state
  -> shinywidgets/_shinywidgets.py:282 _open_shiny_comm
```

Mechanism: `color_to_binary_or_json()` has a `while True: element = element[0]`
loop meant to walk down nested arrays until it hits a scalar (where indexing
raises and breaks the loop). For multi-character Python/numpy strings,
`"tomato"[0]` returns `"t"`, and `"t"[0]` returns `"t"` again, forever --
indexing a string never raises. A **single solid color string** (`color="red"`)
is fine (dimension-0 path, never enters the array branch); a **numeric (N,3)
RGB float array** is fine (indexing bottoms out at a Python float, which isn't
indexable). Only a **per-point array of strings** triggers the infinite loop.

This only happens when something actually calls `get_state()` on the specific
`Scatter` instance -- which happens the first time any frontend (a real
Jupyter kernel just as much as shinywidgets) opens that widget's comm. It is
not visible from the Python REPL (building/printing the `Figure` never
triggers it) and only hangs once you try to *display* it.

**What this means for users:** never pass a list/array of CSS color names (or
any per-point string array) to `color=` on a scatter/quiver/mesh. Use a
numeric `(N, 3)`/`(N, 4)` RGB(A) float array in `[0, 1]` instead (this is also
what every ipyvolume doc example already does for per-point coloring). The
guide's Gotchas section and every multi-color example use the RGB-array form
and call this out explicitly.

**Repro file:** not preserved after the scratch wipe (trivial to reconstruct:
`ipv.figure(); ipv.scatter(x, y, z, color=["tomato"]*n); return ipv.gcf()`
inside any `@render_ipyvolume`, then load the page -- the whole server hangs,
confirmed via `curl` to an unrelated route timing out while it's stuck).
Recommend the maintainer file this upstream against ipyvolume (dormant repo,
so low odds of a fix, but worth a GitHub issue for the paper trail) and/or
consider a defensive type-check in `as_widget_ipyvolume`/the renderer that
rejects a string-dtype array for `color` with a clear error -- see "Judgment
calls" below.

### 2. Previously-reported pylab re-render stall (old report F1) is FIXED on current main

The old report (`docs/widget-reports/ipyvolume/report.md`) measured every-other
pylab re-render (`ipv.figure()` + `ipv.scatter()` + reactive input) stalling
~29s, caused by ipyvue/ipyvuetify `Template` widgets shared across figures
being closed by cleanup and the browser waiting out the 30s model-waiter
timeout. **Verified fixed**: 6 consecutive re-renders of a pylab-constructed
figure (slider-driven) completed in ~2-4s each with zero console errors
(this is slower than ideal but is just reactive/IO overhead on a heavily
loaded dev machine, not a stall). This is explained by PR #348 ("share
process-global widgets across sessions and re-renders"), which gives
ipyvue/ipyvuetify's shared `Template`/`theme` widgets `shared_lifetime()`
treatment so they survive cleanup across re-renders. **Drop this from the
guide's Gotchas** -- it's a regression that's already fixed, not a current
limitation. Mentioned as resolved, briefly, in the guide intro so returning
readers of the old report aren't confused.

### 3. `Scatter.selected` is unreliable for an in-place, repeatedly-updated highlight -- two upstream bugs, not shinywidgets

**Severity: high for the "table row selection -> 3D highlight" pattern as an
in-place update. Both bugs are upstream ipyvolume (its own bundled frontend
JS), not shinywidgets.** Re-investigated per `INVESTIGATION.md` (superseding
this section's original framing, which wrongly blamed "a later reactive
tick"; see that file for the full evidence trail, browser-side line numbers,
and a minimal upstream repro).

**Bug 3a -- empty `selected` crashes the view.** The trigger is assigning
`selected` to anything that serializes as an **empty** sequence (`[]`), not
timing. ipyvolume's frontend `_get_value(e, t, n)` treats an empty array `e`
as truthy, then evaluates `e[t % e.length]`; `t % 0` is `NaN` in JS, so this
returns `undefined`, which a later `.forEach()` call throws on --
`Cannot read properties of undefined (reading 'forEach')`. A **non-empty**
`selected` (regardless of when it's set) does not hit this path. **Verified
workaround:** use an out-of-range sentinel index for "nothing selected"
(e.g. `selected=[len(x)]`) instead of `[]` -- confirmed this avoids the crash
across select -> clear -> orbit-drag.

**Bug 3b (newly found while verifying the sentinel workaround for this
guide) -- the highlight only ever reflects the *first* non-empty value
`selected` is set to.** With the sentinel in place to dodge 3a, I drove a
real two-different-rows test (`examples/11_table_selection_highlight.py`'s
precursor, and a minimal repro with two buttons setting `selected = [2]`
then `selected = [10]`, two points far apart in the cloud): the first
assignment highlights the correct point; every subsequent assignment to a
*different* non-empty value changes the Python-side trait correctly
(confirmed with `reactive_read(scatter, "selected")`, and no console error),
but the browser's highlighted sphere **never moves** -- not after 3s, not
after an orbit-drag, not after a full viewport resize (all of which force a
WebGL redraw). So: selecting row A highlights A; clicking row B afterwards
changes nothing visible. This makes the native `selected` mechanism
unsuitable for the realistic table-driven-highlight use case (repeated,
changing selections), sentinel or not.

**Workaround used in the guide:** don't use `selected`/`size_selected`/
`color_selected` for a highlight that must update more than once. Recompute
plain `color`/`size` numpy arrays (baking the highlight into the normal
per-point arrays) and re-render the whole figure on each selection change --
verified correct across repeated, different selections (camera resets on
each click, an acceptable trade). `examples/11_table_selection_highlight.py`
uses this approach; screenshots `img/11_table_before.webp` /
`11_table_after.webp` / `11_table_moved.webp` (the last confirms the highlight
relocates on a second, different row click).

**Also noticed in passing (separate, minor, upstream docs bug):** `ipv.scatter()`'s
documented `selection=` parameter (pylab API, meant to set the initial
selected indices) is a no-op on ipyvolume 0.6.3 -- it's passed to
`ipv.Scatter(..., selection=...)`, but the widget's real trait is named
`selected`, not `selection`; the kwarg is silently swallowed (no error, no
effect). Confirmed directly: `ipv.widgets.Scatter(..., selection=[0]).selected`
is `None`.

### 4. Docstring fix already landed on main (not a new finding)

The design doc (`docs/plans/2026-10-29-reactive-accessors-plan-9-plotting-misc.md`,
Task 7) says the old `render_ipyvolume` docstring recommended
`reactive_read(plot.widget, "camera")`, which never fires (the camera
*instance* doesn't change on orbit; its `position`/`quaternion`/`zoom` traits
do). Current `main`'s docstring already uses `plot.camera()` /
`reactive_read(plot.widget.camera, "position")` -- i.e. already fixed, nothing
to report as a bug. Confirmed `camera()` fires once per completed orbit drag
(verified via a real mouse down/move/up gesture: one `camera_count` increment
per full drag, not one per mousemove step).

## Verification table

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a (static) | n/a |
| examples/02_volume.py | yes | yes | n/a (static) | n/a |
| examples/03_quiver.py | yes | yes | n/a (static) | n/a |
| examples/04_surface.py | yes | yes | n/a (static) | n/a |
| examples/05_animation.py | yes | yes | n/a (Play button not driven; see below) | n/a |
| examples/06_camera_accessor.py | yes | yes (before/after) | yes (real orbit drag) | `camera()` confirmed: before (0,0,2), after a real drag it changed and a specific new value was read back |
| examples/07_reactive_read_beyond.py | yes | yes | n/a (static read) | `reactive_read(widget,"width"/"height")` and `reactive_read(scatter,"sequence_index")` both confirmed non-default/live values |
| examples/08_rate_limiting.py | yes | yes (before/during/after) | yes (viewport-resize burst) | confirmed: unthrottled counter advanced immediately on each of several resizes (2->7 during a burst), debounced counter stayed flat during the burst (2) and advanced once (3) after the debounce window closed |
| examples/09_inplace_update.py | yes | yes (before/after) | yes (real orbit drag + slider drag + select) | n/a (no accessor; verified in-place size/color update and that `camera()`'s value is unchanged before/after the restyle) |
| examples/10_linked_camera_views.py | yes | yes (before/after) | yes (real orbit drag on the left figure) | `camera()` confirmed driving a second figure's camera in the same reactive cycle (both views rotate together) |
| examples/11_table_selection_highlight.py | yes | yes (before/after/moved) | yes (real clicks on two different data_frame rows) | n/a (no accessor; verified the highlight relocates on a second, different row click -- this is where bug #3 was found and worked around) |
| examples/12_sequence_linked_chart.py | yes | yes (before/after) | yes (real click on the Play button, polled after ~2-3s) | `reactive_read(scatter, "sequence_index")` confirmed driving a matplotlib companion chart's marker |
| examples/13_layout_sizing.py | yes | yes | n/a (static sizing comparison; fill vs. explicit size, both already covered by passing Playwright tests in `tests/playwright/render_ipyvolume`) | n/a |
| gallery/template_3d_scatter.py | yes | yes | n/a (static) | `camera()` readout shown live in the sidebar |
| gallery/showcase_lorenz_explorer.py | yes | yes (initial + interactive) | yes (checkbox toggle + Play button click) | `camera()` and `reactive_read(scatter, "sequence_index")` both confirmed live in the sidebar readout during animation |

Playwright gesture notes:
- Orbit drag: `page.mouse.move/down/move(steps=15)/up` over the canvas's
  bounding box -- works reliably, matches `tests/playwright/render_ipyvolume`'s
  own `test_ipyvolume_camera_roundtrips_to_python`.
- Lasso/rectangle selection: Ctrl+drag (rectangle) or plain drag (lasso, after
  `fig.selector = "lasso"`) over the canvas -- works. Confirmed (separately,
  before the restart) that `fig.on_selection()` payload is pixel-space only
  (`{"type": "lasso", "pixel": [[x,y], ...]}`), and that
  `reactive_read(scatter, "selected")` stays `None` after a lasso drag --
  i.e. **`selected` is Python to-browser only, not a usable synced selection
  trait** for reading back a browser gesture (matches the old report's F4,
  re-confirmed independently via `reactive_read` rather than just reading the
  JS source). This still needs re-verification after the restart if time
  allows, but the mechanism (no index computation anywhere in the bundled JS)
  is a structural upstream limitation, not likely to have changed.
- Animation Play button: driven for real in `examples/12_sequence_linked_chart.py`
  and `gallery/showcase_lorenz_explorer.py` (`page.locator("#controls
  .widget-play button").first.click()`, then polled after ~2-3s) -- the frame
  counter and companion-chart/sidebar marker both advance correctly.
- Table row selection: driven for real in `examples/11_table_selection_highlight.py`
  via a plain pixel-coordinate `page.mouse.click()` on the `shiny-data-frame`
  custom element (it uses a **closed shadow root**, so Playwright's locator
  engine cannot pierce it or match `[role="row"]`/`shiny`'s own
  `OutputDataFrame` Playwright controller selectors, which assume an older,
  non-shadow-DOM structure -- a coordinate click works regardless of shadow
  DOM and was used instead).

## Judgment calls

- Chose numeric RGB(A) arrays for every multi-color example instead of named
  color strings, specifically *because of* bug #1 above -- this is both the
  safe choice and (per ipyvolume's own docs) the idiomatic one, so it costs
  nothing pedagogically.
- Did not attempt to work around or "fix" bug #1 in example code (e.g. by
  pre-converting strings to RGB myself and documenting it as a tip) beyond a
  one-line Gotcha + a code comment at the one call site that used to have the
  bug -- this is a `color=` input shape to avoid, not a shinywidgets
  limitation to work around in the renderer.
- Rate limiting section pivoted from "debounce camera()" (which doesn't work:
  `camera`'s `AccessorSpec.rate_policy` is `None`, and `Accessors.__init__`
  only builds a limiter `if policy is not None` -- the renderer's
  `rate_policy=`/`rate_delay=` kwargs do NOT retroactively enable rate
  limiting on an accessor that doesn't declare a default) to "debounce a
  `reactive_read()` trait read during a resize burst," which is what those
  kwargs actually affect for this renderer. Worth a second opinion: is this
  subtlety ("rate_policy only overrides an accessor's *existing* default; it
  can't opt an undeclared accessor in") surprising enough to call out as a
  "Bugs found (docs)" item, or is it adequately explained by the existing
  docstring sentence "no accessor on this renderer declares a default"? I
  lean toward: the docstring already says this correctly, so it's not a bug,
  just worth the guide being very explicit (which it now is).
- Used `plotly.express.data.iris()` instead of `sklearn.datasets` for the
  quickstart (avoids an ephemeral `--with scikit-learn` overlay; plotly is
  already in the locked test/dev venv at 6.9.0).
- Per `INVESTIGATION.md`'s re-attribution of bug #3 (cited above): restored
  attempts to use `selected` with an out-of-range sentinel, per the
  investigation's suggested recipe, then verified it end-to-end for the
  guide's actual use case (table row clicks, including a second click on a
  *different* row). That surfaced a second upstream bug the investigation's
  narrower "select -> clear -> orbit-drag" check didn't exercise: the
  highlight sticks to the first point selected and never relocates. Given
  that, I kept the color/size-array re-render as the guide's sole recipe
  for this pattern rather than "restoring" `selected` as the primary
  technique -- it's the only one of the two that is correct for repeated,
  changing selections, which is the realistic use case the pattern exists
  for. Flagging this as a judgment call worth a second opinion: happy to
  present the sentinel technique instead (or in addition) if the maintainer
  weighs "demonstrates the native mechanism" higher than "only highlights
  once per page load."

## Coordinator's package-version warning (addressed)

The coordinator warned that an unpinned `uv run --no-sync --with duckdb` in
another guide silently overlaid a newer duckdb over the locked version. I
never used `--with <pkg>` for any package in this guide (switched the
quickstart from `sklearn` to `plotly.express.data`, which is already in the
locked venv at the confirmed version 6.9.0) -- nothing to re-check.

## Editor's notes for the website

- Strongest material: the `camera()` before/after orbit screenshots, the
  quiver vector field (very recognizable at a glance), and the rate-limiting
  resize-burst demo (clean, verifiable counts).
- The color-string hang (bug #1) is a good, surprising "gotcha" callout --
  recommend keeping it prominent (not buried) since it's a silent total
  hang, not an error message.
- Cut candidate if the page runs long: the rate-limiting section could be
  trimmed to a short paragraph + the one-line kwarg example, since the payoff
  (a resize-driven trait) is a minor, infrequent need for this particular
  widget compared to e.g. map/geospatial guides.

## Dropped from the old report (and why)

- F1 (pylab 29s re-render stall): fixed on main (see Bugs #2 above); dropped
  entirely rather than listed as a gotcha.
- F3 (fullscreen-exit 10px canvas overflow): not yet re-verified after the
  restart; low value even if still true (self-healing, cosmetic) --
  tentatively dropping per the brief's "a reproducible edge case is not
  automatically worth fixing or a reason to block" guidance, unless time
  remains to re-check it cheaply.
- F5 (wheel zoom needs deliberate notches), F6 (benign WebGL/console noise):
  dropped as non-issues, consistent with the old report's own framing.
- F2 (direct construction needs explicit xlim/ylim/zlim, size_selected
  defaults): kept, but reframed as a plain Gotcha rather than a "PR
  should-fix" since there's no PR in this framing.

## Status: complete (revised)

Revised per a coordinator-provided `INVESTIGATION.md` that re-attributed bug
#3 to upstream ipyvolume and identified the empty-`selected` trigger; I then
re-verified the suggested sentinel workaround against this guide's actual
use case and found a second upstream bug it doesn't fix (see bug #3 above),
so `examples/11_table_selection_highlight.py` keeps the color/size-array
approach rather than switching to `selected`.

All 13 examples, both gallery apps, `guide.md`, and this `NOTES.md` are
written and verified. Every code block in `guide.md` is confirmed byte-for-byte
identical to its `examples/`/`gallery/` source file (scripted diff check, zero
mismatches). Every screenshot referenced in `guide.md` exists in `img/` and was
viewed before being referenced. The one gesture not driven for real is the
lasso/rectangle selection payload shape (`fig.on_selection()` pixel-space
payload, and `reactive_read(scatter, "selected")` staying `None` after a
lasso) -- verified before the session restart, not re-driven after, but the
underlying mechanism (no index computation anywhere in ipyvolume's bundled
JS) is a structural, unmaintained-upstream limitation very unlikely to have
changed; low risk left unverified a second time.

## Update 2026-11-11 (main @ 32ca7035)

Versions: shinywidgets `main` @ `32ca7035`, ipyvolume 0.6.3, ipywidgets 8.1.9, pythreejs 2.4.2, shiny 1.9.0,
Python 3.13, shared `main-wt` worktree. Playwright: Chromium headless with `--use-angle=swiftshader
--enable-unsafe-swiftshader --ignore-gpu-blocklist`.

**What changed in the guide and why:**

- **Fixed a real, pre-existing inaccuracy in the `camera()` section, surfaced while checking it against the
  new accessor rules.** The guide said `camera()` "cancels silently (like `req(False)`) until the figure has
  rendered and has a camera," which is misleading in practice: `ipv.figure()` always constructs a camera, so
  this essentially never happens in normal use. Verified directly: reading `plot.camera()` immediately after
  page load, with zero orbits, returns the figure's constructed camera (`position = (0.00, 0.00, 2.00)`), the
  same way pythreejs's shared `camera()` accessor behaves (confirmed: `_camera.py`/`_pythreejs.py`'s
  `not_ready=lambda raw: raw is None` only trips when `fig.camera` is literally `None`). Rewrote to say
  "seeded value," matching the pythreejs guide's equivalent fix in this same pass (same accessor code, same
  bug in the prose, independently re-discovered here).
- Added an explicit, verified statement that `camera()` **re-seeds to the new figure's camera on re-render**
  (built a probe app that orbits, re-renders with new data, and reads `plot.camera()` after each step:
  `(0,0,2)` -> orbited `(-0.92, 0.83, 1.57)` -> re-rendered back to `(0,0,2)`, not the orbited value). Wasn't
  stated this plainly before.
- Replaced the accessor table's columns with the new standard ones (`before any interaction` /
  `across re-render`).
- Added a one-line gotcha that `plot.read("camera")` is not a drop-in substitute for `plot.camera()` (verified:
  it returns the raw synced snapshot tuple, not the live `Camera` object) -- same finding as the pythreejs
  guide, since both share `shinywidgets/_pythreejs.py`'s `CAMERA` spec.
- **Re-verified the pylab re-render stall is still fixed** (the guide's one explicit "what's not a gotcha"
  claim, from NOTES.md bug #2 / PR #348): 6 slider-driven re-renders of a pylab figure, no hangs, no console
  errors, each settling in ~0.1s (fixed-wait probe). Nothing in the 00f90249..32ca7035 range touches this path
  (#442 only changes `shared_lifetime()`'s docs, not its behavior), so this is confirmation, not a new finding.
  No guide text changed -- the claim was already accurate.
- Did not re-investigate `INVESTIGATION.md` (the `Scatter.selected` empty-array crash) further: it's an
  upstream, unmaintained-library bug unrelated to any commit in this update's range, and the guide's existing
  workaround (color/size array highlight instead of `selected`) is unaffected by #415/#437/#405.
- No other sections needed changes: #405 (browser-created-model leak) doesn't apply to ipyvolume (it builds no
  browser-created light targets/shadows the way pythreejs does); #415 doesn't change anything here (no example
  calls a `.send()`-backed widget method from the render function).

## Bugs found (2026-11-11)

None new. The one fix re-verified in this pass (the pylab stall) was already known-fixed from a prior commit
outside this update's range; confirmed still fixed.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." Reused the guide's own existing "100k+, see k3d"
framing from the intro rather than re-measuring a new ceiling; classified as GPU-in-the-browser (same bucket as
k3d) with k3d as the explicit escalation path past ~100k points. No new example needed. Links forward to the
not-yet-written `../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) --
expected `check_docs.py` anchor warning.
