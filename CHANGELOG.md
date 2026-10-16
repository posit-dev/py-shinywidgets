# Change Log for shinywidgets

All notable changes to shinywidgets will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### New features

* Added a `render_maplibre()` renderer, and `as_widget()` now coerces a [maplibre](https://eoda-dev.github.io/py-maplibregl/) `Map` into its `MapWidget` (requires `pip install 'maplibre[anywidget]'`). Note that maplibre also ships its own native Shiny bindings, but the widget route gives you `reactive_read()` access to map state (e.g., `view_state`, `clicked`).

### Breaking changes

* shinywidgets now requires ipywidgets 8.1 or newer. (#237, #259)

### New features

* Bokeh documents that reference [bokeh extension](https://docs.bokeh.org/en/latest/docs/user_guide/advanced/extensions.html) models (any package shipping a `bokeh.ext.json`/prebuilt `dist` bundle) now have their extension assets served automatically. (#88, #256)
* Added support for [panel](https://panel.holoviz.org) widgets and layouts (e.g., `pn.widgets.Tabulator`) via the new `@render_panel` decorator or `@render_widget`. Required JS/CSS assets (panel's model bundle, third-party assets like Tabulator, and model stylesheets) are served automatically. (#82, #88, #253)
* Added support for [hvPlot](https://hvplot.holoviz.org) (and holoviews) objects via the new `@render_hvplot` decorator. (#87, #253)
* Added `session_lifetime()`, a context manager for constructing widgets that should outlive the current render (for example, one cached widget per dataset that is displayed again when the user switches back). Widgets constructed while an output renders are still closed when that render is invalidated; returning such a closed widget from a later render now raises an error that points to `session_lifetime()` instead of timing out in the browser. (#258)

### Bug fixes

* Fixed a leak where the `Layout`/`Style` models that ipywidgets creates lazily while serializing a widget were never closed: every re-render of an output leaked a few models on the server and in the browser for the rest of the session. They now share the cleanup of the widget that created them, unless a live widget still references them. (#258)
* Fixed an issue where closing a widget before its comm had opened (for example, re-rendering an output twice in one flush) reopened the widget anyway. (#258)
* Widget comm messages are now always sent through the session that created the widget, and each session routes client messages only to its own widgets. (#258)
* Fixed further widget cleanup gaps found after #258: a widget still referenced by a live widget (e.g. a container) when its render was invalidated could stay open forever, even after that reference was later dropped; a widget built by a background task after its render had already returned could leak until the session ended; and a widget could crash a later session with `AttributeError: 'NoneType' object has no attribute 'comm_id'` if something still referenced it after its own session had ended. (#261)
* The per-render cleanup sweep added in #258 now scales with a session's own widgets rather than every widget across every session, and only follows traits that can actually hold a widget reference (skipping large opaque payloads like GeoJSON `data` or Altair specs). This keeps re-rendering fast with many concurrent sessions or large widgets. (#261)
* Returning a widget that belongs to another Shiny session (for example, one cached in a module-level variable so every visitor shares it) used to leave that session's output stuck recalculating for 30 seconds and then blank. It now raises an immediate, clear error instead, whether the foreign or closed widget is returned directly or nested inside a freshly built container. (#262)
* Fixed an issue where re-rendering a widget constructed with an explicit `model_id` left the output blank: the old widget's `comm_close` is sent after the replacement's `comm_open` (by design, to avoid flicker), so the browser tore the new model down by id. A close is now suppressed when a newer comm has re-registered the id by send time. (#263)
* Bokeh widgets now load the installed BokehJS assets automatically in Core and Express apps, including apps mounted under a URL prefix. Adding `bokeh_dependency()` to the UI is no longer required. (#210, #255)
* Fixed an issue where widgets nested inside other widgets didn't work reliably with ipywidgets 8. Depending on the widget, they either didn't render at all (e.g., an `HTML` child with a `style`, or a Plotly `FigureWidget`, inside an ipyleaflet popup) or rendered while logging errors like `Class HTMLStyleModel not found` (e.g., ipyleaflet popups, `WidgetControl` children, and leafmap legends). Widget outputs inserted dynamically, such as `output_widget()` inside `@render.ui`, had the same problem. The cause was that shinywidgets still bundled the ipywidgets 7-era JavaScript widget manager (`@jupyter-widgets/html-manager` 0.20); it now uses 1.0. (#75, #101, #137, #157, #194, #237)
* Fixed an issue where an ipyleaflet map with many markers could turn gray and show no markers when re-rendered. (#215, #237)
* Fixed an issue where fonts used by widget CSS, such as FontAwesome icons, failed to load (404). (#237)
* Replacing, clearing, or showing an error in a widget output now removes its previous view through the widget lifecycle, so detached views do not remain tracked by the browser manager. Reusing the same widget across renders keeps its model alive. (#246)
* Re-showing a widget output hidden by `@render.ui` (or removed with `remove_ui()` and re-inserted) no longer hangs for 30 seconds when the widget changed while hidden. (#260)
* Outputs removed by dynamic UI now release their widget views instead of leaking one per hide/show cycle. (#260)
* Re-rendering an ipyleaflet map no longer throws uncaught page errors or leaks the old map's listeners and child views. (#260)
* A child view that finishes creating after its parent was removed (e.g., dynamic UI removed the output mid-render) is now torn down instead of leaking. (#260)
* Widget views removed by dynamic UI now get the same widget-specific teardown as views removed at comm close (e.g., `destroy()` for plotly <6 `FigureWidget`s). (#260)

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
