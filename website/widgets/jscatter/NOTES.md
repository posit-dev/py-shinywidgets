# NOTES: jupyter-scatter guide

## Versions and environment

- Date: 2026-10-30
- shinywidgets: `main` @ `f8238de6` (moving target during this pass -- see "Shared-checkout churn" below)
- shiny 1.9.0, jupyter-scatter (`jscatter`) 1.0.1, itables 2.9.1, anywidget 0.11.0
- Playwright Chromium, headless, launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` (matches the old report; SwiftShader WebGL was already active by default in this
  environment, so the flags made no observable difference, but they're harmless to keep)
- Ports 9180-9199 (assigned range); verification driver at
  `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/agents/jscatter/driver.py`

## Verification table

Every example and gallery app was run with `shiny run` via `shiny.run.run_shiny_app`, driven with Playwright, and
screenshotted; every screenshot was viewed with the Read tool before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `quickstart.webp` | long-press lasso | `selected()` count matches lasso |
| `examples/02_scale.py` | yes | `scale_overview.webp`, `scale.webp` | scroll-zoom | `selected()` present (not driven at scale; see below) |
| `examples/03_encodings.py` | yes | `encodings.webp` | none (static) | n/a |
| `examples/04_animated_xy.py` | yes | `animated_xy_before.webp`, `animated_xy_after.webp` | button click (`.xy(animate=True)`) | n/a (no accessor) |
| `examples/05_tooltips.py` | yes | `tooltip.webp` | hover via `plot.api.getScreenPosition()` | n/a |
| `examples/06_selection_accessor.py` | yes | `selection_before.webp`, `selection_after.webp` | long-press lasso | yes, table + count both verified |
| `examples/07_reactive_read_traits.py` | yes | `reactive_read_before.webp`, `reactive_read_after.webp` | hover + scroll-zoom + lasso | `hovering`, `zoom_level`, `lasso_selection_polygon` all confirmed changing |
| `examples/08_update_in_place.py` | yes | `update_in_place_before.webp`, `update_in_place_after.webp` | button click | n/a |
| `examples/09_python_selection_filter.py` | yes | `python_select_before.webp`, `python_select.webp`, `python_filter.webp` | 3 button clicks | `selected()` count matches (301 of 3000, the top 10% by weight) |
| `examples/10_linked_brushing.py` | yes | `linked_brushing_before.webp`, `linked_brushing_after.webp` | long-press lasso | `selected()` drives the link in both directions |
| `examples/11_lasso_to_itables.py` | yes | `lasso_to_itables_before.webp`, `lasso_to_itables_after.webp` | long-press lasso | `selected()` feeds the itables table (744 of 1500 rows) |
| `examples/12_table_to_plot_highlight.py` | yes | `table_to_plot_before.webp`, `table_to_plot_after.webp` | table row click | plot highlight follows `table.cell_selection()` |
| `examples/13_layout.py` | yes | `layout.webp` | none (static) | n/a |
| `gallery/template_linked_scatter.py` | yes | `gallery_template_before.webp`, `gallery_template_after.webp` | long-press lasso | `selected()`, both directions, table |
| `gallery/showcase_single_cell_atlas.py` | yes | `gallery_showcase_before.webp`, `gallery_showcase_after.webp`, `gallery_showcase_colorby.webp` | button click (Python-driven selection + zoom), dropdown (in-place recolor) | `selected()` count and composition panel both verified (3,000 of 300,000 = 1.0%) |

**Accessor coverage: `selected()` is the renderer's only accessor (`_accessor_specs = JSCATTER_ACCESSORS = (SELECTION,)`
in `shinywidgets/_jscatter.py`), and it was exercised with a real browser gesture in 6 of the apps above, plus
confirmed driven from Python in 2 more.** This is complete coverage for this renderer.

### Not independently re-verified

- **>3M-point lasso selections exceeding the 16 MiB websocket limit.** The old report measured this directly
  (26.7 MB frame at 5M points, session disconnect) and it's now documented in the `render_jscatter` class
  docstring. I didn't reproduce the disconnect myself in this pass (it takes tens of seconds to build and would
  have meant running a second large-N app on a loaded shared machine for a fact that's already correctly
  documented on `main`); I did verify 2M points render and pan/zoom smoothly (`02_scale.py`), and that the
  documented mechanism (base64 JSON over a size-limited websocket frame) is architecturally unchanged. Flagging
  per the brief's instruction to say so rather than guess.
- **Upstream jupyter-scatter quirks from the old report** that I did not re-check because they're unrelated to
  the accessor/layout work this pass covers and didn't block anything I verified: the transient `color(by=None)`
  console error, and the `useScatterView must be used within a Toolbar` fullscreen React warning (still present
  as a known-upstream, filtered-out message in `tests/playwright/render_jscatter`). Neither affects functionality.

## Bugs and surprises found

All three below are genuine, verified-in-browser discoveries from this pass (not carried over from the old
report, which predates the accessor and didn't call them out):

1. **Upstream limitation (new finding): at most 2 distinct data dimensions for color/size/opacity.**
   `jscatter.encodings.Encodings.__init__` reserves 2 of 4 point-buffer components for x/y, leaving 2 for
   data-driven channels; a third *distinct* column raises `AssertionError: Only 2 data encodings are supported`.
   This isn't mentioned in jupyter-scatter's docstrings for `.color()`/`.size()`/`.opacity()`. Repro:
   `Scatter(df, x=.., y=..).color(by="a").size(by="b").opacity(by="c")` with three distinct columns. Workaround
   (used in `examples/03_encodings.py`): reuse one column across two channels.
2. **Docs gap (shinywidgets docstring, not wrong, just incomplete): `render_jscatter`'s class docstring doesn't
   mention `hovering`, `zoom_level`, or `lasso_selection_polygon` as `reactive_read()`-worthy traits**, even
   though it recommends `reactive_read()` as the general escape hatch. The old report found these same three
   traits useful; I re-verified all three fire correctly in a real browser (hover, scroll, lasso) and wrote them
   up under "Beyond the accessor" in the guide. Worth adding to the docstring in a future pass.
3. **Shiny-express interaction (judgment call material, see below): a module-level docstring renders as visible
   page text.** `shiny.express`'s `run_express()` compiles each top-level statement in `ast.Interactive` mode,
   which runs Python's display-hook machinery on every top-level expression statement -- including a bare
   docstring. The brief's gallery-file convention calls for a docstring header; as written, that header would
   show up as a run-on paragraph at the top of the rendered app (confirmed: I saw exactly this before fixing it).
   Fixed in both gallery files by assigning `__doc__ = """..."""` (an assignment statement, not a bare
   expression) instead of a bare triple-quoted string. This isn't a shinywidgets bug -- it's `shiny.express`
   behaving as designed -- but it's a real trap for anyone writing a `shiny.express` app with a leading
   docstring, which the brief asks every gallery file to have.

## Judgment calls for the maintainer to revisit

- **The docstring workaround above (`__doc__ = """..."""`)**: I applied this fix silently in both gallery files
  rather than leaving the docstring rendering in the page. If the coordinator would rather gallery files use a
  leading `#`-comment block instead (sidestepping the question entirely, at the cost of losing `__doc__` as a
  machine-readable field), that's an easy swap across all the guides' gallery files once this pattern is
  noticed elsewhere.
- **`examples/03_encodings.py`'s three-encodings-via-two-dimensions trick** (size and opacity both keyed to
  `hp`) is a bit clever for a "teach what's possible" snippet. I kept it because the 2-dimension limit is a real
  constraint readers will hit the first time they try exactly this, and burying it in prose without a working
  example felt worse. Could be simplified to a plain 2-encoding example with the limit mentioned only in
  Gotchas, if the maintainer prefers a less clever quickstart-adjacent snippet.
- **`examples/02_scale.py` uses 2,000,000 points, not the old report's 5,000,000.** 2M was enough to show the
  scale story (smooth pan/zoom, individual points visible when zoomed) without the ~30s render time and risk of
  destabilizing a shared, loaded machine that 5M incurred for the original report's author. If the maintainer
  wants the full 5M number in the guide text, it can be restated as a fact (it's already documented in the
  `render_jscatter` docstring's websocket-limit note) without needing to re-run it here.
- **Gallery `showcase_single_cell_atlas.py` keeps the old report's synthetic single-cell dataset almost verbatim**
  (same cell types, shapes, and marker-gene synthesis), updated to use the `selected()` accessor in place of
  raw `reactive_read()` calls, and to drive selection via `.widget.selection = ...` per the brief's example
  patterns. This felt like reuse of good, already-designed material rather than independent work worth
  reinventing; flagging in case the maintainer wants gallery content to be more clearly original per guide.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: itables** -- `examples/11_lasso_to_itables.py` drives an itables table from a jscatter lasso
  selection (re-rendered on each change).
- **pairs with: (Shiny core, not a widget)** -- `examples/12_table_to_plot_highlight.py` drives jscatter's
  `selection` trait from Shiny's own `@render.data_frame` row-click selection. Not a widget-to-widget pairing,
  but the same "drive one view from another" pattern, included because the brief's own example list names it
  explicitly ("table row selection → highlight in a plot").

## Editor's notes for the website

- **Strongest material**: the "Beyond the accessor" screenshots (`reactive_read_after.webp`) are the single best
  piece of evidence in this guide -- one screenshot shows `hovering`, `zoom_level`, and `lasso_selection_polygon`
  all simultaneously confirmed live. The gallery showcase's three screenshots (default → Python-driven zoom →
  in-place recolor with selection preserved) are the best "wow" sequence and should probably lead any gallery
  page or marketing excerpt.
- **What to cut for a shorter page**: the "Rate limiting" subsection is thin (jscatter's `selected()` has
  nothing to rate-limit by default) -- it could be folded into the accessor reference table's "default rate
  policy" cell with a one-sentence footnote, dropping the subsection heading entirely. The "Beyond the accessor"
  traits could also be trimmed to just `hovering` and `zoom_level` if space is tight; `lasso_selection_polygon`
  is the least commonly useful of the three.
- **What I dropped from the old report, and why**:
  - The fullscreen-button bug and its 3-line JS fix: fixed on `main` (re-verified; see Gotchas). Replaced with a
    one-line "fixed since the earlier review" note instead of describing a bug that no longer exists.
  - The upstream `FullscreenPanel` React warning and the `color(by=None)` transient-error finding: not re-verified
    this pass (see "Not independently re-verified" above); omitted rather than repeated unverified.
  - The scorecard, PR-review verdict, and "should-fix" sections: those were about reviewing a specific PR
    (#293) before merge, not about teaching the shipped feature, which is this document's job.
  - The `--ws-max-size` 5M-point disconnect measurement: kept as a documented fact (it's in the class docstring
    already) but not re-measured; see above.
  - The two-views-of-one-model limitation ("the second view's axes don't follow camera changes"): PR-era
    implementation detail about an unsupported pattern the guide never recommends in the first place (prefer
    separate `@render_jscatter` outputs, as every "coordinating multiple views" example here does); not worth a
    gotcha bullet for a pattern nobody's being told to use.

## Shared-checkout churn (operational note, not about jupyter-scatter)

Several other agents were actively committing to tracked files in this shared checkout
(`shinywidgets/_render_widget.py`, `pyproject.toml`) while this guide was being verified, which intermittently
broke `import shinywidgets` and `uv run` for a few seconds to tens of seconds at a time (merge-conflict markers
left in the file mid-edit). This is expected given "~10 other agents on one machine" and resolved itself every
time within under a minute; the driver script retried `import shinywidgets` before each app launch to ride this
out. No action needed, just noting it in case screenshot timestamps look oddly spaced.

## Update 2026-11-11 (main @ 32ca7035)

Versions: jupyter-scatter 1.0.1, shiny 1.9.0, worktree
`/private/tmp/claude-502/.../ce388f54.../scratchpad/main-wt`. Read `shinywidgets/_jscatter.py` and
`render_jscatter`'s docstring/`selected()` docstring in `shinywidgets/_render_widget.py` against current `main`.

What changed in the guide and why:

- **Converted `reactive_read(w, "hovering"/"zoom_level"/"lasso_selection_polygon")` to
  `plot.read("hovering"/"zoom_level"/"lasso_selection_polygon")`.** All three are traits of `plot.widget`
  itself (the render output's own `JupyterScatter` widget), so `.read()` reaches them directly, and its
  built-in cancel-until-rendered behavior replaces the `w = plot.widget; req(w)` boilerplate every reader used
  to need. Renamed the section "Beyond the accessor: `reactive_read()`" -> "Beyond the accessor: `.read()`",
  and the example file `examples/07_reactive_read_traits.py` -> `examples/07_read_traits.py` (content no
  longer uses `reactive_read` at all, so the old name was misleading; screenshots renamed to match:
  `img/reactive_read_{before,after}.webp` -> `img/07_read_traits_{before,after}.webp`).
  Re-verified live: hover (via `plot.api.getScreenPosition(0)` for a precise hit, since blind-hovering the
  canvas center missed the sparse random data), scroll-zoom (`page.mouse.wheel`), and a long-press lasso all
  updated their respective `.read()` outputs; a combined "after" screenshot shows all three non-default at
  once (`hovering: 0`, `zoom_level: 0.46`, `lasso_selection_polygon: 40 vertices`) by re-hovering after the
  lasso completed (the lasso's own mouse-up moves off the hovered point, so a single pass through the gestures
  can't show all three simultaneously).
- **Accessor reference table reformatted** to the new columns (`before any interaction` / `across re-render`).
  Content unchanged in substance -- `selected()`'s cancel/seed semantics (seeds empty for a normal
  `Scatter(...)`-built plot; cancels like `.widget` for a bare `JupyterScatter` until the browser's first
  report) were already correctly documented, matching `_jscatter.py`'s `SELECTION = AccessorSpec(...,
  not_ready=is_unreported)` and the current `selected()` docstring verbatim.
- **New example: "Reading an accessor on demand"** (`examples/14_download_selection.py`), added to "Reacting
  to user interaction" after "Rate limiting". A `@render.download_button` handler reads `plot.selected()`
  fresh each click. Verified: lassoed a cluster of 2000 points, clicked download, read the CSV back (247 rows,
  matching the visibly highlighted cluster in the screenshot).
- **No warm-up idiom was present to delete.** `selected()`'s "seeded, not None, for a normal Scatter" framing
  was already in place before this pass.

Docs gap noted (not fixed, not shinywidgets's directory to edit): `render_jscatter`'s class docstring in
`shinywidgets/_render_widget.py` still says "Other traits worth reading with `reactive_read()` are `hovering`,
`zoom_level`, and `lasso_selection_polygon`" -- it could mention `.read()` as the simpler option for these
three now that #437 added it, the same way the `bqplot`/`altair`/`bokeh` docstrings already describe `.read()`
for their own widget's bare traits. Not a functional bug (both still work); a source-level follow-up for
whoever next touches `_render_widget.py`.

Verification status (new/changed only):

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/07_read_traits.py` (renamed from `07_reactive_read_traits.py`, rewritten to use `.read()`) | yes | yes (before/after, renamed) | hover (via `getScreenPosition`), scroll-zoom, long-press lasso | all 3 traits confirmed via `.read()` |
| `examples/14_download_selection.py` (new) | yes | yes (before/after) | long-press lasso, then click download | `selected()` read inside `@render.download_button`, content verified (247 rows, CSV spot-checked against the highlighted cluster) |

`selected()` remains verified with a real gesture from the prior pass; no regressions found. No new bugs
found this pass.

Judgment call: kept `examples/01-06, 08-13` and their screenshots as-is after re-reading each one's
surrounding prose against current docstrings/source; found nothing else stale.

## Update 2026-11-11 (B1 rename: selection() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.
- `img/selection_*.webp` and `img/14_download_selection_*.webp` re-shot (the app title shows `plot.selected()`).

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example needed -- this guide's own "Millions of points, interactively" section (2,000,000-point example) and its documented ~3M-point websocket-limit gotcha already cover the contract; summarized and cross-linked both rather than duplicating.

## Update 2026-11-11 (B2: selected_rows() accessor, jscatter first)

- New accessor `plot.selected_rows(df=None)`: the selected rows of the plot's data frame (defaults to the
  frame the returned `Scatter` was built with; explicit `df=` for a bare `JupyterScatter`; pandas/polars in,
  same type out). Implemented in the `b2-jscatter-selected-rows` worktree (PR pending).
- Front matter `accessors:` list, intro paragraph, and the accessor reference table all gained
  `selected_rows()`. New subsection "`selected_rows()`: the selection, as rows of your data frame" after
  `selected()`; the `selected()` prose no longer teaches `df.iloc[plot.selected()]` for the rows use case
  (positions remain the right shape for programmatic selection/filtering and linked brushing).
- Examples switched from the hand-rolled `df.iloc[plot.selected()]` to `plot.selected_rows()`:
  `06_selection_accessor.py` (the selected-cars grid), `11_lasso_to_itables.py` (now a one-line link),
  `14_download_selection.py` (also retitled "Reading selected_rows() on demand"), and
  `gallery/template_linked_scatter.py` (`selected_cars` grid). `10_linked_brushing.py` and the showcase keep
  positions on purpose (selection setters take positions; the showcase wants all rows when nothing is
  selected).
- Cross-cutting articles updated: cheatsheet (new row), reacting-to-widgets "Rows of your data" (jscatter
  added to the list + a bullet), choosing-a-widget matrix (accessor count 1 -> 2), linked-views example 02
  re-synced with `11_lasso_to_itables.py` (code block + prose + screenshot).

Verification (all against the B2 worktree's code, real gestures, screenshots looked at):

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/06_selection_accessor.py` | yes | yes (before/after re-shot) | long-press lasso | `selected_rows()` grid: "1937 of 3000 cars selected", 34 grid rows |
| `examples/11_lasso_to_itables.py` | yes | yes (before/after re-shot) | long-press lasso | itables "Showing 1 to 10 of 805 entries" |
| `examples/14_download_selection.py` | yes | yes (before/after re-shot, new title) | long-press lasso + download click | CSV has 451 data rows |
| `gallery/template_linked_scatter.py` | yes | yes (before/after re-shot) | long-press lasso on one plot | table 2,054 rows; mirror ring visible on the other plot |
| `articles/linked-views/examples/02_jscatter_lasso_to_itables.py` | yes | yes (after re-shot) | long-press lasso | itables "Showing 1 to 10 of 805 entries" |

No new bugs found. Operational note for future agents: Playwright drivers that spawn `uv run ... shiny run`
must kill the process *group* (`start_new_session=True` + `os.killpg`); killing the `uv run` wrapper orphans
the server, and the next run on the same port silently hits the stale server.
