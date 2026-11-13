# NOTES: ipycanvas guide

## Update 2026-11-11 (main @ 32ca7035)

shinywidgets commit `32ca7035` (worktree `main-wt`), same ipycanvas/numpy/pillow/scikit-learn/shiny versions as
the original pass (unchanged on this branch).

**Accessors: still none.** `render_ipycanvas` has no `_accessor_specs` on current main either -- re-confirmed by
reading the class directly. No accessor-reference table needed; this guide was and remains correctness-fixes +
terminology only (per the update brief: "a guide whose widget has no new capability gets correctness fixes
only").

**What changed and why:**
- Converted the one `reactive_read(canvas.widget, "image_data")` pattern to `canvas.read("image_data")`
  throughout -- `render_ipycanvas` subclasses `render_widget_base`, so `.read()` is available even though there
  are no accessors (it falls through straight to the bare-trait path). Touched `guide.md` (5 sites:
  "Beyond callbacks" section + code block, the re-render section's isolate() note, the digit-classifier section +
  code block, Gotchas, and the showcase gallery blurb), `examples/14_coordinate_digit_classifier.py`, and
  `gallery/showcase_digit_sketchpad.py`. Re-verified both files in a browser: drew a "1" by hand in each
  (`page.mouse` strokes), confirmed the SVM prediction updated correctly off `canvas.read("image_data")`
  (98% confidence on "1" in the showcase, correct single-shot prediction in `14_...py`); replaced
  `img/digit_classifier_one.webp` and `img/gallery_digit_sketchpad_after.webp` with fresh screenshots.
  `img/digit_classifier_before.webp`/`digit_classifier_zero.webp` were not re-screenshotted -- the pixel/visual
  result is identical regardless of which Python-side accessor reads the bytes, so the existing images still
  show accurate rendering; only the files whose *code* changed got fresh shots.
- **#415 (widget messages delivered before the output finishes rendering) does not change any drawing-before-
  render advice in this guide, and the guide needed no new caveat.** Investigated because ipycanvas draw
  commands (`fill_rect`, `stroke_line`, ...) go through `Canvas._send_custom()` -> `Widget.send()`, the exact
  custom-message path #415 touches -- and every example in this guide draws directly inside the `@render_ipycanvas`
  function, the shape that render-widget's guide documents as historically risky for a literal `widget.send()`.
  Despite that, the prior pass's NOTES already verified these examples worked on main @ `00f90249` (pre-#415),
  and re-verification on `32ca7035` confirms they still do -- drawing inside the render function was never
  actually subject to the dropped-placeholder-send problem for the initial widget-construction case (unlike a
  *re-render*'s dependent effect, which render-widget's mapwidget example did hit). The guide's existing
  `11_inplace_vs_rerender.py` section (an in-place color effect that re-runs against a freshly re-rendered
  widget, reading `.widget` inside the same flush as the re-render) was already verified working pre-#415 too,
  for the same reason. Nothing to add or remove; confirmed by re-reading the relevant guide sections (no
  existing caveat claimed drawing-in-render was risky) and by one fresh end-to-end re-verification of the digit
  classifier (draw -> correct prediction, same as the prior pass).
- No other commits in 00f90249..32ca7035 touch ipycanvas; nothing else in the guide needed updating.

## Versions

- Date: 2026-11-02
- ipycanvas 0.14.3, numpy 2.5.4, pillow 13.0.0, scipy 1.18.1, scikit-learn (overlay, latest resolvable via
  `--with scikit-learn`; not pinned in the base venv), shiny 1.9.0, Python 3.12
- shinywidgets: `main` @ `00f90249` (the dedicated run worktree, detached from `origin/main`) for the whole session
- Playwright Chromium, headless, launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` for every screenshot (defensive; plain 2D canvas content rendered fine either way)
- Session note: this guide was built across two interruptions (coordinator restarts) that wiped the scratchpad and
  killed all running servers. Research and conclusions below reflect the final, re-verified pass. During the
  second resumption the coordinator reported "machine load spiked to 200+" and "disk nearly full" -- both had
  largely subsided by the time of final verification (load avg ~8-10 one-minute, ~33GB free), but see the "Bugs
  found" entry below for a finding made partly under the high-load window that was re-confirmed afterward anyway.

## Accessors

None. `render_ipycanvas` (in `shinywidgets/_render_widget.py`) is a plain `render_widget_base` subclass with no
`_accessor_specs` -- confirmed by reading the class definition directly (no `ACCESSORS` constant referenced,
unlike `render_plotly`/`render_bokeh`/etc.). This matches the assignment's expectation and the roster's "Input &
drawing" category being accessor-light. The guide instead documents the callback -> `reactive.value` recipe (the
assignment's explicit ask) and the one `reactive_read()`-worthy trait, `image_data` (via `sync_image_data=True`).

## Verification table

All examples run via `uv run --no-sync python -m shiny run <file> --port <9820-9839>` from the worktree, screenshotted
with Playwright Chromium (1280x800, device_scale_factor=2), and every screenshot read back with the Read tool
before being referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | fill+center confirmed |
| `examples/02_drawing_primitives.py` | yes | yes | n/a (static) | real gapminder 2007 top-6 GDP data |
| `examples/03_multicanvas_layers.py` | yes | yes (before/after) | click "Clear sketch" button | per-layer clear confirmed: ink layer erased, grid layer untouched |
| `examples/04_put_image_data.py` | yes | yes | n/a (static) | real iris correlation matrix |
| `examples/05_game_of_life.py` | yes | yes (t0/t1) | n/a (auto-animates); separately re-verified play/pause click actually works (fingerprint unchanged while paused, changed while playing) | |
| `examples/06_rough_canvas.py` | yes | yes (hachure + cross-hatch) | `select_option` on fill-style dropdown | |
| `examples/07_hold_canvas_noop.py` | yes | yes | click "Draw 8 bars" button | mechanism verified via source (see Bugs found: docs below, not a bug); websocket frame-count experiment was inconclusive (Shiny's own per-flush batching masks any ipycanvas-level difference) -- documented as source-verified instead |
| `examples/08_mouse_events_recipe.py` | yes | yes (before/after) | real `page.mouse` drag | stroke count, last point both confirmed exact |
| `examples/09_keyboard_recipe.py` | yes | yes (before/after) | click to focus + `page.keyboard.press` arrow keys x8 | square moved correctly, last key displayed |
| `examples/10_rate_limiting.py` | yes | yes | 80 synthetic `page.mouse.move` calls | 80 raw events -> 14 throttled samples at a 100ms gate |
| `examples/11_inplace_vs_rerender.py` | yes | yes (before/after) | drag stroke + `select_option` color + click re-render button | stroke survives color change, lost after re-render; color re-applies after re-render (see "widget re-render subscription" finding below) |
| `examples/12_coordinate_click_to_table.py` | yes | yes (before/after) | 4x `canvas.click(position=...)` | table rows match click order and (offset) coordinates |
| `examples/13_coordinate_table_to_canvas.py` | yes | yes (before/after) | `page.get_by_text("Mizar").click()` | highlight ring + label appear at the right star |
| `examples/14_coordinate_digit_classifier.py` | yes | yes (before/"1"/"0") | synthetic mouse strokes drawing a "1" and a "0" | both classified correctly by the trained SVM |
| `examples/15_layout_sizing.py` | yes | yes | n/a (static, 3-column layout) | measured exact px via `getBoundingClientRect` for all 3 sizing paths |
| `gallery/template_game_of_life.py` | yes | yes (seeded/running) | click to seed a glider, click Play, pixel-fingerprint check | generation counter advanced (0 -> 17 in ~2s at a 0.12s tick, consistent with real time), play/pause and clear buttons all confirmed working after the fix described below |
| `gallery/showcase_digit_sketchpad.py` | yes | yes (before/after) | synthetic mouse strokes drawing a "7" | predicted "7" at 84% confidence, "2" at 16%; drawn-count incremented correctly |

Not covered: touch events (`on_touch_*`) -- headless Chromium via Playwright has no simple multi-touch
synthesis, and `on_client_ready` replay (no second-client scenario was built for this guide; out of scope per the
brief's per-widget focus).

## Bugs found

### shinywidgets (docs only, not a defect)
`own_ipycanvas_manager()`'s docstring and the `render_ipycanvas` docstring both describe `hold_canvas()` as a
no-op under shinywidgets. Confirmed precisely by reading ipycanvas 0.14.3's installed source: `hold_canvas()`
toggles `ipycanvas.canvas._CANVAS_MANAGER._caching` (the module-level singleton), while
`own_ipycanvas_manager()` replaces each rendered canvas's `_canvas_manager` trait with a fresh per-canvas instance
before the canvas's state is ever serialized -- so `hold_canvas()` is toggling an object nothing actually draws
through. This is accurately documented already; no action needed, just independently re-verified against
current main's exact source.

### Old report findings, confirmed FIXED on current main
`docs/widget-reports/ipycanvas/report.md` findings 3.1 ("`layout.height` stretches the bitmap") and 3.2 ("canvas is
left-aligned, not centered, on non-fill paths") do **not** reproduce on current main. Measured exact
`getBoundingClientRect()` values for all three sizing paths (default fill, explicit `height=`, `widget.layout.height`)
in `examples/15_layout_sizing.py`: all three now shrink preserving aspect ratio and center both horizontally and
vertically. Reading `shinywidgets/static/shinywidgets.css`'s `.shinywidgets-ipycanvas` rule confirms the fix is
already in place (the centering/no-stretch rule explicitly covers non-fill paths too, with a comment explaining
why). Dropped from this guide's Gotchas section; noted here so the old report isn't mistakenly treated as still
current.

### Possible py-shiny reactive-flush edge case (not shinywidgets-specific) -- judgment call, flagged for a second opinion
While building `gallery/template_game_of_life.py`, an initial version made the simulation grid a `reactive.value`,
written from three places: a mouse-click callback, a `reactive.invalidate_later()`-driven tick effect, and
separate button-triggered effects (play/pause via `@reactive.event(input.toggle)`, randomize, clear). The
play/pause button never worked -- confirmed server-side with `print()` statements that the toggle effect's body
simply never executed, no matter how long (10+ seconds) the test waited. A render.text output depending on the
same tick loop's value got stuck permanently in Shiny's `recalculating` state (confirmed via `outerHTML`, never
received a single value).

I narrowed this to a **minimal, pure core-Shiny repro with no shinywidgets or ipycanvas involved at all**:
```python
from shiny import App, reactive, render, ui
app_ui = ui.page_fillable(ui.input_action_button("toggle", "Play/pause"), ui.output_text("state_text"))
def server(input, output, session):
    generation = reactive.value(0)
    running = reactive.value(False)
    @reactive.effect
    @reactive.event(input.toggle)
    def _():
        running.set(not running())
    @render.text
    def state_text():
        return f"running={running()} gen={generation()}"
    @reactive.effect
    def _tick():
        reactive.invalidate_later(0.12)
        if not running():
            return
        generation.set(generation() + 1)
app = App(app_ui, server)
```
Clicking "toggle" never changes `state_text`, at any wait length, in this environment. I could not fully isolate
the exact triggering condition in the time available (it did *not* reproduce once `generation`/`grid` was changed
to a plain mutable Python global instead of a `reactive.value`, matching `examples/05_game_of_life.py`'s existing,
already-working pattern) -- so the practical fix (documented in the guide's "Updating the widget from Python"
section) is: **for animation-loop state driven by `invalidate_later()`, use a plain mutable object, not a
`reactive.value`, and have every writer redraw the widget directly.**

I'm flagging this as a judgment call rather than a confirmed, filed bug because: (a) it reproduces with no
shinywidgets code at all, so it's out of this repo's scope to fix; (b) part of the investigation happened during a
reported machine load spike (200+), and I could not rule out load-sensitivity with full confidence even though a
clean re-test at a calmer moment (~load avg 8-10) reproduced it identically; (c) I did not have time to bisect
py-shiny's source for the exact mechanism. Worth a second opinion from the maintainer, and possibly worth
mentioning to the py-shiny team if it reproduces for them too. The user's own memory notes reference prior,
possibly-related investigation into py-shiny flush ordering (`project_shiny_flush_ordering.md`,
`project_shiny19_auto_output_flush.md`) that I did not have access to re-read in depth given the time already
spent; worth cross-referencing.

**Resolution (2026-11-02, Decision 6):** root-caused as a self-read-write starvation loop, not a py-shiny
flush bug -- `generation.set(generation() + 1)` makes the tick effect depend on the value it writes, so it
re-invalidates itself continuously and the input event never gets processed. Re-verified in this environment:
the original repro above stayed broken (toggle never registered, 0/3 clicks), while the same app with
`with reactive.isolate():` around the read-write passed 3/3 clicks with the generation counter advancing while
running. The guide's Gotchas entry now names the mechanism and recommends `reactive.isolate()` alongside the
plain-mutable pattern. No py-shiny issue filed.

## Judgment calls

- Treated "no accessors" as settled fact (confirmed by reading `_render_widget.py` directly), per the assignment's
  own expectation, and leaned the whole "Reacting to user interaction" section on the callback recipe + the one
  `reactive_read`-able trait (`image_data`) instead of an accessor table.
- Chose the digit-sketchpad-classifies-via-sklearn pattern as the "coordinating multiple views" headline and the
  showcase gallery app, per the assignment's explicit suggestion. Built the small in-guide version
  (`examples/14_...`) and a richer gallery showcase with confidence bars rather than duplicating full complexity in
  the guide body.
- `template_game_of_life.py` was chosen as the required gallery template over a simpler "click to place points"
  app because it exercises three ipycanvas concepts at once (click interaction, `put_image_data`, an
  `invalidate_later` animation loop) in one small, adaptable file -- and because building it surfaced the reactive-flush
  finding above, which is valuable for the maintainer to see either way.
- Used real/recognizable data wherever it didn't fight the point of the snippet: `plotly.express.data.gapminder()`
  (bar chart highlight), `plotly.express.data.iris()` (correlation heatmap via `put_image_data`),
  `sklearn.datasets.load_digits()` (the classifier). Game of Life, the mouse/keyboard recipes, and the layout demo
  are necessarily synthetic (there's no "real dataset" for a cellular automaton or a focus-ring demo).
- Did not attempt to verify touch events (`on_touch_start/move/end/cancel`) -- no straightforward way to synthesize
  multi-touch in headless Playwright was readily available within the time budget. Documented as unverified in
  Gotchas rather than silently skipped.

## Editor's notes for the website

- Strongest sections: "What you can build" (Game of Life highlight + before/after screenshots), the digit
  classifier (both the small in-guide version and the full gallery showcase) -- this is the "wow" moment for the
  whole guide and should probably lead the page or be the hero if the coordinator wants a more dynamic hero than a
  static screenshot.
- The "Reacting to user interaction" section is dense because there's no accessor table to lean on; could trim the
  rate-limiting subsection for a shorter page (it's useful but not as visually interesting as the others).
- Cut from the old report: the detailed PR-review content (manager-swap correctness, multi-session isolation
  internals, `SESSION_WIDGET_ID_MAP` growth) -- all implementation detail, not user-facing, and the old report
  itself says PR #328 (which it reviewed) is merge-ready with no blockers. Kept only the two findings that affect
  what a user should actually do (`hold_canvas()` no-op, sizing behavior) and re-verified both against current
  main rather than trusting the old report's dates.
- Pairs well with: itables/reactable (table row selection -> canvas highlight, example 13's pattern generalizes),
  mols2grid or k3d (click a canvas-driven index into another visualization).

## What from the old report was dropped, and why

- PR review mechanics (manager-swap ordering, comm-open race analysis, `WIDGET_INSTANCE_MAP` lifecycle counts) --
  internal implementation detail aimed at a code reviewer, not a guide reader; the PR has already merged.
- The "scorecard" (star ratings per dimension) -- replaced by concrete, current-main-verified claims throughout
  the guide body instead of a summary table.
- `3.5` (`SESSION_WIDGET_ID_MAP` growth), `3.6` (mouse coordinate scaling correctness), `3.8` (environment/harness
  noise) -- all "non-issue" findings about testing infrastructure, not user-facing behavior.
- `3.1`/`3.2` (stretched bitmap / left-aligned canvas on non-fill paths) -- re-verified and found fixed on current
  main (see "Bugs found" above); kept as a one-line historical note instead of a current limitation.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views" -- the one-sentence "no meaningful large-data story"
treatment the task called for, since ipycanvas is a drawing surface with no point/row count to scale against.
Pointed to k3d as the sibling for exploring large data interactively. No new example or measurement needed.
