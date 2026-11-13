# NOTES: Choosing a widget

Versions: shinywidgets `0.8.2.post1.dev102+g00f90249` (worktree `main-wt`, detached at `origin/main`), shiny 1.9.0,
Python 3.12. Date: 2026-11-02.

## Status: complete

`article.md` has all sections from the brief (statistical charts; tables/grids display vs. input;
maps and geospatial by sub-task; big data 10^5-10^7; 3D/scientific by domain; networks; drawing/canvas
input; ML/embedding exploration; bring your own; one comparison matrix across all ~45 widgets;
decision flow; 3 verified examples; Learn more). `examples/`, `img/`, and this `NOTES.md` are
populated. No outstanding TODOs in `article.md`.

## Research sourcing for the by-task sections and the comparison matrix

After the fork-collision incident below, per-widget facts (best-for, measured scale, bundle cost,
maturity/upstream caveats, multi-session caveats, distinguishing feature) were gathered via three
`Explore` subagents (tool-restricted, read-only, cannot Write/Edit/Agent -- so they cannot repeat the
fork incident), each reading guide.md's intro/"What you can build"/Gotchas and NOTES.md for one
category batch (maps; 3D & scientific; plotting+networks+input+generic), plus one earlier `fork`
(tables + large-scale scatter, completed before the collision was caught). All four reports were
read, cross-checked against `FINDINGS.md` and the accessor cheatsheet already in hand, and
synthesized into the article's prose and the comparison matrix -- not copied verbatim. Numbers
quoted as "measured" in the article (e.g. datashader's 6.9 MB flat payload, pyvista's 12 KB-800 KB
per-render cost, ipysigma's 20k/40k nodes, quak's 5M-row table) all trace back to a guide's own
NOTES.md measurement, not to something re-run for this article -- consistent with the brief's "don't
regurgitate guides; summarize and link" and "re-verify any claim you lean on heavily if it isn't
already in a guide's verification table" (these all already were).

## Incident: concurrent-agent collision (resolved)

Early in this task I launched 4 `fork` subagents for read-only research extraction. Forks inherit the parent's
full context, including this task's instructions and permissions -- so all 4 began independently writing into
`examples/`, `img/`, and starting `shiny run` servers on ports 10120-10139 (the exact range assigned to me),
racing my own work. I mistook this for a second, independently-dispatched agent and stopped to report it. The
coordinator clarified: there was no second agent, it was my own forks over-acting on inherited context. The
coordinator killed the forks and their servers. **Lesson for future runs of this kind of task: never use
`subagent_type: "fork"` for "just read and report" research when the parent prompt also authorizes writing files
and running servers -- use a tool-restricted agent (e.g. `Explore`, which cannot Write/Edit/Agent) instead, even
though forks are otherwise cheaper (shared cache).** Followed for the rest of this task.

Fallout handled:
- `examples/01_selection_three_ways.py` (mine) was overwritten by a fork's own version of the same idea,
  `examples/01_selection_three_libraries.py`. Kept the fork's version (equally good, already had log-scale axes
  on all three panels); deleted the stale duplicate name was never separately recreated, so nothing to delete there.
- Forks also produced `examples/02_tables_display_vs_input.py` and `examples/03_maps_location_vs_feature_pick.py`,
  which were better-scoped than my own in-progress drafts (same idea, but `03` compared `clicked()` vs
  `selected()` -- a feature-pick distinction -- instead of my plain two-map click comparison). Kept both,
  fixed bugs in them (below), re-verified all three myself with real Playwright gestures and server-side state
  before trusting them.
- Deleted two redundant leftover screenshots (`01_selection_altair.webp`, `01_selection_bokeh.webp`, single-panel
  crops superseded by my own `01_selection_before/after.webp` which show all three panels together).

## Bugs found in the fork drafts (fixed before verifying)

- `examples/02_tables_display_vs_input.py`: the ipydatagrid panel returned a bare `pd.DataFrame`, which
  `render_ipydatagrid` wraps with `DataGrid(..., selection_mode="none")` by default (confirmed by reading the
  class docstring, `shinywidgets/_render_widget.py:3062-3064`) -- so the panel's own caption ("cell-block
  selection") was unachievable; `.selected()` would stay `[]` forever. Fixed by explicitly constructing
  `DataGrid(df[cols], selection_mode="cell")`.
- Same file: the caption said "drag across cells" but ipydatagrid's lumino canvas grid doesn't register a
  click-drag as a selection in headless Playwright the way `tests/playwright/ipydatagrid_accessors` drives it
  (click, then shift-click, extends the rectangle) -- a plain mouse drag never fired `.selected()` in my testing.
  Switched the caption to match the gesture that actually works, and used `page.mouse.click()` +
  `page.keyboard.down("Shift")` + `page.mouse.click()` (the pattern from
  `tests/playwright/ipydatagrid_accessors/test_ipydatagrid_accessors.py`), not a drag.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Server-side state confirmed? |
|---|---|---|---|---|
| `examples/01_selection_three_libraries.py` | yes | `img/01_selection_before.webp`, `img/01_selection_after.webp` | yes -- real mouse-drag box-select/brush on all 3 panels (plotly `dragmode="select"`, altair `selection_interval`, bokeh `box_select`) | yes -- `selected_rows()` counts printed below each chart: plotly 14, altair 4, bokeh 46 (different because the log-x drag box covers a different data range per library's own axis rendering -- expected, not a bug) |
| `examples/02_tables_display_vs_input.py` | yes | `img/02_tables_before.webp`, `img/02_tables_after.webp` | yes -- real row click (plain `render.data_frame`), real row click (itables), real click+shift-click cell block (ipydatagrid) | yes -- `cell_selection()["rows"]`, `selected_rows()`, and `selected()` all read back correctly after the fix above |
| `examples/03_maps_location_vs_feature_pick.py` | yes | `img/03_maps_before.webp`, `img/03_maps_after.webp` | yes -- real click on blank map area (ipyleaflet `clicked()`), real click on a rendered point (lonboard `selected()`) | yes -- "Nearest pod #74: 1322 car-hours" (ipyleaflet, nearest-neighbor from a raw lat/lng click) and "Picked pod #208: 1500 car-hours" (lonboard, direct row pick) |

No accessors are introduced fresh by this article -- all three examples reuse accessors already documented and
gesture-verified in their own guides (plotly, altair, bokeh, itables, ipydatagrid, ipyleaflet, lonboard). This
article's job is the side-by-side comparison, not new accessor coverage.

## Judgment calls

1. **Kept the forks' example choices over my own original drafts** where theirs demonstrated something more
   interesting (feature-pick vs. location-click distinction in example 3; log-scale consistency in example 1).
   Fixed their bugs rather than discarding them. Flagging in case the maintainer prefers a from-scratch rewrite.
2. **Scope cut: 3 examples, not 5.** The brief says "~3-5" and "keep the other widget simple." Given lean-mode
   (one server, one browser at a time) and that this article's main value is the matrix + decision flow + honest
   "just use plain Shiny" callouts (not more worked examples -- `linked-views` and `reacting-to-widgets` already
   have 16+23 of those), I judged 3 sufficient: one plotting/selection comparison, one tables comparison, one
   maps comparison. Big-data (jscatter/datashader/lonboard-at-scale) and 3D comparisons are described in prose
   with numbers pulled from each guide's own measurements, not re-run live here -- re-running a 1M-10M point
   datashader/jscatter comparison under lean mode (one browser at a time, machine already crashed once from load)
   for a cross-cutting article that doesn't introduce a new pattern isn't worth the risk; the datashader and
   jscatter guides already did that work and are linked.
3. **The gapminder-2007 dataset for example 1** deliberately matches a pattern already used across several
   per-widget guides (plotly, altair, bokeh, lonboard, mosaic) -- reusing a dataset readers may have already seen
   in a sibling guide reduces cognitive load for "same task, different library" comparisons, at the cost of some
   novelty. Judgment call, not dictated by the brief.
4. **Comparison matrix columns**: chose accessor-count / in-place-update support / measured scale ceiling /
   first-render cost tier / multi-session caveat / typical use, rather than a longer list, to keep the single
   table scannable at roughly 40 rows. Full detail stays in each guide; this table is a triage aid.
5. **Did not build a dedicated 3D/scientific or big-data example app.** Those categories are covered by prose +
   links; the three examples cover selection/brushing, tables, and maps, which is where "same task, different
   widget" comparisons are most legible at a glance. If the coordinator wants a fourth example (e.g. a 3D
   point-cloud vs. volumetric comparison, or embedding-atlas vs. jscatter at scale), it is a natural scope add,
   not implied as mandatory by "3-5."

## Dropped / not used

- Did not reuse any gallery template/showcase apps verbatim; all 3 examples are purpose-built for a direct,
  simple A/B/C comparison (the brief's gallery apps are more elaborate single-widget showcases, not comparisons).
- Did not build a dedicated `articles/performance` cross-link beyond citing the per-guide numbers directly
  (`articles/performance/` did not exist yet in this worktree at the time of writing -- see the "Performance and
  scale" section's sourcing note in article.md).

## Editor's notes for the website

- Strongest screenshot: `img/01_selection_before.webp`/`after.webp` -- one glance shows three different selection
  idioms (dashed lasso box, gray brush rectangle, highlighted points) converging on the same answer. Good hero
  candidate for this article.
- The matrix is long (~40 rows); consider collapsing it to an expandable table or splitting by category on the
  live site rather than one scroll of a page.
- The ipyleaflet `(lat, lng)` dict vs. lonboard `(lng, lat)` tuple `clicked()` mismatch (surfaced by example 3) is
  a small, concrete, easy-to-miss gotcha worth pulling into its own callout box rather than leaving it buried in
  prose -- it will bite exactly the reader this article is for (someone switching between two map widgets).

## Update 2026-11-11 (main @ 32ca7035)

shinywidgets `0.8.2.post1.dev135+g32ca7035`, shiny 1.9.0. Worktree `scratchpad/main-wt`. This pass brought the
article up to date with the 33 commits since the original `00f90249` pass (per `docs/widget-guides/UPDATE-BRIEF.md`),
focused on the accessor comparison matrix and the `.read()`-tier narrative; no example was behaviorally edited
(see "Re-verification" below), so none was re-run.

**Accessor/feature updates, verified against `shinywidgets/_render_widget.py` and `_accessor_specs` on current
`main` (not guessed from the old report):**

- **Reactable is no longer dead.** The original pass's "release-blocker" callout (`accessor_specs` vs.
  `_accessor_specs` typo) is fixed on `main` -- confirmed by reading `render_reactable`'s class body
  (`_accessor_specs = REACTABLE_ACCESSORS`, correctly spelled, at `_render_widget.py:5891`). Removed the
  callout box and the "dead on main" matrix annotation; reactable's row now just lists its 5 accessors.
- **quak and mosaic now lock DuckDB down by default** (#395: `allow_unrestricted_connection=False` is the
  default, confirmed by reading both renderers' docstrings and the `allow_unrestricted_connection` parameter in
  `_render_widget.py`). Rewrote the security callout from "don't deploy until this lands" (true at the original
  pass) to describe the actual default behavior and the opt-out, including mosaic's permanent/database-wide
  lockdown caveat for a shared connection (from its own docstring).
- **plotly**: 10 accessors now (was ~6 at the original pass) -- #443 added `hover()`, `double_clicked()`,
  `legend_clicked()`, `visible_traces()`. Updated the Statistical Charts intro sentence and the matrix count
  (7 -> 10).
- **plotnine**: gained `limits(ax=0)` (#402); matrix count 1 -> 2, updated the matplotlib/plotnine bullet in
  Statistical Charts.
- **panel**: gained a dynamic `param(name)` accessor (#438, `slider.param("value")`); matrix count 0 -> 1, and
  rewrote the "you already live in HoloViews/hvPlot/Panel" bullet, which previously said none of
  holoviews/panel/obsplot have dedicated accessors -- now true only for holoviews and obsplot.
- **ipycytoscape**: gained `selected_nodes()`/`selected_edges()` (box/multi-select, debounced; #428), on top of
  the already-renamed `clicked_node()`/`clicked_edge()` (the old `node_clicked()`/`edge_clicked()` names were
  already absent from this article before I started -- no rename needed here). Matrix count 2 -> 4. Also
  confirmed via the renderer's docstring that #404 made `rate_policy`/`rate_delay` reach the child `Node`/`Edge`
  widgets (previously a near-no-op, per the old `FINDINGS.md` entry) -- not mentioned in this article before or
  after, since the article doesn't discuss ipycytoscape's rate limiting specifically.
- **ipydatagrid's `clicked_cell()` naming** was already correct in this article before I started (the
  pre-rename `cell_clicked()` never appeared here) -- confirmed, no change needed.

**`.read()`-tier phrasing** (per the brief: fix "no accessors, use `reactive_read()`" phrasing to point at the
new universal `.read()` tier first): updated the "How to read the trade-offs" intro, the table's accessor-count
footnote, maplibre's bullet and matrix-adjacent decision-flow line, and the ipysigma/drawdata/ipycanvas/
render_widget bullets in their respective sections -- all of these read traits on the *same* render output's
own widget (confirmed for ipysigma specifically by reading `render_ipysigma`'s docstring: `selected_node`,
`selected_edge`, `camera_state` are traits on `.widget` itself, not a child widget), so `.read("trait")` is the
correct first-tier pointer, not `reactive_read()`. Left `reactive_read()` language alone where it's actually
about a genuine child/nested widget (ipyfilechooser's plain-property explanation, the general "three tiers"
pointer into `reacting-to-widgets`) or about library mechanics that are independent of this distinction.

**#415 gotcha removed.** "Bring your own widget" described two timing traps (a `.send()`-backed message issued
before the comm opens, or in the same flush as a re-render, being silently dropped) that #415 fixes --
confirmed via `CHANGELOG.md`'s own entry ("Widget methods that message the browser are no longer silently
ignored when called before the output finishes rendering... (#415)") and independently via the k3d guide's own
re-verified Gotchas section ("now delivered to the browser instead of being silently dropped -- confirmed with
a websocket capture"), which the brief's "reuse a guide's already-verified knowledge" instruction covers.
Rewrote the paragraph to describe the current (fixed) behavior and the one real remaining nuance (some
libraries' own JS won't visibly act on an early call until a later user gesture -- a browser-autoplay-style
restriction, not a shinywidgets bug), citing k3d's guide rather than re-deriving the websocket capture myself.
Updated the matching matrix-row text for `render_widget`.

**Links checked, none stale.** The brief flagged specific renamed/deleted example files in other guides
(jscatter `07_reactive_read_traits.py` -> `07_read_traits.py`; panel's `07_param_watch_bridge.py`/
`08_param_read_helper.py` gone). This article links only to `../../<slug>/guide.md` pages, never to a specific
`examples/*.py` file in another guide's directory -- confirmed by grepping the whole article for
`examples/[a-z0-9_.]+\.py` references outside this article's own `examples/`. Nothing to fix.

**Re-verification:** none of the three side-by-side example apps (`examples/01-03_*.py`) were touched -- no
accessor they use was renamed or removed, and their behavior (plotly/altair/bokeh selection,
render.data_frame/itables/ipydatagrid tables, ipyleaflet/lonboard click vs. pick) is unaffected by any PR in
the brief's list. Per the brief ("Re-verify the three side-by-side examples only if you edit them"), I did not
re-run them or retake their screenshots.

**Bugs found (2026-11-11):** none. Everything checked against current `main` either confirmed the brief's
summary directly or was independently visible in the renderer source/docstrings.

**Judgment calls:**
- Treated "fix `.read()` phrasing" as applying only where the article currently frames a trait read as
  `reactive_read()` *on the output's own widget* (the case `.read()` now covers), not every mention of
  `reactive_read()` in the article -- several remaining mentions are about genuinely different things (child
  widgets, properties instead of traits, a pointer to the conceptual three-tier explanation in
  `reacting-to-widgets`) and rewriting those would misrepresent what `.read()` actually does.
- Did not touch the "In-place updates" column for panel (`via .param.watch() bridge`) even though the new
  `param(name)` accessor makes that phrase read oddly next to the Accessors column now saying `1`. That column
  describes *writing* a widget in place (`.value.value = df`, per the renderer's own docstring), which
  `param()` doesn't change -- fixing the column's wording would be a defensible but out-of-scope cleanup the
  brief didn't ask for; flagging for a second opinion rather than guessing at new wording.
