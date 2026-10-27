# GeoLibre example

Run with:

```sh
pip install -r requirements.txt
shiny run app.py
```

What `@render_geolibre` offers over a static map export: the full
[GeoLibre](https://geolibre.app) GIS app embedded in the page, with
two-way sync -- recenter the map from Python (`set_center()`), add and restyle
layers in place, and read clicks (`on_click()`) or the whole live project
(`reactive_read(map.widget, "project")`, which invalidates on every pan/zoom)
back in Python.

One limitation to know about: geolibre's blocking command methods
(`fly_to()`, `fit_bounds()`, `get_center()`, ...) can never run on Shiny's
event-loop thread (a render function, `reactive.calc`, or any
`reactive.effect`/observer) -- the wait would block the very loop that must
deliver the reply. They do work from a worker thread, e.g. inside
`reactive.extended_task` via `run_in_executor`, with a geolibre release
that polls for the reply instead of pumping a Jupyter kernel event loop
(current releases raise a `jupyter_ui_poll` error; see
https://github.com/opengeos/GeoLibre/pull/3266). Otherwise, use the
project-mutation alternatives (`set_center()`, `fit_project_bounds()`, ...)
shown here.

(Layers read from files on the server's disk, e.g. `add_raster()` of a local
GeoTIFF, *do* work in deployed apps: shinywidgets proxies geolibre's
localhost server at `/proxy/{port}/`, so the browser reaches it same-origin.)
