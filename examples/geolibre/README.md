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

Two limitations to know about:

* Layers read from files on the server's disk (e.g., `add_raster()` of a
  local GeoTIFF) are served from a localhost server inside the Python process,
  so they only render for browsers on that host -- they don't work in deployed
  apps (URL-based layers like this example's are unaffected).
* geolibre's blocking command methods (`fly_to()`, `fit_bounds()`,
  `get_center()`, ...) don't work in Shiny -- they wait for the app's reply
  by pumping a Jupyter kernel event loop that doesn't exist. Use the
  project-mutation alternatives (`set_center()`, `fit_project_bounds()`, ...)
  shown here.
