## leafmap app

What `@render_leafmap` offers over a static map or an embedded HTML export: a fully interactive [leafmap](https://leafmap.org) map whose state (e.g., `zoom`, `center`, `bounds` on the ipyleaflet backend) is readable with `reactive_read()`, and whose layers and tools can be updated in place from the server without re-rendering. It renders leafmap's widget-backed backends: `leafmap.Map` (ipyleaflet, used in `app.py`), `leafmap.maplibregl.Map`, `leafmap.plotlymap.Map`, and `leafmap.kepler.Map`.

### Plotly backend

Install `shinywidgets[leafmap]` and run `shiny run app_plotly.py` for the Plotly
backend. Its `Map` is already a `FigureWidget`; the zoom and color controls
update the same map in place. The leafmap extra selects Plotly >=5.12 and <7.

Plotly's existing `mapbox._derived` validation error can appear during browser
map feedback in both Plotly 5 and 6. The example demonstrates rendering and
Python-driven updates; it does not depend on reading pan state back from Plotly.
