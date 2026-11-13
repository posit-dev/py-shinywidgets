# NOTES: rerun guide

Versions: rerun-sdk 0.41.0, rerun-notebook 0.41.0 (both bundled by `rerun-sdk[notebook]>=0.40`), Python 3.12.13,
shiny (worktree-synced, `uv sync --all-groups`), plotly 6.9.0. shinywidgets commit: `00f90249` (main). Date:
2026-11-02 (work spanned 2026-10-30 to 2026-11-02; the coordinator's scratchpad was wiped and the worktree
recreated mid-task at a slightly newer `main` commit -- `00f90249` vs the `f8238de6` seen at the start of the
session -- no rerun-related files changed between those commits, so earlier screenshots/examples were not
re-verified against the newer commit, only continued from).

All work run from the dedicated worktree per BRIEF.md (`uv run --no-sync ...`, `RERUN_NOTEBOOK_ASSET=serve-local`
in every app to avoid the CDN). Ports 9740-9750 used, one Chromium instance at a time, servers started/stopped by
PID via a context manager, nothing left running.

## Verification table

Every app launched with `shiny run`, driven with Playwright (Chromium headless, 1280-wide viewports, heights
varied 800-1100 to fit rerun's full chrome when relevant, `device_scale_factor` 1.5-2), screenshots read back with
the Read tool before referencing them in the guide.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a (static build) | also the first proof that a bare `os.environ.setdefault(...)` line renders as page text in Shiny Express -- fixed to an `if`, see Bugs |
| examples/02_multimodal_scene.py | yes | yes (+2 timeline before/after) | playhead drag (mouse down/move/up at calibrated pixel offsets) | drag required 3 calibration attempts; see Bugs |
| examples/03_blueprint_layout.py | yes | yes | n/a (static build) | dark theme + collapse_panels verified visually |
| examples/04_streaming.py | yes | yes (before/after, 4s apart) | n/a (timer-driven) | confirms live `rec.log()` after first render streams with no re-render |
| examples/05_selection.py | yes | yes (before/after) | selection simulated via `window.widgetManager` model.send() (see Bugs/judgment calls); empty-selection-at-load verified with zero simulation | accessor **verified**: entity path + 40 history rows rendered correctly |
| examples/06_update_in_place.py | yes | yes (3 before/after pairs) | 3 button clicks (log_more, toggle_panel, replay) | `update_panels()` toggle only visibly moves an icon in this app (no custom blueprint); content-visible case is in 03 |
| examples/07_slider_scrub.py | yes | yes (before/after) | Shiny slider handle dragged via `.irs-handle` (ion.rangeSlider), not the outer container -- first attempt (outer div bounding box) silently no-opped | `set_time_ctrl()` from a Shiny input verified: robot position + chart cursor moved together |
| examples/08_selection_to_plotly.py | yes | yes (before/after) | selection simulated via model.send() | cross-widget highlight verified: correct obstacle turned red in the plotly trace |
| gallery/template_live_tracker.py | yes | yes (before/after) | selection simulated via model.send() | |
| gallery/showcase_robot_patrol.py | yes | yes (3 screenshots) | log_event click, selection simulated, pause toggle + slider drag | first pass at default viewport height clipped the Events panel to its header row only; a taller viewport confirmed the row was there all along (see Judgment calls) |

Accessor coverage: `selected()` is the only accessor (`shinywidgets._rerun.SELECTION`). Verified in 4 apps
(05, 08, both gallery apps) via the empty-selection-at-load case (100% real, no simulation) and via a simulated
`selection_change` message for a populated selection (see "Judgment calls" for why).

## Bugs found

**shinywidgets/example-authoring (not a shinywidgets runtime bug, but a sharp edge worth flagging loudly):**

- A bare top-level expression whose value is a string renders as page text in Shiny Express (the same display-hook
  mechanism as a Jupyter REPL cell). `os.environ.setdefault("RERUN_NOTEBOOK_ASSET", "serve-local")` returns the
  string `"serve-local"`, and my first draft of every example rendered that string above the viewer. Fixed by
  using `if "RERUN_NOTEBOOK_ASSET" not in os.environ: os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"` (an
  `if` statement, not an expression statement) in every example. This isn't rerun-specific -- it would bite any
  guide whose setup code calls a function for its side effect but happens to return a string -- so flagging for
  the coordinator in case other guides hit the same thing with a different stdlib call.

**Upstream rerun (verified on rerun-sdk/rerun-notebook 0.41.0, matches the pre-accessors report where it also
checked):**

- `rr.notebook_show()` is a no-op in Shiny (renders via Jupyter's display machinery) and drains the recording.
  Matches the old report; still true. Covered in the `render_rerun` docstring already.
- An empty `rerun_notebook.Viewer` (nothing logged yet) shows rerun's marketing welcome screen despite
  `hide_welcome_screen: true` being set. Cosmetic; matches the old report.
- Viewer sizing traits (`_width`/`_height`) accept only `"auto"` or an integer; any other CSS string silently
  falls back to 640x480. Matches the old report.
- The top bar's environment warning badge ("Software rasterizer" under headless Chromium without a GPU) can
  visually overlap its own icon row in a narrow (~620px) container. Not mentioned in the old report (that report
  didn't test narrow containers); minor, upstream chrome, not reported further.

**No shinywidgets runtime bugs found.** The comm/anywidget machinery, the `rerun_notebook` layout-defaults
handler (`rerun_layout_defaults`), and the `selected()` accessor's eager-attach/generation-guard machinery all
behaved exactly as documented across every example and gallery app.

## Judgment calls

- **Selection verification uses a simulated browser-side message for the "populated" case**, not a real pixel
  click. shinywidgets' own `tests/playwright/rerun_accessors/test_rerun_accessors.py` already has a *skipped*
  test (`test_selection_follows_stream_tree_clicks`) documenting that coordinate-based clicks on this canvas-drawn
  UI are flaky; I independently hit the same thing (clicks landed on the view background or the wrong box
  several times during exploration) before reading that test, and later found it confirms the approach. Per
  BRIEF.md's explicit guidance for this exact situation, I used `window.widgetManager` to get the widget's model
  and called `model.send(JSON.stringify(selectionChangeEvent))` directly -- the same code path
  (`handle_msg` -> `_raw_event_callbacks` -> `_on_raw_event` -> `_viewer_event_from_json_str` -> `selected()`) a
  real click's message takes, with only the pixel-perfect click gesture substituted. The **one** fully organic,
  unsimulated proof is the empty-selection-at-load case (verified in 05/08/both gallery apps with no simulation
  at all), which already proves the eager-attach mechanism end-to-end; the simulated message additionally proves
  the full event parses and threads through to a populated `.items` list correctly. Flagging this clearly in case
  the maintainer wants a stronger standard for "verified."
- **The timeline-scrubber drag (02_multimodal_scene) is a real mouse drag**, not a simulation -- it just took
  calibrating pixel offsets against the ruler's labeled tick marks (`#0`...`#50`) to find the playhead and a
  destination x-coordinate. A plain click (no drag) at a point on the track set a "visible range" highlight
  instead of moving the playhead; only a mouse-down-move-up drag on the current playhead position seeks it. Not
  worth generalizing into reusable driver code for a single guide, but worth a line here in case another agent
  hits the same surprise.
- **Dropped a fourth "coordinating multiple views" pattern** (a Shiny dropdown recoloring a box entity --
  "Shiny input -> what gets logged/shown" in the reverse direction) to stay within the brief's "2-4, never pad"
  guidance. The two directions it would have covered are both already present elsewhere: "Shiny input -> what
  gets logged" is the `log_more`/`log_event` button in `06_update_in_place.py` and the showcase; "Shiny input ->
  what's shown" is the slider-scrub pattern. Happy to add it back if the maintainer wants a fourth, purpose-built
  linked-view example.
- **`06_update_in_place.py`'s panel-toggle demo has a weak "after" photo** -- this app has no custom blueprint, so
  the viewer's default panel state doesn't show a blueprint-tree panel to begin with at the tested viewport size;
  toggling `update_panels(blueprint=...)` only visibly changes the top-bar icon's active state, not an actual
  panel sliding open. The guide text says so explicitly and points to the blueprint-layout section for a case
  with visible panel content. Considered cutting this screenshot pair entirely; kept it because the Python-side
  call still demonstrably reaches the browser (icon state is real evidence), and removing it would leave
  `update_panels()` with zero visual evidence at all.
- **The showcase app's first screenshot pass clipped the "Events" panel to its header row** at the original
  900px-tall viewport -- the TimeSeriesView's legend box ate most of the shared column's height. I initially
  worried this meant `rec.log("robot/log", ...)` wasn't reaching the TextLogView, but a taller viewport (no code
  change) showed the row was there all along. Re-shot all three showcase screenshots at 1050px tall. Mentioning
  in case the maintainer wants the blueprint's `row_shares` tuned for shorter viewports instead of relying on
  viewport height.
- Used a synthetic robot-patrol dataset (circular/spiral path, a few box obstacles, a synthetic sky/ground camera
  frame) throughout, reused across nearly every example for a consistent "running example," rather than a
  different dataset per section. BRIEF.md's data guidance prefers real/recognizable data "especially for the
  hero, quick start, and gallery," but also explicitly allows synthetic data "when no real dataset fits" -- rerun
  itself is built around exactly this kind of multimodal robotics log, and I could not find a small, licensable,
  offline-available real recording (rerun's own example datasets are fetched from their asset server, which
  BRIEF.md's no-network-except-public-docs rule and the Python 3.11-floor/isolated-worktree setup made impractical
  to depend on for a guide that should keep working later). The synthetic data is built to look plausible (smooth
  spiral, sensible battery/speed ranges, no hard cutoffs).

## Editor's notes for the website

- Strongest sections: "The timeline scrubber" (two-screenshot before/after makes the shared-timeline concept
  concrete immediately) and "Updating the widget from Python" (three distinct in-place mechanisms, each with its
  own before/after).
- The "What you can build" multimodal-scene screenshot is probably a better hero candidate than the showcase if
  the website wants the hero to double as the Quick-start-adjacent image (it's light-themed and reads cleanly at
  small sizes); I used the showcase's "selected" screenshot as the hero instead because it's the most visually
  rich single frame (dark dashboard + 3D + chart + table + Python-driven detail panel in one shot) and most
  directly sells "what this lets you do." Easy to swap -- both are in `img/`.
- If the page needs to shrink: cut the `06_update_in_place.py` panel-toggle pair first (weakest evidence, see
  Judgment calls above) before cutting anything else; the three in-place mechanisms could be reduced to two
  (log-more, replay) without losing much.
- The "Gotchas and limitations" list is longer than some sibling guides' because rerun carries real,
  non-obvious session-isolation and testing-methodology caveats that a reader will hit quickly; I'd keep all of
  it rather than trim for length.

## Dropped from the old report (`docs/widget-reports/rerun/report.md`)

- The whole PR-review framing (scorecard, merge-readiness verdict, severity-ranked findings list, "follow-ups"
  asking the maintainer questions about an unmerged PR) -- `render_rerun` is merged and on main now, so none of
  that framing applies; this guide reports what's true of main today instead.
- The code-review notes about the implementation itself (file-by-file description of `_as_widget.py`,
  `_render_widget.py`, the layout-defaults handler) -- that's implementation detail for shinywidgets contributors,
  not for someone learning to use the renderer; the parts a *user* needs (per-session recording, `notebook_show()`
  dead end, sizing vocabulary) are carried into this guide's "Gotchas" instead.
- The "Scorecard" dimension-by-dimension ratings table -- redundant with the prose once the PR-review framing is
  gone.
- `send_table()` (pyarrow tables) and `block_until_ready()` -- the old report flagged these as untested/a no-no,
  respectively; I didn't re-test `send_table()` (no compelling Shiny-specific use case surfaced for this guide)
  and dropped `block_until_ready()` entirely rather than devoting guide space to a function a Shiny user should
  simply never call (it pumps `jupyter_ui_poll` in a loop and would block the event loop) -- the docstring already
  omits it for the same reason.
- Thread-based logging (the old report verified logging from a background Python thread worked, with a caveat
  about `on_flushed`/thread-safety). Deferred: the reactive-accessors design doesn't add anything new here, and
  BRIEF.md's effort is better spent on accessors/linked-views than re-verifying a threading caveat that hasn't
  changed since the old report. Worth re-adding if the maintainer wants a "streaming from a background task"
  example distinct from the `reactive.invalidate_later` one in this guide.

## Update 2026-11-11 (main @ 32ca7035)

- **`selected()`'s re-render behavior was imprecise in the old guide (fixed).** The original pass (written
  against `00f90249`, before #437) called `selected()` "an event accessor, not state" that "resets to `None`
  on every re-render." Current source (`shinywidgets/_rerun.py`) declares `SELECTION` with `kind="state"`, and
  `tests/unit/test_rerun_accessors.py::test_renderer_selection_round_trips_and_is_retained` explicitly asserts
  "a re-render keeps the last selection." Verified live with the same `window.widgetManager`
  model-message-simulation technique the old guide used (still the only reliable way to drive this canvas-drawn
  UI -- see below): simulated a selection, forced a re-render, and read `selected()` at increasing delays.
  Found a real, three-part nuance neither "kept" nor "re-seeded" alone captures: immediately after the
  re-render (~200ms) `selected()` still returned the *old* selection (genuinely kept, matching the unit test);
  about a second later it had flipped to `evt.items == []`, because the *new* viewer's frontend sends its own
  empty-selection message once it finishes loading in the browser -- the same message that produces the
  empty-at-mount state. Net effect for a user: a carried-over selection is visible only for a brief,
  unreliable window after a re-render, so the guide now says to treat a re-render as clearing the selection in
  practice, while being accurate about the underlying "kept" mechanism. Rewrote the accessor reference table
  (new `before any interaction` / `across re-render` columns) and the "Three things worth knowing" paragraph
  accordingly.
- **The "verified via a simulated event" honesty note still applies and is unchanged.** Re-confirmed this pass:
  `tests/playwright/rerun_accessors/test_rerun_accessors.py::test_selection_follows_stream_tree_clicks` is
  still `@pytest.mark.skip`'d for the same canvas-hit-testing-is-flaky reason the old guide documented, and my
  own probe reproduced the same difficulty. No code example changed (only `guide.md` prose/table), so no new
  screenshots were needed for this update.
- No other `render_rerun` behavior changed between `00f90249` and `32ca7035`; the rest of the guide (session
  isolation, multimodal logging, blueprints, streaming, in-place updates, linked views, layout, Gotchas) was
  re-read against current `main` source and still matches.
- `accessors:` front matter unchanged (`[selection]`).
- No read-on-demand example added for this guide: unlike niivue's `location()` or ipyaladin's `target()`/`fov()`,
  rerun's `selected()` does *not* stay reliably readable after a re-render (see above), so a "read it later
  behind a button" example would be misleading rather than illustrative. Skipped per the brief's "don't pad"
  guidance and because no per-widget instruction asked for one here.

### Verification (this update)

Via a scratch probe app (a re-render button + a `@render.code` selection readout), driven with the same
`window.widgetManager` / `model.send(json_str)` technique as the original pass (confirmed the right model via
its unique trait set: `_width`/`_height`/`_panel_states`/`_theme`/`_url`/`_fallback_token`).

| Check | Result |
|---|---|
| `selected()` before anything | `[]` (load-time empty selection) |
| `selected()` after a simulated selection | `[EntitySelectionItem:points]` |
| `selected()` ~200ms after a forced re-render | still `[EntitySelectionItem:points]` -- kept |
| `selected()` ~1s after the same re-render | `[]` -- the new viewer's own load-time message overwrote it |
| `selected()` ~3s after | `[]` -- stable |

### Bugs found (2026-11-11)

None. `selected()`'s `kind="state"` classification and its unit test's "retained" assertion are both accurate;
the old guide's informal "event, not state" language was the only thing wrong, and it undersold a real nuance
(the brief window where it's genuinely kept) rather than misstating the eventual outcome.

## Pairs with

- **plotly** -- `examples/08_selection_to_plotly.py`: rerun's `selected()` drives an in-place `go.FigureWidget`
  marker-color update, mirroring the in-place-update idiom plotly's own guide already documents.
- Any renderer with a settable widget trait could stand in for the plotly half of that pattern (e.g.
  **ipyleaflet**'s marker colors, **itables**' `selected_rows`) -- noted in the guide's cross-reference line.

## Update 2026-11-11 (C4 fix: load-time empty selection is now ignored)

- **Behavior change (fix/accessor-c-fixes, PR pending):** `shinywidgets/_rerun.py`'s `attach_selection` now
  ignores the *first* empty `selection_change` per attach (the viewer's load-time seed). Consequences, both
  verified below: (a) `selected()` stays `None` until the user's first selection (previously it settled on
  `evt.items == []` shortly after mount); (b) a selection is now genuinely **kept across re-renders** -- the
  new viewer's load-time report no longer overwrites it (previously it did, ~1s after the re-render, per the
  repro table in the 2026-11-11 update above).
- **Verified:** `tests/unit/test_rerun_accessors.py` gained `test_selection_ignores_the_load_time_empty_seed`
  (seed ignored; a *subsequent* empty event is a real deselection and is emitted) and the retention test now
  asserts the seed doesn't clobber a kept selection. `tests/playwright/rerun_accessors/` gained
  `test_selection_survives_a_rerender` (simulated selection, forced re-render, selection still present 5s
  later) and `test_selection_waits_for_the_first_selection`; all pass. `examples/05_selection.py` re-run in
  the browser against the fixed code: before/after screenshots re-taken and looked at (the before shot now
  shows the new "(nothing selected yet...)" message, proving `None`-at-load).
- **Guide updates:** accessor reference table (`before any interaction` / `across re-render` columns), the
  `selected()` subsection prose, the "Three things worth knowing" paragraph, and the verification note;
  `examples/05_selection.py`'s `None`-branch message ("(waiting for the viewer's first report)" made no sense
  once there's no pending first report); the cheatsheet's rerun row.
- **Now viable, not done:** the 2026-11-11 judgment call against a read-on-demand example ("selected() does
  not stay reliably readable after a re-render") no longer applies -- a "read the selection behind a button"
  example would work now. Left out of the C4 fix to keep the diff focused; easy follow-up.

## Update 2026-11-11 (B1 rename: selection() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views," classified as "only send what's visible" (the
Live-streaming example above). Fetched Rerun's own memory-limit docs
(`https://rerun.io/docs/howto/visualization/limit-ram`) for the attributed number (2.5 GB default / 4 GiB
addressable web-viewer cap) rather than inventing one. Caught and corrected a near-miss while writing this: that
page's `memory_limit` knob belongs to `RecordingStream.spawn()`/`.serve_grpc()` (the native-viewer-process path);
I checked `inspect.signature()` on `rerun.notebook.Viewer.__init__` and `rerun.RecordingStream.__init__` directly
in this pass's venv and confirmed neither takes a `memory_limit` kwarg, so the section says the limit isn't
configurable from this integration rather than citing a kwarg that doesn't exist here. No new example needed.
Links forward to the not-yet-written `../articles/performance/article.md#three-approaches-to-large-data` (Task
7, same wave) -- expected `check_docs.py` anchor warning.
