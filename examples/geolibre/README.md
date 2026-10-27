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
containing https://github.com/opengeos/GeoLibre/pull/3266 (merged upstream;
the first release after 3.5.1), which polls for the reply instead of pumping
a Jupyter kernel event loop. On geolibre <= 3.5.1 they raise a
`jupyter_ui_poll` error wherever they're called, so prefer the
project-mutation alternatives (`set_center()`, `fit_project_bounds()`, ...).
The app shows both patterns: `set_center()` on selection change, and
`fly_to()` from an `extended_task` (the "Fly there" button).

(Layers read from files on the server's disk, e.g. `add_raster()` of a local
GeoTIFF, *do* work in deployed apps: shinywidgets proxies geolibre's
localhost server at `/proxy/{port}/`, so the browser reaches it same-origin.)
