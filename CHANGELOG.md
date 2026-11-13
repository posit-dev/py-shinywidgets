# Change Log for shinywidgets

All notable changes to shinywidgets will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### New features

* Added more than 30 new `@render_*` decorators, bringing many more visualization and widget ecosystems into Shiny. Unless noted, each output fills its container in filling layouts and respects an explicit `output_widget(height=...)`, and the methods listed are reactive accessors (see the next item). Install each one's dependencies with its extra, e.g., `pip install 'shinywidgets[holoviews]'` (see the README for the full list).
  * `@render_bqplot` for [bqplot](https://bqplot.github.io/bqplot/) figures, including those built with `bqplot.pyplot`. Figures follow Shiny's light/dark theme. Accessors: `selected()`, `brush()`, and `selected_rows()` (the selected rows of a data frame at a mark's selected positions, ready for a table or download). (#278)
  * `@render_drawdata` for [drawdata](https://github.com/koaning/drawdata) drawing canvases. Users draw a dataset (or sculpt histogram bars), and Python sees every stroke via `reactive_read(widget, "data")`. See `examples/drawdata`. (#278)
  * `@render_embedding_atlas` for [Embedding Atlas](https://apple.github.io/embedding-atlas/) explorers (Python 3.11+). Accessors: `selected_rows()`, `predicate()`. (#278, #294)
  * `@render_geolibre` for the [GeoLibre](https://geolibre.app) GIS workbench. Project changes (e.g., `add_geojson()`, `set_center()`) update the live map in place, `on_click()` and `reactive_read(widget, "project")` bring interactions back to Python, and it works deployed, including layers read from the server's disk. (#341, #360)
  * `@render_holoviews` for [HoloViews](https://holoviews.org), [hvPlot](https://hvplot.holoviz.org), and [geoviews](https://geoviews.org) objects, including [datashader](https://datashader.org) plots that re-aggregate as you zoom and pan. Pass `responsive=True` to make plots fill their container. (#87, #250, #253, #278)
  * `@render_ipyaladin` for [ipyaladin](https://cds-astro.github.io/ipyaladin/) sky viewers. Accessors: `clicked_object()`, `selected()`, `target()`, `fov()`. (#278)
  * `@render_ipycanvas` for [ipycanvas](https://ipycanvas.readthedocs.io) canvases. Draw from Python at any time (including `asyncio`-driven animations) and handle mouse/touch events in Python callbacks. In a filling layout, the canvas keeps its pixel size and is centered rather than stretched. (#278)
  * `@render_ipycytoscape` for [ipycytoscape](https://github.com/cytoscape/ipycytoscape) network graphs, from a networkx graph or a `CytoscapeWidget`. Accessors: `clicked_node()`, `clicked_edge()`, `selected_nodes()`, `selected_edges()`. (#278)
  * `@render_ipydatagrid` for [ipydatagrid](https://github.com/bloomberg/ipydatagrid) data grids, from a pandas DataFrame or a `DataGrid` (requires ipydatagrid >= 1.2). Accessors: `selected()`, `clicked_cell()`, `edited_cell()`, `visible_data()`. (#99, #278)
  * `@render_ipyfilechooser` for [ipyfilechooser](https://github.com/crahan/ipyfilechooser) choosers for files on the server. Use `register_callback()` with a `reactive.value` to react to selections. (#245, #278)
  * `@render_ipyleaflet` for [ipyleaflet](https://ipyleaflet.readthedocs.io) maps and subclasses. Accessors: `bounds()`, `zoom()`, `center()`, `clicked()`, `drawn_features()`. Maps now respect an explicit `height` instead of always being 400px tall. (#278)
  * `@render_ipysigma` for WebGL network graphs with [ipysigma](https://github.com/medialab/ipysigma), from a networkx graph or a `Sigma` widget. The selected node is readable with `reactive_read()`. This is a widget-based option for [pyvis](https://pyvis.readthedocs.io) users. (#63, #278)
  * `@render_ipyvolume` for [ipyvolume](https://ipyvolume.readthedocs.io) 3D scatter, quiver, and volume plots, built with either the pylab API or direct construction. Accessor: `camera()`. (#278)
  * `@render_itables` for pandas and polars data frames as interactive [itables](https://itables.org) tables. Return an `itables.widget.ITable` to pass options such as `select=True`. Accessor: `selected()`. (#54, #278)
  * `@render_jscatter` for [jupyter-scatter](https://jupyter-scatter.dev) GPU-accelerated scatter plots. Accessors: `selected()` (e.g., to link brushing across plots and tables) and `selected_rows()` (the selected rows of the plot's data frame, ready for a table or download). (#278, #293)
  * `@render_k3d` for [k3d](https://k3d-jupyter.org) 3D plots. Accessor: `camera()`. (#278)
  * `@render_keplergl` for [kepler.gl](https://kepler.gl) maps, from a pandas `DataFrame`, a geopandas `GeoDataFrame`, or a `KeplerGl` widget. Use `reactive_read()` to react to the map's configuration. (#278)
  * `@render_leafmap` for [leafmap](https://leafmap.org) maps, covering its ipyleaflet (with the same accessors as `@render_ipyleaflet`), maplibre, plotly, and kepler.gl backends. Its folium and pydeck backends aren't widgets, so they raise an error that points to an alternative. (#278)
  * `@render_lonboard` for [lonboard](https://developmentseed.org/lonboard/) maps, from a `Map`, one or more layers, or any data `lonboard.viz()` accepts. Accessors: `view_state()`, `selected()`, `selected_bounds()`, `clicked()`, and `selected_rows()` (the picked row of a data frame, defaulting to the pickable layer's own data, ready for a table or download). (#278)
  * `@render_maplibre` for [maplibre](https://eoda-dev.github.io/py-maplibregl/) maps. Accessors: `view_state()`, `clicked()`, `drawn_features()`. Compared to maplibre's own Shiny bindings, maps fill their container (including `full_screen` cards), any effect can update a map in place (e.g., `.widget.set_paint_property()`), and the same code runs in Jupyter.
  * `@render_matplotlib` for matplotlib figures, covering anything that produces one (seaborn, `pandas.DataFrame.plot()`, scikit-learn displays, etc.), rendered as interactive [ipympl](https://matplotlib.org/ipympl/) widgets that resize with their container. Accessors: `clicked()`, `picked()`, `limits()`.
  * `@render_mols2grid` for [mols2grid](https://mols2grid.readthedocs.io) molecule grids, from a `MolGrid` or a DataFrame with a SMILES column. Accessors: `selected()`, and `clicked()` when `clicks=True`. Filter the grid from Python with `grid.grid.filter(mask)`. Requires an internet connection. (#55)
  * `@render_mosaic_widget` for [Mosaic](https://idl.uw.edu/mosaic/) dashboards of linked, DuckDB-backed views. Accessors: `params()`, `data()` (the rows matching the current selections, optionally narrowed with `filter_by=`). (#278, #403)
  * `@render_nglview` for [nglview](https://nglviewer.org/nglview/latest/) molecular viewers. Method calls like `.widget.add_representation()` update the viewer in place, picked atoms are readable with `reactive_read()`, and custom color schemes registered on `ColormakerRegistry` work in every session. (#57, #278)
  * `@render_niivue` for [NiiVue](https://niivue.com) neuroimaging viewers: multiplanar and 3D volume rendering with overlays and meshes. Colormap, opacity, and slice-type changes apply live via `.widget` methods. Accessor: `location()` (the crosshair's coordinates and voxel intensities).
  * `@render_obsplot` for [Observable Plot](https://observablehq.com/plot/) charts built with [pyobsplot](https://juba.github.io/pyobsplot/). Update charts in place with `.widget.spec = {...}`. (#359)
  * `@render_panel` for [panel](https://panel.holoviz.org) widgets and layouts, accepting anything `pn.panel()` accepts. Accessor: `param(name)`, which reads any Panel parameter reactively (e.g., `slider.param("value")` for a `pn.widgets.IntSlider`). (#82, #88, #253, #438)
  * `@render_perspective` for [Perspective](https://perspective-dev.github.io) viewers, from a pandas or polars DataFrame, a `perspective.Table`, or a `PerspectiveWidget`. Accessors: `filter()`, `view_config()`. To change the data, prefer `.widget.update()` (optionally after `.widget.clear()`) over re-rendering, since Perspective keeps hosted tables in memory. (#278)
  * `@render_plotnine` for [plotnine](https://plotnine.org) plots and compositions (e.g., `p1 | p2`), rendered as interactive ipympl widgets that plotnine re-lays out as they resize. Accessors: `clicked()`, `limits()`. (#278)
  * `@render_pygwalker` for [PyGWalker](https://docs.kanaries.net/pygwalker) data exploration, from a pandas DataFrame or a `walk()` widget. (#278)
  * `@render_pythreejs` for [pythreejs](https://pythreejs.readthedocs.io) 3D scenes. Accessor: `camera()`, which follows `OrbitControls` gestures. (#278)
  * `@render_pyvista` for [pyvista](https://pyvista.org) 3D plots (Python 3.11+). Scenes rotate, zoom, and pan in the browser without running a separate trame server. (#278)
  * `@render_quak` for [quak](https://github.com/manzt/quak) data tables, from any DataFrame-like object. Accessors: `sql()` (the current sort and filter as a SQL query), `data()`. (#278, #286)
  * `@render_reactable` for [reactable](https://machow.github.io/reactable-py/) tables, with client-side sorting, filtering, searching, pagination, selection, grouping, and expandable details. Accessors: `selected()`, `page()`, `sorted()`, `filtered()`, `search()`.
  * `@render_rerun` for [rerun](https://rerun.io) viewers of time-indexed multimodal data (Python 3.11+). Data logged to the viewer's `RecordingStream` streams live to the browser. Create the `RecordingStream` inside the render function, since rerun's global recording is shared by every session. Accessor: `selected()`. (#362)
  * `@render_vizarr` for [vizarr](https://github.com/hms-dbmi/vizarr) viewers of OME-NGFF (zarr) bioimages, from a local store or a URL. The camera syncs both ways via the `view_state` trait, and `add_image()` adds layers in place. Requires an internet connection. (#358)

  The DuckDB-backed renderers (`@render_embedding_atlas`, `@render_mosaic_widget`, `@render_quak`) lock down their DuckDB connection by default, so app visitors can't read or write server files through the widget; pass `allow_unrestricted_connection=True` to opt out. `@render_pygwalker`, which runs SQL sent from the browser, goes further: it refuses to render until DuckDB's default connection is locked down (see its docstring). (#278, #294, #395)

* Rendered outputs gain reactive accessors: methods that read what the user does in a widget, much like reading an input. Read one in a reactive function and the function re-runs when the user interacts:

  ```python
  @render_plotly
  def plot():
      return px.scatter(df, x="x", y="y")

  @render.data_frame
  def picked():
      return plot.selected()
  ```

  `@render_plotly` has `clicked()`, `hover()`, `selected()`, `brushed()`, `relayout()`, `double_clicked()`, `legend_clicked()`, and `visible_traces()`. `@render_altair` has `selected(name)` and `selected_rows(name)`. `@render_bokeh` has `selected()`, `selected_rows()`, `tapped()`, and `zoomed()`. Many of the new renderers have their own (see above). Accessors keep their value across re-renders. Continuous streams, such as a selection while the user drags, are debounced by 250 ms by default; adjust this with the decorator's `rate_policy` and `rate_delay` parameters. `.read(name)` reads an accessor, or any widget trait, by name. (#379, #437, #443)

* Added per-renderer extras, so you can install a decorator's widget dependencies in one command (e.g., `pip install 'shinywidgets[plotly]'` or `'shinywidgets[maplibre,bokeh]'`). See the README for the full list.

* Added `session_lifetime()`, a context manager for building widgets that outlive the current render, e.g., one cached widget per dataset that is shown again when the user switches back. (#258)

* Added `shared_lifetime()`, an experimental context manager for building one widget that every session displays. Any user's interaction changes it for everyone. (#348)

* ipyleaflet layers from [localtileserver](https://github.com/banesullivan/localtileserver)'s `get_leaflet_tile_layer()` now load in deployed apps (e.g., Posit Connect, shinyapps.io) with no extra code (requires localtileserver >= 1.0.0). Only rasters the app itself requested are readable. Set `SHINYWIDGETS_LOOPBACK_PROXY_DISABLE=1` to opt out. See `examples/localtileserver/`.

* Bokeh assets now load automatically, including for plots that use [extension models](https://docs.bokeh.org/en/latest/docs/user_guide/advanced/extensions.html) and apps mounted under a URL prefix. You no longer need `bokeh_dependency()` in your UI. (#88, #210, #255, #256)

* `@render_plotly` now accepts a Dash-style `(figure, config)` return value, where `config` is a dict of [Plotly.js config options](https://plotly.com/javascript/configuration-options/) (e.g., `{"displayModeBar": False}`). (#173)

* `@render_plotly` (and `@render_widget`) now warn when given a figure with animation frames, which `FigureWidget` silently drops. The warning points to a `@render.ui` + `fig.to_html()` workaround. (#156)

### Breaking changes

* shinywidgets now requires ipywidgets 8.1 or newer, and the bundled JavaScript widget manager was upgraded to `@jupyter-widgets/html-manager` 1.0. Together these fix many long-standing issues with ipywidgets 8 (see the bug fixes below). (#237, #259)
* shinywidgets now requires shiny 1.9.0 or newer. With it, widget updates made from a background thread (e.g., nglview's, or your own `threading.Thread`) reach the browser right away instead of waiting for the next unrelated input. (#377)
* shinywidgets now requires plotly 5.12 or newer for plotly widgets. With an older plotly, you now get an error explaining how to upgrade instead of a blank output. (#332)

### Deprecated

* `@render_pydeck` is deprecated: pydeck 0.9 removed its Jupyter widget, so no pydeck release that works with ipywidgets 8 can render through it. Returning a `pydeck.Deck` now raises an error that explains the alternatives. To keep using pydeck layers reactively, pass `pydeck.Layer` objects to a maplibre map's `add_deck_layers()` and render it with `@render_maplibre` (see `examples/pydeck/app.py`). For large data, consider `@render_lonboard`. For a static map, return `deck.show()` from shiny's `@render.ui`. (#187)
* `bokeh_dependency()` is deprecated, since Bokeh's assets now load automatically. Remove the call from your UI.

### Bug fixes

* A widget that fails after its render function returns (e.g., an Altair/VegaFusion chart without `vl-convert-python` installed) now shows the user an error notification instead of leaving the output blank. (#320)
* Fixed many issues with widgets nested inside other widgets and with widget outputs inserted dynamically (e.g., `output_widget()` inside `@render.ui`). With ipywidgets 8, these either didn't render at all (e.g., a Plotly `FigureWidget` or a styled `HTML` widget inside an ipyleaflet popup) or rendered while logging errors like `Class HTMLStyleModel not found` (e.g., ipyleaflet popups, `WidgetControl` children, and leafmap legends). (#75, #101, #137, #157, #194, #237)
* Re-rendering, replacing, hiding/showing, or removing widget outputs no longer leaks memory on the server or in the browser. Re-rendered widgets, and the data they hold, are now freed right away instead of when the session ends. (#246, #258, #260, #261, #262, #263, #303, #405) Related fixes:
  * pythreejs widgets no longer cause Shiny sessions to hang indefinitely with ipywidgets 8. (#244)
  * Re-showing a widget output hidden by `@render.ui` (or removed with `remove_ui()` and re-inserted) no longer hangs for 30 seconds if the widget changed while hidden. (#260)
  * Re-rendering an ipyleaflet map no longer throws page errors. (#260)
  * Re-rendering a widget constructed with an explicit `model_id` no longer leaves the output blank. (#263)
  * Returning a widget that belongs to another session (e.g., one cached in a module-level variable) now raises a clear error pointing to `session_lifetime()` and `shared_lifetime()`, instead of a blank output after 30 seconds. Returning a widget closed by an earlier render raises a similar error. (#258, #262)
  * Re-rendering stays fast with many concurrent sessions or large widgets (e.g., large GeoJSON payloads or Altair specs). (#261)
* Widgets built on [ipyreact](https://github.com/widgetti/ipyreact) now work. Previously, importing such a package after shinywidgets raised "shinywidgets requires that all ipywidgets be constructed within an active Shiny session". (#160)
* Widget subclasses defined directly in your app module (e.g., `class ConfettiButton(ipyreact.ValueWidget)` in `app.py`) now load their JavaScript dependencies correctly. Previously, subclassing a widget whose `_model_module` doesn't match its nbextension registration (ipyreact being the known example) silently produced a broken widget with no Python-side error. (#414)
* Widgets that update their own state from the browser several times in a row no longer have newer values rolled back by stale ones. This fixes, for example, kepler.gl maps rendering blank or with duplicated layers. (#309)
* Widget methods that message the browser are no longer silently ignored when called before the output finishes rendering, e.g., k3d's `start_auto_play()` in the render function, or mapwidget's `add_call()` in an effect that runs right after a re-render. (#415)
* Widgets whose JavaScript creates extra models in the browser (e.g., bqplot's toolbar, pythreejs lights) no longer raise `TraitError`s about unresolved `IPY_MODEL_` references.
* Exceptions raised in widget callbacks triggered from the browser (e.g., an `on_click` handler or a trait observer) are now logged to the server console instead of silently disappearing. (#304)
* Re-rendering a widget output no longer briefly flashes the previous content before the new widget appears, a regression in 0.8.2. (#318)
* `@render_plotly` outputs with an explicit height (e.g., `output_widget("fig", height="300px")`) now use that height instead of 360px, and the compact default margins now survive an in-place template change (e.g., `fig.widget.update_layout(template="plotly_dark")`). (#401)
* Plotly widgets no longer render as a blank output when an outdated copy of the plotly JavaScript is installed in another Jupyter data directory (e.g., `/usr/local/share/jupyter`). (#332)
* Fixed several sizing issues with bokeh-based outputs (`@render_bokeh`, `@render_panel`, and `@render_holoviews`):
  * A bokeh `figure` given an explicit `width`, `height`, `sizing_mode`, or `aspect_ratio` now keeps that size instead of always stretching to fill its output.
  * A plot that stretches to fill no longer collapses to a sliver inside an output with an explicit height.
  * Content with its own size no longer reserves empty space below it in non-filling layouts.
* An Altair chart in an output with an explicit height no longer collapses to a sliver.
* Observers registered on an `altair.JupyterChart`'s `selections` or `params` before returning it from `@render_altair` (e.g., `jchart.selections.observe(fn, ["brush"])`) now fire.
* An output that once rendered a filling widget no longer keeps stretching later widgets that have their own height. (#300)
* An ipyleaflet map with many markers no longer turns gray and loses its markers when re-rendered. (#215, #237)
* Fonts used by widget CSS, such as FontAwesome icons, no longer fail to load. (#237)
* Error messages for objects that can't be rendered as widgets are clearer. Subclasses of supported types (e.g., `leafmap.deck.Map`) get their base package's guidance, unsupported builtins (e.g., a string) get the intended `TypeError` instead of an `AttributeError`, and messages no longer include huge object reprs. (#287)
* Reading `.widget` or `.value` inside the output's own render function now raises an error instead of silently returning the previous render's widget or value.
* With shinywidgets imported, constructing a `pydeck.Deck` outside a Shiny session (e.g., at module level) no longer raises "shinywidgets requires that all ipywidgets be constructed within an active Shiny session".
* ipydatagrid grids (and other widgets that detect JupyterLab's theme) now follow the app's light/dark color mode instead of always rendering light. Toggling the mode re-themes grids rendered after the toggle; grids already on screen keep their palette, an ipydatagrid limitation. (#439)

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
