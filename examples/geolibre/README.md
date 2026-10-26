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

* The widget embeds the bundled app from a localhost server inside the Python
  process, so the browser must run on (or be able to reach) that host -- it
  works with a local `shiny run`, not with a deployed app.
* geolibre's blocking command methods (`fly_to()`, `fit_bounds()`,
  `get_center()`, ...) don't work in Shiny -- they wait for the app's reply
  by pumping a Jupyter kernel event loop that doesn't exist. Use the
  project-mutation alternatives (`set_center()`, `fit_project_bounds()`, ...)
  shown here.
