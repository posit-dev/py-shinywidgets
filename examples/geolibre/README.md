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

One limitation to know about: geolibre's command methods (`fly_to()`,
`get_center()`, ...) wait for a reply from the app, and the reply is only
delivered once the current `reactive.effect` finishes -- so they can't be
called (or their `*_async()` variants awaited) inside a render function,
`reactive.calc`, or `reactive.effect`. Instead, `await` the `*_async()`
variants (`map.fly_to_async(...)`, ...) inside a `reactive.extended_task`,
which runs outside that flush. Where a fire-and-forget alternative exists
(`set_center()`, `fit_project_bounds()`, ...), it's the cheaper option. The
app shows both patterns: `set_center()` on selection change, and
`fly_to_async()` in an `extended_task` (the "Fly there" button).

(Layers read from files on the server's disk, e.g. `add_raster()` of a local
GeoTIFF, *do* work in deployed apps: shinywidgets proxies geolibre's
localhost server at `/proxy/{port}/`, so the browser reaches it same-origin.)
