# Change Log for shinywidgets

All notable changes to shinywidgets will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### New features

* ipyleaflet layers created by [localtileserver](https://github.com/banesullivan/localtileserver)'s `get_leaflet_tile_layer()` now work in deployed apps with no extra code (requires localtileserver >= 1.0.0). shinywidgets mounts a same-origin loopback proxy for the layer's in-process tile server (as it already did for geolibre) and rewrites the layer's tile URLs onto it -- including restyle URLs from `client.get_tile_url()` -- so tiles load locally, on Posit Connect, and on shinyapps.io. Because localtileserver's tile API takes unauthenticated raster-source query parameters (`filename`, `files`, `url`; arbitrary local raster read + SSRF once the port is proxied), the proxy only forwards requests carrying a per-client capability token, so the app (and only the app) decides which rasters are readable. Set `SHINYWIDGETS_LOOPBACK_PROXY_DISABLE=1` to opt out. See `examples/localtileserver/`.
* Added per-renderer extras, so each `@render_*` decorator's widget dependencies can be installed in one command (e.g., `pip install 'shinywidgets[plotly]'` or `'shinywidgets[maplibre,bokeh]'`). See the README for the full list.
* `@render_jscatter`, `@render_bqplot`, `@render_itables`, `@render_ipydatagrid`, and `@render_embedding_atlas` outputs gain reactive accessor methods for what the user does in the widget, readable in a reactive function much like an `input` value: `selection()` (jscatter's selected points; bqplot's per-mark selections; embedding_atlas's filtered rows), `brush()` (bqplot's brush region), `selected_rows()` (itables' selected rows), `selections()`, `cell_clicked()`, `cell_edited()`, and `visible_data()` (ipydatagrid's displayed rows), and `predicate()` (embedding_atlas's cross-filter as a SQL expression).
* Added `shared_lifetime()`, a context manager for constructing one widget that every session displays (any user's interaction changes it for everyone, and it is never freed). Widgets that ipyvue and ipyvuetify share across the whole process (e.g., `ipyvuetify.theme` and custom `VueTemplate`s) now work across re-renders and sessions instead of hanging for 30 seconds. Ownership errors now explain both `session_lifetime()` and `shared_lifetime()`. (#348)

### Bug fixes

* Widgets built on [ipyreact](https://github.com/widgetti/ipyreact) (e.g., [reactable-py](https://github.com/machow/reactable-py)) now work. `ipyreact.define_module()` and `define_import_map()` construct process-global `Module`/`ImportMap` widgets (usually at import time) whose browser models register ES modules with the import shim; previously, importing such a package after shinywidgets raised "shinywidgets requires that all ipywidgets be constructed within an active Shiny session", and any widget depending on those modules never rendered. These dependency widgets are now mirrored into every session, like `shared_lifetime()` widgets. (#160)
* Widgets whose JavaScript creates models in the browser (e.g., bqplot's toolbar PanZoom, pythreejs light targets and shadows) now get a Python counterpart, so their state syncs instead of raising `TraitError`s about unresolved `IPY_MODEL_` references, and models the browser closes are closed on the server too.
* Widget updates made from a background thread (e.g., nglview's remote-call thread, or your own `threading.Thread`) are now delivered to the browser promptly instead of waiting for the next unrelated input.
* Improved error messages when an object can't be rendered as a widget: subclasses defined in another package (e.g., `leafmap.deck.Map`, which subclasses pydeck's `Deck`) now route to the coercer for their base class's package, so they get that package's specific guidance instead of the generic "Don't know how to coerce" error. Error messages also no longer dump enormous object reprs (e.g., a pydeck `Deck`'s entire JSON spec) into the output.
* Fixed widget asset lookup to use the first matching Jupyter data directory, respecting Jupyter's search order. Previously, a stale JavaScript bundle in a later directory (e.g., `/usr/local/share/jupyter`) could override the active environment's bundle and cause plotly 5 `FigureWidget`s to render as a blank output. (#332)

### Deprecated

* `bokeh_dependency()` is deprecated and will be removed in a future release. Bokeh's JavaScript/CSS assets are included automatically with every bokeh-based output (including dynamically created ones), so the call can simply be removed from your UI.

### Changed

* shinywidgets now requires ipywidgets 8.1 or newer, and the bundled JavaScript widget manager (`@jupyter-widgets/html-manager`) was upgraded from 0.20 to 1.0. Together these fix a wide range of long-standing issues with ipywidgets 8 (see the bug fixes below). (#237, #259)
* shinywidgets now requires plotly >= 5.12 (the first release whose `FigureWidget` frontend supports ipywidgets 8). Constructing a plotly widget with an older plotly raises an error explaining how to upgrade, instead of rendering a blank output with no error. (#332)
* shinywidgets now requires shiny 1.9.0 or newer, which sends widget updates made outside the reactive graph (e.g., from a background thread) to the browser right away. (#377)
* The `ipydatagrid` extra now requires ipydatagrid 1.2.0 or newer. Earlier releases construct ipywidgets while the package is being imported, so `import ipydatagrid` after `import shinywidgets` raised "shinywidgets requires that all ipywidgets be constructed within an active Shiny session". (#99)

### Deprecated

* `@render_pydeck` is deprecated. pydeck v0.9 (April 2024) removed its Jupyter widget, so `@render_pydeck` (and `@render_widget` with a `pydeck.Deck`) can't render a map with any pydeck release that works with ipywidgets 8. It now emits a `DeprecationWarning`, and returning a `Deck` raises a `TypeError` that explains the alternatives up front (previously the advice was wrong, and with pandas 3 a cryptic `vars()` error from pydeck hid it). To keep using pydeck layers reactively, pass `pydeck.Layer` objects to a maplibre map's `add_deck_layers()` and render it with `@render_maplibre` (see `examples/pydeck/app.py`). For large data, consider `@render_lonboard`. For a static map, use shiny's `@render.ui` and return `deck.show()`. (#187)

### New features

* Added several new `@render_*` decorators that bring more visualization and widget ecosystems into shinywidgets:
  * `@render_panel` for [panel](https://panel.holoviz.org) widgets and layouts (e.g., `pn.widgets.Tabulator`). Like Panel itself, it renders anything `pn.panel()` accepts (e.g., a `pn.viewable.Viewer` or `pn.custom.JSComponent` subclass, a string, a DataFrame, or a figure). All required JS/CSS assets are served automatically. (#82, #88, #253)
  * `@render_holoviews` for [HoloViews](https://holoviews.org), [hvPlot](https://hvplot.holoviz.org), and [geoviews](https://geoviews.org) objects, including [datashader](https://datashader.org)-rasterized plots, which re-aggregate as you zoom and pan. Pass `responsive=True` to make plots fill their container. (#87, #250, #253, #278)
  * `@render_ipycanvas` for [ipycanvas](https://ipycanvas.readthedocs.io) canvases. Draw on the browser canvas from Python at any time (including animations driven by `asyncio` tasks), handle mouse/touch events in Python callbacks (e.g., interactive drawing), and send images efficiently with `put_image_data()`. In a filling layout, the canvas keeps its pixel size and is centered (shrinking to fit) rather than stretched. (#278)
  * `@render_ipyaladin` for [ipyaladin](https://cds-astro.github.io/ipyaladin/) interactive sky viewers. The viewer fills its container unless given an explicit `height`, and `reactive_read()` gives you access to the view's center and field of view (via the `_target`/`_fov` traits) as the user pans and zooms. (#278)
  * `@render_ipyleaflet` for [ipyleaflet](https://ipyleaflet.readthedocs.io) maps and subclasses like [leafmap](https://leafmap.org)'s `Map`, with typed access to the map via `.widget` and map state (e.g., `zoom`, `center`, `bounds`) via `reactive_read()`. Maps now also respect an explicit `height` on `output_widget()` instead of always being 400px tall. (#278)
  * `@render_jscatter` for [jupyter-scatter](https://jupyter-scatter.dev) GPU-accelerated scatter plots. Plots fit their output (in a filling layout or with an explicit `output_widget(height=)`) unless they have a height of their own, and `reactive_read(widget, "selection")` brings the selected points back to Python, e.g., to link brushing across plots and tables. (#278, #293)
  * `@render_k3d` for [k3d](https://k3d-jupyter.org) 3D plots. Plots fill their container in filling layouts (unless `k3d.plot(height=...)` is set), and the plot's state (e.g., `camera`) can be read reactively with `reactive_read()`. (#278)
  * `@render_keplergl` for [kepler.gl](https://kepler.gl) maps. Return a pandas `DataFrame` or geopandas `GeoDataFrame` (or a `keplergl.KeplerGl` widget) to get the full interactive kepler.gl interface, and use `reactive_read()` to react to its configuration. The map fills its container (or takes an explicit `height`) instead of staying at 400px. (#278)
  * `@render_leafmap` for [leafmap](https://leafmap.org) maps. Renders leafmap's widget backends -- `leafmap.Map` (an ipyleaflet map, including leafmap's toolbar and basemap gallery), `leafmap.maplibregl.Map`, `leafmap.plotlymap.Map` (a Plotly `FigureWidget`), and `leafmap.kepler.Map` -- and treats leafmap's 600px default height as unset, so maps fill their container. Its folium and pydeck backends aren't ipywidgets, so they raise a `TypeError` that points to an alternative. The `leafmap` extra installs a compatible Plotly version, and `examples/leafmap/app_plotly.py` demonstrates in-place zoom and marker updates. (#278)
  * `@render_lonboard` for [lonboard](https://developmentseed.org/lonboard/) maps. Return a `Map`, one or more layers, or any data `lonboard.viz()` accepts (e.g., a GeoPandas `GeoDataFrame` or a GeoArrow table). Maps fill their container unless given an explicit `height`, and `reactive_read()` gives you access to map state (e.g., `view_state`, or a layer's `selected_index`). (#278)
  * `@render_maplibre` for [maplibre](https://eoda-dev.github.io/py-maplibregl/) maps. Compared to maplibre's own Shiny bindings, maps fill their container (including `full_screen` cards) unless given an explicit height, any effect can update a map in place via `.widget` methods (e.g., `set_paint_property()`), and the same code runs in Jupyter. `reactive_read()` gives you access to map state (e.g., `view_state`, `clicked`).
  * `@render_matplotlib` for matplotlib figures -- covering anything that produces one (seaborn, `pandas.DataFrame.plot()`, scikit-learn displays, etc.) -- rendered as interactive [ipympl](https://matplotlib.org/ipympl/) widgets. Figures fill and resize with their container in filling layouts, and repeated re-renders don't leak pyplot figures.
  * `@render_nglview` for [nglview](https://nglviewer.org/nglview/latest/) molecular structure viewers. The viewer fills its container (and tracks it as the window resizes) or respects an explicit `height`, picking an atom is readable from Python with `reactive_read()`, method calls like `.widget.add_representation()` update the displayed viewer in place, and custom color schemes registered on nglview's `ColormakerRegistry` work in every session. (#57, #278)
  * `@render_perspective` for [Perspective](https://perspective-dev.github.io) viewers, accepting a pandas or polars DataFrame, a `perspective.Table`, or a `PerspectiveWidget`. Viewer state is readable with `reactive_read()`. Perspective keeps hosted tables in memory, so prefer `.widget.update()` (streams new rows) or `.widget.clear()` followed by `.widget.update()` (swaps the data) over re-rendering from a new DataFrame. DataFrames are hosted on a Perspective server of their own, so other sessions can't reach their data from the browser. (#278)
  * `@render_pythreejs` for [pythreejs](https://pythreejs.readthedocs.io) 3D scenes. Scenes fill (and resize with) their container unless the `Renderer` has an explicit `width`/`height`, and orbiting with `OrbitControls` syncs the camera back to Python, where `reactive_read()` can pick it up. (#278)
  * `@render_pyvista` for [pyvista](https://pyvista.org) 3D plots. A `pyvista.Plotter` is exported via pyvista's `jupyter_backend="html"` into a self-contained, client-side vtk.js view, so scenes can be rotated, zoomed, and panned in the browser without running a separate trame server. Views fill their container unless given an explicit height. (#278)
  * `@render_bqplot` for [bqplot](https://bqplot.github.io/bqplot/) figures, including those built with `bqplot.pyplot`. Figures fill their container, follow Shiny's light/dark theme, and respect an explicit `height`; interaction state like `Scatter.selected` is available through `reactive_read()`. (#278)
  * `@render_mosaic_widget` for [Mosaic](https://idl.uw.edu/mosaic/) dashboards of linked, DuckDB-backed views (`mosaic_widget.MosaicWidget`). The widget's `params` (the current selections) can be read reactively with `reactive_read()`, and `widget.data()` returns the selected rows. (#278)
  * `@render_ipydatagrid` for pandas DataFrames (or `ipydatagrid.DataGrid` widgets), rendered as interactive [ipydatagrid](https://github.com/bloomberg/ipydatagrid) data grids. Grids fill their container in filling layouts and fit an explicit `height`, and `reactive_read()` gives you access to grid state like `selections`. (#278)
  * `@render_itables` for pandas and polars data frames as interactive [itables](https://itables.org) (DataTables) tables. Return an `itables.widget.ITable` to pass itables options such as `select=True`, then use `reactive_read()` on the widget's `selected_rows` to react to row selection. Tables fill their container and scroll their rows. itables' bundle replaces the global `$` with its own jQuery, so once an itables table is shown, shinywidgets keeps `$` pointing at the page's `jQuery` (lending it the DataTables plugin, so `$.fn.dataTable` helpers in itables JS options keep working). (#54, #278)
  * `@render_plotnine` for [plotnine](https://plotnine.org) plots and plot compositions (e.g., `p1 | p2`), rendered as interactive [ipympl](https://matplotlib.org/ipympl/) widgets. In filling layouts, plots fill their container and are re-laid out by plotnine (legend, labels, and all) as it resizes. With an explicit output `height`, the figure isn't fitted to it, so set `theme(figure_size=...)` to match (the default figure size gets clipped by smaller outputs). `@render_matplotlib` and `@render_widget` also accept plotnine plots. (#278)
  * `@render_pygwalker` for [PyGWalker](https://docs.kanaries.net/pygwalker) data exploration apps. Return a pandas `DataFrame`, or a widget from `pygwalker.api.anywidget.walk()` to pass PyGWalker options. The explorer fills its container (scrolling when the container is shorter than its UI) and computes in the Python process, so only the first 500 rows are sent to the browser up front. Because PyGWalker runs the SQL that the browser sends, rendering requires DuckDB's default connection to be locked down (`enable_external_access = false` and `lock_configuration = true`) and rejects the requests that would let a visitor set the server's Kanaries token or open a `gw://` link on the server. The SQL the browser sends is validated too: only single `SELECT` statements against the widget's own data are allowed, since the connection (and its table namespace) is shared by every PyGWalker widget in the process. A polars `DataFrame` is accepted when the installed pygwalker can read it (every release so far can't with polars >= 1.0 -- the fix is merged upstream and due in pygwalker 0.6 -- so it's rejected with a hint to convert it). (#278)
  * `@render_embedding_atlas` for [Embedding Atlas](https://apple.github.io/embedding-atlas/) explorers: return an `EmbeddingAtlasWidget` (requires Python 3.11+), and use `reactive_read()` to react to the filter a user builds in the browser. The explorer fills its container in filling layouts and respects explicit heights. Since the explorer queries its DuckDB connection with SQL sent from the browser, the renderer locks the connection down by default (`SET enable_external_access = false`; `SET lock_configuration = true`), so visitors can't read or write server files; pass `allow_unrestricted_connection=True` to opt out. (#278, #294)
  * `@render_ipysigma` for network graphs, either a networkx graph or an [ipysigma](https://github.com/medialab/ipysigma) `Sigma` widget. It's a WebGL network renderer that fills its container in filling layouts (unless the widget sets its own `height`) and, via `reactive_read()`, reports the selected node back to Python -- a widget-based option for [pyvis](https://pyvis.readthedocs.io) users. (#63, #278)
  * `@render_ipyvolume` for [ipyvolume](https://ipyvolume.readthedocs.io) 3D scatter/quiver/volume plots. Both the pylab API (`ipv.quickscatter()`, `ipv.gcf()`) and direct construction (`ipyvolume.Figure` + `ipyvolume.widgets.Scatter`/etc.) work, including for outputs that re-render. The WebGL canvas fills (and resizes with) its container unless the figure has an explicit size, and rectangle/lasso selections and camera state round-trip to Python. (#278)
  * `@render_ipycytoscape` for network graphs with [ipycytoscape](https://github.com/cytoscape/ipycytoscape). Return a `networkx` graph (or a `CytoscapeWidget`) and it fills its container, or follows an explicit `height`. Register `CytoscapeWidget.on()` callbacks in the render function to feed node clicks into a `reactive.value`. (#278)
  * `@render_quak` for [quak](https://github.com/manzt/quak) data tables, built from any DataFrame-like object (pandas, polars, pyarrow, etc.). The table fills its container (or respects an explicit height), and `reactive_read()` gives you the table's current sort and filter state as a SQL query. (#278, #286)
  * `@render_geolibre` for [GeoLibre](https://geolibre.app) maps. You get the full GeoLibre GIS workbench as a Shiny output: project mutations (`add_geojson()`, `set_center()`, layer styling) update the live map in place, and `on_click()` callbacks plus `reactive_read(widget, "project")` bring browser interactions back to Python. The map fills its container unless given an explicit `height`, and it works deployed (shinyapps.io, Posit Connect), including layers read from files on the server's disk. geolibre's blocking command methods (e.g., `fly_to()`, `get_center()`) can't run on Shiny's event-loop thread, but they work from a worker thread (e.g., inside `reactive.extended_task`). (#341)
  * `@render_drawdata` for [drawdata](https://github.com/koaning/drawdata) `ScatterWidget`/`BarWidget` drawing canvases. Users draw a dataset with the brush (or sculpt histogram bars) and Python sees every batch via `reactive_read(widget, "data")` -- great for teach-a-model-by-drawing apps (see `examples/drawdata`, which re-fits a k-NN on every stroke). The canvas fills its container's width while preserving the drawing's aspect ratio. (#278)
  * `@render_obsplot` for [Observable Plot](https://observablehq.com/plot/) charts built with [pyobsplot](https://juba.github.io/pyobsplot/). Return the widget from `Plot.plot()`; pyobsplot has no browser-to-Python sync, so there's nothing for `reactive_read()`, but charts update in place via `.widget.spec = {...}`. Charts shrink to fit their container but never grow past the spec width (default 640px), and filtered pandas DataFrames need `df.reset_index(drop=True)` to serialize with pyobsplot 0.5.4. (#359)
  * `@render_vizarr` for [vizarr](https://github.com/hms-dbmi/vizarr) viewers of OME-NGFF (zarr) bioimages. Local zarr stores are served chunk-by-chunk over the widget comm (or pass a URL string and the browser fetches it directly), the camera syncs both ways via the `view_state` trait (`reactive_read()` it, or set it to fly to a region), and `add_image()` can be called in place to add layers without a re-render. The viewer fills filling layouts, respects an explicit `output_widget(height=...)`, and honors its own `height` trait otherwise. Requires an internet connection (the viewer's JavaScript loads from a CDN). (#358)
  * `@render_rerun` for [rerun](https://rerun.io) viewers -- a multimodal viewer for time-indexed data (3D scenes, images, tensors, timeseries, text logs) with a scrubbable timeline that shows how it all evolved together. Data logged to the viewer's `rr.RecordingStream` streams live to the browser, both during the initial render and from later reactive updates, and viewer interactions (selection, timeline, play/pause) drive reactivity back in Python via `Viewer.on_event()` plus a `reactive.Value` (events aren't synced traits, so `reactive_read()` can't see them). Create the `RecordingStream` inside the render function -- rerun's usual `rr.init()`/`rr.log()` pattern logs to a global recording shared by every session -- and leave the viewer's size at its default to have it fill its container (an explicit `output_widget(height=...)` is respected too). Requires Python 3.11+. (#362)
  * `@render_ipyfilechooser` for [ipyfilechooser](https://github.com/crahan/ipyfilechooser) file choosers, letting users browse and select files on the server. A default-constructed `FileChooser()` now works out of the box (its import-time default `Layout` is swapped for a per-instance copy), and since the chooser's `selected`/`selected_path`/`selected_filename` are plain properties rather than widget traits, use `register_callback()` with a `reactive.value` to react to selections. (#245, #278)
  * `@render_niivue` for [NiiVue](https://niivue.com) neuroimaging viewers ([ipyniivue](https://github.com/niivue/ipyniivue)): multiplanar and 3D GPU volume rendering with overlays and meshes. Colormap, gamma, opacity, and slice-type changes apply live via `.widget` methods (no re-render), and clicking or dragging the crosshair reports millimeter coordinates and voxel intensities back to Python through the widget's `on_location_change` callback (the crosshair doesn't sync as a trait, so `reactive_read()` can't see it). Don't pass `height=` to `NiiVue()` -- the viewer fills its container, or follows an explicit `output_widget(height=...)`.
* Bokeh plots using [extension models](https://docs.bokeh.org/en/latest/docs/user_guide/advanced/extensions.html) now work out of the box -- their assets are served automatically. (#88, #256)
* `@render_plotly` now accepts a Dash-style `(figure, config)` tuple return value, where `config` is a dict of [Plotly.js config options](https://plotly.com/javascript/configuration-options/) (e.g., `{"displayModeBar": False}`). The config is merged over plotly's defaults and takes precedence over shinywidgets' own defaults. (#173)
* Added `session_lifetime()`, a context manager for constructing widgets that should outlive the current render (for example, one cached widget per dataset that is displayed again when the user switches back). Attempting to return a widget that was already closed by an earlier render now raises an error pointing to `session_lifetime()` instead of timing out in the browser. (#258)

### Improvements

* Bokeh widgets now load the installed BokehJS assets automatically in Core and Express apps, including apps mounted under a URL prefix. Adding `bokeh_dependency()` to the UI is no longer required. (#210, #255)
* `@render_plotly` (and `@render_widget`) now warn when given a plotly figure with frames (i.e., an animation), since `FigureWidget` doesn't support frames and silently drops them. The warning points to the `@render.ui` + `fig.to_html()` workaround. (#156)

### Bug fixes

* Widgets that update their own state from the browser several times in a row no longer have newer values rolled back by stale echoes from Python. This fixes, for example, kepler.gl maps rendering blank or with duplicated layers. (#309)
* Exceptions raised in widget callbacks triggered from the browser (e.g., an `on_click` handler, a trait observer, or a plotly click callback) are now logged to the server console (via the `shinywidgets` logger) instead of silently disappearing. (#304)
* Fixed numerous issues with widgets nested inside other widgets and widget outputs inserted dynamically (e.g., `output_widget()` inside `@render.ui`). With ipywidgets 8, these either didn't render at all (e.g., an `HTML` child with a `style`, or a Plotly `FigureWidget`, inside an ipyleaflet popup) or rendered while logging errors like `Class HTMLStyleModel not found` (e.g., ipyleaflet popups, `WidgetControl` children, and leafmap legends). (#75, #101, #137, #157, #194, #237)
* Substantially overhauled widget cleanup and lifecycle management. Re-rendering, replacing, hiding/showing, or removing widget outputs no longer leaks widgets, views, or event listeners on the server or in the browser (#246, #258, #260, #261, #262, #263), and many related failure modes are fixed:
  * pythreejs widgets no longer cause Shiny sessions to hang indefinitely with ipywidgets 8. (#244)
  * Every re-render of an output no longer leaks a few helper models for the rest of the session. (#258)
  * Re-rendered widgets (and the data they hold, e.g. figure images or DataFrames) are now freed right away instead of staying in server memory until the session ends. (#303)
  * Re-showing a widget output hidden by `@render.ui` (or removed with `remove_ui()` and re-inserted) no longer hangs for 30 seconds when the widget changed while hidden. (#260)
  * Re-rendering an ipyleaflet map no longer throws uncaught page errors or leaks the old map's listeners and child views. (#260)
  * Re-rendering a widget constructed with an explicit `model_id` no longer leaves the output blank. (#263)
  * Returning a widget that belongs to another Shiny session (for example, one cached in a module-level variable so every visitor shares it) now raises an immediate, clear error instead of leaving the output stuck recalculating for 30 seconds and then blank. (#262)
  * Re-rendering stays fast with many concurrent sessions or large widgets (e.g., large GeoJSON payloads or Altair specs). (#261)
  * Fixed additional cleanup edge cases involving widgets closed before opening, background tasks, and cross-session references. (#258, #261)
* Returning an unsupported builtin value (e.g., a string, number, or dict) from a `@render_widget` function now raises the intended "Don't know how to coerce ..." `TypeError` instead of a confusing `AttributeError: ... has no attribute '__module__'`. (#287)
* With shinywidgets imported, constructing a `pydeck.Deck` (pydeck v0.9 or newer) no longer raises "shinywidgets requires that all ipywidgets be constructed within an active Shiny session" outside a session (e.g., a module-level `Deck` in a core app), and no longer leaks unused widget comms (and browser console errors) inside a session (e.g., a static `deck.show()` map in `@render.ui`).
* Fixed an issue where an ipyleaflet map with many markers could turn gray and show no markers when re-rendered. (#215, #237)
* Fixed an issue where fonts used by widget CSS, such as FontAwesome icons, failed to load (404). (#237)
* Fixed an issue where an Altair chart in an output with an explicit height (e.g., `output_widget("plot", height="300px")`) collapsed to a sliver instead of filling that height.
* Fixed an issue where observers registered on an `altair.JupyterChart`'s `selections` or `params` before returning it from `@render_altair` (e.g., `jchart.selections.observe(fn, ["brush"])`, as documented by Altair) never fired.
* Fixed an issue where an output that once rendered a filling widget kept stretching later widgets to fill it, even ones given their own height (e.g., `layout.height="200px"`). (#300)
* Fixed several sizing issues with bokeh-based outputs (`@render_bokeh`, `@render_panel`, and `@render_holoviews`):
  * A bokeh `figure` given an explicit `width`, `height`, `sizing_mode`, or `aspect_ratio` now keeps that size, instead of always being stretched to fill its output.
  * A plot that stretches to fill (e.g., a default `figure`, or a HoloViews plot with `responsive=True`) no longer collapses to a sliver inside an output with an explicit height (e.g., `output_widget(height="300px")`).
  * Content with a size of its own (e.g., a fixed-size figure, a HoloViews plot without `responsive=True`, or a panel `Markdown` pane) no longer reserves empty space below it in non-filling layouts.
* Fixed a regression (introduced alongside the busy-indicator fix in 0.8.2, #243) where re-rendering a widget output could show a brief flash of the previous (stale) content: Shiny stops showing the recalculating spinner, and un-hides the old content, as soon as the new value arrives -- before shinywidgets has had a chance to build and attach the new view. The output now stays hidden across that gap and reveals only once the new view has actually rendered, so widgets whose view takes noticeable time to construct (e.g., Bokeh, HoloViews/datashader, ipyleaflet, lonboard) no longer pop back to the old content before swapping to the new one. (#318)

## [0.8.2] - 2026-10-15

* Fixed an issue where Shiny's busy indicator (spinner) did not appear over widget outputs while recalculating, because the output element's inline `visibility: hidden` also hid the spinner. Recalculating widget outputs now mirror Shiny's own handling of htmlwidgets, keeping the element (and spinner) visible while hiding the stale widget content. (#213)
* Fixed an issue where async `@render_widget` functions could tie a widget to the wrong output when Shiny runs outputs concurrently (posit-dev/py-shiny#2549): re-rendering one output could close the widget shown by another, and some old widgets were never closed. Old widgets made by a `@render_widget` inside a Shiny module are now also closed when the output re-renders. (#241, #242)

## [0.8.1] - 2026-05-06

* Fixed a performance regression where Plotly widgets took ~5 seconds to appear because the `plotly_afterplot` event listener was attached after Plotly had already fired it, causing the reveal to wait for a timeout fallback. (#239)

## [0.8.0] - 2026-04-13

* Fixed an issue where Plotly `FigureWidget` outputs in filling layouts could briefly render at the wrong height and then visibly jump to their final size on initial render or rerender. Plotly outputs now wait for Plotly's own resize cycle before being revealed, and Playwright coverage was added for the first visible Plotly paint. (#208, #236)
* Fixed an issue where browser-originated widget buffers were not decoded back into bytes on the server before being forwarded to ipywidgets, which broke binary `update` and `custom` comm traffic from widgets running in the browser. Added Playwright regression coverage for both paths. (#151, #230)
* Hardened widget teardown for re-rendered views so replacing a widget no longer emits known cleanup noise like `Widget is not attached` or dead-comm sync errors. Added Playwright regression coverage for repeated rerenders across plotly, altair, bokeh, and ipyleaflet, and wired that suite into GitHub Actions on Python 3.12. (#223)
* Fixed an issue where parent widget updates could arrive before newly introduced child widget models were opened client-side, causing one-interaction lag or dropped updates in cases like `ipyleaflet` marker insertion. (#225)

## [0.7.2] - 2026-04-09

* Fixed an issue where widgets created inside `reactive.isolate()` could be cleaned up too early because cleanup was registered on the wrong reactive context. This also fixes plotly widgets disappearing in the `model-score` example. (#222)

## [0.7.1] - 2026-01-22

* Fixed an issue where anywidget-based widgets (like plotly) failed to initialize with `websockets>=16.0`. (#218)

## [0.7.0] - 2025-07-14

* `datetime.date()` values are properly JSON serialized. (#204)
* Fixed an issue were callbacks on a plotly `FigureWidget` object were getting dropped with recent versions of plotly. (#207, thanks @simeonschwarzenberg)

## [0.6.2] - 2025-05-21

* Eliminate the possibility of a single `@render_widget` output from keeping a view of prior renders. (#196)

## [0.6.1] - 2025-05-21

* Fixed an issue introduced by v0.6.0 where cleanup wasn't happening when it should be. (#195)

## [0.6.0] - 2025-05-19

* Widgets initialized inside a `reactive.effect()` are no longer automatically removed when the effect invalidates. (#191)

## [0.5.2]  - 2025-04-04

* Constructing a widget inside of a `shiny.reactive.ExtendedTask()` no longer errors out. (#188)

## [0.5.1] - 2025-01-30

* Fixes 'AttributeError: object has no attribute "_repr_mimebundle_"'. (#184)

## [0.5.0] - 2025-01-29

* Updates to accomodate the new plotly v6.0.0 release. (#182)
* Fixed an issue with plotly graphs sometimes not getting fully removed from the DOM. (#178)
* Added `anywidget` as a package dependency since it's needed now for `altair` and `plotly` (and installing this packages won't necessarily install `anywidget`). (#183)
* Fixed an issue with ipyleaflet erroring out when attempting to read the `.model_id` property of a closed widget object. (#179)
* Fixed an issue where altair charts would sometimes render to a 0 height after being shown, hidden, and then shown again. (#180)

## [0.4.2] - 2024-12-18

* Fixed an issue where `@render_widget` would sometimes incorrectly render a new widget without removing the old one. (#167)

## [0.4.1] - 2024-12-17

* Fixed a Python 3.9 compatibility issue.

## [0.4.0] - 2024-12-16

* Fixed a memory leak issue. (#167)

## [0.3.4] - 2024-10-29

* Fixed an issue where widgets would sometimes fail to render in a Quarto document. (#159)
* Fixed an issue where importing shinywidgets before a ipywidget implementation can sometimes error in a Shiny Express app. (#163)

## [0.3.3] - 2024-08-13

* Fixed a bug with receiving binary data on the frontend, which gets [quak](https://github.com/manzt/quak) and [mosaic-widget](https://idl.uw.edu/mosaic/jupyter/) working with `@render_widget`. (#152)

## [0.3.2] - 2024-04-16

* Fixed a bug with multiple altair outputs not working inside a `@shiny.render.ui` decorator. (#140)
* `@render_widget` no longer errors out when giving a `altair.FacetChart` class. (#142)
* `@render_widget` no longer fails to serialize `decimal.Decimal` objects. (#138)

## [0.3.1] - 2024-03-01

* Widgets no longer have a "flash" of incorrect size when first rendered. (#133)
* `@render_widget` now works properly with `Widget`s that aren't `DOMWidget`s (i.e., widgets that aren't meant to be displayed directly). As a result, you can now use `@render_widget` to gain a reference to the widget instance, and then use that reference to update the widget's value. (#133)

## [0.3.0] - 2024-01-25

* The `@render_widget` decorator now attaches a `widget` (and `value`) attribute to the function it decorates. This allows for easier access to the widget instance (or value), and eliminates the need for `register_widget` (which is now soft deprecated).  (#119)
* Added decorators for notable packages that require coercion to the `Widget` class: `@render_altair`, `@render_bokeh`, `@render_plotly`, and `@render_pydeck`. Using these decorators (over `@render_widget`) helps with typing on the `widget` attribute. (#119)
* The `.properties()` method on `altair.Chart` object now works as expected again. (#129)
* Reduce default plot margins on plotly graphs.

## [0.2.4] - 2023-11-20

* Fixed several issues with filling layout behavior introduced in 0.2.3. (#124, #125)
* `reactive_read()` now throws a more informative error when attempting to read non-existing or non-trait attributes. (#120)

## [0.2.3] - 2023-11-13

* Widgets now `fill` inside of a `fillable` container by default. For examples, see the [ipyleaflet](https://github.com/posit-dev/py-shinywidgets/blob/main/examples/ipyleaflet/app.py), [plotly](https://github.com/posit-dev/py-shinywidgets/blob/main/examples/plotly/app.py), or other [output](https://github.com/posit-dev/py-shinywidgets/blob/main/examples/outputs/app.py) examples. If this intelligent filling isn't desirable, either provide a `height` or `fillable=False` on `output_widget()`. (#115)
* `as_widget()` uses the new `altair.JupyterChart()` to coerce `altair.Chart()` into a `ipywidgets.widgets.Widget` instance. (#113)

## [0.2.2] - 2023-10-31

* `@render_widget` now builds on `shiny`'s `render.transformer` infrastructure, and as a result, it works more seamlessly in `shiny.express` mode. (#110)
* Closed #104: Officially support for Python 3.7.

## [0.2.1] - 2023-05-15

* Actually export `as_widget()` (it was mistakenly not exported in 0.2.0).

## [0.2.0] - 2023-04-13

* Closed #43: Fixed an issue where widgets would sometimes not load in a dynamic UI context. (#91, #93)
* Closed #14: Added a `bokeh_dependency()` function to simplify use of bokeh widgets. (#85)
* Closed #89: Exported `as_widget()`, which helps to coerce objects into ipywidgets, and is especially helpful for creating ipywidget objects before passing to `register_widget()` (this way, the ipywidget can then be updated in-place and/or used as a reactive value (`reactive_read()`)). (#90)
* Closed #94: New `SHINYWIDGETS_CDN` and `SHINYWIDGETS_CDN_ONLY` environment variables were added to more easily specify the CDN provider. Also, the default provider has changed from <unpkg.com> to <cdn.jsdelivr.net/npm> (#95)
* A warning is no longer issued (by default) when the path to a local widget extension is not found. This is because, if an internet connection is available, the widget assests are still loaded via CDN. To restore the previous behavior, set the `SHINYWIDGETS_EXTENSION_WARNING` environment variable to `"true"`. (#95)
* Closed #86: Fixed an issue with `{ipyleaflet}` sometimes becoming unresponsive due to too many mouse move event messages being sent to the server. (#98)

## [0.1.6] - 2023-03-24

* Closed #79: make shinywidgets compatible with ipywidgets 8.0.5. (#66)

## [0.1.5] - 2023-03-10

* Stopped use of `_package_dir` function from `htmltools`.

* Miscellaneous typing fixes and updates.

## [0.1.4] - 2022-12-12

### Bug fixes

* Fixed installation problems on Python 3.7. (#68)


## [0.1.3] - 2022-12-08

### Bug fixes

* Closed #65: get shinywidgets working with ipywidgets 8.0.3. (#66)


## [0.1.2] - 2022-07-27

Initial release of shinywidgets
