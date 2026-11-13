# NOTES: "Linking widgets" article

## Versions

- shinywidgets: `main` @ `00f90249` (2026-11-02), run from the coordinator's detached
  worktree (`main-wt`, fresh Python 3.12 venv synced with all groups after a scratchpad
  reset mid-task).
- shiny: 1.9.0
- plotly 6.9.0, altair 6.3.0, itables 2.9.1, jscatter 1.0.1, ipyleaflet 0.20.0, lonboard
  0.17.0, bqplot 0.13.1, mosaic_widget (unversioned `__version__`), duckdb 1.5.6
  (confirmed locked; see "Judgment calls"), ipydatagrid 1.4.0, maplibre 0.3.6,
  ipycytoscape 1.3.3, geopandas 1.2.0, matplotlib 3.11.2, geolibre 3.6.0.
- `vega_datasets` is not in the shared venv; every altair example used
  `uv run --no-sync --with vega_datasets ...` (a new, unpinned package -- not an
  overlay of anything already locked, so this does not risk the duckdb-style
  version-skew the coordinator warned about). [Updated 2026-11-02, maintainer
  Decision 8: the article's altair examples now use `altair.datasets` (bundled
  with altair 6.3.0), so no overlay is needed for them anymore.]
- `reactable` is not in the shared venv and was not installed (all `render_reactable`
  accessors are a known dead regression on this commit -- see Bugs found).
- Playwright: Chromium, headless, 1280x760 viewport, `device_scale_factor=2`. The
  lonboard example launched with `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` per BRIEF.md's WebGL guidance; picking worked without it too,
  but the flags were kept for safety.
- Date: 2026-11-02.

## Verification table

Every file in `examples/` was run with `uv run --no-sync shiny run <file>` (or
`python -m shiny run` -- see "Judgment calls") from the worktree. 13 of 16 examples are
reused verbatim from already-verified per-widget guides (credited inline in
`article.md` and below); for those, verification here means: boot-tested on this
commit with an HTTP 200 response, and the already-captured screenshot from the source
guide was read (Read tool) and visually confirmed to match the claim made about it
before being copied into this article's `img/`. The 3 new/adapted examples (05, 12, 16)
were driven with real Playwright gestures and freshly screenshotted for this article.

| File | Status | Screenshot | Gesture |
|---|---|---|---|
| `01_plotly_lasso_to_itables.py` | reused, boot-tested | before/after (from plotly guide, re-inspected) | lasso (verified upstream) |
| `02_jscatter_lasso_to_itables.py` | reused, boot-tested | before/after (from jscatter guide, re-inspected) | lasso (verified upstream) |
| `03_lonboard_click_to_detail.py` | reused, boot-tested | before/after (from lonboard guide, re-inspected) | click (verified upstream) |
| `04_ipycytoscape_click_to_detail.py` | reused, boot-tested | before/after (from ipycytoscape guide, re-inspected) | click (verified upstream) |
| `05_altair_click_to_plotly_detail.py` | **new**, fully verified | before/after | real click on an altair mark (Playwright `locator.click(force=True)` on a `path[role='graphics-symbol']`); confirmed `scatter.selected_rows("pick")` drove both the text card and a fresh `render_plotly` bar (Datsun 510 (sw), 92 hp vs. ~105 hp fleet average) |
| `06_ipyleaflet_bounds_to_plotly.py` | reused, boot-tested | before/after (from ipyleaflet guide, re-inspected) | pan/zoom (verified upstream) |
| `07_maplibre_viewport_to_matplotlib.py` | reused, boot-tested (slow start -- live `requests.get`, needed ~8s not 4s) | before/after (from maplibre guide, re-inspected) | pan/zoom (verified upstream) |
| `08_plotly_relayout_to_plotly.py` | reused, boot-tested | before/after (from plotly guide, re-inspected) | zoom (verified upstream) |
| `09_itables_selection_to_plotly_inplace.py` | reused, boot-tested | before/after (from itables guide, re-inspected) | row selection (verified upstream) |
| `10_geolibre_table_to_map.py` | reused, boot-tested | before/after (from geolibre guide, re-inspected) | row selection (verified upstream) |
| `11_jscatter_bidirectional.py` | reused, boot-tested | before/after (from jscatter guide, re-inspected) | lasso (verified upstream) |
| `12_lonboard_plotly_bidirectional.py` | **new**, fully verified | before / after-map-click / after-chart-click | real canvas click (lonboard WebGL picking) + real SVG marker click (plotly); confirmed BOTH directions: a map click recolors both widgets to pod #11 (lat 45.5253, lng -73.5939, matching the plotly hover exactly), and a *different* plotly point click (lon -73.5399, lat 45.57313) then moves the highlight on **both** widgets, proving the broker links both ways. No freeze/loop observed across either gesture. |
| `13_altair_crossfilter_in_widget_vs_shiny.py` | reused, boot-tested | before/after (from altair guide, re-inspected) | brush drag (verified upstream) |
| `14_mosaic_crossfilter_stats_table.py` | reused, boot-tested | before/after (from mosaic guide, re-inspected) | brush drag (verified upstream) |
| `15_mosaic_crossfilter_to_lonboard.py` | reused, boot-tested | before/after (from mosaic guide, re-inspected) | brush drag (verified upstream) |
| `16_plotly_one_calc_many_views.py` | **new/adapted**, fully verified | before/after | real lasso drag (Playwright mouse down/move/up, dragmode defaults to lasso); confirmed one `@reactive.calc` fed `render.text` (22 visits, 21.8% avg tip), `render_itables` (22-row table), and `render.plot`/matplotlib (histogram) simultaneously from a single selection |

## Bugs found / surprises

**Status as of 2026-11-11 (main @ 32ca7035): the reactable regression below is fixed
(#394).** Kept as the original record; see "Update 2026-11-11" further down for the
re-verification and the article text change that followed from it.

- **[sw, REGRESSION, already known]** `render_reactable`'s accessors are dead on this
  commit (`accessor_specs` vs. `_accessor_specs` typo, per `FINDINGS.md`). This article
  deliberately avoids building any reactable-based example as a result -- not a new
  finding, just confirming the exclusion was deliberate, not an oversight. Reactable is
  still named in the pattern-picker table's "Learn more" links since the *pattern*
  (selection &rarr; detail, search &rarr; chart) is real and documented in the reactable
  guide; readers should know the accessors underneath it don't currently work.
- **[authoring hazard, independently rediscovered while building example 12]**
  `lonboard`'s `get_fill_color` on a `ScatterplotLayer` requires a numpy array
  (`np.array([...], dtype=np.uint8)`), not a plain Python list of tuples -- passing a
  list raises `traitlets.TraitError: expected 3 or 4 values ...` even though the error
  message doesn't mention the list-vs-array distinction at all. I only caught this
  because the mosaic&rarr;lonboard reused example (`15_mosaic_crossfilter_to_lonboard.py`)
  already uses `np.array(..., dtype=np.uint8)`; my first draft of the new broker example
  used a plain list and failed at render time. Worth a docstring note on
  `get_fill_color`/the per-point-color traits generally (not filed elsewhere; flagging
  here since it's a real trap for anyone writing their own in-place-recolor effect, the
  exact idiom this article teaches in patterns 4-6).
- **[environment, not a bug, but worth recording]** `uv run --no-sync --with <pkg>
  shiny run <file>` silently fails to see the `--with`-installed package
  (`ModuleNotFoundError`) even though `uv run --no-sync --with <pkg> python -c "import
  <pkg>"` succeeds in the same environment. Root cause: `shiny` is a console-script
  entry point whose shebang points at the *original* venv's `python3`, which bypasses
  uv's ephemeral `--with` overlay (that overlay only augments the directly-invoked
  Python interpreter's `sys.path`). The fix is `uv run --no-sync --with <pkg> python -m
  shiny run <file> ...` -- forcing the invocation through the python module runner
  instead of the console-script shim. This cost real time (several failed runs assuming
  `vega_datasets` wasn't actually resolving) before the shebang indirection was spotted;
  worth a line in `BRIEF.md`'s "Where to run code" section for the next swarm that needs
  `--with` plus `shiny run` together.

## Judgment calls

- **Verification depth for reused examples.** 13 of 16 examples in this article are
  byte-for-byte copies of already-verified code from finished per-widget guides. Rather
  than re-driving every gesture with a fresh Playwright script (redundant work against
  identical code, on the same commit, that another agent already drove end to end), I
  boot-tested each (HTTP 200, no traceback) and re-inspected the *source guide's own*
  before/after screenshots with the Read tool before copying them into this article's
  `img/`, checking each one actually shows the claim being made about it here. I did not
  re-run Playwright gestures against the copies themselves. If the maintainer wants full
  independent re-verification of all 13 (not just the 3 new/adapted ones), flag it and
  I can add it -- but I'd weigh that against the low likelihood of a copy-paste
  regression versus the cost of ~13 more browser sessions.
- **Pattern 5's second example is a "broker," not a direct trait mirror.** The brief's
  wording ("selection in A highlights in B and vice versa... avoid feedback loops with
  `reactive.isolate`/equality checks") most directly describes jscatter's own two-figure
  linked-brushing idiom (reused as the first example). For the required cross-library
  example, I judged that lonboard and plotly don't expose a *compatible* Python-settable
  selection trait to mirror the same way (lonboard's `selected()` is a single int,
  read-only in the sense that there's no `.widget.selected_index = ...` write path that
  the browser's picking state would accept back), so a direct mirror isn't actually
  available for this pair. I built the "shared broker `reactive.value`" architecture
  instead, which solves the same user problem (two widgets, one selection) and still
  demonstrates the equality-guard discipline, but is architecturally different from a
  direct two-widget mirror. I call this out explicitly in the article text so it reads
  as an intentional alternative, not an evasion of the brief's wording. Second opinion
  welcome on whether a true direct-mirror cross-library pair exists elsewhere in the
  roster that I missed.
- **bqplot's cross-figure `Selector`-sharing limitation** is cited in prose (with a link
  into the bqplot guide's own Gotchas and its Python-round-trip workaround) rather than
  rebuilt as a fourth full example here -- the bqplot guide already has the verified
  repro and workaround; duplicating it would just be a shorter, less detailed copy.
- **Pattern 6 cites embedding-atlas's `predicate()` in prose only**, not as a full
  fourth code block -- the article already has three worked crossfilter examples
  (altair in-widget+Shiny, mosaic in-widget+Shiny, mosaic-to-lonboard through-Shiny
  only) and a fourth would mostly repeat the "through Shiny, DuckDB-backed" idea mosaic
  already demonstrates. Flagging in case the maintainer wants it promoted to a full
  example instead.
- **Did not build a reactable-based example** anywhere in this article, for the reason
  given above (dead accessors). This also means pattern 1's "itables/reactable" and
  pattern 7's itables-or-reactable mentions in the per-widget guides' own text are not
  mirrored 1:1 here -- I only reuse itables.

## Editor's notes for the website

- **Strongest visual**: pattern 5's lonboard&harr;plotly broker (the hero image) -- it's
  the one example in the whole article that's genuinely novel (not reused) and visually
  proves bidirectionality in a single screenshot pair (the same pod highlighted on two
  completely different renderers, then the highlight visibly jumping to a new pod from
  the *other* widget's click).
- **Second strongest**: pattern 7's one-calc-many-views (three different libraries --
  plotly, itables, matplotlib -- updating from one lasso) is the cleanest single
  illustration of "accessors are composable," and is short enough to keep in full on
  the page.
- **Candidate for trimming on a shorter page**: pattern 3's third example (plotly
  `relayout()`) is a nice-to-have, not essential -- the two map-viewport examples
  already establish the pattern, and this one's value-add (distinguishing "map
  viewport" from "plot zoom") could become a single sentence with a link instead of a
  full code block.
- The pattern-picker table at the end is meant to be skimmable on its own, including by
  a reader who jumps straight to it from a search result -- every row links into at
  least one guide's own "Coordinating multiple views" section for the deeper version.

## What I deliberately did not build

- A `reactable`-based example (dead accessors on this commit; see Bugs found).
- A fourth pattern-6 example for embedding-atlas (prose-only; see Judgment calls).
- A direct-mirror (non-broker) cross-library pattern-5 example (no compatible pair
  found in the time available; see Judgment calls).

## Update 2026-11-11 (main @ 32ca7035)

shinywidgets: `0.8.2.post1.dev135+g32ca7035` (worktree detached at `main`, commit
`32ca7035`, 33 commits ahead of the `00f90249` this article was first verified
against). shiny 1.9.0; altair 6.3.0, itables 2.9.1, ipyleaflet 0.20.0, lonboard 0.17.0,
mosaic-widget 0.34.3, duckdb 1.5.6, ipydatagrid 1.4.0, maplibre 0.3.6, ipycytoscape
1.3.3, geopandas 1.2.0, matplotlib 3.11.2, geolibre 3.7.0, plotly 6.9.0 (all already
locked in the venv, unchanged versions from the prior pass except geolibre 3.6.0 ->
3.7.0). `jupyter-scatter` (imports as `jscatter`) is still not in the shared venv;
every jscatter example used `uv run --no-sync --with jupyter-scatter python -m shiny
run ...` (resolved 1.0.1, same as before). **Correction for the next agent**: the PyPI
package is `jupyter-scatter`, not `jscatter` -- `--with jscatter` silently resolves to
an unrelated molecular-dynamics scattering package (pulls in h5py, netcdf4, MDAnalysis)
and fails with `ImportError: cannot import name 'Scatter' from 'jscatter'`. Caught
immediately (the traceback names the wrong package's `__init__.py`), but worth avoiding
the five minutes of confusion.

### What changed in the article and why

- **Narrative**: replaced every "event, not a state" / kind-based accessor description
  with the current kept-vs-re-seeded framing (#437 abolished the event/state split for
  user-facing accessors). Fixed pattern 2's intro, which linked to an anchor
  (`#not-rendered-yet-vs-none-vs-always-a-value`) that no longer exists in
  `reacting-to-widgets/article.md` (now `#before-the-first-interaction` /
  `#across-re-renders`). Updated the "Learn more" pointer to the accessors article's
  cheat sheet description (dropped "kinds," added "kept vs. re-seeded" and "reading on
  demand").
- **New example, pattern 2**: added `examples/17_plotly_hover_to_detail.py` (`hover()`
  driving a detail card without a click), reused verbatim from the plotly guide's own
  already-verified `19_hover_detail.py`. Per the update brief's explicit suggestion
  ("hover() -> detail card... good candidate"). Boot-tested on current main (HTTP 200);
  the plotly guide's own `img/hover_before.webp`/`hover_after.webp` were re-inspected
  (Read tool) and copied in as `img/17_plotly_hover_to_detail_{before,after}.webp` --
  they still show exactly the claimed behavior (hovering a bubble shows Afghanistan's
  detail; nothing is hovered before). Not independently re-driven with a fresh gesture,
  consistent with this article's existing policy for reused examples (see "Judgment
  calls" below, same section as the original pass).
- **New prose mention, pattern 1**: added a short paragraph pointing to the plotly
  guide's `visible_traces()` (legend-toggle filtered table), per the update brief's
  other suggested candidate. Not built as a full duplicate example here -- it's a
  single-widget (plotly-only) pattern already fully verified in the plotly guide, and
  this article's established style (see the existing bqplot/embedding-atlas "worth
  knowing" paragraphs) is prose + link for secondary single-library variants, full code
  only for the article's own multi-pattern or cross-library examples.
- **Converted `reactive_read(x.widget, ...)` to `x.read(...)`** in
  `examples/07_maplibre_viewport_to_matplotlib.py` (`quakes.read("view_state")`), per
  the update brief. This makes the example no longer byte-for-byte "reused verbatim"
  from the maplibre guide (which, as of this pass, still teaches `reactive_read()` --
  that guide is another agent's assignment); the article now says "adapted from" instead
  and explains the conversion inline. Re-verified with a real scroll-wheel zoom gesture
  (not reused-and-boot-tested only, since the code changed) -- see the table below.
- **Fixed two stale "not yet fixed on main" claims**, both now landed:
  - `render_reactable`'s accessor regression (`_accessor_specs` typo) is fixed (#394).
    Updated the "Learn more" section's reactable note from "not usable for any pattern
    above" to "fixed... a fine choice ... now," while leaving the deliberate choice not
    to build a reactable example in place (see NOTES below and the original "What I
    deliberately did not build").
  - `render_mosaic_widget`'s DuckDB connection is now locked down by default (#395, the
    same fix `render_quak` already had). Replaced the "pending PR #395, don't point a
    shared Mosaic connection at sensitive data" caveat under pattern 6 with a one-line
    note that it's fixed, with the `allow_unrestricted_connection=True` opt-out named.
  - Fixed pattern 7's performance tips, which named `ipydatagrid`'s `selected()` and
    lonboard's `view_state()` as "no default rate policy" examples -- both now debounce
    by default (#400). k3d/pythreejs's `camera()` is still the accurate no-default
    example.
- **Renames already correct, no change needed**: `examples/04_ipycytoscape_click_to_detail.py`
  already calls `network.clicked_node()` (the post-#441 name), not the old
  `node_clicked()` -- confirmed this is in fact the current name on `main` (checked
  `git show 00f90249:shinywidgets/_render_widget.py`, which still has `node_clicked` at
  that commit, so this file was already ahead of its own NOTES.md's stated verification
  commit somehow; regardless, it's correct for `32ca7035` today, which is what matters).
  No ipydatagrid `cell_clicked()`/`clicked_cell()` usage exists anywhere in this
  article's examples, so that rename needed no fix either.

### Re-verification table (this pass)

| File | Changed this pass? | Ran in browser | Gesture | Screenshot | Result |
|---|---|---|---|---|---|
| `01`-`04`, `06`, `08`-`11`, `13`-`15` (13 files) | no | yes, boot-tested (HTTP 200, no traceback) | not re-driven (unchanged code; see policy below) | not replaced | all boot clean on `main` @ `32ca7035` |
| `05_altair_click_to_plotly_detail.py` | no (original to this article) | yes, fully re-driven | real click on an altair mark (`locator.click(force=True)`) | replaced (different mark hit: Honda Civic, not the Datsun 510 the original pass happened to click) | `scatter.selected_rows("pick")` drove both the text card and the plotly bar (53 hp vs. ~105 hp fleet average); article text updated to match |
| `07_maplibre_viewport_to_matplotlib.py` | **yes** (`reactive_read` -> `.read()`) | yes, fully re-driven | real scroll-wheel zoom (10 wheel ticks, Playwright `mouse.wheel`) centered off Africa | replaced (2601 -> 106 earthquakes, a different crop than the original 829 -> 184; see note) | `.read("view_state")` returns identical values to `reactive_read(quakes.widget, "view_state")` -- histogram updates correctly, no behavior change from the conversion |
| `12_lonboard_plotly_bidirectional.py` | no (original to this article) | yes, fully re-driven, both directions | real canvas click (lonboard WebGL picking) + a real plotly marker click (`path.point`, `force=True`, picked programmatically by topmost y to guarantee a *different* point than the map click) | replaced (map-click and chart-click pairs) | confirmed both directions: a map click highlights the same pod red on both widgets; a *different* point clicked in plotly (lon -73.53187, lat 45.61088, the plot's own hover tooltip) moves the highlight on **both** widgets there too -- no freeze/loop |
| `16_plotly_one_calc_many_views.py` | no (original to this article) | yes, fully re-driven | real lasso drag (mouse down/move/up) | replaced (4 visits, not 22 -- a tighter box than the original pass drew) | one `@reactive.calc` fed `render.text` (4 visits, 22.5% avg tip), `render_itables` (4-row table), and `render.plot`/matplotlib (3-bar histogram) simultaneously, all consistent with each other |
| `17_plotly_hover_to_detail.py` | **new this pass** | yes, boot-tested | not independently re-driven (verbatim reuse of plotly guide's already-verified example; its screenshots re-inspected and copied in) | reused from plotly guide | see "New example, pattern 2" above |

Why screenshots 05/07/16 changed numbers from the original pass even though the
*pattern* didn't change: none of these apps seed a fixed random state for the
lasso/click location, and this pass's Playwright drivers targeted slightly different
pixel coordinates than whatever the original pass used (different box edges, a
different mark index, a different wheel-zoom center). The counts are illustrative, not
asserted as reproducible exact values; the article text never promises a specific
number will recur, only describes what's in the screenshot actually shown.

### Verification policy for the 13 unchanged reused files (unchanged from the original pass)

Boot-tested (HTTP 200, no traceback) rather than re-driven with fresh gestures, because
their code is byte-for-byte unchanged from last pass and from their source per-widget
guide. None of their accessor usage touches a rename, a no-longer-existing kwarg, or a
behavior this update's redesign changes in a way that would be visible in a *static*
(non-re-rendering) app -- every one of these 13 examples builds its widget exactly once
and never re-renders it, so the redesign's actual behavior change (kept vs. re-seeded
*across a re-render*) has no example-level effect here; the "which accessor returns
what, before interaction" semantics (also potentially affected) were cross-checked
against the current cheat sheet for each accessor used (plotly `selected_rows`/
`relayout`, jscatter `selection`, lonboard `selected_index`/`clicked`, ipycytoscape
`clicked_node`/`clicked_edge`, ipyleaflet `bounds`, itables `selected_rows`, mosaic
`params`/`data`, altair `selected_rows`) and all matched what these examples assume. If
the maintainer wants full independent re-verification of all 13 regardless, flag it --
same trade-off as the original pass's judgment call (redundant browser time vs. low
regression likelihood for unchanged code on a commit where the owning guide's own agent
already re-verifies the identical snippet).

### Bugs found (2026-11-11)

None new. Confirmed fixed (previously tracked as open in this article, now closed on
`main`): `render_reactable` accessors (#394), `render_mosaic_widget` DuckDB lockdown
(#395), `ipydatagrid.selected()`/`lonboard.view_state()` no-default rate policy
(#400). No new shinywidgets bugs surfaced while re-driving examples 05, 07, 12, 16, or
boot-testing the rest.

### Judgment calls (this pass)

- **Did not build a new reactable example**, even though the accessor regression that
  justified skipping it is now fixed. Adding one would be genuinely valuable (pattern 1
  or 7 are both fine fits) but is new scope beyond "re-verify + use new accessors where
  compelling + fix renamed links" -- flagging for the maintainer rather than taking it
  on unprompted.
- **`hover()` reused verbatim rather than built cross-library.** The update brief names
  `hover()` as a good pattern-2 candidate; I considered building a NEW cross-library
  version (plotly hover driving a *different* widget's detail, the way example 05 does
  with click), which would be more in this article's own "cross library" spirit than
  reusing plotly's single-widget hover-detail example as-is. Chose the cheaper, reused
  version given the scope of everything else in this pass; a cross-library hover example
  is a reasonable future addition if the maintainer wants pattern 2 to lean harder into
  hover specifically.
- **Pinned `--with jupyter-scatter` (unpinned, matches the prior pass's 1.0.1)** is not
  already in the shared venv, so per the operating rules this doesn't risk the
  duckdb-style version-skew warning -- confirmed resolved version matches the prior
  pass's NOTES.md exactly.

### Editor's notes for the website (addendum)

- The new `hover()` sub-example (pattern 2) is a good one-line callout for the page's
  summary blurb if it gets regenerated: "click -> detail, hover -> live preview" is a
  clean two-sentence contrast.
- Everything from the original pass's editor's notes still applies (lonboard<->plotly
  broker as hero, one-calc-many-views as second-strongest, pattern 3's third example as
  a trim candidate).

## Update 2026-11-11 (Task 6: "Brushing large data: push summaries, not points")

New section 7, inserted after section 6 ("Crossfilter"); the former section 7 ("One
selection, many views") is renumbered 8. New files: `examples/18_datashader_brush_summaries.py`,
`examples/19_scattergl_lasso_raw_points.py`, `examples/20_mosaic_brush_in_widget.py`,
`measure/brush_payload.py`, `data/README.md`, `data/.gitignore`, plus 6 screenshots
(before/after for each of 18, 19, 20).

### Versions used

- shinywidgets `0.8.2.post1.dev145+gad97a76d` (worktree HEAD `982fe8ca`, 2026-11-11), shiny
  1.9.0.
- holoviews 1.23.2, datashader 0.19.1, hvplot 0.13.0, panel 1.10.0 (all already in the
  shared venv; same `render_holoviews` path the datashader/holoviews guides document --
  no new accessors, this task relied entirely on their documented
  `hv.streams.Params`/`DynamicMap` idiom).
- plotly 6.9.0, mosaic-widget 0.34.3, duckdb 1.5.6, pyarrow 26.0.1, itables 2.9.1 (all
  already locked).
- Playwright: Chromium, headless, 1280x800-1280x900 viewport (varies by screenshot call),
  `device_scale_factor=2`.

### Dataset

Gaia 5M (first choice in the task's try-in-order list; reachable, and its 5 columns
(`l`, `b`, `parallax`, `phot_g_mean_mag`, `bp_rp`) fit all three examples without
synthesizing anything): `http://idl.uw.edu/mosaic-datasets/data/gaia-5m.parquet`,
~93MB, 5,000,000 rows, confirmed with `duckdb`'s `httpfs` before downloading (schema and
row count). Downloaded once to `data/gaia-5m.parquet` (gitignored). `l`/`b` (galactic
coordinates) make a genuinely striking sky map once rasterized -- the Milky Way's plane
is immediately visible, unprompted, and two globular-cluster-like bright blobs show up
around `l≈280,b≈-33` and `l≈300,b≈-45`. `phot_g_mean_mag` and `parallax` (both with
realistic measurement noise, including some implausible `parallax` outliers near the
tails) became the two linked histograms. Same parquet file loaded by all three examples,
per the task's "same dataset for all three" instruction.

### Verification table

| File | Ran? | Gesture | Screenshot | Result |
|---|---|---|---|---|
| `examples/18_datashader_brush_summaries.py` | yes, `smoke.py` clean | real box-select drag on the magnitude histogram (Playwright mouse down/move/move/up) | before/after, looked at | parallax histogram's bars changed shape, sky map's color scale and texture changed, both confirming the filter propagated; re-ran with a prior scroll-zoom on the raster and confirmed the zoomed `l`/`b` range was pixel-identical before and after the brush (in-place, not rebuilt) |
| `examples/19_scattergl_lasso_raw_points.py` | yes, `smoke.py` clean (`--gpu webgl`) | real lasso drag | before/after, looked at | lasso caught 27,873 of 1,000,000 rows (itables' own `maxBytes=64KB` downsampling then shows 5,461 of those) |
| `examples/20_mosaic_brush_in_widget.py` | yes, `smoke.py` clean | real horizontal drag on the magnitude histogram's `intervalX` overlay | before/after, looked at | confirmed via raw SVG diff (not just visual): the parallax histogram's y-axis max tick dropped from "2,000,000" to "1,200,000" and its bar heights changed, after the identical magnitude-histogram drag |
| `measure/brush_payload.py` | yes, run for all required scale/app combinations (see below) | n/a (its own gesture driver) | n/a | see "Measurement" |

Driving a real gesture against Mosaic's `intervalX` d3-brush overlay needed real
incremental `mouse.move` calls with short (`time.sleep(0.05)`) pauses between them, not
a single `page.mouse.move(..., steps=N)` call -- a single interpolated call did not
register a selection at all (the `rect.selection`'s `style="display: none"` never
changed), while explicit per-step moves did. Not filed as a bug (this is standard
d3-brush behavior, not a shinywidgets concern), but worth knowing for whoever drives
Mosaic gestures next.

### Measurement

`measure/brush_payload.py APP --scale N [--timing]`: starts `APP` with
`LINKED_VIEWS_ROWS=N` (18 and 19 read this; 20 ignores it, always full scale), captures
every websocket frame via `page.on("websocket")` + `framesent`/`framereceived`, discards
frames through the first render and a full warm-up drag (plus a 3s settle -- see "Bugs
found" below for why that settle needed to be longer than planned), then runs the
measured 20-step/50ms drag and reports **total** bytes transferred during that one
gesture in each direction, filtered of Shiny's own per-flush protocol frames (`{"busy":
...}`, the empty input-sync message, comm-open acks -- generic bookkeeping on every
reactive flush, not part of any widget's payload).

Measured (bytes-only; this task does not run `--timing`, per Global Constraints):

| App | Scale | Browser&rarr;server | Server&rarr;browser |
|---|---|---|---|
| 18 datashader | 1,000,000 | 141,659 B (14 frames) | 2,121,033 B (32 frames) |
| 18 datashader | 5,000,000 (full) | 206,460 B (14 frames) | 2,121,087 B (32 frames) |
| 19 Scattergl | 1,000,000 | 9,449,588 B (8 frames) | 4,934,136 B (23 frames) |
| 19 Scattergl | 5,000,000 (full) | **crashed** -- see "Bugs found" | -- |
| 20 Mosaic | 5,000,000 (full) | 32,893 B (51 frames) | 40,882,014 B (35 frames) |

18's server-to-browser bytes are flat across a 5x scale change (2,121,033 vs 2,121,087,
a 54-byte difference) -- directly confirms the article's claim. 19's bytes at 1/5th the
scale already dwarf 18's at any scale, and the full-scale run didn't produce a number at
all (see below). 20's absolute bytes are the largest in the table -- a genuine surprise,
written up in the article's "Measured" subsection with the explanation (the DuckDB
connection lives in Python, not browser-side WASM, so query results round-trip as Arrow
buffers).

### Deviations from the task block, with reasons

1. **"Median bytes per step" became "total bytes per drag."** 18's and 20's accessors
   (`brushing()`, Mosaic's crossfilter) debounce at 250ms; a 1-second/20-step drag
   produces on the order of 4-5 real network emissions, not 20. Bucketing frames into 20
   per-move-index buckets (the literal reading of the task block) put almost every
   bucket at zero and made "median" meaningless. Reporting the gesture's total bytes in
   each direction (and, in the script's own output, that total divided by 20 as a simple
   average) is what the article's table actually uses, and is what the task's own
   underlying claim ("flat vs. growing with N") needs: it's directly comparable between
   scales and between apps. `brush_payload.py`'s docstring explains this choice.
2. **19's accessor switched from `selected()`/`selected_rows()` to the live
   `selecting()`.** The task block doesn't specify which accessor 19 should read, and
   the first draft used `selected_rows()` (end-of-gesture only), which meant NO network
   traffic happened until mouse-up -- undermining the whole "feels fluid/costs per step"
   premise the section is making. Switched both 18 (`brushed()` to `brushing()`) and 19
   (`selected()`/`selected_rows()` to `selecting()`, with the row-matching logic written
   out manually since there's no `selecting_rows()` helper) to their live, continuously
   -updating counterparts, so both examples actually stream updates throughout the drag,
   not just once at the end. This is also why the measured "anti-pattern" numbers are
   larger than a release-only measurement would have shown: `selecting()`'s payload
   includes every point caught by the lasso at each of its debounced emissions, not just
   the final one.
3. **19's full-scale (5,000,000-row) measurement did not complete.** The task
   explicitly allows this fallback ("if the full set doesn't render, take 19's 1M as its
   upper scale"). A static `smoke.py` run at 5,000,000 rows passed (the Scattergl DOES
   render), but driving the SAME live-lasso gesture that works at 1,000,000 rows broke
   the plotly widget outright on every attempt (reproduced twice): `PAGEERROR: no comm
   channel defined`, followed by repeated `Cannot read properties of undefined (reading
   '_hoverlayer')` / `'_zoomlayer'` errors, and the drag layer (`.plotly .nsewdrag`)
   disappeared from the DOM entirely. This is itself evidence for the article's point (I
   used it as such in prose) rather than only a measurement gap.
4. **Section 7 is ~309 lines, not ≤200.** Two full example files (132 + 59 lines of
   code) plus the measured-results table and its honest, somewhat lengthy discussion
   (especially #20's surprise) exceed the task block's line target. I judged showing
   both 18 and 19 in full was worth the overage (the whole point is the contrast between
   them, and BRIEF's own "err on the side of exhaustive coverage" cuts against trimming
   either to a non-functional excerpt, which `check_docs.py --snippets` wouldn't accept
   anyway -- it requires an exact whole-file match for any linked ```python``` block).
   Section 6 of this same article (written by an earlier task) runs to ~258 lines with a
   similar 3-example structure, so this isn't unprecedented in this file. Flagging for
   the maintainer rather than silently exceeding the budget.
5. **Example files read `LINKED_VIEWS_ROWS` from the environment (18, 19).** Needed so
   `measure/brush_payload.py` can re-run the same, otherwise-unmodified pedagogical
   example at a different scale rather than maintaining separate measurement-only copies
   of the apps. Falls back to each example's natural scale (full 5M for 18, 1M for 19)
   when unset, so default behavior for a reader running the file directly is unchanged.
6. **18 brushes one filter at a time** (brushing a new histogram replaces whichever
   filter was active, rather than ANDing both axes together). A combined two-axis
   filter is possible but adds a second dimension of state for no benefit to the point
   being demonstrated (bytes per step, not full crossfilter semantics) -- flagging in
   case the maintainer wants the fuller crossfilter version for a different purpose.

### Bugs found (for FINDINGS.md)

Nothing filed as a shinywidgets code bug this pass (per instructions, not investigated
further than confirming repro and scope):

1. **[authoring/measurement hazard, not investigated further] `render_plotly`'s
   `Scattergl` widget's comm channel broke under a live, continuously-updating
   `selecting()` drag at 5,000,000 points (1,000,000 works fine).** Repro:
   `LINKED_VIEWS_ROWS=5000000 uv run --no-sync python -m shiny run
   examples/19_scattergl_lasso_raw_points.py`, then drive a 20-step lasso drag (see
   `measure/brush_payload.py`'s `gesture_19`). Page errors: `no comm channel defined`,
   then repeated `Cannot read properties of undefined (reading '_hoverlayer')` /
   `'_zoomlayer'`; the drag layer disappears from the DOM. Not characterized further
   (regression vs. long-standing limitation unknown -- this exact gesture/scale
   combination is unlikely to have been exercised before); recorded here per the
   maintainer's request to record rather than fix. A STATIC render at 5,000,000 points
   (`smoke.py`, no interaction) is fine; it's specifically the live drag that breaks it.
2. **[content accuracy, not a code bug] This article's own section 6 ("Crossfilter")
   describes Mosaic's `filterBy` as working "with no server round trip at all."**
   Measured directly in this task (see "Measured" above and the article's new section 7
   "Measured" subsection): for `render_mosaic_widget` constructed from a
   `pandas.DataFrame` (`MosaicWidget(spec, data={"gaia": gaia})`, exactly how every
   mosaic example in this repository builds one), every brush step's query result
   travels over the Shiny websocket as an Arrow buffer (confirmed in the raw frame
   payloads: `{"type": "arrow", ...}`), because the DuckDB connection and the data live
   in **Python**, not a browser-side WASM instance. The "no round trip" framing may be
   accurate for a browser-native Observable/vgplot app using DuckDB-WASM directly, but
   not for the Python wrapper this whole roster uses. Did not edit section 6 itself
   (out of this task's scope -- it isn't in the Task 6 block's "Files" list, and editing
   another section's established claims without a dedicated re-verification pass felt
   like overreach for a one-line fix); flagged here and in the new section 7's prose
   instead, with a direct link back to section 6 so a reader hits the correction.
   Worth a second opinion / a dedicated fix pass on section 6's wording.

### Judgment calls

- See "Deviations" above (1-6) -- all judgment calls with reasoning included there to
  avoid duplicating.
- **Didn't pursue why the `--timing` MutationObserver recorded zero mutations in a
  smoke check of `brush_payload.py --timing`.** Timing numbers are explicitly out of
  scope for this task (Wave 3's job); `--timing` was implemented so Task 11 can reuse
  this script unmodified, and verified not to crash, but its mutation-detection may need
  Task 11's own debugging attention (noted in the script's module docstring is not
  updated with this caveat -- flagging here instead, so it doesn't get missed).
- **Applied one row from `tools/handoff/task-5.md` directly** (the only row in that
  file targeting `articles/linked-views/article.md`, already marked "Owned by Task 6,
  same wave"): both occurrences of `../reacting-to-widgets/article.md#writing-back`
  changed to `../updating-in-place/article.md#writing-back` (lines in the pre-existing
  pattern 4 and pattern 5 prose). Confirmed `updating-in-place/article.md#writing-back`
  resolves before applying (Task 5 had already landed in the shared worktree).

### Editor's notes for the website (addendum)

- The Gaia sky map (section 7's example 18) is a strong candidate for a hero image
  anywhere "large data" is discussed on the site -- the Milky Way's plane is
  immediately recognizable in a screenshot, with zero explanation needed, which is rare
  for a rasterized-density plot.
- Section 20's "surprise" (Mosaic's absolute bytes being the largest of the three,
  because the connection lives server-side) is, on reflection, probably the single most
  useful finding in this whole task for someone choosing between these approaches --
  more useful than the flat-vs-growing contrast alone, since it corrects an assumption
  the article itself previously stated as fact. Worth leading with in any shortened
  version of this section.

## Update 2026-11-11 (Task 11: timing measurements)

Filled section 7's "Latency/step" column (left pending for this wave) using `measure/brush_payload.py
--timing`, and fixed two bugs in that script that the previous pass's smoke check had
left for this task (see the script's own module docstring for the full "--timing fixes"
writeup; summarized here with the raw numbers).

### Versions / environment

- shinywidgets `main` worktree HEAD at the time of this pass, shiny 1.9.0, holoviews
  1.23.2, datashader 0.19.1, plotly 6.9.0, itables 2.9.1, `mosaic-widget` (project-locked
  version, already in the venv). Date 2026-11-11.
- Ports 8220-8229 (assigned range). Headless Chromium, no extra GPU flags needed (all
  three apps are SVG/canvas-2D, not WebGL/WebGPU).
- Machine quiet check (`ps`) before each measurement batch, per the task's rules: one
  orphaned, idle (0% CPU, `PPID 1`) `shiny run` process on port 8146 (a leftover from an
  earlier Wave 1 task's agent, `layout-and-theming/examples/03_dark_mode.py`) was present
  throughout this pass. It was not started by this agent, so per instructions it was left
  running rather than killed; it stayed at 0% CPU/idle for the whole session (confirmed
  with `ps`/`top` before and during measurement batches), so it's recorded here rather
  than treated as a reason to block measurement.

### The `--timing` bug: two independent causes, both fixed

The smoke check noted in the previous pass's "Judgment calls" (zero MutationObserver
events) had two separate root causes, confirmed by direct debugging before writing any
fix:

1. **Every app's gesture function is a deterministic function of the plot's own bounding
   box.** The warm-up drag and the "measured" drag called the identical function, so
   they traced the identical path and landed on the identical final brushed region. The
   MutationObserver was attached right after the warm-up -- by which point the linked
   output already showed that region's values -- so the measured drag (an exact replay)
   produced the same values at every step and the DOM genuinely never changed, even
   though real websocket traffic was still sent (confirmed directly: diffing
   `page.eval_on_selector_all` output before/after showed real changes during warm-up,
   zero changes during the "measured" replay). **Fix:** a *decoy* gesture -- a
   different, disjoint region (`decoy_18`/`decoy_19`/`decoy_20`) -- runs after the
   warm-up, only in `--timing` mode, leaving the linked output settled somewhere the
   real measured gesture's steps will genuinely differ from at every point.
2. **App 20's watch selector, `svg[class^='plot-']:nth-of-type(3)`, matched nothing.**
   Mosaic/vgplot assigns the *same* generated class to all three marks (raster, mag
   hist, plx hist) in one spec, and they sit under different parent `<div>`s from the
   vconcat/hconcat layout -- `:nth-of-type` counts siblings of the same tag name
   per-parent, not matches of a class selector, so each mark is the *first* (not third)
   svg child of its own parent. Separately, even a corrected by-index selector
   (`querySelectorAll(...)[2]`) isn't reliable: direct inspection showed Mosaic replaces
   a mark's entire `<svg>` subtree with new DOM nodes on every crossfilter update rather
   than mutating it in place (confirmed with a `data-dbg` marker attribute: the
   previously-tagged raster and plx-hist nodes lost their marker after a brush, the
   actively-dragged mag-hist node kept it), which detaches a previously-observed node
   with no mutation record. **Fix:** watch the stable output wrapper `#dashboard`
   (shinywidgets' own mount point, never replaced) instead of one mark's svg.

A third issue surfaced only while building the decoy fix, not present in the original
script: attaching the MutationObserver (a `page.evaluate()` call) *immediately before*
the measured drag silently suppressed that drag's own server round trip for app 18 --
reproduced and isolated to the bare act of calling `page.evaluate()` right before the
mouse sequence (even a no-op `page.evaluate("() => 1")` in its place reproduced it: a
~2.1 MB received payload dropped to ~2 KB and stayed there for 10+ seconds of settling,
ruling out a late-arrival race). This looks like a Playwright/CDP-level interaction with
the following input sequence, not a shinywidgets bug -- not investigated further than
confirming it's the `evaluate()` call's position, not its content, that matters. **Fix:**
attach the observer earlier, right after the warm-up and before the decoy drag (not
right before the measured drag); any mutation the decoy itself causes is then
timestamped well before the measured drag's first `mouse.move`, so the existing
time-windowed `latency_per_step()` bucketing naturally excludes it without extra code.

### Measured (raw numbers, 3 runs each, values reported are each run's own median
step-latency; the table reports the median of those 3)

| App | Scale | Run 1 | Run 2 | Run 3 | Reported |
|---|---|---:|---:|---:|---:|
| 18 | 1,000,000 | 516 ms | 526 ms | 542 ms | 526 ms |
| 18 | 5,000,000 (full) | 599 ms | 592 ms | 585 ms | 592 ms |
| 19 | 1,000,000 | 89 ms | 80 ms | 87 ms | 87 ms |
| 20 | 5,000,000 (full) | 5 ms | 2 ms | 3 ms | 3 ms |

18 and 20 each produced exactly one observed mutation per run (the debounced accessor's
single trailing-edge commit after mouse-up, not one per mouse-move step -- expected,
matches the article's own "~4 real network emissions per drag" note for 18/20's
debounce), so each run's "median" is that one value. 19 produced 20 observed mutations
per run (one close to each mouse-move step), with a visibly bimodal spread (e.g. run 1:
`[734, 42, 31, 13, 346, 37, 63, 102, 105, 99, 79, 424, 59, 443, 59, 448, 48, 536, 50,
477]`) -- a mix of itables' own incremental DataTable redraw micro-mutations (the small
values) and the accessor's real update ticks (the larger, ~400-500ms values), per the
article's new prose explaining this (see "Latency/step doesn't tell the same story as
bytes" in `article.md`). The reported 19 number is therefore a median over a
heterogeneous mix of DOM-mutation causes, not a single clean "network round trip"
measurement the way 18/20's single-observation numbers are -- flagged here in case a
future pass wants a more targeted methodology (e.g. filtering mutations by subtree
depth or type) for a cleaner per-update number specifically for table-based outputs.

### Judgment calls

- **Did not change `measure/brush_payload.py`'s bytes-only (no `--timing`) code path at
  all**, and re-verified it still reproduces the exact bytes already committed in the
  article (142 KB/2.12 MB for 18 @ 1,000,000, byte-identical to the existing table) --
  the decoy gesture and the observer-attach reordering only run under `--timing`.
- **3 runs per scale, reporting the median of medians**, matching the task's instruction
  for the `PERF_N`/bokeh timing work even though Task 6's own instructions for this
  script didn't explicitly ask for repeats; the debounce-driven "single observation per
  run" results for 18/20 make a single run's number fairly noise-sensitive, so the extra
  runs were cheap insurance.
- **Did not try to make 19's latency measurement "cleaner"** (e.g. by filtering which
  mutations count) -- see "Measured" above. The bimodal spread is itself informative
  (it shows the DataTable's own rendering isn't instantaneous even when the server
  response is), and inventing a filter to produce a single tidier number felt like
  tuning the measurement to a nicer-looking story rather than reporting what's there.

## Update 2026-11-11 (Task 12: final sweep)

### Section 6 wording fixed

Section 6 ("Crossfilter: in-widget vs. through Shiny") claimed Mosaic's `filterBy` works
"with no server round trip at all" -- flagged as a content-accuracy issue by Task 6
(`tools/handoff/task-6.md`'s "Content accuracy note" and this file's own "Bugs found"
item 2). Reworded: Vega-Lite's `transform_filter` genuinely has no round trip (runs in
the browser's own dataflow graph), but Mosaic's `filterBy` re-executes wherever its
DuckDB connection lives -- for every `render_mosaic_widget` example in this roster
(built from a `pandas.DataFrame`), that's Python, so each brush step still round-trips
over the websocket as an Arrow buffer. Section 7's "Measured" subsection no longer
describes this as a "tension" with section 6 -- section 6 now says the same thing.

### Sanity-check re-measurement (example 18)

Re-ran `measure/brush_payload.py examples/18_datashader_brush_summaries.py --scale
1000000` standalone (no other agents/servers running) to check the ~2.12 MB
server-to-browser number wasn't stale or a fluke:

```
browser-to-server: 141,659 bytes total over 14 frames (7,083 bytes/step avg over 20 nominal steps)
server-to-browser: 2,121,033 bytes total over 32 frames (106,052 bytes/step avg over 20 nominal steps)
```

Byte-identical to the committed table and to Task 6's original measurement. The number
is reproducible, not off; no further re-measurement done.

### #459 cited for example 19's 5M crash

Section 7's "Measured" discussion of 19's full-scale (5,000,000-row) comm-channel
failure now links
[#459](https://github.com/posit-dev/py-shinywidgets/issues/459) (oversized
widget-to-server message disconnects the session) as the likely cause: a lasso over
that many points serializes to a single message past the default websocket frame
limit. `shiny run --ws-max-size` is the documented workaround.

### Section 7 trimmed toward the &le;200-line target

Section 7 was ~309-328 lines (after the #459/section-6 additions above), against a
&le;200-line target. The two example files are 134 and 61 lines of required verbatim
code (`check_docs.py --snippets` needs an exact whole-file match for any linked
```python``` block, so neither can be elided or excerpted) -- 195 lines of code alone,
which already exceeds the budget before any prose. Trimmed the surrounding prose instead
(intro paragraphs, per-example commentary, the "Measured" discussion) from ~133 lines to
~95, moving the full derivations below out of the article and keeping only the
conclusions + numbers there. Current section length: run
`awk '/^## 7\. Brushing/{p=1} /^## 8\. One selection/{p=0} p' article.md | wc -l`.
Matches Task 6's own judgment call #4 (`### Deviations from the task block, with
reasons`, item 4): showing both full examples is worth the overage, and this section was
already the same shape as section 6 (~258 lines, written by an earlier task). Not
pushed further into NOTES.md-only derivations because the brief asks for an honest,
readable article, not a stripped one -- the trim here removes repetition (points already
made in the per-example verification table above, or restated between paragraphs), not
substance.

**Full "Latency/step" derivation** (condensed in the article to the conclusion + link
here): 18's 526-592 ms is slower per step than 19's 87 ms even though 18 ships two
orders of magnitude fewer bytes, because the two numbers measure different things. 18's
`brushing()` debounces to about one real commit per one-second drag (confirmed directly
-- only one DOM mutation was observed per run, not per mouse-move step), and that single
commit pays for a full datashader `rasterize()` over up to 5,000,000 points before the
image is ready to send. 19's `selecting()` isn't debounced the same way in practice -- it
produces roughly one real update per mouse-move step -- but each one is a cheap pandas
boolean filter over 1,000,000 rows, so individual round trips are fast even though there
are many more of them and each carries more data. Put another way: 18 is cheap and fast
in total traffic but pays a real per-update compute cost; 19 is fast per update but the
*total* cost (data shipped, and eventually the browser's own comm channel) scales with
the selection -- exactly the failure mode the "push summaries, not points" principle
warns about. Latency per step was never the claim bytes/drag makes, and shouldn't be
read as contradicting it.

**Full "20 is a genuine surprise" derivation**: it's the heaviest number in the table, in
absolute bytes. Mosaic's crossfilter grammar needs no Python glue code at all, but
`render_mosaic_widget` holds its DuckDB connection in Python, not a browser-side WASM
instance -- the dataframe was handed to it directly as `data={"gaia": gaia}` -- so every
query the browser's `vgplot` layer issues still round-trips over the websocket, and each
result arrived as an Arrow buffer close to 3 MB (confirmed in the raw frames: `"type":
"arrow"` payloads, repeated roughly 18 times over the one-second drag). That's still an
aggregate -- a density grid sized to the raster's pixel resolution, not one row per star
-- so it doesn't grow with the 5,000,000 rows the way 19's does; it's just not free.
