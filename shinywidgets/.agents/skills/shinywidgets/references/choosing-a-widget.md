# Choosing a widget

## Overview

shinywidgets integrates dozens of libraries; almost none compete head-to-head
— each earns its place by doing one task well. Don't reach for a widget at
all when a plain Shiny output already does the job: `render.plot` for a
genuinely static chart, `render.data_frame` for a table nobody needs to
search/export/pivot. What matters more in Shiny than in a notebook: does
user interaction come back as a named **accessor**; can you update the
widget **in place** (preserving zoom/camera/selection) instead of
re-rendering; what scale was actually **measured**; and how **mature** is
the integration (a few have known upstream bugs or multi-session caveats —
see the widget's own reference).

## Decision table

| Task | Default pick | Reach for instead when |
|---|---|---|
| Statistical chart, need click/lasso/zoom back | `plotly` — richest accessor set (10) | Selection declared in the chart's own grammar: `altair`. Live Python objects (`ColumnDataSource`): `bokeh`. Already matplotlib/plotnine code: `matplotlib`/`plotnine`. Grammar-of-graphics with native widget state: `bqplot`. Already in HoloViews/Panel: `panel`/`holoviews` |
| Static chart, no interaction needed | plain `render.plot` | — |
| Table, nothing more than reading it | plain `render.data_frame` | Zero-config search/export: `itables`. Cell-block selection/editing: `ipydatagrid`. Grouping/theming: `reactable`. User-driven pivot/BI: `perspective` |
| Map as an input (draw/click/bounds/zoom) | `ipyleaflet` (or `leafmap` if unsure which engine) | Styled vector tiles, 3D/globe, no accessors needed: `maplibre`. Tens of thousands+ GPU points: `lonboard`. Raster GeoTIFF/COG: `localtileserver`. Full GIS authoring app: `geolibre`. No-code analysis studio: `keplergl`. Non-Mercator projections: `geoviews` |
| Data too big for one mark per row (>~500k) | Table: `quak`/`mosaic` (DuckDB). Scatter: `jscatter` (real GPU points) or `datashader` (server-rasterized). Map: `lonboard`. Full workbench: `embedding-atlas` (needs WebGPU) | — |
| 3D / scientific, pick by domain | Generic scene: `k3d`. VTK mesh/volume: `pyvista`. Molecule/protein: `nglview` (structures) or `mols2grid` (2D SMILES). Brain/medical volume: `niivue`. Sky survey: `ipyaladin`. Microscopy pyramid: `vizarr`. Robotics/multimodal log: `rerun`. Custom scene graph: `pythreejs` | — |
| Graph/network | Fine styling, low thousands of nodes: `ipycytoscape` | Tens of thousands of nodes, GPU-smooth: `ipysigma` |
| User draws/picks something | A dataset for ML: `drawdata`. Arbitrary pixels/game loop: `ipycanvas`. A file on the server: `ipyfilechooser` | A file from the visitor's own computer: plain `ui.input_file()` |
| Not in this roster at all | `render_widget` (generic escape hatch, see `any-widget.md`) | — |

## Notes on the trade-offs

- **Accessors**: `0` doesn't mean a dead end — every renderer output still
  has `.read("trait")` (and `reactive_read()` for a nested widget); see
  `reacting-to-widgets.md`.
- **In-place updates**: most widgets support them; a few are re-render-only
  by design (`pyvista` has zero accessors and no in-place path; `ipysigma`
  has no Python-to-browser trait sync at all). `updating-in-place.md` has
  the general mechanism and the per-widget table.
- **Deprecated: pydeck.** `render_pydeck` is deprecated — pydeck ≥ 0.9
  dropped its live Jupyter widget entirely. Bring `pdk.Layer` objects to
  `render_maplibre`'s `add_deck_layers()` (recommended default) or
  `lonboard`'s native API for very large data.
- **Security — quak and mosaic**: both run browser-supplied SQL against the
  widget's DuckDB connection, so by default the renderer locks it down
  (`enable_external_access = false`, `lock_configuration = true`); pass
  `allow_unrestricted_connection=True` only for a local, single-user app.

## Common mistakes

- Reaching for a widget when `render.plot`/`render.data_frame` already does
  the job — every widget adds a JS bundle the plain renderer doesn't.
- Picking a DOM-based widget (a plain table, `ipyleaflet` markers,
  `ipycytoscape`) for hundreds of thousands of rows/points — check the
  widget's own reference for its measured scale before committing to it.
- Using `render_pydeck` in new code — it's deprecated; use `render_maplibre`
  or `render_lonboard`.

**More:** <https://shinywidgets.org/guide/choosing-a-widget/>
