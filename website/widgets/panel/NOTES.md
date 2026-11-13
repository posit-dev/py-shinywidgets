# NOTES: panel guide

## Versions

- panel 1.10.0, bokeh 3.10.1, jupyter_bokeh 4.1.0, param 2.4.2, shiny 1.9.0, ipywidgets (via shinywidgets' own
  deps), plotly 6.9.0, Python 3.12.
- shinywidgets commit: `main` as of 2026-10-30 (worktree `main-wt`, detached at `origin/main`).
- Date: 2026-10-30.

## Verification log

Every file below ran in headless Chromium (`--use-angle=swiftshader --enable-unsafe-swiftshader
--ignore-gpu-blocklist`, 1280x800 or 1280x900, `device_scale_factor=2`) via `shiny.run.run_shiny_app` + Playwright,
screenshotted, and every screenshot was read with the Read tool before being referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Confirmed |
|---|---|---|---|---|
| examples/01_quickstart.py | yes | yes | n/a | renders, fills card |
| examples/02_tabulator_formatters.py | yes | yes | n/a | progress-bar + money formatters render |
| examples/03_indicators.py | yes | yes | n/a | Dial/Number/Progress all fill their cards |
| examples/04_chat.py | yes | yes (before/after) | type + click Send | canned reply appears, Python callback ran |
| examples/05_jscomponent.py | yes | yes (before/after) | 3 real clicks | `model.count` went 0 -> 3 in the browser |
| examples/06_viewer.py | yes | yes (before/after) | drag slider to max | Fahrenheit readout updated via internal `pn.bind` |
| examples/07_param_watch_bridge.py | yes | yes (before/after) | click row 2 | `reactive.value` became `[2]` |
| examples/08_param_read_helper.py | yes | yes (before/after) | drag slider 10->58 | `param_read()` readout updated to 58 |
| examples/09_update_in_place.py | yes | yes (before/after) | sort + 2-row select, then move year slider | sort and selection (by country) survived the in-place update |
| examples/10_selection_to_chart.py | yes | yes (before/after) | Cmd-click 3 rows | plotly chart showed exactly those 3 countries |
| examples/11_click_to_detail.py | yes | yes (before/after) | click 1 row | Number indicator updated in place, no re-render |
| examples/12_chat_to_indicator.py | yes | yes (before/after) | 2 chat round trips | counter went 0 -> 4 |
| gallery/template_tabulator_filter.py | yes | yes (before/after) | uncheck 2 continents, Cmd-click 2 rows | table re-filtered in place; chart updated from selection |
| gallery/showcase_fleet_dashboard.py | yes | yes (before/after) | click a row, send a chat message | Dial/Number updated in place; chat answered from live data |

Accessor coverage: **n/a -- `render_panel` declares zero accessors** (confirmed by reading
`shinywidgets/_render_widget.py`: the `render_panel` class, unlike every renderer with accessors, has no
`_accessor_specs` class attribute). The bridge pattern (`.param.watch()` -> `reactive.value`, and the
`param_read()` helper) was verified with real gestures instead, across three different Panel component families
(Tabulator selection, a plain `IntSlider`, and `ChatInterface`'s message list) to demonstrate it's genuinely
generic, not table-specific.

## Bugs found

**shinywidgets (main), one confirmed regression-relevant bug:**

1. **`pn.pane.ECharts` and the ECharts-backed `pn.indicators.Gauge` fail to render.** Repro:
   `/private/tmp/claude-502/.../scratchpad/agents/panel/apps/echarts_plain.py` (a bare 2D ECharts bar chart) and
   `indicators_probe.py`/`03_indicators_echarts.py` (Gauge). Both show "Could not load the resources this
   component requires: Failed to load .../static/extensions/panel/bundled/echarts/echarts-gl@2.0.9/dist/echarts-gl.min.js".
   Calling `pn.extension("echarts")` up front does **not** fix it (ruled out explicitly). The browser requests the
   GL sub-bundle via a raw `static/extensions/<pkg>/...` URL -- the bokeh-server convention -- which
   `shinywidgets`' extension-asset pipeline (`shinywidgets/_bokeh.py`: `bokeh_extension_urls()` ->
   `extension_assets()` -> `local_extension_url()`, which mounts `bokeh-ext-<pkg>` dependencies) does route
   correctly for every *other* asset I checked (Tabulator's JS/CSS, Vega, chat's dependencies) but apparently
   misses this one, since nothing in `_bokeh.py` ever registers a mount at the bare `/static/extensions/...`
   prefix the browser actually requests (only `/lib/bokeh-ext-<pkg>-<version>/...` and `/lib/panel-assets-<version>/...`
   are served). I did not trace the exact client-side code path that issues the raw request (time-boxed); it's
   specific to ECharts' GL sub-bundle, since every other pane/indicator this guide uses (Tabulator, Vega, chat,
   Dial, Number, Progress, JSComponent, Viewer) rendered correctly, including through the same extension-asset
   mechanism. Dropped `pn.pane.ECharts`/`Gauge` from the "what you can build" feature tour in favor of `Dial`
   (unaffected) and noted the bug in Gotchas, pointing users at `render_plotly`/`render_bokeh`/`render_altair`
   instead for charting.

**shinywidgets (main), confirmed fixed since the old report (`docs/widget-reports/panel/report.md`, 2026-10-22):**

2. **Cross-session leak of module-level Panel objects (old report's #3.1, "high").** Repro'd the exact scenario
   with two live Playwright browser contexts against a module-level `pn.widgets.IntSlider`
   (`scratchpad/.../apps/cross_session.py` + `cross_session_driver.py`/`cross_session_driver4.py`): dragging the
   slider in session A's browser to 100 left session B's browser showing 10, unaffected. No warning or error in
   either session's console or server stderr. **Could not reproduce the leak.** I did not trace the exact
   mechanism that now prevents it (my best guess, not verified: `ShinyComm.send()` in `shinywidgets/_comm.py`
   binds to `self.session`, the session captured at the comm's construction, rather than the ambient "current
   session" -- which would route Panel's own `_update_model()` push-to-every-root loop through the *correct*
   session for each root even when the ambient context during the callback is a different session -- but I did
   not confirm this is actually what changed, or whether it was ever the mechanism at all). Worth a second,
   deeper look if the maintainer wants a definitive fix confirmation; documented as "did not reproduce" rather
   than "fixed", per the brief's "verify every claim" rule, since I can't point to the specific commit/line that
   fixed it.
3. **`render_panel` didn't route non-Panel values through `pn.panel()` (old report's #3.4, "medium").** Fixed:
   `render_panel._as_widget()` (`shinywidgets/_render_widget.py`) now calls `as_widget_panel()` ->
   `panel_to_widget()`, which calls `pn.panel(x)`, for any non-`Widget` value. Verified directly via
   `tests/unit/test_render_panel.py::test_render_panel_routes_values_through_pn_panel` (parametrized over `str`,
   `DataFrame`, a `matplotlib.figure.Figure`, a plotly `go.Figure`, and a `pn.viewable.Viewer`, all asserting the
   result `isinstance(..., BokehModel)`) and by building `examples/01_quickstart.py` and
   `examples/02_tabulator_formatters.py` myself.
4. **User-defined `Viewer`/`JSComponent`/widget subclasses failed to coerce (old report's #3.3, "medium-high").**
   Fixed via an MRO-based fallback in `shinywidgets/_as_widget.py`'s `as_widget()` (checks `type(x).__mro__` for
   a known package when the object's own `__module__` isn't one of the ones in `AS_WIDGET_MAP`). Verified: my own
   `examples/05_jscomponent.py` returns a `JSComponent` subclass *directly* (no `pn.Column(...)` wrapper, which
   the old report said was required) and renders and syncs correctly; `examples/06_viewer.py` returns a `Viewer`
   subclass directly. Both match `tests/unit/test_render_panel.py::test_as_widget_coerces_user_defined_panel_subclasses`.
5. **Offline/CDN-blocked deployments failed entirely (old report's #3.2, "high", shared with bokeh).** Fixed:
   `panel_to_widget()` (`shinywidgets/_as_widget.py`) now registers an `HTMLDependency` for `panel`'s own `dist`
   directory and sets `document.template_variables["dist_url"]` to the locally-served path, rather than relying
   on jupyter_bokeh's jsdelivr fallback. Verified indirectly: every example's network log (captured via
   `page.on("requestfailed"/"response")` in my Playwright driver) shows Tabulator's JS/CSS, chat's dependencies,
   and Panel's own theme CSS loading from `/lib/panel-assets-<version>/...` and `/lib/bokeh-ext-panel-<version>/...`,
   never from `cdn.jsdelivr.net`. I did not additionally verify with all-`https://` blocked (the old report's
   exact test), since the never-hits-a-CDN evidence from every other example already answers the same question.
6. **Panel templates still fail, but with the same error as before (old report's #3.9, "low", not newly broken).**
   `pn.template.FastListTemplate(...)` still raises `AttributeError: 'FastListTemplate' object has no attribute
   'get_root'` (`scratchpad/.../apps/template_probe.py`). This is a long-standing limitation the current
   `render_panel` docstring already documents correctly in prose ("Panel templates are full pages... use Shiny's
   page layouts"); the implementation just doesn't turn it into a friendly `TypeError` yet. Kept as a gotcha, not
   elevated to a "bug" since nothing regressed and the docs already set the right expectation.

**Not independently verified this pass (noted, not re-chased):**
- The old report's #3.7 (ipywidget/traitlets callback exceptions logging to a `NullHandler` by default) and #3.8
  (no default `sizing_mode` for Panel objects) weren't re-tested in a dedicated repro; #3.8 is effectively
  superseded by the `bokeh_layout_defaults()` fill-detection logic now in `_render_widget_base.py` (confirmed
  working via `examples/01-03`, and the explicit no-`sizing_mode` check in the Layout and sizing section), and
  #3.7 is an ipywidgets-wide concern (not panel-specific) already out of scope for a single-widget guide.

## Judgment calls

- **Dropped `pn.pane.ECharts`/`pn.indicators.Gauge` from the feature tour** in favor of `pn.indicators.Dial` once
  the ECharts bug was confirmed (see Bugs Found #1). Keeping a broken component in "what you can build" would
  contradict the brief's "teach what's possible" framing; the bug is still fully documented in Gotchas with a
  verified repro.
- **`LinearGauge`/`Trend`/`BooleanStatus` indicators were probed but not included in the guide body.** They
  render blank with `sizing_mode="stretch_both"` in a plain card but work fine with explicit pixel `width=`/
  `height=` (verified in `scratchpad/.../apps/indicators_probe2.py` and `indicators_probe3.py`). This is a minor,
  narrow Panel sizing quirk (three specific SVG-based indicators); documented as one bullet in Gotchas rather
  than given a full example, to avoid padding the "what you can build" section with low-value API surface.
- **Used `Meta` (Cmd) as the multi-select modifier in every Playwright multi-row-selection gesture**, not `Control`.
  Ctrl-click silently selected only the first row in this headless-Chromium-on-macOS environment; Tabulator reads
  the modifier based on the browser's reported platform. Documented as a Gotcha since a reader scripting their own
  tests (or simply using a Mac) needs to know this; it's standard Tabulator behavior, not a shinywidgets quirk.
- **The cross-session leak repro is reported as "did not reproduce" rather than "fixed"**, since I didn't trace
  the exact code path responsible (see Bugs Found #2). This is a case where I'd rather underclaim a fix than
  overclaim one I can't point to in the source.
- **Chose a synthetic "server fleet" dataset for the showcase gallery app** rather than real data, since the
  showcase's point is demonstrating three different Panel component families working together (table, indicators,
  chat) under one Shiny reactive graph, not a specific real-world dataset; no small, locally-available real
  "server fleet" dataset exists. Made the values plausible (no hard cutoffs, `np.clip` to sane ranges) per the
  brief's synthetic-data guidance. The template gallery app and every other example use real data
  (`plotly.express.data`).
- **`param_read()` and the inline `.param.watch(lambda e: rv.set(e.new), ...)` form are both shown**, with the
  first introduced via the Tabulator-selection bridge (concrete, matches the brief's req() teaching pattern) and
  the second as the reusable, `reactive_read()`-shaped helper. Showing both costs one extra short example
  (`08_param_read_helper.py`) but makes the "copyable recipe" the brief asks for genuinely drop-in.
- **`selectable=1` (an int) for single-row selection** in `examples/11_click_to_detail.py` and the fleet
  dashboard, rather than `selectable=True` plus manually taking `selection[0]`. Verified this caps Tabulator at
  one selected row; simpler than filtering a multi-select list down to one entry.

## Dropped from the old report, and why

- **The full scorecard/star-rating system and "UX verdict" framing** -- this guide is teaching material aimed at
  "what's possible", not an evaluation report; dropped per the brief.
- **The `pn.state.{location,onload,notifications,add_periodic_callback}` and `.servable()` behavior-without-a-server
  survey (old report's #3.10)** -- interesting for an exhaustive API audit, but low value for a reader building an
  app: `pn.state.notifications` is explicitly unsupported (use `ui.notification_show`), and the rest
  (`pn.state.cache`, `.servable()` as a no-op) are edge cases a reader is unlikely to reach for. One line in
  Gotchas would have been the ceiling; decided it wasn't worth even that, since nothing here is specific advice
  a Shiny user needs that isn't implied by "build Panel objects per session."
- **The `traitlets`/ipywidgets silent-exception-logging finding (old report's #3.7)** -- real, but it's an
  ipywidgets-wide concern (every `on_msg` callback under shinywidgets, not Panel-specific), so it belongs in a
  cross-cutting article or the generic `render_widget` guide, not repeated here.
- **The exhaustive page-weight/global-JS-namespace/Tabulator-editable-by-default "non-issues ruled out" list
  (old report's #3.11)** -- most of these were either already folded into actionable advice above (e.g.,
  `disabled=True` for Tabulator's edit-by-default cells is now just part of every Tabulator snippet's code, not
  a separate callout) or are console noise not worth a reader's attention (jQuery version, polyfill-mode
  warnings). Kept only what changes what a reader should write.
- **The `CHANGELOG.md:17` overclaim about "All required JS/CSS assets are served automatically"** -- this is now
  true for Panel specifically (verified: Bugs Found #5), so the old report's complaint about it no longer applies
  and isn't worth relitigating. The one remaining real exception (ECharts' GL sub-bundle) is documented fresh in
  Gotchas, not inherited from the old finding.

## Update 2026-11-11 (main @ 32ca7035)

- shinywidgets commit: `main` @ `32ca7035` (worktree `main-wt`, detached at `origin/main`). Same library versions
  as the original pass (panel 1.10.0, bokeh 3.10.1, jupyter_bokeh 4.1.0, param 2.4.2, shiny 1.9.0, plotly 6.9.0,
  Python 3.13).
- **Headline change: `param(name)` accessor (#438).** `render_panel` now has one accessor, `param(name)`, which
  reads any parameter of the rendered object reactively -- seeded at render, re-seeded on re-render (follows the
  new `.value` object), fires on both browser and Python changes, no rate limiting by default. Rewrote the intro
  paragraph, the whole "Reacting to user interaction" section (accessor reference table, a new headline example,
  a dedicated "can't reach it" nested-widget case, and the `reactive_read()`/`.read()` note), and converted every
  example and gallery app that used the old `.param.watch()` → `reactive.value` bridge to call `.param(name)`
  directly instead, dropping the bridge code entirely where the watched state lived on the top-level rendered
  object. Updated front-matter `accessors:` from `[]` to `[param]`.
- Kept the manual `.param.watch()` recipe for exactly one case, confirmed by reading `shinywidgets/_panel.py`
  and a live probe (`layout.param("value")` on a `pn.Column`/`pn.Row` wrapping an `IntSlider` raises `ValueError:
  Row has no parameter 'value'`, since the dynamic accessor only reads parameters on `renderer._value` itself,
  never a nested child): a widget nested inside a layout you return. New example
  `examples/08_param_watch_nested.py` demonstrates and explains why.
- **#406 (panel serves `/static/extensions`): `pn.indicators.Gauge` and `pn.pane.ECharts` now render.** This was
  the guide's one shinywidgets bug (`pn.indicators.Gauge` dropped from the feature tour, documented in Gotchas).
  Re-verified live: the ECharts-GL sub-bundle request now 200s from `/static/extensions/panel/...` (confirmed in
  the server log), and `Gauge` draws a correct circular gauge next to `Dial` with no console errors. Added `Gauge`
  back into `examples/03_indicators.py` (now a 2x2 grid) and updated Installation/Gotchas prose; removed the old
  "shinywidgets bug" Gotchas entry entirely (fixed, not a residual caveat).
- Converted `table.value.iloc[...]`-shaped manual bridges to `table.param("selection")` reads in
  `examples/10_selection_to_chart.py`, `examples/11_click_to_detail.py`,
  `gallery/template_tabulator_filter.py`, and `gallery/showcase_fleet_dashboard.py`. **Caught my own bug while
  verifying 10_selection_to_chart.py in the browser**: `table.value` is the renderer's `.value` (the Tabulator
  object itself), not its data -- the data is `table.value.value` (the Tabulator's own `.value` parameter). My
  first draft wrote `table.value.iloc[idx]` and got `AttributeError: 'Tabulator' object has no attribute 'iloc'`
  live in the browser; fixed to `table.value.value.iloc[idx]` across all four files and re-verified each one.
- Fixed a second self-made layout bug caught in the browser: a first attempt at a 2x2 indicators grid
  (`col_widths=[6, 6, 6, 6]`, no explicit height) squished `Dial` into a clipped oval, because wrapping into two
  rows inside one fillable `layout_columns()` halves the vertical space each row gets. Fixed by keeping the
  indicators in a single row (`col_widths=[3, 3, 3, 3]`, matching the original layout) and shortening the
  `Number` indicator's value so it no longer wraps at that width.
- Deleted `examples/07_param_watch_bridge.py` and `examples/08_param_read_helper.py` (the hand-rolled bridge and
  its `param_read()` generalization) -- both fully superseded by `param(name)`. Replaced with
  `examples/07_param_accessor.py` (the headline browser+Python example, reusing the exact gesture from
  `tests/playwright/panel_param/test_panel_param.py`) and `examples/08_param_watch_nested.py` (the one remaining
  case for manual `.param.watch()`).
- Updated the "Learn more" cross-reference to holoviews/bokeh, since panel is no longer in the "no accessors"
  bucket alongside holoviews.

### Verification table (this update)

| File | Ran | Screenshot | Gesture | Confirmed |
|---|---|---|---|---|
| examples/03_indicators.py (edited: added Gauge) | yes | yes (replaces old) | n/a | Dial + Gauge both full circles, Number no longer wraps; `/static/extensions/panel/...echarts-gl...` 200s in server log |
| examples/07_param_accessor.py (new) | yes | yes, before/after | 2x ArrowRight on slider handle, then Python button click | `quantity` 5 -> 7 -> 9, both paths confirmed server-side |
| examples/08_param_watch_nested.py (new) | yes | yes, before/after | 32x ArrowRight on nested slider, then Reset button click | `quantity` 10 -> 42 -> 10 (reset), confirming the manual-watch recipe still works for a nested widget |
| examples/10_selection_to_chart.py (edited) | yes | yes, before/after | Cmd-click 3 rows (China, US, Brazil) | plotly chart shows exactly those 3 countries; caught and fixed the `.value.value` bug live |
| examples/11_click_to_detail.py (edited) | yes | yes, before/after | click 1 row | Number indicator updates in place (United States, 78.2 yrs) |
| examples/12_chat_to_indicator.py (edited) | yes | yes, before/after | 2 chat round trips | counter 0 -> 4 |
| gallery/template_tabulator_filter.py (edited) | yes | yes, before/after | uncheck 2 continents, Cmd-click 2 rows | table re-filters in place; chart updates from `.param("selection")` (needed an extra ~1.5s wait for Plotly's own resize before the chart became visible -- not a regression, just Plotly's normal reveal animation) |
| gallery/showcase_fleet_dashboard.py (edited) | yes | yes, before/after | click a row, send a chat message | Dial/Number update in place from `.param("selection")`; chat answers from live data |
| examples/01-02, 04-06, 09 (unchanged) | not re-run | n/a | n/a | no code or behavior-claim changes; text-only guide edits don't reference new behavior for these |

Accessor coverage: `param(name)` verified with a real gesture in `07_param_accessor.py` (browser slider + Python
button, both paths) and exercised further in 10/11/12 and both gallery apps (click/multi-select gestures). The
one case `param(name)` can't reach (a nested widget) is verified separately in `08_param_watch_nested.py`.

### Bugs found (2026-11-11)

None on current shinywidgets main. The one bug from the previous pass (#1, ECharts/Gauge) is now fixed (#406);
verified above, not re-filed.

### Judgment calls

- Kept `examples/09_update_in_place.py`'s direct (non-accessor) read of `tab.selection` as-is: it's a synchronous
  snapshot taken inside a `@reactive.effect` that's already triggered by `input.year()`, not a reactive dependency
  on the selection itself, so routing it through `table.param("selection")` would change the effect's dependency
  set (it would also re-run on every selection change, not just year changes) for no benefit.
- Chose `table.value.value.iloc[idx]` (go through the live Tabulator's own `.value`) over indexing the
  module-level `latest`/`fleet` DataFrame directly in `10_selection_to_chart.py` and the gallery apps, even where
  the data is static and either would work, so the pattern generalizes to the one gallery app
  (`template_tabulator_filter.py`) where the table's data *does* change (continent filter) and indexing the
  stale module-level frame would be wrong.

## Pairs with

- `plotly` -- `examples/10_selection_to_chart.py` and the `template_tabulator_filter.py` gallery app both drive a
  `render_plotly` chart from a Tabulator selection bridged through `.param.watch()`. Good cross-cutting-article
  material: "linking a non-accessor widget's state into an accessor-based one."
- `bokeh`, `holoviews` -- all three render through the same `jupyter_bokeh.BokehModel` mechanism (bokeh gets real
  accessors; holoviews and panel don't, for the documented reason that their state isn't shaped like a curated
  browser event). Cross-linked in "Learn more" and the intro's "choose this vs. siblings" paragraph.
- `itables`, `reactable` -- named in the "What you can build" Tabulator section and "Learn more" as the
  Shiny-native alternative when you want an accessor-backed table instead of Tabulator's richer formatting/theming.

## Editor's notes for the website

- **Strongest material:** the "bring your own JavaScript component" (JSComponent) and "compose your own reusable
  component" (Viewer) sections are the most distinctive -- they're capabilities genuinely unique to Panel among
  this roster, verified with real two-way-sync gestures. The fleet-dashboard showcase is the best single argument
  for "why Panel in Shiny" (three component families, one reactive graph, zero Panel server).
- **Cuttable for a shorter page:** the "Rate limiting" subsection is one paragraph of "this doesn't apply here" --
  easy to compress into a single sentence inside the accessor-reference paragraph if the page runs long. The
  `param_read()` helper example could be merged into the inline-bridge example's prose (show the helper as a
  code comment/variant) rather than as a fully separate numbered example, if trimming is needed.
- **The ECharts/Gauge bug callout in Gotchas is important to keep** even in a trimmed page -- it's the one place
  in this guide where a reader's natural first instinct (reach for `pn.indicators.Gauge`, the most commonly
  recommended Panel gauge) will fail, and the fix (`Dial`) isn't obvious without this note.
- Screenshots captured but not referenced from `guide.md` (kept in `img/` as verification evidence):
  `03_indicators_echarts.webp`-equivalent bug screenshots were kept in scratch, not copied into `img/`, since they
  show a broken state rather than a guide-worthy capture -- the Gotchas bullet describes the error message
  verbatim instead.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example. Panel has no large-data story of its own (it's a thin wrapper); pointed to itables/reactable for tables and bokeh/holoviews for charts, since Panel's panes render through `jupyter_bokeh` either way.
