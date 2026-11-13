# NOTES: Your first widget app

## Versions

- shinywidgets: worktree `widget-guides` @ `5e8dcea0`, shiny 1.9.0, plotly 6.9.0 (pandas/narwhals come with
  `shinywidgets[plotly]`). Date: 2026-11-12.
- Playwright: Chromium headless, no special GPU flags needed (plain SVG/canvas 2D plotly rendering).
  Viewport 1400x760, `device_scale_factor=2`, saved as WebP (Pillow, quality 85).

## Verification table

| File | Ran (`smoke.py`) | Screenshot | Gesture driven | Confirmed |
|---|---|---|---|---|
| `examples/01_render.py` | yes, exit 0 | `img/01_render.webp` (element screenshot of `#plot`; no card wraps it) | n/a (no interaction yet) | scatter renders, sized by population, colored by continent |
| `examples/02_react.py` | yes, exit 0 | `img/02_before.webp` / `img/02_after.webp` (full page) | real lasso (mouse down, several `mouse.move` steps per edge, up, tracing the 5-point polygon given as fractions of `#plot .nsewdrag`'s bounding box, closing back to the first vertex) | table empty before; after, the data-frame footer reads "Viewing rows 1 through 15 of 65" -- read from the output's shadow-root `textContent` via `page.evaluate()`, not just a visual check (the rendered `<tr>` count undercounts because the grid virtualizes/paginates to 15 rows) |
| `examples/03_update.py` | yes, exit 0 | `img/03_zoomed.webp` / `img/03_after.webp` (element screenshots of the plot's `.card` ancestor) | modebar "Zoom" click + box-zoom drag, then modebar "Lasso Select" click + the same real lasso polygon as `02_react.py` | `xaxis.range` identical before/after the lasso (`[3.0458, 4.6563]`, log10 units), confirming the zoom survived the in-place update; selection matched 37 countries (fewer than `02_react.py`'s 65 because the view was zoomed into a narrower gdpPercap/lifeExp range first, so the same screen-space polygon covers a different, smaller set of points); the annotation text read exactly `<b>37 countries</b><br>avg life expectancy 78.9 yrs<br>0.9B people`, matching what `rows.lifeExp.mean()`/`rows["pop"].sum()` compute for that selection; both read directly from the live `FigureWidget` via `page.evaluate()` (`el.layout.xaxis.range`, `el.layout.annotations[0].text`), not just a visual check |
| `examples/03_update.py` (landing-page asset -- not referenced from `index.md`) | yes, exit 0 | `img/03_summary.webp` (element screenshot of the plot's `.card` ancestor, same framing as `03_after.webp`) | the same real lasso polygon as `02_react.py`/`03_update.py`, **no zoom first** | selection matched 65 countries (same unzoomed lasso as `02_react.py`); annotation text read exactly `<b>65 countries</b><br>avg life expectancy 77.0 yrs<br>1.8B people`, read from the live `FigureWidget` via `page.evaluate()` (`el.layout.annotations[0].text`). The landing page's "Update in place" card wants the 65-country summary unzoomed, distinct from `03_after.webp`'s zoomed 37-country one. |

Driver script (scratch, not committed): drove all three apps with a custom Playwright script (`smoke.py` has
no gesture support). Lasso traces the 5-vertex polygon `(0.55,0.04) (0.98,0.04) (0.98,0.30) (0.70,0.36)
(0.55,0.22)` (fractions of the `.nsewdrag` element, closing back to the first point) with several
intermediate `mouse.move` calls per edge -- a straight line back-and-forth encloses zero area and silently
no-ops, so a closed polygon with real area is required. The plot-card element screenshots for `03_update.py`
locate the card via `#plot`'s nearest `.card` ancestor (`page.locator("#plot").locator("xpath=ancestor::div[contains(@class,'card')][1]")`),
not by adding an `id=` to the example's `ui.card()` -- that keeps `03_update.py` exactly `02_react.py` plus
one effect, with no unrelated UI-wiring diff.

## Judgment calls

- **`color="continent"` added to the scatter (landing-page reuse).** The screenshots in this guide are
  reused on the site's landing page, which wanted a visually richer chart than a single-color scatter.
  Added `color="continent"`, `size_max=48`, `template="plotly_white"`,
  `fig.update_traces(marker=dict(opacity=0.85, line=dict(width=0)))`, and `legend_title_text=""` to all
  three examples (matching `docs/plans/2026-11-12-widgets-site-spike/gapminder_variant_app.py`, a throwaway
  variant built for this exact purpose).
- **Replaced the step-3 per-point outline effect with an annotation summary.** The previous `_highlight`
  effect restyled `plot.widget.data[0].marker.line.width`, which assumed a single trace -- `color="continent"`
  splits the figure into one trace per continent, so a flat per-row list indexed into `data[0]` no longer
  lines up with the data. Rather than rewrite the highlight to track (trace index, position within trace),
  switched to the variant's `_summarize` effect: it sets `plot.widget.layout.annotations` to a summary box
  (count, average life expectancy, total population) and clears it when nothing is selected. This sidesteps
  the multi-trace indexing problem entirely (layout-level state, not per-trace marker state) and is a more
  interesting demonstration of "update in place" for a reader skimming the guide.
- **Verified `selected_rows(df)` still works across multiple traces, rather than assuming it from the
  variant.** `shinywidgets/_plotly.py`'s `customdata_value()`/`select_rows()` match each selected point to a
  `df` row by the point's own `customdata` value, independent of which trace fired the selection event --
  there's no per-trace indexing anywhere in the accessor. Confirmed empirically too: the real lasso gesture
  against the `color="continent"` figure (five traces) returned rows spanning multiple continents with
  correct `country`/`gdpPercap`/`lifeExp` values, and the annotation's computed average/population matched
  what pandas computes for that same row set.
- **This NOTES.md's old "No `color=continent` grouping" judgment call no longer holds** -- superseded by the
  two calls above. It was reasoned around keeping the highlight effect a flat per-row list; replacing that
  effect with the annotation approach removed the constraint.
- **`img/03_zoomed.webp` kept, re-shot in the new style.** The article still uses the zoom step to make the
  "update in place preserves view state" point, so this file is still referenced and needed.
- **Row count differs between `02_react.py` (65) and `03_update.py` (37) for what the task description calls
  "the same lasso".** Same five-vertex polygon, same fractions of `.nsewdrag`'s bounding box (which is a
  fixed screen-pixel rectangle) -- but `03_update.py`'s screenshot sequence zooms in with the modebar
  *before* lassoing, to demonstrate that the zoom survives. Zooming remaps what data range those same screen
  pixels cover, so the same polygon encloses a different, smaller set of points after the zoom. Reported the
  actual count (37) and the annotation text it produced rather than adjusting the polygon to force 65.
- Reused the exact `01`/`02`/`03` structure established before this change; `02_react.py` is still
  `01_render.py` plus the table, and `03_update.py` is still `02_react.py` plus one effect.

## Findings for FINDINGS.md

None. No shinywidgets or upstream bugs surfaced while updating or verifying these three files.

## Editor's notes for the website

- `img/03_after.webp` (zoomed + lassoed + annotated, all at once) is the strongest single screenshot of the
  three files and is used as both the page hero and a landing-page image.
- The "why zoom survives" explanation at the end of step 3 is worth keeping prominent -- it's the one
  surprising takeaway a reader who skims code blocks might miss.
- The new annotation-based effect also sidesteps a subtlety the old marker-outline effect had (needing to
  know which trace index to restyle); worth noting if this example is ever extended to show a 4th idea,
  since `plot.widget.layout` is shared across all traces while `plot.widget.data[i]` is per-trace.
