# NOTES: Altair guide

Agent: altair guide writer. Date: 2026-10-30.

## Versions

- altair 6.3.0, pandas 3.1.0, polars 2.0.0, narwhals 2.27.1, shiny 1.9.0 (installed in the shared repo venv).
- `reactable` is not in the shared venv; `13_brush_to_reactable_table.py` runs used
  `uv run --no-sync --with reactable shiny run ...` (ephemeral overlay, per the operating
  rules). [Updated 2026-11-02, maintainer Decision 8: examples switched from `vega_datasets`
  to `altair.datasets` (bundled with altair 6.3.0), so `--with vega_datasets` is no longer
  needed for any example; the verification below was originally done with `vega_datasets`,
  which serves the same `cars`/`seattle_weather` files from the same upstream vega-datasets
  package.]
- shinywidgets: current `main` at the time of writing, which moved under me mid-session (other agents/the
  coordinator were merging branches into `main` concurrently -- see "Operating notes" below). Final verification
  pass was against `main` after that settled; `_render_widget.py`/`_altair.py`/`_accessors.py` contents quoted in
  the guide match what's on disk as of this note.
- Browser: headless Chromium via Playwright, viewport 1280x800, `device_scale_factor=2`. No special launch flags
  needed (Altair's SVG renderer doesn't need the WebGL/swiftshader flags other guides mention).

## Verification table

All driven with a Playwright script in scratch (`drive.py`), one shiny app per file, real mouse/keyboard gestures,
screenshots read back with the Read tool before referencing them in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | n/a |
| `examples/02_layers_and_facets.py` | yes | yes | n/a (static) | n/a |
| `examples/03_bound_widget.py` | yes | before/after | range-slider keyboard (`End`) | n/a (pure Vega-Lite param, no accessor) |
| `examples/04_interval_selection.py` | yes | before/after | mouse drag (brush) | `selected_rows()` -- table empty, then 13 rows |
| `examples/05_point_and_index_selection.py` | yes | before/after | legend click; click + shift-click on marks | `selected()` (legend: `[{'Origin': 'Europe'}]`), `selected_rows()` (2 rows, row positions `[0, 237]`) |
| `examples/06_binned_temporal.py` | yes | before/after | click a bar; mouse drag (temporal brush) | `selected_rows()` on both (18 cars in a bin; 131 cars in a year range) |
| `examples/07_multiple_selections.py` | yes | before/legend/brush | legend click, then brush drag (separately) | `selected()` on two named selections; also used to find the mutual-clear gotcha |
| `examples/08_polars_frame.py` | yes | before/after | mouse drag (brush) | `selected_rows()` returns `polars.DataFrame` (checked via `type(...).__name__`) |
| `examples/09_params_reactive_read.py` | yes | before/after | range-slider keyboard (`End`) | `reactive_read(chart.widget.params, "year")` |
| `examples/10_params_inplace_update.py` | yes | before/after | Shiny `ion.rangeSlider` keyboard (`ArrowRight` x15) | n/a (param set from Python; checked the dot recolors) |
| `examples/11_vegalite_vs_shiny_linking.py` | yes | before/after | mouse drag (brush) | `selected_rows()` feeding a text summary; bar chart verified driven by `transform_filter` alone (no accessor) |
| `examples/12_click_to_detail_card.py` | yes | before/after | click one mark | `selected_rows()` (detail card renders the clicked row) |
| `examples/13_brush_to_reactable_table.py` | yes | before/after | mouse drag (brush) | `selected_rows()` feeding `render_reactable` (cross-widget pairing) |
| `gallery/template_weather_brush.py` | yes | before/after | mouse drag (brush) | `selected_rows()` |
| `gallery/showcase_weather_dashboard.py` | yes | before/after-brush/after-slider | mouse drag (brush); Shiny slider keyboard | `selected_rows()` driving 3 value boxes, a derived chart, and a table; param in-place update verified to preserve the brush |

Every accessor on the renderer (`selected`, `selected_rows`) was exercised with a real browser gesture and
confirmed by reading the rendered Python-side output back, not just by inspecting source. No gesture was
impossible to automate for this widget (SVG rendering, ordinary mouse events).

## Bugs found

**shinywidgets: none found.** Both historical shinywidgets bugs in `docs/widget-reports/altair/report.md`
(explicit output height collapsing the chart; `set_layout_defaults` orphaning `jchart.selections.observe()`) are
fixed on current `main` -- confirmed both by reading `_render_widget_base.py`'s `_altair_layout_defaults` (which
now patches `.spec` in place rather than reassigning `.chart` when only width/height are unset) and by the
existing passing Playwright tests `tests/playwright/altair_sizing_and_observers/`.

**Upstream Vega-Lite (regression status: not applicable, longstanding upstream behavior):**
1. A point selection's `alt.condition(...)` highlight doesn't visually apply to the clicked mark when the chart
   is an aggregated, binned bar chart (`06_binned_temporal.py`'s histogram). Reproduced in plain `vega-embed`
   (saved via `chart.save()`, loaded with no shinywidgets/anywidget involved at all), so this is Vega-Lite itself,
   not shinywidgets or Altair's Python layer. The selection is reported correctly to Python throughout; only the
   in-chart color feedback is missing. Documented in the guide's Gotchas.
2. Two selections sharing one view clear each other: clicking a legend-bound point selection clears a co-located
   interval brush, and dragging the brush clears the legend pick. Verified in both directions. This is consistent
   with Vega-Lite's single-view interaction model, not a bug exactly, but surprising enough to call out loudly --
   it's the kind of thing that looks like a shinywidgets accessor bug when it's actually upstream chart behavior.

**Docs gap (not exactly a "bug," but undocumented anywhere I could find, upstream or in shinywidgets):**
3. `selected_rows()`'s default `df` resolution (`chart_frame()` in `_altair.py`) only finds a frame on a
   layered/concatenated chart when every layer was built from the *same* data frame object -- Altair's own
   internal data-hoisting checks object identity, not equality. Calling a filter function twice for two layers
   (`alt.Chart(f()) + alt.Chart(f())`) silently produces an un-hoisted spec and `selected_rows()` then raises
   `TypeError` pointing at `df=`. I hit this myself writing `gallery/showcase_weather_dashboard.py` and fixed it
   by computing the frame once and reusing the object. Verified the identity-vs-equality mechanism directly with
   a small altair-only repro (no shinywidgets). Flagged in Gotchas; the `selected_rows()`/`chart_frame()`
   docstrings could mention this.

**Shiny Express (pre-existing, documented in the old report's "harness mistakes" section, still true today):**
4. A bare top-level triple-quoted string at the top of an Express file renders as literal page text, not just
   `__doc__`. This broke my first draft of both gallery files (which used a docstring header per an earlier
   reading of the brief); switched to a `#`-comment header instead. Noted in the guide's Gotchas and in
   `BRIEF.md`'s coordinator update.

## Judgment calls

- **Accessor scope**: took `selected`/`selected_rows` directly from `ALTAIR_ACCESSORS` / the methods on
  `render_altair` in `_render_widget.py`, not from the design doc's (stale, per the coordinator's update) listing
  -- they matched in this case, but I verified independently rather than trusting the doc.
- **`fields=` vs `encodings=`**: the brief asked me to cover this distinction. Rather than adding a 14th example
  file just for `fields=`, I verified it with a throwaway probe (`fields=["Origin"]` vs `encodings=["color"]` on
  the same legend-bound chart, identical `[{'Origin': 'Europe'}]` result) and explained the difference in prose in
  "Point and index selections," pointing at the existing `05_point_and_index_selection.py` example. No code block
  claims to be backed by a file it isn't; the maintainer may want an explicit `fields=` example instead if the
  website format expects every claim to have a runnable snippet.
- **Multiple-selections example became two screenshots, not one.** I originally planned one "after" screenshot
  showing both a brush and a legend pick active simultaneously; the mutual-clearing behavior (see Bugs found #2)
  made that impossible to produce honestly, so the example instead demonstrates each selection in isolation, which
  I think is the more honest and more useful lesson anyway.
- **Real vs. synthetic data**: per the coordinator's update preferring real/recognizable datasets, I used
  `vega_datasets`' `cars` (quickstart, hero, and all of the "Reacting to user interaction" examples) and
  `seattle_weather` (layers/facets example and both gallery apps) instead of synthesizing data. [Resolved
  2026-11-02, maintainer Decision 8: both datasets are also bundled in altair 6.3.0 as `altair.datasets`
  (same upstream vega-datasets files), so every example now imports `from altair.datasets import data` and
  needs no extra package at all.]
- **Gallery showcase scope**: `showcase_weather_dashboard.py` demonstrates five things at once (brush, in-place
  param restyle, re-render-on-filter, a derived chart, a leaderboard table) in ~135 lines. This is deliberately at
  the dense end of "showcase," to actually earn the word -- let me know if it should be split or trimmed for the
  website.
- **Hero image**: used `04_interval_selection_after.webp` (the brush-to-table example) rather than a dedicated
  hero shot, since it's the single clearest "chart as an input" image produced. Happy to generate a custom hero
  if the website wants a different crop/composition.

## Operating notes (not for the website)

- The shared checkout's `shinywidgets/_render_widget.py` and `pyproject.toml` were transiently unparseable twice
  during this session (mid-merge from another agent/the coordinator: a Python `SyntaxError` and a TOML merge-
  conflict-marker error, each resolved within ~20 seconds on retry). Not a bug in shinywidgets; just noting it in
  case other agents hit the same transient failures and need to know to retry rather than report it.
- Ports used: 9120-9125ish out of the assigned 9120-9139 range, one shiny app at a time, each started/stopped by
  PID from the driver script; nothing left running.

## What I dropped from the old report and why

- The detailed byte-size/latency comparison tables (altair vs. plotly payload sizes, debounce-timing recalc
  counts, VegaFusion/canvas-renderer timings) -- these were measured once, under variable machine load, and
  restating specific numbers without re-measuring them this round would be exactly the "regurgitate stale content"
  the brief warns against. The qualitative comparison (altair's payload is smaller because it doesn't ship a JS
  bundle; pick plotly for WebGL/3D/scale) survives in the guide's intro.
- The "swallowed browser-to-Python exceptions" finding and the VegaFusion/pyarrow repro -- real, but about general
  ipywidgets error handling, not Altair-specific or accessor-related; out of scope for an accessors-focused guide
  aimed at teaching, not a bug report.
- The upstream `input_dark_mode` stale-brush race and the CDN/offline investigation detail -- both still
  presumably true but not re-verified this round (would need dedicated repro time); the CDN/offline point survives
  as a one-line Gotcha since it's simple and stable (`enable_offline()` exists and is documented upstream).
- The large-data byte/timing measurements for `disable_max_rows()`/VegaFusion -- kept the qualitative advice
  (use one or the other above 5,000 rows) without restating unverified numbers.

## Update 2026-11-11 (main @ 32ca7035)

Versions: altair 6.3.0, pandas 3.1.0, shiny 1.9.0, worktree
`/private/tmp/claude-502/.../ce388f54.../scratchpad/main-wt`. Read `shinywidgets/_altair.py` and
`render_altair`'s docstring in `shinywidgets/_render_widget.py` against current `main`; read PR bodies for
#437 and #398.

What changed in the guide and why:

- **Accessor reference table reformatted** to the new columns (`before any interaction` / `across re-render`).
  Content unchanged in substance: `selected()`/`selected_rows()` were already correctly documented as seeded
  (never `None`) and re-seeding to empty on every re-render -- this guide was written with the post-#437
  semantics already in place (`_altair.py`'s `attach_selections` calls `emit()` once at attach, matching
  "seeded"). Reworded the surrounding prose ("Unlike renderers whose accessors start at `None` ... there's no
  warm-up") to use the redesign's vocabulary explicitly.
- **`selected_rows()`'s layered-chart identity caveat (#398) was already correct** in this guide's "Gotchas"
  section and the "Polars frames" prose -- no changes needed there; re-verified the identity-vs-equality
  behavior directly (`jc.params` trait check, see below) rather than assuming the existing text was right.
- **Clarified why `reactive_read(chart.widget.params, "name")` is still correct** (the "Beyond the accessors"
  section used to just say "read one with reactive_read instead" with no explanation of why `.read()` doesn't
  apply). Verified directly: `JupyterChart.has_trait("year")` is `False` even with a bound param named `year`
  added via `add_params()` -- the param becomes a trait of `chart.widget.params` (a separate `Params` object
  the widget builds), not of `chart.widget` itself, so `chart.read("year")` (which only checks
  `chart.widget.has_trait(name)`) can't reach it. This is genuinely tier-3 usage, not a missed `.read()`
  conversion.
- **Converted `chart.widget.local_tz` / `chart.widget.debounce_wait` to `chart.read("local_tz")` /
  `chart.read("debounce_wait")`.** These *are* direct traits on `chart.widget`, verified
  (`jc.has_trait("local_tz")` / `jc.has_trait("debounce_wait")` both `True`), so `.read()` reaches them
  directly -- no need for `reactive_read()`. Verified live in a browser: a tiny probe app
  (`scratchpad/agents/plot-sel/test_altair_read.py`, driven by `drive_altair_read.py`) read both through
  `.read()` inside `@render.text` outputs; `debounce_wait` showed `10.0` immediately (a Python-set default,
  no round trip needed) and `local_tz` showed `'America/Chicago'` after the browser reported it (~1-2s after
  first render, since it's a value the browser computes and sends up, unlike `debounce_wait`).
- **New example: "Reading on demand"** (`examples/14_download_selection.py`), added to "Reacting to user
  interaction" after "Rate limiting". A `@render.download_button` handler reads `scatter.selected_rows("brush")`
  fresh each time it's clicked -- demonstrates that altair's accessors (already always-seeded, never `None`)
  are safe to read from a handler that runs occasionally, with no warm-up. Verified: brushed a box over the
  dense mid-horsepower cluster, clicked download, read the CSV back in Playwright (299 of 406 rows, a
  plausible count for that region of the cars scatter -- confirmed visually against the screenshot).
  Screenshots `14_download_selection_before.webp` / `14_download_selection_after.webp`.
- **No warm-up idiom was present to delete** -- this guide's `selected()`/`selected_rows()` narrative was
  already "always safe to call, no `req()` needed" before this pass, consistent with #437's final state.

Verification status (new/changed only -- the rest of the verification table above still applies unchanged):

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/14_download_selection.py` (new) | yes | yes (before/after) | box-select, then click download | `selected_rows("brush")` read inside `@render.download_button`, content verified (299 rows, CSV header + data spot-checked) |
| `.read("local_tz")` / `.read("debounce_wait")` (prose claim, no example file -- probed directly) | yes | n/a (text-only outputs) | n/a | both confirmed live via a scratch probe app, not just by reading source |

Both accessors (`selected`, `selected_rows`) remain verified with real gestures from the prior pass; no
regressions found.

Judgment calls:

- Did not add a dedicated example file for the `.read("local_tz")`/`.read("debounce_wait")` conversion (kept it
  as prose only, as the original guide did for these two traits) -- verified with a throwaway probe instead of
  a new numbered example, consistent with this guide's existing judgment call about `fields=` vs `encodings=`
  (prose + probe, not a 15th file) to avoid padding.
- `examples/14_download_selection.py`'s brush selects a large fraction of the dataset (299/406) because the
  cars scatter is dense in the brushed region; left it as-is rather than hand-picking brush coordinates to hit
  a smaller, "nicer" count, since the screenshot still makes the selected/unselected contrast obvious and the
  point of the example is the download mechanism, not the brush shape.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views" and a new verified example,
`examples/15_vegafusion_scale.py` (1,000,000-row binned histogram, `alt.data_transformers.enable("vegafusion")`,
click-to-select a bin, `selected_rows()` read back). Versions: altair 6.x (as pinned in the project venv),
vegafusion 2.0.3, vl-convert-python 1.9.0 (both via `uv run --no-sync --with`, pinned; neither is in the
project's locked venv or the `altair` extra).

Verification: smoked (`smoke.py`, exit 0), gesture-driven (a real `mouse.click` on the rendered SVG bar, via a
scratch Playwright script, not `smoke.py`'s default wait alone), before/after screenshots looked at
(`img/15_vegafusion_before.webp`, `img/15_vegafusion_after.webp`): clicking a bar moved
`histogram.selected_rows('bin')` from "0 of 1,000,000" to "93,797 of 1,000,000 rows in the selected bin".

**Measured directly** (not estimated): built identical `JupyterChart`s at 5,000 / 200,000 / 2,000,000 rows with
VegaFusion enabled, read `.spec` after manually setting `.local_tz` (the trait the browser normally sets to
trigger the transform) to avoid needing a browser for this specific measurement:
- A binned histogram's transformed spec: 5,451 / 3,724 / 3,816 bytes -- flat regardless of row count.
- A raw `mark_circle` scatter's transformed spec: 344,416 / 13,460,637 / 134,534,287 bytes -- grows linearly.

This contradicts a plausible-sounding assumption (that enabling VegaFusion alone makes any chart cheap at
scale) and is why the example uses an aggregating mark (a histogram), not a raw scatter.

**Bugs found / gotchas (not filed, since they're expected-missing-dependency behavior, correctly logged)**:
`alt.data_transformers.enable("vegafusion")` alone (without `vl-convert-python`) fails the chart's vegafusion
compile step inside an ipywidgets trait-change observer triggered by the browser's `local_tz` message. The
widget area then stays permanently blank, with **no error in the browser console** and no immediately obvious
terminal output -- but shinywidgets' `ClientMsgErrorFilter` (`_comm.py`) does correctly reroute the swallowed
ipywidgets/traitlets callback exception to the server log as `Exception in widget method ... ImportError:
vl-convert-python`, with the real upstream fix (`pip install "vl-convert-python>=1.9.0"`) in the message. Also
discovered: `docs/widget-guides/tools/smoke.py` doesn't catch this particular failure -- the `.lm-Widget` div
exists (empty) before the async `local_tz` round trip resolves, so smoke.py's wait condition passes and it exits
0 even though the chart never renders. Not a bug in smoke.py's design so much as a sharp edge of polling for
element presence rather than content; flagging for whoever next touches `tools/smoke.py` or `tools/README.md`,
not fixing it myself (owned by Task 1, not 8a).

**Judgment call**: used a binned histogram, not a raw scatter, for the required VegaFusion example, after
measuring that a raw per-row scatter gets zero payload benefit from VegaFusion (see above) -- the design doc's
phrasing ("VegaFusion for altair" under "summarize on the server") only holds for aggregating transforms, so an
example built around a raw scatter would have demonstrated the opposite of the guide's own claim.
