# NOTES: "Layout & theming"

## Versions

- shinywidgets: `main` @ worktree HEAD (branch `docs/site-content-gaps`), run with `uv run --no-sync` from
  `/Users/cpsievert/github/py-shinywidgets/.worktrees/site-content-gaps`.
- shiny 1.9.x (per the worktree's locked venv); plotly, altair, bokeh, matplotlib, itables, ipyleaflet, maplibre,
  lonboard all from the shared venv (`uv pip list`). reactable is not in the shared venv (see pyproject.toml's
  comment on `ipyreact` pin conflicts) -- served via `--with reactable==0.1.6` (the locked extra version) for the
  dark-mode example only.
- Playwright: Chromium headless, `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`
  for the maplibre/lonboard screenshots (WebGL), per BRIEF.md.
- Date: 2026-11-11. Ports 8140-8149.

## Step 1: survey of existing "Layout and sizing" sections

Read all guide `## Layout and sizing` sections (45 guides; `pydeck` and `localtileserver` have none). Shared
rules that recur across most guides, which this article generalizes instead of repeating:

1. **Fill is the default.** With no explicit height, a `DOMWidget` output fills its container: a
   `ui.card()` under `ui.page_opts(fillable=True)`, a sidebar, a column. This is implemented once, generically,
   in `set_layout_defaults()` (`shinywidgets/_render_widget_base.py`): every renderer goes through it, and most
   guides say "the same as every other shinywidgets renderer" rather than re-deriving it.
2. **An explicit height opts out.** Three equivalent ways to give a widget an explicit height, in order of
   how most guides phrase it: `@render_x(height="300px")` / `output_widget(height=...)` (the output container);
   the widget's own constructor height (`Scatter(height=300)`, `k3d.plot(height=250)`, ...); or
   `ipywidgets.Layout(height=...)` on `.layout` (generic path, read directly in `set_layout_defaults()`: "If the
   ipywidget Layout() height is set to something other than 'auto', then don't do filling layout"). Any of the
   three sets the per-render `fill` flag to `False`.
2a. **"Unset" vs. "the library's own default" is a real distinction `set_layout_defaults()` has to make.**
    Several libraries always set a concrete height trait (lonboard 500px, maplibre/rerun 400/640px, k3d 512px,
    jscatter 240px, keplergl 400px, ipysigma 500px, ipyaladin 400px, geolibre "800px", leafmap 600px) rather than
    leaving it `None`/`"auto"` the way plain ipywidgets does. Each has a package-specific handler in
    `_LAYOUT_DEFAULTS` (keyed by `widget_pkg()`) that treats that one default value as "unset" (so the widget
    still fills) and anything else as a user choice (opts out). This is why "the default height" and "a height
    equal to the default, typed explicitly" are indistinguishable for these widgets -- a documented, intentional
    tradeoff repeated in nearly every guide with its own concrete numbers (e.g. jscatter: ask for `height=241`,
    not `240`, if you want a genuinely fixed 240px-ish plot).
3. **`full_screen=True` on the card works uniformly.** Every guide that mentions it says the widget resizes
   correctly entering and leaving full screen, with no widget-specific caveats (the few exceptions, e.g.
   ipycytoscape not re-fitting its own graph layout on resize, are about redrawing content, not the fill
   mechanics).
4. **`widget.layout.height` set after the fact, while the output is filling, has no visible effect** --
   not spelled out in any per-guide section (it's a generic concept, not a per-widget quirk), but explicit in
   `output_widget()`'s own docstring: fill is CSS (`flex: 1 1 auto` on the widget's direct DOM child, see
   `shinywidgets.css`); `set_layout_defaults()` only reads `layout.height` once, at render time, to decide the
   *initial* `fill` flag sent to the browser. A later Python-side assignment to an already-filling widget's
   `.layout.height` changes the trait but not the CSS already in effect, so nothing moves on screen. Demonstrated
   in `examples/01_fill_vs_fixed.py` (own content, not duplicated from any guide).
5. **A handful of widgets don't participate in fill at all.** Plain `@jupyter-widgets/controls` widgets
   (sliders, checkboxes, dropdowns -- anything that isn't itself one of the special-cased packages) never fill;
   `render-widget/guide.md` documents this as the one generic-path caveat worth knowing.
6. **Dark mode / theming is inconsistent and almost entirely per-widget**, not a shinywidgets-wide feature.
   Only two places in `shinywidgets.css` patch a widget's own CSS variables onto Bootstrap's theme variables:
   bqplot (`--jp-*`/`--bq-*` tokens aliased to `--bs-body-bg`/`--bs-body-color`/`--bs-border-color`) and
   itables (`:root[data-bs-theme=dark] .itables_anywidget` remaps DataTables' dark-palette tokens, since
   DataTables itself only switches on its own `.dark`/`data-theme` markers, not Bootstrap's). ipyleaflet's map
   *chrome* (zoom buttons, attribution, layers control) is similarly patched to Bootstrap variables, but the map
   tiles themselves are whatever images the tile provider serves, so a Leaflet map only half-follows. Every other
   widget in the roster draws its own colors (an SVG/canvas figure, a WebGL map style, a React/DataTables theme
   prop) with no shinywidgets-side connection to `ui.input_dark_mode()`; following the toggle for those needs
   app code that reads `input.<id>()` and re-themes the figure (matplotlib's guide and perspective's guide each
   show this pattern already; this article links to them rather than re-deriving the code).

## Step 2: examples

| File | Ran | Screenshot(s) | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_fill_vs_fixed.py` | yes | `img/fill_vs_fixed.webp`, `img/layout_override_before.webp`/`after.webp` | button click (sets `.widget.layout.height` in an effect) | plotly for fill-vs-fixed; bqplot for the post-render `layout.height` override (bqplot has no `_LAYOUT_DEFAULTS` entry, so the generic ipywidgets `Layout` path applies unmodified) |
| `examples/02_full_screen.py` | yes | `img/full_screen_before.webp`/`after.webp` | clicked the card's expand icon | plotly scatter in a `full_screen=True` card |
| `examples/03_dark_mode.py` | yes | `img/dark_mode_light.webp`/`dark.webp` | clicked the real `ui.input_dark_mode()` toggle | 9 widgets, default code (no manual theme-sync), to observe actual behavior rather than assume it |

## Step 2 continued: dark-mode follows/doesn't-follow findings (from screenshots actually opened)

| Widget | Follows `input_dark_mode()`? | Evidence |
|---|---|---|
| plotly | No | Figure keeps its white plot background and default (light) template in both screenshots; unchanged pixels around the plot area. |
| altair | No | Vega-Lite chart keeps a white background and dark axis/text colors in both screenshots; unchanged. |
| bokeh | No | Figure background and glyph colors are identical in both screenshots; only the card chrome around it changed. |
| matplotlib | No | Default `Figure()` (no `plt.style.context`) renders a white canvas in both modes; see the matplotlib guide's own "Figures can match bslib's light/dark theme" section for the opt-in fix. |
| itables | Yes | The table's header/body/footer switch to DataTables' dark palette (dark background, light text, dark search box) in the dark screenshot -- confirms the `shinywidgets.css` `:root[data-bs-theme=dark] .itables_anywidget` rule. |
| reactable | No (and worse: a low-contrast trap) | The table's own background stays hard-coded white in both screenshots, but its text color switches to Bootstrap's dark-mode `--bs-body-color` (`rgb(222, 226, 230)`, confirmed via `getComputedStyle`) -- light gray text on a white background, clearly lower-contrast than either pure light or pure dark mode. Cropped evidence: `img/reactable_dark_crop.webp` vs. the light screenshot's same region. |
| ipyleaflet | Partial | The zoom control and attribution strip switch to dark Bootstrap colors (confirms the `.jupyter-widgets.leaflet-widgets` CSS variable patch; cropped evidence: `img/leaflet_light_crop.webp`/`leaflet_dark_crop.webp`), but the OpenStreetMap tile imagery itself is identical in both screenshots -- it's server-rendered raster tiles, not styleable from the page. |
| maplibre | No | The default Carto Positron basemap style and all map colors are pixel-identical between the two screenshots. |
| lonboard | No | Verified in its own isolated app (`examples/04_dark_mode_lonboard.py` -- see "Bugs found" for why): the scatter layer and (basemap-less, black) canvas are pixel-identical between the two screenshots. |

Every "No"/"Partial" above is the *default*, unmodified widget: none of these guides' own quickstarts tie the
widget's theme to `input_dark_mode()`. matplotlib and perspective already document a working opt-in pattern
(swap `plt.style.context()` / `.widget.theme` from a `@reactive.effect` reading `input.mode()`); this article
links to those sections instead of re-deriving the same code for plotly/bokeh/altair.

## Bugs found

- **lonboard fails to render on the same page as a maplibre widget.** Repro:
  `docs/widget-guides/articles/layout-and-theming/examples/03_dark_mode.py` originally included a lonboard
  card alongside the maplibre card; the lonboard output showed only
  `jupyter-widgets-error-widget` text reading `Failed to create view for 'AnyView' ... Error: deck.gl -
  multiple versions detected: 9.1.11 vs 9.4.0`. Confirmed reproducible (not flaky): happens every run.
  Confirmed it's the *combination*, not lonboard itself: lonboard alone (`examples/04_dark_mode_lonboard.py`)
  renders fine. Both widgets bundle their own copy of deck.gl's JS and load it on the same page, where
  deck.gl's own version-guard throws rather than letting two copies coexist. Not investigated further (e.g.
  whether this is new or has always been true for this pair) since neither widget's `NOTES.md`/guide in this
  roster combines them on one page elsewhere -- can't tell regression from long-standing without digging into
  each library's bundling, which is out of scope here. Worked around in this article by giving lonboard its own
  page (`04_dark_mode_lonboard.py`) instead of fixing it.

Otherwise, none in shinywidgets itself. The dark-mode table above describes upstream/widget-level theming
limits (most widgets simply don't take a dark/light flag from shinywidgets), not a shinywidgets regression.

## Findings for FINDINGS.md

- **lonboard + maplibre on the same page: lonboard's view fails to mount.** `Error: deck.gl - multiple versions
  detected: 9.1.11 vs 9.4.0`, thrown by lonboard's anywidget bundle when a maplibre widget (which bundles its
  own, different, deck.gl build) is rendered on the same page. Lonboard alone renders fine. Unknown whether this
  is a regression or long-standing (not investigated past confirming reproducibility). Repro:
  `docs/widget-guides/articles/layout-and-theming/examples/03_dark_mode.py` with the lonboard card re-added
  next to the maplibre card (removed in the committed version to work around it); minimal repro is any page
  with one `render_lonboard` output and one `render_maplibre` output together.

## Judgment calls

- Chose plotly (not altair/bokeh) for the fill-vs-fixed example and bqplot for the `layout.height`-after-render
  gotcha, since bqplot is the simplest widget with no package-specific `_LAYOUT_DEFAULTS` handler -- the
  generic ipywidgets `Layout` path is exactly what's being demonstrated, with no renderer-specific code in the
  way.
- `03_dark_mode.py` renders every widget with its plain quickstart-level code (no theme-sync effects), on
  purpose: the point of this article's table is to report what actually happens by default, not to show the
  fixed version a second time (that's one or two sentences with links, not new code).
- reactable needed an unlocked-from-venv package (`--with reactable==0.1.6`, the version pinned in
  `pyproject.toml`/`uv.lock`) to run at all; this matches the `BRIEF.md` guidance to pin to the locked version
  rather than let `--with` silently resolve a newer one.

## Editor's notes for the website

- The dark-mode table is the most load-bearing content on this page (Review Focus calls it out explicitly) --
  keep it near the top of that section, above the prose.
- The fill/full_screen examples are deliberately generic (plotly as the stand-in widget), since every guide's
  own "Layout and sizing" section already demonstrates the same fill-vs-fixed contrast with its own widget; this
  article isn't trying to be exhaustive per-widget, just to state the shared mechanism once.
