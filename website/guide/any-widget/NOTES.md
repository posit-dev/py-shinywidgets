# NOTES: render_widget (generic path: ipywidgets, anywidget, ipyreact)

## Update 2026-11-11 (main @ d882da46): ipyreact subclass gotcha removed (fixed by #414)

#414 ("fix: resolve JS dependencies for app-module widget subclasses via MRO walk") fixes the root cause the
ipyreact subclass Gotcha documented: `jupyter_extension_destination()` now walks `type(w).__mro__`
(`installed_widget_pkg()`) to the first ancestor class defined in an installed package, instead of trusting a
subclass's own `__module__` (which names the app module for a class defined in `app.py`).

Switched `examples/10_ipyreact_confetti.py` and `guide.md`'s matching snippet from constructing
`ipyreact.ValueWidget(_esm=...)` directly to ipyreact's normal subclass idiom
(`class ConfettiButton(ipyreact.ValueWidget): _esm = ...`), re-verified end-to-end with a real browser click
(`uv run --no-sync python -m shiny run`, Playwright, headless Chromium): the subclassed button renders, reads
`button.read("value")` correctly, and a real click fires confetti and increments the counter (`confetti fired 0
time(s)` -> `confetti fired 1 time(s)`), with zero console errors. Card header text changed ("ipyreact.ValueWidget"
-> "ipyreact.ValueWidget subclass"), so both screenshots (`img/10_ipyreact_before.webp`,
`img/10_ipyreact_after.webp`) were reshot (same crop/framing as the originals) and confirmed looked at.

Removed the in-code comment above `CONFETTI_ESM` that said to construct the base class directly instead of
subclassing (the reason it gave no longer applies), and removed the "Subclassing a third-party widget in your
own app module can silently break its JS dependency resolution" Gotchas bullet entirely (along with its
`../investigations/narrow-canvas-and-subclass/INVESTIGATION.md` Item B cross-link). Added one sentence after
the ipyreact prose instead: subclassing a third-party widget directly in your app module now works the same
way it does in Jupyter, with no special handling needed. Bumped the Gotchas "Verified on current `main`"
commit from `32ca7035` to `d882da46`.

**Judgment call:** while re-verifying, found that the *original* example's `_esm` string
(`React.createElement(...)` with no `import * as React from "react"`) relies on a bare global `React` that
ipyreact does not actually provide -- confirmed independently that a plain, non-subclassed
`ipyreact.ValueWidget` using that exact string also fails with "React is not defined", regardless of #414. This
guide's own `CONFETTI_ESM` was never affected (it already does `import * as React from "react"`), so nothing
needed fixing here; flagging only because it's the same `_esm` text the installation article's now-removed
subclass demo used, and that demo's "fix confirmed" claim had to be checked against a *corrected* `_esm`, not
its original one. See `../articles/installation/NOTES.md` for the full writeup.

Also updated per the coordinator's request: `../FINDINGS.md`'s ipyreact-subclass entry, `../README.md`'s
review-pass TODO rows mentioning it, and an "Update: fixed by #414" note at the top of Item B in
`../investigations/narrow-canvas-and-subclass/INVESTIGATION.md`.

## Update 2026-11-11 (main @ 32ca7035), earlier same day

### Follow-up fix (coordinator-flagged)

Missed on the first pass: the `#### Custom messages, both directions (and a real timing trap)` heading still
named the retired timing-trap narrative even though the section's prose underneath it had already been
rewritten to describe the current (fixed) behavior. Retitled to `#### Custom messages, both directions`.
Checked the whole guide for leftover "trap" language (`grep -ni trap guide.md`) -- zero matches now. No anchor
elsewhere in the roster linked to the old heading slug, so nothing else needed updating.

Versions: shinywidgets commit `32ca7035` (worktree `main-wt`), same shiny/ipywidgets/anywidget/ipyreact/mapwidget/
ipydeck versions as the original pass (unchanged on this branch). Apps run the same way: `uv run --no-sync
[--with <pkg>] python -m shiny run --port <N> <file>` from the worktree, screenshotted with Playwright Chromium,
`device_scale_factor=2`, WebGL apps launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
--ignore-gpu-blocklist`.

**`render_widget` has no accessors**, confirmed unchanged against `_accessor_specs` and the cheat sheet's
"renderers with no accessors" list. The redesign still matters here: `render_widget_base.read()` (defined once,
on the base class every renderer -- including this one -- inherits) is new, so this guide now teaches it as
tier 2 (`output.read("trait")`, a documented shortcut for `reactive_read(output.widget, "trait")`, with an
AttributeError + "did you mean?" hint on an unknown name), keeping `reactive_read()` only for the one genuine
tier-3 case in this guide: a *child* widget (`panel.widget.children[0]` in "Plain ipywidgets").

**What changed in the guide and why:**
- Converted every `reactive_read(x.widget, "trait")` on an output's own widget to `x.read("trait")`, across
  `guide.md` and 9 example/gallery files (`01_quickstart.py`, `03_anywidget_trait_sync.py`,
  `04_anywidget_messages.py`, `07_accessor_helper.py`, `08_third_party_mapwidget.py`, `09_third_party_ipydeck.py`,
  `10_ipyreact_confetti.py`, `11_coordinate_brush_to_table.py`, `gallery/template_anywidget_starter.py`,
  `gallery/showcase_mapwidget_engines.py`). Left `02_plain_composition.py`'s `reactive_read(x, 'value')`
  unconverted (a genuine child widget). `examples/05`, `06`, `12` needed no change (no `reactive_read` calls).
- **#415 (widget messages delivered before the output finishes rendering) retires the guide's entire
  "timing trap" narrative for `render_widget`'s custom messages.** Verified directly with three probes (see
  below): a `widget.send(...)` issued literally inside the render function, and from a bare effect with no
  dependency, both now reach the browser, and a trait write (the shape of mapwidget's `add_call()`) made the
  same way is also delivered -- including across a re-render. Rewrote the big comment block in
  `04_anywidget_messages.py` (no longer claims sends "MUST run from an effect gated on a later event," no
  longer cites k3d's INVESTIGATION.md for a "gate it" conclusion), the "timing trap" paragraph in `guide.md`,
  `08_third_party_mapwidget.py`'s `add_call()` comment, and `gallery/showcase_mapwidget_engines.py`'s header
  comment and in-app comments. Removed two Gotchas bullets that no longer reproduce ("custom message/call
  queued in the same flush... silently dropped," "`widget.send()` issued before comm opens is silently
  dropped"). Removed the two "gotcha" screenshots (`gotcha_engine_swap_drops_pending_call.webp`,
  `gotcha_engine_swap_reapply_after.webp`) and the Gallery blurb describing the drop; replaced with a positive
  demonstration (`gallery_showcase_style_survives_swap.webp`) that the chosen MapLibre style now survives an
  engine swap. This closes the "Bugs found" item from the prior pass below (attributed to #415).
- Rewrote the "Reacting to user interaction" intro and "Beyond the accessors" prose to state the two-tier model
  explicitly (`.read()` for the output's own widget, `reactive_read()` for a child widget), linking to the
  reacting-to-widgets article's mental-model section with the corrected anchor
  (`#the-mental-model-accessors-are-inputs-that-remember` -- the old anchor,
  `#the-mental-model-a-rendered-widget-is-an-input`, was stale from before the article's heading was renamed).
- Updated the quick-start and overview paragraphs to mention `.read()` alongside `.widget`.
- Bumped "Verified on current `main`" in Gotchas from commit `00f90249` to `32ca7035`.
- Did **not** change: front-matter `accessors: []` (still correct, no accessors exist), the subclassing/JS-
  dependency-resolution Gotcha, the ipydeck `@@=` Gotcha, the mapwidget browser-to-Python-only Gotcha, the
  `ipywidgets.Output()` Gotcha, or the output-naming Gotcha -- none are affected by the accessor redesign or by
  any commit in 00f90249..32ca7035.

**Verification probes (scratch, not shipped):** three minimal anywidget probes confirmed #415 before editing
anything: (1) `widget.send(...)` called inside the render function is delivered (`received: 1`); (2) a bare
`@reactive.effect` with no `@reactive.event` gate, same result; (3) a trait write (`add_call`-shaped) made
inside the render function, and again from an effect keyed to the same re-render trigger, both delivered --
matching the real `showcase_mapwidget_engines.py` app, driven end-to-end in a browser: select "Fiord (dark)",
switch engine to leaflet, switch back to maplibre -- the new MapLibre widget shows Fiord dark, not the default
Liberty light style (screenshotted before/after).

**Re-verification table** (every edited example/gallery file re-run in a real browser, fresh screenshot looked
at, `.read()` output confirmed on the Python side):

| File | Re-verified? | Gesture | `.read()` confirmed |
|---|---|---|---|
| `examples/01_quickstart.py` | yes | n/a (static) | `slider.read('value') = 7` |
| `examples/03_anywidget_trait_sync.py` | yes | real click + button | `spark.read("clicked_index")` -> `clicked index: 27`, line redraws after "New random walk" |
| `examples/04_anywidget_messages.py` | yes | real double-click + button | double-click counted (1), flash visible mid-animation |
| `examples/07_accessor_helper.py` | yes | slow drag on both sparklines | 11 vs. 2 fires (unchanged from original pass), `nearest_point()` helper value correct |
| `examples/08_third_party_mapwidget.py` | yes | real click + button | `map.read("clicked_latlng")`/`map.read("zoom")` correct, dark style applied |
| `examples/09_third_party_ipydeck.py` | yes | `window.widgetManager` model-set (real clicks still unreliable under swiftshader, as in the original pass) | `deck.read("click")` returns the set picked object |
| `examples/10_ipyreact_confetti.py` | yes | real button click | `button.read("value")` -> `1` |
| `examples/11_coordinate_brush_to_table.py` | yes | slow drag | `spark.read("brush")` drives both the in-place highlight and the filtered table |
| `gallery/template_anywidget_starter.py` | yes | 4 real cell clicks | `heatmap.read(...)` -> `total clicks: 4, last cell: 40` |
| `gallery/showcase_mapwidget_engines.py` | yes | clicks, selects, button, engine swaps | `mw.read("zoom")`/`mw.read("clicked_latlng")` correct; style/basemap survive an engine swap (new finding, see above) |

Files not touched this pass (`02_plain_composition.py`, `05_anywidget_binary_trait.py`, `06_esm_sources.py`,
`12_coordinate_table_to_widget.py`) were left as originally verified; only re-checked for valid Python syntax.

## Versions

- shinywidgets commit `00f90249` (worktree `main-wt`, detached `origin/main`), shiny 1.9.0, ipywidgets 8.1.9,
  anywidget 0.11.0, ipyreact 0.7.0, numpy 2.5.4, pandas 3.1.0 -- all already in the shared worktree venv.
  `--with` overlays used only for packages NOT already in the venv: `mapwidget` (0.2.0) and `ipydeck` (0.5.0).
  Date: 2026-11-02. Apps run via `uv run --no-sync [--with <pkg>] python -m shiny run --port <N> <file>` from the
  worktree, screenshotted with Playwright Chromium, viewport ~900-1200 wide, `device_scale_factor=2`. WebGL/deck.gl
  apps (ipydeck, mapwidget's maplibre backend) launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist`.
- **Session interruption**: the coordinator's terminal crashed partway through (after 14 example files and 4
  screenshots were already on disk); the worktree, venv, and prior outputs all survived untouched and needed no
  rework. Finished in "lean mode" afterward (one server/one browser at a time, no new `--with` beyond what was
  already used, scratch probes deleted when done) per the coordinator's resume instructions.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? |
|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static slider value) |
| `examples/02_plain_composition.py` | yes | yes | n/a (static read; see Bugs: `Output` widget) |
| `examples/sparkline_widget.py` | n/a (shared module, not a standalone app) | -- | -- |
| `examples/03_anywidget_trait_sync.py` | yes | yes (before/after) | real click (JS->Python) + button (Python->JS) |
| `examples/04_anywidget_messages.py` | yes | yes (before/after) | real double-click + button click, both directions |
| `examples/05_anywidget_binary_trait.py` | yes | yes | n/a (payload measured, not gesture) |
| `examples/06_esm_sources.py` | yes | yes (before/after) | real click (inline-string widget only, representative of all three) |
| `examples/07_accessor_helper.py` | yes | yes | real slow mouse drag on both sparklines |
| `examples/08_third_party_mapwidget.py` | yes | yes (before/after) | real click + real button click |
| `examples/09_third_party_ipydeck.py` | yes | yes (before/after) | browser-model `set()` via `window.widgetManager` (real mouse clicks landed between deck.gl's picking buffer and the visible marker radius unreliably under headless swiftshader; documented in Gotchas) |
| `examples/10_ipyreact_confetti.py` | yes | yes (before/after) | real button click |
| `examples/11_coordinate_brush_to_table.py` | yes | yes (before/after) | real slow mouse drag |
| `examples/12_coordinate_table_to_widget.py` | yes | yes (before/after) | real table row click |
| `gallery/template_anywidget_starter.py` | yes | yes (before/after) | real clicks on 4 distinct grid cells |
| `gallery/showcase_mapwidget_engines.py` | yes | yes (4-shot sequence: initial/clicked/dark/flew-to-Tokyo/leaflet) | real clicks, real selects, real button |

`render_widget` has no accessors (confirmed against the cheat sheet's "renderers with no accessors" list), so
every example uses `reactive_read()` on `.widget` instead, per the brief's fallback instruction.

## Bugs found

- **[authoring hazard, shinywidgets, real and reproducible -- corrected per
  `../investigations/narrow-canvas-and-subclass/INVESTIGATION.md` Item B -- FIXED on main @ d882da46 by #414,
  re-verified 2026-11-11]** Subclassing a third-party widget whose
  `_model_module`/`_view_module` string doesn't match its installed nbextension's registered `dest` name --
  directly in your own app module -- does **not** crash the render with `ModuleNotFoundError`, as I originally
  wrote. Under a real `shiny run`, Shiny has already registered the app file as `sys.modules["app"]` by the time
  any output renders, so the module import that resolution falls back to succeeds and returns the app's own
  module instead of raising. The actual, verified symptom is worse: `require_dependencies()` silently returns `[]`
  for the subclassed widget, no warning is printed by default (`SHINYWIDGETS_EXTENSION_WARNING` defaults to
  `"false"`), and the browser shows a client-side `ReferenceError: React is not defined` with the output stuck in
  an "Error / Try again" state -- no Python traceback anywhere pointing at the cause.
  Root cause: `shinywidgets/_dependencies.py`'s `jupyter_extension_destination()` resolves the widget's *owning
  package* via `widget_pkg(w)` = `type(w).__module__.split(".")[0]`, which is correct for an instance of the
  upstream class itself, but resolves to the *app's own module* for a user-defined subclass. Reproduced exactly
  with `class ConfettiButton(ipyreact.ValueWidget): _esm = "..."` defined in a Shiny app file (ipyreact's own
  `_model_module` is `"@widgetti/jupyter-react"`, which has no `nbextensions/@widgetti/jupyter-react` directory --
  only `nbextensions/jupyter-react`, found via the owning package's own `_jupyter_nbextension_paths()`).
  ~~**Workaround used in `examples/10_ipyreact_confetti.py`**: construct the base class directly
  (`ipyreact.ValueWidget(_esm=...)`) instead of subclassing it, matching ipyreact's own kwarg-based `_esm`
  support.~~ No longer needed (see the fix note above): `examples/10_ipyreact_confetti.py` now subclasses
  `ipyreact.ValueWidget` directly, like any other example in this guide. Plain `anywidget.AnyWidget` subclasses
  were unaffected even before the fix (`_model_module` defaults to `"anywidget"`,
  which matches its own nbextension `dest` exactly, so the first-choice path never fell through to the buggy
  one), and the investigation separately confirmed `ipyleaflet.Map` subclasses were unaffected too (its
  `_model_module` likewise already matches its own nbextension dest) -- this only bit libraries, like ipyreact,
  whose declared module name differs from their nbextension registration *and* were subclassed outside their own
  package. The `_dependencies.py` source comment above `jupyter_extension_destination()` already flagged this
  general class of risk ("it's possible for the widget instance's `__module__` to not point to the right
  package") but didn't mention the subclass-in-app-module case specifically.
- **[FIXED on main @ 32ca7035 by #415 -- re-verified 2026-11-11]** ~~An effect that calls
  `add_call()`/`add_basemap()` in response to a real, later input (not a bare effect) still drops the call
  if that SAME reactive flush is the one that (re-)constructed the widget~~. As of #415 ("widget messages sent
  before the output finishes rendering are now delivered"), this no longer reproduces: driving
  `gallery/showcase_mapwidget_engines.py` through the exact repro described below (select "Fiord (dark)",
  switch engine to leaflet, switch back to maplibre, all in separate flushes but each one re-rendering or
  restyling a brand-new widget) now shows the dark style correctly on the new widget, not the default. Also
  re-verified with two minimal anywidget probes: a trait write made literally inside the render function, and
  one made from an effect keyed to the same re-render-triggering input, are both delivered now. The original
  (now-historical) finding follows, for provenance:
  An effect that calls `add_call()`/`add_basemap()` in response to a real, later input (not a bare effect) used
  to still drop the call if that SAME reactive flush was the one that (re-)constructed the widget -- e.g.,
  switching the `engine` select from maplibre to leaflet, in the same flush, invalidated an effect that also set
  a non-default leaflet basemap on the brand-new widget; the call was silently dropped and the new widget showed
  its own default. Verified with a deliberate repro (`gallery/showcase_mapwidget_engines.py`'s probe: pre-select
  "Esri.WorldImagery", then switch to leaflet -> map rendered plain OpenStreetMap, not satellite). Confirmed
  `await asyncio.sleep(0)` and even `await asyncio.sleep(0.1)` inside the effect did NOT fix it (ruled out as a
  "later asyncio tick" problem) -- only a genuinely separate, later reactive flush (e.g., changing the basemap
  select again afterward) worked. This generalized the single-widget `08_third_party_mapwidget.py` finding (and
  the k3d investigation's root cause) from "first render" to "any render, including a re-render triggered by the
  same input the effect reads."
- **[upstream, ipydeck quirk, re-verified]** `get_position="position"` (a plain string, no `@@=` prefix) still
  silently renders nothing on current ipydeck 0.5.0 -- re-confirmed independently with a fresh repro app (not
  just cited from the old report).
- **[own-code bug, caught before shipping]** The gallery showcase originally named its `@render_widget` output
  function `map`, which shadowed Python's builtin `map()` used inside the showcase's own `haversine_km()` helper
  -- `TypeError: Renderer.__call__() takes 2 positional arguments but 3 were given`. Fixed by renaming the output
  to `mw`. Not a shinywidgets bug, but worth flagging generically: an output function is a module-level name like
  any other, and `map`/`id`/`list`/`type`/`filter`/`input`/`vars` are all real risks for a widget whose
  Pythonic name is also a plain English noun or verb.
- **[environment, not a bug -- root-caused per
  `../investigations/narrow-canvas-and-subclass/INVESTIGATION.md` Item C]** `ipywidgets.Output()` renders nothing
  visible in Shiny when its `outputs` trait is populated via `print()` inside `with out:`. Root cause: `Output`'s
  `__enter__`/`__exit__` don't redirect `sys.stdout` themselves -- they record the current Jupyter kernel's
  message id so the *frontend* can later match incoming IOPub stream messages to this output, the same mechanism
  any notebook cell uses. shinywidgets has no real IPython kernel, so that id is never set, and `print()` just
  writes to the server process's own stdout (confirmed directly: the printed text shows up verbatim in the server
  log, never in the browser). `out.append_stdout(...)` / `out.append_display_data(...)` write directly to the
  `outputs` trait instead, which is the normal state-sync path shinywidgets already handles -- confirmed these
  render correctly in the same session. Worked around in `examples/02_plain_composition.py` by using a plain
  `ipywidgets.Label` updated via `.value = ...` instead (also correct, simpler for a one-off message, but the
  guide now also recommends `append_stdout()` as the direct substitute when `Output`'s own API is wanted).

## Judgment calls

- **Verified only one of the three old reports' widgets end-to-end in the browser (mapwidget), plus a second,
  shorter one (ipydeck)**, and left carbonplan-maps to the existing old report rather than re-running it. Reason:
  time budget, and carbonplan-maps needs a live S3 + esm.sh round trip for its core "cloud-native Zarr pyramid"
  story, which is a much bigger rebuild than reusing mapwidget's already-clean API for this guide's narrower
  purpose (illustrating the "no dedicated renderer" recipe, not re-auditing three widgets). The old
  `docs/widget-reports/carbonplan-maps/report.md` and this guide's own citations of it are not independently
  re-verified in this pass; say so explicitly in the guide text rather than implying it was re-checked.
- **ipydeck's pick gesture was verified via `window.widgetManager` model-set, not a real mouse click**, after
  several real-click attempts landed between deck.gl's picking buffer and the visually rendered marker radius
  under headless Chromium + swiftshader (every attempt that DID land registered a pick with `object: None`,
  proving the click plumbing works end-to-end -- `reactive_read()` genuinely updates -- just not that a specific
  real click can reliably hit a specific circle in this harness). This matches the brief's documented fallback
  for "canvas picking that Playwright can't hit reliably," and mirrors the method the old ipydeck report itself
  used for some of its evidence.
- **Built one shared `sparkline_widget.py` module instead of a fresh widget per example.** This keeps every
  individual code snippet in the guide short (one widget definition shown once, in full, in "What you can
  build," per the lifetimes-article precedent of a shared `globals.py`) while still demonstrating trait sync,
  custom messages, a brush gesture, and cross-widget coordination with one realistic, moderately complex widget
  rather than four trivial, disconnected ones.
- **Rate limiting (`rate_policy`/`rate_delay`) can only be demonstrated via `reactive_read()` for this
  guide**, since `render_widget` has no accessors. Added a `mousemove`-while-dragging handler to the shared
  Sparkline widget specifically so there would be a genuine multi-tick stream to debounce (a single `click` only
  fires once per gesture, which can't show a rate-limiting contrast). This is slightly more JS than the brief's
  "short" guidance might suggest for a single example, but it is shared, single-sourced code, not duplicated
  in the guide body.
- **Discovered and fixed a canvas-blur bug in my own widget during verification**, not a pre-existing
  shinywidgets issue: shinywidgets' generic fill CSS (`.lm-Widget > *:not(.deckgl...) { flex: 1 1 auto;
  min-height: 0; min-width: 0; }`) stretches a `<canvas>` to its container's size because a canvas's
  `width`/`height` HTML *attributes* (its drawing-buffer resolution) aren't a CSS size for flexbox purposes --
  only an explicit `style.width`/`style.height` is. Fixed by pinning the canvas's CSS size to its buffer size in
  `sparkline_widget.py`; documented as a verified Gotcha in the guide (with the ResizeObserver alternative named
  but not built, for apps that want a canvas to genuinely scale with its container).
- **Didn't build a dedicated carbonplan-maps CSS-fix example** (the old report's F1 finding, a one-line
  `z-index` override) since it would require re-verifying a live Zarr-over-HTTP + esm.sh round trip for a
  narrow, already-documented upstream quirk; summarized in prose instead, attributed to the old report.

## Editor's notes for the website

- **Strongest assets**: the `04_anywidget_messages.py` flash screenshot (visibly brighter line, mid-flash) and
  the `11_coordinate_brush_to_table.py` before/after (orange brush highlight + table filtering to exactly that
  day range) are the clearest "this is the payoff" images. The mapwidget showcase's 4-shot sequence (plain ->
  clicked-nearest-city -> dark style -> flew to Tokyo -> leaflet swap) reads well as a single strip.
- **Candidates to cut for a shorter page**: the ESM-sources section (`06_esm_sources.py`) is the most skippable
  if space is tight -- it's useful but the least "wow," and the CDN-import variant depends on a live esm.sh
  fetch at every render (a caveat worth keeping in prose even if the example itself is cut). The binary-trait
  section's payload numbers (384,625 vs 106,668 bytes) are more useful as a stated fact than as a screenshot.
- **[2026-11-11 update: fixed by #415, see "Bugs found" above]** ~~The engine-swap timing finding (Bugs found,
  mapwidget) is the most surprising thing found in this pass and generalizes a pattern (k3d's investigation)
  that's so far only been confirmed for an initial render -- worth flagging to the maintainer as evidence that
  `when_comm_open()` (or an equivalent public API) would help more than just the widgets that already use it
  internally.~~ This whole class of timing trap (the motivation for this note) is now gone: #415 queues and
  reliably delivers both custom messages and trait writes made before a widget's comm opens, on first render and
  on any re-render. No `when_comm_open()`-style public API is needed anymore for this guide's examples.
- **What I did NOT carry over from the old reports, and why**: the ipydeck report's full scorecard/PR-review
  framing (not applicable here -- this guide isn't reviewing ipydeck for adoption, just using it as a "no
  dedicated renderer" example); the carbonplan-maps report's full debugging narrative (kept only the one-line
  actionable fact: it needs the F1 CSS override, cited rather than re-demonstrated); the mapwidget report's
  PR-review sections (not relevant -- there is no PR in scope here, mapwidget still has no renderer on `main`).

## Pairs with

- **plotly**: `11_coordinate_brush_to_table.py`'s pattern (custom widget -> filtered table) generalizes directly
  to "custom widget -> filtered plotly figure" (swap the `render.data_frame` for a `render_plotly` reading the
  same brushed range).
- **itables / reactable**: `12_coordinate_table_to_widget.py` uses Shiny's own `render.data_frame` for the "table
  row -> custom widget" direction; the itables/reactable guides' own `selected_rows()` accessors are drop-in
  replacements for `table.cell_selection()["rows"]` if the table itself is one of those widgets instead.
- **ipyleaflet / leafmap / lonboard / maplibre**: all have dedicated renderers and accessors; this guide's
  `08_third_party_mapwidget.py` and the showcase exist specifically because mapwidget does NOT (yet) have one --
  see those guides first if the roster's own map widgets fit the use case.
- **k3d**: `04_anywidget_messages.py`'s "custom messages during render are dropped" gotcha, and the showcase's
  engine-swap variant of the same bug, both cite and extend `../k3d/INVESTIGATION.md`.
