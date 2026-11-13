# NOTES: plotnine guide

## Versions

- plotnine 0.15.8, matplotlib 3.11.2 (via ipympl), ipympl 0.10.0, shiny 1.9.0.
- shinywidgets: checked out at `main` branch `mols2grid-3-widget-port-clean`'s base (commit `f8238de6`, "Port
  render_mols2grid..."), i.e. current `main` as of 2026-10-30, including the reactive-accessors work
  (`_matplotlib.py`, `CLICKED`/`PICKED`/`LIMITS` specs).
- Verified by running every example/gallery app with `uv run --no-sync shiny run ...` against a worktree venv
  synced from the same `main` (`scratchpad/main-wt`), driven with Python Playwright (sync API), Chromium, default
  headless mode (no special GPU flags needed -- ipympl streams PNG frames over the comm, not WebGL).
- Date: 2026-10-30.

## Verification table

| file | ran | screenshot | gesture driven | accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `img/quickstart.webp` | n/a (static) | n/a |
| `examples/02_compositions.py` | yes | `img/compositions.webp` | n/a (static) | n/a |
| `examples/03_facets_relayout.py` | yes | `img/facets_relayout.webp`, `img/facets_relayout_narrow.webp` (viewport resize) | resize | n/a |
| `examples/04_toolbar_zoom.py` | yes | `img/toolbar_zoom_before.webp` / `_after.webp` | toolbar zoom-to-rectangle drag | n/a (no accessor; toolbar only) |
| `examples/05_accessor_clicked.py` | yes | `img/accessor_clicked_before.webp` / `_after.webp` | mouse click | yes -- `clicked()` confirmed via circled point + detail text |
| `examples/06_zoom_tracking.py` | yes | `img/zoom_tracking_before.webp` / `_after.webp` | toolbar zoom-to-rectangle drag | n/a (manual `ax.callbacks.connect`, not an accessor -- that's the point of the section) |
| `examples/07_update_inplace.py` | yes | `img/update_inplace_zoomed.webp`, `img/update_inplace_after_slider.webp` | toolbar zoom (both panels) + slider | n/a |
| `examples/08_pattern_click_facet.py` | yes | `img/pattern_click_facet_before.webp` / `_after.webp` | mouse click inside a facet panel | yes -- `clicked()`, plus facet-lookup via `get_layout_engine().plot.facet.layout.layout` |
| `examples/09_pattern_zoom_linked.py` | yes | `img/pattern_zoom_linked_before.webp` / `_after.webp` | toolbar zoom-to-rectangle drag | n/a (manual zoom tracking driving a second plot) |
| `examples/10_layout_sizing.py` | yes | `img/layout_sizing.webp` | n/a (static) | n/a |
| `gallery/template_click_explorer.py` | yes | `img/gallery_template_click_explorer_before.webp` / `_after.webp` | mouse click | yes -- `clicked()` |
| `gallery/showcase_economics_dashboard.py` | yes | `img/gallery_showcase_economics_before.webp`, `_zoomed.webp`, `_marked.webp`, `_theme.webp` (last two used in guide: `_before`/`_theme`) | toolbar zoom, toolbar-mode toggle, click to mark, theme `<select>` change | yes -- `clicked()` for the mark; manual zoom tracking for the view |

`clicked()` is the only accessor this renderer has, and every exercise above drives it with a real
`page.mouse.click(...)` against the rendered canvas's bounding box, then confirms the Python-side read in a
`@render.text`/`@render.ui` output (not just "no console error").

No gesture was impossible to automate here -- ipympl renders to an ordinary 2D `<canvas>` (PNG frames over the
comm), so regular Playwright mouse events work directly; no `window.widgetManager` trick or special Chromium flags
were needed.

## Bugs found

**shinywidgets / shared infrastructure:**

- **(pre-existing, low severity) Unhelpful error for a duck-typed non-plot.** `as_widget_plotnine`'s coercion
  check is `callable(getattr(x, "draw", None))`, which also matches plotnine objects like `guide_legend()` that
  aren't plots. Verified: `as_widget_plotnine(guide_legend())` raises `AttributeError: 'guide_legend' object has
  no attribute 'key'` from deep inside plotnine's drawing code, instead of a clear `TypeError` naming the actual
  problem. This is the same issue an earlier (pre-accessors) report on this renderer flagged. Not a regression,
  and in practice very unlikely to be hit by accident (a user has to go out of their way to return a guide object
  from a render function). I didn't put this in the guide's Gotchas section -- it's not something a reader of this
  guide will realistically run into, and documenting a confusing-error-message footgun in a teaching doc without a
  code change to point to isn't useful. Flagging here per the brief instead. Fix (not applied): an `isinstance(x,
  (ggplot, Compose))` check in `_as_widget.py`.

**Not a shinywidgets bug, but worth a maintainer's attention**: the `clicked()`/`picked()`/`limits()` docstring
note on `render_matplotlib` and the `render_plotnine` class docstring are both accurate as written -- I didn't find
any docstring claim that failed to verify in a browser (unlike the brief's general warning that docstrings can be
wrong elsewhere in this pass). `reactive_read(canvas.toolbar, "_current_action")`, which the plotnine design plan
flags as a `render_matplotlib`-adjacent trait, works exactly as documented (confirmed `''` → `'zoom'` on toolbar
tool activation).

**Upstream (plotnine), long-standing, documented as design in the guide's Gotchas, not filed as issues here:**

- Fixed axis breaks at draw time (zooming in can lose tick labels) -- verified, with the `AutoDateLocator` fix
  also verified to restore ticks.
- `ggplot.__deepcopy__`/`draw()` figure-sharing that an earlier (pre-accessors) report flagged against an older
  branch is **already fixed on current `main`**: `forget_drawn_figure()` in `_as_widget.py` pops `figure`/`axs` off
  the copy before `draw()`, and I verified two renders of a plot that was pre-`.draw()`'d by the user get
  independent figures (`c1.figure is not c2.figure`). I did not re-verify the composition case specifically beyond
  what the existing unit tests (`tests/unit/test_plotnine.py`) already cover.
- Header/footer clipping that the same earlier report flagged is also already fixed: `as_widget_plotnine` sets
  both `header_visible = False` and `footer_visible = False` unconditionally (not just on first hover), so this
  never reproduced in any of my screenshots.

## Judgment calls

- **Dropped `picked()`/`limits()` coverage for plotnine entirely**, rather than noting "not supported" at length,
  because `_accessor_specs = (CLICKED,)` on `render_plotnine` is a deliberate, documented design decision (see
  `docs/plans/2026-10-29-reactive-accessors-plan-9-plotting-misc.md`), not a gap. I do explain *why* in the
  accessor reference section (facet ambiguity, no `picker=` on plotnine's artists) since a reader coming from the
  matplotlib guide will wonder where they went.
- **"Beyond the accessor" repurposed**: the brief's skeleton calls this section `reactive_read` (useful traits not
  covered by accessors). plotnine's canvas genuinely has no trait for "current view" to `reactive_read()` -- only
  the private `toolbar._current_action` is useful, and I said so. The bulk of that section is instead the
  roll-your-own `ax.callbacks.connect` recipe, which directly answers the brief's explicit instruction to check
  whether `reactive_read`/other traits give you zoom limits (they don't; this is the alternative). Flagging this
  deviation explicitly in case the maintainer wants a stricter reading of "no section content outside
  `reactive_read`."
- **Facet-to-value lookup uses a private plotnine attribute path**
  (`figure.get_layout_engine().plot.facet.layout.layout`), carried over (independently reverified against current
  plotnine 0.15.8) from the pre-accessors report. I called this out explicitly in the guide text as "undocumented,
  verify against upgrades" rather than presenting it as a stable API, since I couldn't find a public plotnine API
  for this mapping.
- **req() vs. None-check footgun**: while writing `examples/05_accessor_clicked.py` I used `req(nearest())`, which
  broke the moment a click landed on row position 0 (an `AttributeError`-adjacent `ValueError` in the gallery
  template's variant, since there I stored a pandas `Series` and `req()`'s `if not arg` raised "truth value of a
  Series is ambiguous"). I fixed both examples to compare to `None` explicitly instead, and added this as a
  Gotcha, since it's a realistic mistake for anyone copying the `req(x.accessor())` idiom this guide (and the
  brief) recommends. This isn't plotnine-specific, but I surfaced it here because the nearest-point pattern makes
  it easy to hit.
- **Didn't verify facet-panel zoom linking (`ax.sharex()`) in a filling layout.** Said so explicitly in Gotchas
  rather than presenting it as confirmed; this was out of scope for the time available and is a minor,
  easily-worked-around limitation.
- **Only 3 "What you can build" highlights**, not 4-8. plotnine's general grammar-of-graphics breadth is well
  covered by upstream docs (that's explicitly out of scope per the brief); the Shiny-specific highlights are
  compositions, live relayout on resize, and the free toolbar. A fourth highlight would have been padding.

## Editor's notes for the website

- **Strongest sections**: the compositions screenshot (hero candidate, very clear "only this renderer can do
  this"), the zoom-before/after pair on the economics series (immediately legible), and the re-render-vs-in-place
  side-by-side (`update_inplace_after_slider.webp` makes the point at a glance without reading any text).
- **Could cut for a shorter page**: the "Beyond the accessor" subsection's `toolbar._current_action` paragraph is
  the single most skippable paragraph in the guide -- it's a minor, private-trait aside. The facet-click pattern's
  internals explanation (the `get_layout_engine()` paragraph) is important for correctness but could be shortened
  to "see the example file" if the page needs to be tighter.
- **Gallery**: both apps are strong. If only one can ship in a condensed gallery, use the showcase
  (`showcase_economics_dashboard.py`) -- it demonstrates every major concept in the guide (accessor, manual zoom
  tracking, in-place state preservation across re-render, layout) in one app.
- Two gallery screenshots (`gallery_showcase_economics_zoomed.webp`, `gallery_showcase_economics_marked.webp`) exist
  in `img/` but aren't referenced from `guide.md` -- they're the intermediate zoom-only and mark-only steps,
  superseded by the combined `_theme.webp` (zoom + mark + theme all visible at once). Kept them in case the
  maintainer wants a 3- or 4-step sequence instead of a single before/after pair.

## Dropped from the old report (`docs/widget-reports/plotnine/report.md`) and why

- **Memory-leak finding (every rendered widget kept alive until session end).** Confirmed out of scope: the old
  report itself says this is a shinywidgets+py-shiny issue affecting every renderer, not plotnine-specific. Not
  re-verified or repeated here; it belongs in a cross-cutting article, not this guide.
- **Footer-clipping-on-first-hover bug and the scientific-notation footer readout.** Already fixed on `main`
  (`footer_visible = False` is now set unconditionally for plotnine) -- confirmed by reading `_as_widget.py` and by
  the complete absence of any footer in every screenshot in this guide. Not a current gotcha.
- **Pre-drawn-plot figure-sharing bug.** Already fixed (`forget_drawn_figure()`), reverified above. Not a current
  gotcha.
- **Flaky Playwright test in the PR's own test suite, and the PR-rebase/uv.lock-conflict notes.** Those were PR
  review findings about a specific pull request, not about the shipped renderer; `render_plotnine` is already
  merged to `main`, so there's no PR left to review.
- **Performance numbers for panning at 2k/50k points (23 fps / 4 fps)**, and the per-session RSS growth
  measurements. Didn't re-measure: these are about the shared ipympl/matplotlib rendering pipeline (same as
  `render_matplotlib`), not plotnine-specific, and re-measuring server-side frame rates was out of scope for a
  teaching guide. Summarized qualitatively instead ("each pan/zoom frame is a fresh server-side render") in
  Gotchas.
- **The "download button always saves Figure 1.webp" nit and `canvas.manager.set_window_title(...)` fix.** Low
  value for this guide (a cosmetic default, trivially fixed, not something most readers will hit) -- dropped per
  the usual bar for what's worth documenting.
- **The old report's "gallery_app.py" (US economy dashboard) concept** was kept and rebuilt from scratch as
  `gallery/showcase_economics_dashboard.py`, since it was a strong idea -- but trimmed significantly (no
  presidential-term shading data, no multi-page nav) and rewritten against the current `clicked()` accessor
  instead of raw `mpl_connect` wiring.

## Pairs with

- `matplotlib` -- shared canvas, shared `clicked()`, shared in-place-update technique. Cross-linked both
  directions should be considered (this guide links to matplotlib's; matplotlib's guide should probably link back
  here for "the grammar-of-graphics version").
- No other cross-widget linked-view pairing was built for this guide (e.g., a plotnine plot driving a table) --
  the brief's "coordinate multiple views" patterns here are plotnine-plot-to-plotnine-plot, which was enough to
  cover the brief's required click→facet and zoom→linked-view cases without reaching for a second widget library.

## Update 2026-11-11 (main @ 32ca7035)

Versions: plotnine 0.15.9, matplotlib 3.11.2 (via ipympl), ipympl 0.10.0, shiny 1.9.0, pandas 3.1.1, numpy 2.5.4,
shinywidgets `main` @ `32ca7035`. Worktree venv, Python 3.13.

### What changed in the guide and why

- **#402 (`limits()` accessor):** added as the renderer's second accessor. Rebuilt the "Beyond the accessor"
  section's hand-rolled `ax.callbacks.connect` zoom-tracking recipe around it everywhere it appeared: the
  standalone recipe (now `examples/06_accessor_limits.py`, replacing the deleted `06_zoom_tracking.py`), the
  "Zoom drives a second, independently-scaled plot" linked-view pattern (`examples/09_pattern_zoom_linked.py`,
  now ~20 lines shorter: no `reactive.value`, no manual effect, `bottom`/`summary` just call `top.limits()`), and
  the gallery showcase. Added a new facet-indexing example (`examples/11_accessor_limits_facets.py`) since the
  brief specifically asked that `ax` indexing facets be demonstrated, not just asserted.
- **#437 (accessor semantics) + verification:** rewrote the accessor reference table to
  `returns | before any interaction | across re-render | rate policy`. Verified (see below) that `clicked()`
  **keeps** its value across a re-render while `limits()` **re-seeds** -- the previous table's "no click yet, or
  the plot just (re-)rendered" wording was wrong for current `main` (or at least incomplete) and is removed.
- **picked() absence, re-justified**: the old rationale for why plotnine has no `picked()` conflated two accessors
  ("limits(ax) is ambiguous under faceting" -- no longer true, `limits(ax)` now exists and is exactly
  panel-indexed) with the real reason (plotnine geoms reject `picker=` outright). Verified directly:
  `geom_point(picker=5)` raises `PlotnineError: Parameters {'picker'} ... are not understood`. Kept only that
  half, worded as fact rather than guesswork.
- **New "Reading an accessor on demand" section** (`examples/13_read_on_demand.py`, the brief's suggested "save
  the current zoom window" pattern): a button reads `plot.limits()` in a `@reactive.event` handler with no
  warm-up. Verified: Save before any zoom records the full extent; Save again after zooming appends the new
  window.
- **Rate limiting rewritten**: `limits()` has a real default rate policy now (debounced 250 ms), so the old "no
  accessor here has a rate policy" framing is gone. Added `examples/12_rate_limiting.py` (ported from the
  matplotlib guide's version), verified debounced vs. `rate_delay=0` recompute counts (2 vs. 15).
- **Non-plot coercion error (#402)**: the old Gotchas bullet documented the *bug* (`guide_legend()` raising an
  unhelpful `AttributeError`). That bug is fixed -- `as_widget_plotnine` now raises a clear `TypeError` naming
  what was returned. Rewrote the bullet to describe the new, better error instead of the old one.
- **Header-chrome bullet corrected**: "unlike `render_matplotlib`, you don't need to hide the header" is no
  longer an accurate contrast -- `render_matplotlib` hides its header by default too now (#397). Reworded to say
  plotnine's footer-hiding is still the one thing `render_matplotlib` doesn't do by default.
- Converted every `reactive_read(x.widget, "trait")`-style fallback this guide ever taught: there wasn't one (the
  canvas has nothing worth reading that way); the one `reactive_read()` call that remains
  (`reactive_read(canvas.toolbar, "_current_action")`) is on a *child* widget of the canvas, not the output
  itself, so it's correctly left as `reactive_read()`, not converted to `.read()` -- the guide now says why.
- `accessors:` front matter updated to `[clicked, limits]`; tagline/intro paragraphs updated to mention both
  accessors instead of just `clicked()`.

### Bugs found (2026-11-11)

**shinywidgets/plotnine/matplotlib interaction -- re-rendering a plot from an effect that also reads that plot's
`clicked()` event can permanently break `clicked()` for every reader, with no error shown.** Found while building
the gallery showcase's "click to mark a month" feature (which conditionally added a `geom_vline` to `top()` based
on a `reactive.value` set from inside the `clicked()`-reading effect -- the exact pattern the *original*,
pre-this-session version of this same gallery file already used).

Minimal repro (run with `uv run --no-sync shiny run <file>`, click anywhere on the plot):

```python
import matplotlib.dates as mdates
import pandas as pd
from plotnine import aes, geom_line, geom_vline, ggplot, labs, theme_minimal
from plotnine.data import economics
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(fillable=True)
picked = reactive.value(None)


@render_plotnine
def plot():
    marked = picked()
    p = ggplot(economics, aes("date", "unemploy")) + geom_line() + theme_minimal()
    if marked is not None:
        p += geom_vline(xintercept=marked, color="firebrick")
    return p


@render.text
def reading():
    ev = plot.clicked()
    return "None" if ev is None else f"x={ev.xdata}"


@reactive.effect
def _mark():
    ev = plot.clicked()
    req(ev)
    month = pd.Timestamp(mdates.num2date(ev.xdata).replace(tzinfo=None)).replace(day=1)
    picked.set(month)  # <-- triggers plot() to re-render with the vline
```

After one click: `reading` stays stuck at `"None"` forever (confirmed via a raw `canvas.mpl_connect` handler that
a *later* click never fires either), and the output div's `recalculating` CSS class never clears -- the whole
output appears to hang mid-render rather than error. Confirmed the original (unmodified by me) gallery file has
the exact same symptom: `marked_label` never leaves `"none yet -- click the top plot"` on a current-`main` run.

Isolated the trigger precisely (every variant below swaps one line and was run 2-3x for consistency):
- `picked.set(ev.xdata)` (store the click value completely unchanged, still triggering a `geom_vline`
  re-render) -- **works**.
- `picked.set(ev.xdata * 1.0)` (a numerically-identical new `float` object) -- **breaks**.
- `picked.set(100.0)` or `picked.set(7300.0)` (fixed constants, unrelated to the click) -- **work**.
- `picked.set(mdates.num2date(ev.xdata).replace(tzinfo=None, day=1))` (plain `datetime`, no pandas at all,
  still derived from `ev.xdata`) -- **breaks**.

So it isn't about pandas, dates, or value range -- it's specifically "derive a new value from the click event,
then feed it to a reactive value that `plot()`'s render depends on, inside the same effect that read the
event." A `reactive.Value` holding a brand-new object computed from the click breaks the *next* read of
`clicked()` itself; reusing the same object, or using a value with no relationship to the click, doesn't.

**Workaround found and applied**: draw the mark as an in-place `ax.axvline()` edit (an effect that reads
`.widget` and calls `canvas.draw_idle()`) instead of a plotnine `geom_vline` layer that makes `plot()` depend on
`picked()`. This sidesteps the bug entirely (no re-render is triggered by marking at all) and is *also* a better
design per this guide's own "Updating the widget from Python" teaching -- it needed no "restore the zoom"
workaround either, since there's no re-render to restore after. Rewrote
`gallery/showcase_economics_dashboard.py` this way; fully re-verified (zoom, mark, theme switch, in that order)
to confirm both the zoom and the mark now survive a theme-triggered re-render correctly.

Did not dig further into *why* (would need to bisect which of plotnine/matplotlib/ipympl/shinywidgets is
responsible, likely with a debugger attached to the running kernel) -- flagging for the maintainer as a
`shinywidgets`-or-upstream interaction bug with a precise, minimal, reliable repro above. Only known-affected
code in this guide roster was the gallery showcase (fixed); no example in the matplotlib guide uses this pattern
(checked: none of its `clicked()`/`picked()` examples feed a derived value back into their own render function's
dependencies).

### Verification table (new/edited files this pass)

| File | Ran | Screenshot looked at | Gesture | Accessor confirmed |
|---|---|---|---|---|
| `examples/06_accessor_limits.py` (new, replaces `06_zoom_tracking.py`) | yes | yes (before/after) | toolbar zoom-to-rectangle drag | **`limits()` yes** -- window text updated from full range to the zoomed dates |
| `examples/09_pattern_zoom_linked.py` (rewritten) | yes | yes (before/after) | toolbar zoom-to-rectangle drag | **`limits()` yes** -- linked plot and summary both updated from the new window |
| `examples/11_accessor_limits_facets.py` (new) | yes | yes (before/after) | toolbar zoom-to-rectangle drag on one facet panel | **`limits(ax=i)` yes** -- only the zoomed panel's range changed; the other two stayed at the full range |
| `examples/12_rate_limiting.py` (new, ported from matplotlib guide) | yes | yes | pan drag on two linked plots | **`limits()` rate policy yes** (2 vs. 15 recomputes) |
| `examples/13_read_on_demand.py` (new) | yes | yes (after two saves) | click Save before and after a zoom drag | **`limits()` read-on-demand yes** -- console showed `1. x: 1.3-7.3, ...` then `2. x: 2.4-4.9, ...` |
| `gallery/showcase_economics_dashboard.py` (rewritten: in-place mark, `_restore_view`/`_track_view` split) | yes | yes (before/zoomed/marked/theme) | zoom, click to mark, switch theme | **`limits()`, `clicked()` yes** -- zoom and mark both survived a theme-triggered re-render |

Also spot-re-verified two **unchanged** files given how much this pass's testing revealed: `examples/05_accessor_clicked.py` (`clicked()` yes, unchanged) and `examples/08_pattern_click_facet.py` plus `gallery/template_click_explorer.py` (both `clicked()` yes, unchanged) -- all three use the safe pattern (a click-derived value consumed only by a *different* output, never fed back into the clicked plot's own render), confirming the bug above doesn't affect them.

### Judgment calls

- **Deleted `examples/06_zoom_tracking.py` outright** rather than keeping it alongside the new
  `06_accessor_limits.py`, since the section it illustrated (hand-rolled zoom tracking) no longer exists in the
  guide -- the brief says to rebuild this section *around* `limits()`, and keeping a dead file with no guide
  reference seemed like confusing cruft. Its orphaned screenshots (`zoom_tracking_*`) are still in `img/`; the
  maintainer may want them deleted too.
- **Redesigned the gallery showcase's mark mechanism** rather than just swapping in `limits()` for the view and
  leaving the click-to-mark feature as originally built, because the original approach is the one that triggers
  the bug above on current `main` -- shipping a guide showcase that silently hangs on click would be worse than
  fixing the underlying pattern. The fix is a genuine simplification (see above), not just a workaround, so I'm
  confident it's the right call rather than a stopgap.
- **Priority + a one-shot skip flag for `_restore_view`/`_track_view`**: a theme switch re-seeds `limits()` to
  the new figure's full extent before the restore effect gets to re-apply the saved zoom; without
  `priority=10` on `_restore_view` and a `skip_next_track` flag discarding the one spurious `limits()` publish
  the restore's own `set_xlim` triggers, the saved zoom was being silently overwritten by the re-seed on every
  theme switch (verified broken, then verified fixed, by polling the view label every 100ms for 2s after a theme
  switch with zoom active).
- **`examples/13_read_on_demand.py` uses `mpg`/scatter instead of reusing the `economics` series** used
  everywhere else in this guide, for variety and because the matplotlib guide's equivalent example already uses
  a signal-style dataset -- a second data source for this one example didn't seem worth flagging as a
  consistency problem.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data`: no new example. Same ipympl engine as matplotlib, so the section mirrors matplotlib's and cross-links to it, plus this guide's own existing "When to use @render.plot instead" Gotchas bullet.

## Update 2026-11-11 (loop fixed upstream; natural pattern restored)

- The infinite re-render loop in "Bugs found (2026-11-11)" above is **fixed** (PR #457): a re-render no
  longer re-runs readers of a kept accessor whose value didn't change, so the click -> derive -> `geom_vline`
  pattern renders exactly once per click. Re-verified the minimal repro against the fix: settles at 2 renders,
  vline drawn, `clicked()` stays live.
- Restored the natural pattern in `gallery/showcase_economics_dashboard.py`: the mark is a `geom_vline()`
  layer in `top()` fed by `picked` again (the `ax.axvline()`/`_draw_mark` workaround is gone, including the
  mark half of `_restore_view()`). Re-verified against the fixed code in Chromium: zoom to May 1978--May 1994,
  click marks August 1985, zoom survives the mark, theme switch to `bw` keeps both zoom and mark, zero console
  and server errors (screenshots looked at).
