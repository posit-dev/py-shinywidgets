## leafmap app

What `@render_leafmap` offers over a static map or an embedded HTML export: a fully interactive [leafmap](https://leafmap.org) map whose state (e.g., `zoom`, `center`, `bounds`) is readable with `reactive_read()`, and whose layers and tools can be updated in place from the server without re-rendering. It renders any of leafmap's widget-backed backends: `leafmap.Map` (ipyleaflet, used here), `leafmap.maplibregl.Map`, and `leafmap.kepler.Map`.
