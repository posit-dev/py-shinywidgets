---
name: shinywidgets
description: "Adding interactive widgets to a Shiny for Python app with shinywidgets - `from shinywidgets import ...`, `@render_widget`, `output_widget`, and `@render_<library>` for plotly, altair, bokeh, matplotlib, itables, ipyleaflet, maplibre, lonboard, pydeck, k3d, pyvista, ipycytoscape, anywidget, and 30+ more. Index skill: read this, then open the linked reference. Covers how widgets fit Shiny's reactivity, reading selections/clicks/zoom back with reactive accessors, updating a widget in place, linked views, choosing a widget, custom widgets, sizing, performance, and troubleshooting. Use when rendering any Jupyter widget or plotting library in Shiny, or when tempted to re-render a widget just to change it, wire hidden inputs or custom JavaScript to get widget state, or poll a widget for changes."
---

# shinywidgets

shinywidgets renders [ipywidgets](https://ipywidgets.readthedocs.io) (and
anything that coerces to one — plotly figures, altair charts, bokeh models,
...) inside a Shiny for Python app. The mental model is always the same:
**render** a widget with `@render_widget` (or a library-specific
`@render_<library>`), **read** its state back reactively with the
renderer's accessors, then **update it in place** from a `@reactive.effect`
instead of re-rendering. Read the linked reference before writing code for
your task — each one is short and has the facts this index leaves out.

## Concepts

| Topic | Use when | Reference |
|---|---|---|
| How it works | First widget output in an app; confused about `@render_widget` vs `output_widget`, re-render vs. reactive read, Express vs. Core, or modules | `references/how-it-works.md` |
| Reacting to widgets | Reading a selection, click, hover, or zoom back from a widget as a reactive input | `references/reacting-to-widgets.md` |
| Updating in place | Changing an already-rendered widget's state without re-rendering it (and avoiding an infinite reactive loop) | `references/updating-in-place.md` |
| Linked views | Coordinating two or more widgets/outputs — a selection filters a table, a highlight propagates, a zoom syncs | `references/linked-views.md` |
| Choosing a widget | Deciding which widget or library fits a chart, table, map, or 3D need | `references/choosing-a-widget.md` |
| Any widget | The library has no dedicated `render_<x>`, or using anywidget / `as_widget()` directly | `references/any-widget.md` |
| Layout and sizing | Sizing a widget's output, fill layouts, or matching the app's light/dark theme | `references/layout-and-sizing.md` |
| Performance | Large data, slow renders, or payloads that make the browser sluggish | `references/performance.md` |
| Troubleshooting | A widget doesn't show, its JS fails to load, or deploying an app that uses widgets | `references/troubleshooting.md` |

## Widgets

Each row: widget, the renderer it uses, the install extra, what to pick it
for, and its reference (accessors and gotchas live there, not here). Each
reference notes the major version of the widget library it was written
against — if its advice doesn't match what you observe, compare that with
the installed version, and on a mismatch prefer the library's own docs.

### Charts

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| Plotly | `render_plotly` | `shinywidgets[plotly]` | Two-way clicks, hovers, zoom, legend toggles | `references/widgets/plotly.md` |
| Altair | `render_altair` | `shinywidgets[altair]` | Vega-Lite selections as reactive Python values | `references/widgets/altair.md` |
| Bokeh | `render_bokeh` | `shinywidgets[bokeh]` | Live Python-object plots, two-way sync | `references/widgets/bokeh.md` |
| Matplotlib | `render_matplotlib` | `shinywidgets[matplotlib]` | Any matplotlib figure as a zoomable widget | `references/widgets/matplotlib.md` |
| plotnine | `render_plotnine` | `shinywidgets[plotnine]` | Pan/zoom/click any ggplot-style plot | `references/widgets/plotnine.md` |
| bqplot | `render_bqplot` | `shinywidgets[bqplot]` | Grammar-of-graphics plots with brush/drag feedback | `references/widgets/bqplot.md` |
| HoloViews | `render_holoviews` | `shinywidgets[holoviews]` | Declarative Bokeh plots, crossfilter multiple views | `references/widgets/holoviews.md` |
| Datashader | `render_holoviews` | `shinywidgets[holoviews]` | Aggregate tens of millions of points server-side | `references/widgets/datashader.md` |
| jscatter | `render_jscatter` | `shinywidgets[jscatter]` | GPU scatter plots for millions of points, lasso select | `references/widgets/jscatter.md` |
| Observable Plot | `render_obsplot` | `shinywidgets[obsplot]` | Grammar-of-graphics JS charts with tooltips | `references/widgets/obsplot.md` |
| Panel | `render_panel` | `shinywidgets[panel]` | Any Panel component (Tabulator, chat, indicators) | `references/widgets/panel.md` |

### Tables & grids

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| itables | `render_itables` | `shinywidgets[itables]` | Searchable/sortable/exportable DataTable with row selection | `references/widgets/itables.md` |
| reactable | `render_reactable` | `shinywidgets[reactable]` | R-reactable-style table with sort/filter/group | `references/widgets/reactable.md` |
| ipydatagrid | `render_ipydatagrid` | `shinywidgets[ipydatagrid]` | Canvas spreadsheet grid, cell selection, heatmaps | `references/widgets/ipydatagrid.md` |
| Perspective | `render_perspective` | `shinywidgets[perspective]` | A pivot table users build, that you read back | `references/widgets/perspective.md` |

### Data exploration

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| PyGWalker | `render_pygwalker` | `shinywidgets[pygwalker]` | Tableau-style drag-and-drop explorer over a DataFrame | `references/widgets/pygwalker.md` |
| quak | `render_quak` | `shinywidgets[quak]` | Millions of rows with per-column histograms | `references/widgets/quak.md` |
| Mosaic | `render_mosaic_widget` | `shinywidgets[mosaic_widget]` | Crossfilter millions of rows via DuckDB | `references/widgets/mosaic.md` |
| Embedding Atlas | `render_embedding_atlas` | `shinywidgets[embedding_atlas]` | Embedding map, auto-charts, table, and SQL cross-filter | `references/widgets/embedding-atlas.md` |

### Maps & geospatial

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| ipyleaflet | `render_ipyleaflet` | `shinywidgets[ipyleaflet]` | A fully interactive Leaflet map — draw, click, drag | `references/widgets/ipyleaflet.md` |
| leafmap | `render_leafmap` | `shinywidgets[leafmap]` | One high-level API for basemaps and vector/raster layers | `references/widgets/leafmap.md` |
| MapLibre | `render_maplibre` | `shinywidgets[maplibre]` | Styled vector-tile maps with 3D extrusions and deck.gl layers | `references/widgets/maplibre.md` |
| lonboard | `render_lonboard` | `shinywidgets[lonboard]` | GPU-accelerated maps with 100k+ points | `references/widgets/lonboard.md` |
| GeoLibre | `render_geolibre` | `shinywidgets[geolibre]` | Full GeoLibre desktop-GIS app embedded in a Shiny output | `references/widgets/geolibre.md` |
| kepler.gl | `render_keplergl` | `shinywidgets[keplergl]` | Full geospatial-analysis studio with time playback | `references/widgets/keplergl.md` |
| GeoViews | `render_holoviews` | `shinywidgets[holoviews]` | Cartopy-projected, tile-backed Bokeh maps | `references/widgets/geoviews.md` |
| localtileserver | `render_ipyleaflet` | `shinywidgets[ipyleaflet]` | Serve a local GeoTIFF/COG as slippy-map tiles | `references/widgets/localtileserver.md` |
| pydeck | `render_pydeck` (deprecated; see maplibre) | — | Don't; use `render_maplibre` + `pdk.Layer` | `references/widgets/pydeck.md` |

### 3D

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| K3D | `render_k3d` | `shinywidgets[k3d]` | A GPU 3D scene — millions of points, meshes, volumes | `references/widgets/k3d.md` |
| pythreejs | `render_pythreejs` | `shinywidgets[pythreejs]` | A custom three.js scene graph built from Python | `references/widgets/pythreejs.md` |
| PyVista | `render_pyvista` | `shinywidgets[pyvista]` | An interactive client-side 3D view, no server round-trip | `references/widgets/pyvista.md` |
| ipyvolume | `render_ipyvolume` | `shinywidgets[ipyvolume]` | Orbit 3D point clouds/volumes/surfaces, reactive camera | `references/widgets/ipyvolume.md` |

### Scientific

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| mols2grid | `render_mols2grid` | `shinywidgets[mols2grid]` | A searchable grid of 2D chemical structures | `references/widgets/mols2grid.md` |
| NGLView | `render_nglview` | `shinywidgets[nglview]` | A WebGL molecular structure/trajectory viewer | `references/widgets/nglview.md` |
| vizarr | `render_vizarr` | `shinywidgets[vizarr]` | Pan/zoom gigapixel multichannel bioimages (OME-Zarr) | `references/widgets/vizarr.md` |
| NiiVue | `render_niivue` | `shinywidgets[niivue]` | A clinical-grade WebGL2 neuroimaging viewer | `references/widgets/niivue.md` |
| ipyaladin | `render_ipyaladin` | `shinywidgets[ipyaladin]` | A real-sky atlas that pans, zooms, and clicks | `references/widgets/ipyaladin.md` |
| Rerun | `render_rerun` | `shinywidgets[rerun]` | Stream multimodal, time-indexed data (3D, images, plots) | `references/widgets/rerun.md` |

### Networks

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| ipycytoscape | `render_ipycytoscape` | `shinywidgets[ipycytoscape]` | A networkx graph as a clickable network with communities | `references/widgets/ipycytoscape.md` |
| ipysigma | `render_ipysigma` | `shinywidgets[ipysigma]` | A GPU-accelerated, clickable network explorer | `references/widgets/ipysigma.md` |

### Input & drawing

| Widget | Renderer | Extra | Pick it for | Reference |
|---|---|---|---|---|
| drawdata | `render_drawdata` | `shinywidgets[drawdata]` | Draw a dataset with your mouse | `references/widgets/drawdata.md` |
| ipycanvas | `render_ipycanvas` | `shinywidgets[ipycanvas]` | Draw on a live HTML canvas, read mouse/keyboard events back | `references/widgets/ipycanvas.md` |
| ipyfilechooser | `render_ipyfilechooser` | `shinywidgets[ipyfilechooser]` | Browse/pick server-side files, sandboxed to a directory | `references/widgets/ipyfilechooser.md` |
