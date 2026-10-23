## mapwidget app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fmapwidget%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

Why `@render_mapwidget` instead of `@render_maplibre` or `@render_ipyleaflet`?
[mapwidget](https://github.com/opengeos/mapwidget) wraps several map backends
(MapLibre GL, Leaflet, OpenLayers, plus token-based Mapbox and Cesium) behind
one tiny anywidget package with a uniform Python API, so the same app can swap
rendering engines (or go from a 2D map to a 3D globe) by changing one class.
The trade-off is depth: mapwidget exposes little more than a basemap, method
forwarding (`add_call()` on the maplibre backend), and synced `center`/`zoom`/
`bounds`/`clicked_latlng` traits -- if you need layers, sources, and controls,
use the dedicated `maplibre` or `ipyleaflet` packages instead.
