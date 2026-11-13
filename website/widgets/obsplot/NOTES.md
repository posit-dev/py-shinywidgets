# NOTES: obsplot guide

## Versions

- Date: 2026-11-02
- shinywidgets: `main` at commit `00f90249` (worktree detached at this commit; the brief's PRs #394/#395/#398 are
  not merged into it)
- pyobsplot: 0.5.4
- shiny: 1.9.0
- itables: 2.9.1
- plotly: 6.9.0
- Python 3.12, venv at `scratchpad/main-wt/.venv` synced with all groups

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | penguins scatter, tip shorthand |
| `examples/02_histogram.py` | yes | yes | n/a (static) | binX/rectY, stacked by continent |
| `examples/03_facets.py` | yes | yes | n/a (static) | implicit fx facet |
| `examples/04_groupY_bars.py` | yes | yes (2 iterations) | n/a (static) | found+fixed a label-clipping bug, see Bugs |
| `examples/05_dodge_beeswarm.py` | yes | yes | n/a (static) | |
| `examples/06_hexbin.py` | yes | yes | n/a (static) | |
| `examples/07_tip.py` | yes | yes, before/after | yes -- real `.hover(force=True)` on a `<circle>` | tip card with custom `channels` verified to show Species/Island/Sex |
| `examples/08_select_input_spec.py` | yes | yes, before/after | yes -- `select_option(label=...)` | verified spec swap to density contours |
| `examples/09_inplace_vs_rerender.py` | yes | yes, 3 shots | yes -- real `.click()` on both buttons | found+fixed an infinite-reactive-loop bug in my own example (see Bugs: shinywidgets-guide); render counter confirmed 1 -> 1 (recolor) -> 2 (rerender), color confirmed red then reset to black |
| `examples/10_year_slider_bubble.py` | yes | yes, before/after | yes -- real mouse drag on the ion.rangeSlider handle | confirmed chart updates across the full 1952-2007 range |
| `examples/11_lasso_filter_linked.py` | yes | yes, before/after | yes -- real mouse drag (box-select, corner to corner) on the plotly scatter | confirmed histogram narrows to the lassoed cluster's distribution |
| `examples/12_table_row_highlight.py` | yes | yes, before/after | yes -- real `.click()` on a `<tr>` | confirmed ring mark appears on Angola's bubble after selecting its row |
| `gallery/template_penguins_explorer.py` | yes | yes, before/after | yes -- `select_option` + button `.click()` | verified view switch and in-place accent color change |
| `gallery/showcase_gapminder_dashboard.py` | yes | yes, before/after | yes -- slider present; verified via table row `.click()` | simplified from 2 obsplot outputs to 1 after finding the concurrency bug below; verified reliable across 3+ repeated full-process runs after the fix |

No accessors exist on this renderer, so there is nothing in the "every accessor: verified with a real gesture?"
sense to report -- see guide.md's "Reacting to user interaction" section for how that was investigated and
written up.

## Bugs found

### Upstream (pyobsplot)

1. **Filtered pandas DataFrames need `reset_index(drop=True)` or pyobsplot raises `KeyError: 0`.** Root cause:
   `pyobsplot/data.py`'s `pd_to_arrow()` does `col = df[colname].dropna(); ... isinstance(col[0], date)` for every
   column, unconditionally positional-looking-like but actually *label*-indexing position 0. Any DataFrame whose
   index doesn't contain label `0` (the normal result of boolean filtering, `.query()`, or a lasso/table
   selection) throws. Verified directly with a minimal repro (`gapminder[gapminder['year']==2007]` -> `Plot.dot()`
   -> `KeyError: 0`), and found it a second time live during this investigation: the gallery showcase's
   highlight-row mark crashed the whole bubble chart output with `Error: 0` the first time I exercised the
   row-selection gesture, because I'd forgotten the same `reset_index(drop=True)` fix in that one spot. Fixed in
   `gallery/showcase_gapminder_dashboard.py`. This is already mentioned (tersely) in the current docstring/CHANGELOG
   ("filtered pandas DataFrames need `df.reset_index(drop=True)`"), so it's a known, not new, upstream limitation --
   but it's easy to hit and worth the guide's prominent callout, since reactively filtering a DataFrame is one of
   the most common things a Shiny app does.
2. **Two `render_obsplot` outputs on one page intermittently cross-contaminate scales on first paint.** This is new
   and not documented anywhere I found. Built a gapminder dashboard with a bubble chart (`y` domain `[20, 85]`
   explicit) and a histogram (`y` left at its default linear 0-based scale) side by side. Across repeated full
   process restarts (fresh `shiny run` + fresh browser each time, not just re-screenshotting the same session):
   sometimes both charts rendered correctly; sometimes the histogram's bins collapsed to 1-2 wide bars and its
   y-axis started at 20 instead of 0 (i.e., it visibly adopted the *other* chart's y-domain); sometimes the bubble
   chart lost its low-lifeExp points instead. A single obsplot chart alone on a page never showed any corruption
   (confirmed across ~10 repeated runs of several single-chart variants). I ruled out, in order: a
   `@reactive.effect`-driven double-render race on startup (`ignore_init=True` didn't fix it; a version with *no*
   effect at all, pure `@render_obsplot` functions reading reactive inputs directly, still showed it); the
   `ui.card(height=...)` parameter; `ui.card_header()`; and the presence of a third `render_itables` widget on the
   page (a 2-obsplot-chart-only page without any table also reproduced it, though less often in my sample than the
   3-widget version). The common factor in every failure was always exactly 2+ `ObsplotWidget` instances
   constructing at nearly the same client-side moment. This smells like shared mutable state in pyobsplot's
   generated JS (possibly in how it evaluates/caches scale configuration) that's supposed to be per-instance but
   isn't under concurrent initialization. I did not dig into pyobsplot's JS source to pin the exact line -- that
   would need a pyobsplot issue/PR, out of scope here. **Workaround used in the guide's gallery**: keep the
   showcase to a single obsplot output (dropped the second histogram panel). I'd recommend flagging this to the
   pyobsplot maintainer with a minimal repro if/when this guide's findings get triaged upstream.

### shinywidgets-guide (my own example code, not shinywidgets or pyobsplot)

3. While writing `examples/09_inplace_vs_rerender.py`, my first draft had `chart()` both read and set the same
   `reactive.value` (`render_count.set(render_count.get() + 1)` with no `reactive.isolate()`), which is a classic
   Shiny self-dependency bug: the read makes `chart()` depend on `render_count`, and the write immediately
   invalidates it again, producing an infinite re-render loop (visible client-side as
   "Shiny server has sent a progress message for chart, but the output is in an unexpected state of: running").
   Fixed with `with reactive.isolate(): render_count.set(...)`. Not a shinywidgets bug -- a generic Shiny gotcha --
   but worth calling out since it's an easy trap for anyone copying a "render counter" pattern.

### Docs

None found specific to `render_obsplot`'s docstring; it reads accurately against current `main` (checked every
claim: the "no sync back to Python" claim, the "other formats return None" claim, the fixed-width/shrink-not-grow
behavior, and the `.widget`/`.value` attributes).

## Judgment calls

- **No accessor reference table.** The brief's skeleton calls for one; since this renderer has zero accessors, I
  replaced that subsection with a short explanation of why, backed by two lines of verification (inspecting the
  widget's traits and grepping the compiled JS for sync calls), plus pointers to the patterns that substitute for
  it (input-driven re-render, pairing with another widget's accessor). I'd flag this as the one section worth a
  second look -- happy to restructure if the website wants a different shape for "renderer has no accessors"
  pages.
- **Dropped the second obsplot panel from the showcase** after finding the two-obsplot concurrency bug (see Bugs
  #2). This was a real trade-off: the original design (bubble chart + histogram + table, all three linked) was
  more impressive, but unreliable. I chose reliability for a maintainer-facing deliverable over a flashier demo;
  happy to revisit if the coordinator wants to keep the richer version with a documented caveat instead.
- **`examples/04_groupY_bars.py` needed real tuning**, not just verification: Plot's default `marginLeft` clipped
  the "Oceania"/"Americas" tick labels against a rotated "continent" axis title in my first draft. I fixed it with
  `"marginLeft": 80, "y": {"label": None}` rather than reporting it as a pure upstream bug, since it's a normal
  "give Plot a bigger margin" tuning step any user would do, not a correctness bug. Documented in a code comment in
  the example itself.
- **Used gapminder (`plotly.express.data.gapminder()`) for most of "What you can build"** rather than pyobsplot's
  own bundled penguins CSV, to get a believable count-per-bin histogram, facets, groupY aggregation, and a
  beeswarm with enough countries to look non-trivial. Penguins is used for the quick start, tip, and the
  dropdown-driven example, where its three-species structure and raw scatter shape fit better. Both are real,
  recognizable public datasets per the brief's data guidance.
- **Hero image** is the quick-start penguins scatter rather than an interaction screenshot, since obsplot's
  headline feature is the grammar/defaults, not interactivity (which this library explicitly doesn't have, from
  Python's perspective). The tip-hover before/after pair is the closest thing to an "interaction" hero and is
  featured prominently in "What you can build" instead.

## What was dropped from an old report

None -- no old report exists for obsplot (`docs/widget-reports/obsplot/` was confirmed empty/absent before
starting). This guide was written entirely from `shinywidgets` source, its tests, `examples/obsplot/`, pyobsplot's
installed source in the worktree venv, and upstream docs.

## Editor's notes for the website

- **Strongest sections**: "What you can build" (six short, visually distinct snippets, each verified) and
  "Coordinating multiple views" (the lasso-select-filters-histogram and table-row-highlights-a-point patterns are
  concrete and screenshot well). The Gotchas section's `reset_index` callout is probably the single most valuable
  sentence in the guide for a working data scientist, since it will bite reactively-filtered Shiny apps constantly.
- **Candidate for cutting if the page runs long**: the `hexbin` and `dodge` subsections could be merged into one
  "other transforms" subsection with two smaller side-by-side images, if the web page wants a shorter "What you can
  build" -- they're the two least load-bearing for teaching the obsplot-in-Shiny integration specifically (as
  opposed to Observable Plot generally).
- The "Reacting to user interaction" section is unusually short for this roster (no accessors), which is expected
  and correctly reflects the library, not a gap in the guide.
- `examples/` directory has 12 files (more than the "4-8 highlights" target for the feature tour, because the brief
  asked for exhaustive coverage and the Reacting/Updating/Coordinating sections each needed their own verified,
  runnable file). All are short (15-55 lines) per the brief's snippet-length guidance.

## Pairs with (for cross-widget articles)

- **plotly**: `examples/11_lasso_filter_linked.py` -- lasso-select in a plotly scatter filters an obsplot
  histogram via `.selected_rows(df)`.
- **itables**: `examples/12_table_row_highlight.py` and `gallery/showcase_gapminder_dashboard.py` -- table row
  selection (`.selected_rows()`) highlights/rings a point in an obsplot chart.

## Update 2026-11-11 (main @ 32ca7035)

### What changed and why

- Renamed the "### Beyond the accessors: reactive_read" heading to "### Beyond the accessors: `.read()`" per the
  brief, and added `.read()` alongside the existing `reactive_read()` mentions in the surrounding prose (the
  "Reacting to user interaction" intro, "Rate limiting", and the matching Gotchas bullet). No example code
  changed: obsplot has zero `reactive_read()` calls anywhere in this guide's `examples/`/`gallery/` -- confirmed
  by grep before and after -- because `ObsplotWidget` declares exactly one trait (`spec`), and it's
  Python-to-browser only (verified in the original pass by grepping the compiled JS bundle for
  `model.save_changes`/`model.set(`: zero matches). There is nothing for `.read()` to read here either, so this
  update is a vocabulary change only, not a behavior change.
- Checked the other items in the brief that might apply (#415 message-delivery timing, #437 accessor redesign):
  neither is relevant. obsplot has no accessors and no custom browser->Python messages; `.widget.spec = ...`
  assignments (used throughout "Updating the widget from Python") are a plain, already-reliable ipywidgets trait
  write, not a queued custom message, so #415 doesn't change anything here either.
- `accessors: []` in the front matter is unchanged (still correct).

### Verification

No browser run needed this pass: every change is a prose/heading edit with no corresponding code change, per
the brief's "text-only edits to `guide.md` need no browser run" rule. No screenshots affected.

### Bugs found (2026-11-11)

None.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example. Reused this guide's existing Gotchas item ("Large datasets mean large messages", Arrow IPC sent in full) and pointed to datashader/jscatter as the siblings for genuinely large data.
