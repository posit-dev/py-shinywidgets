## geoviews app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fgeoviews%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

geoviews objects are holoviews elements, so `@render_holoviews` renders them with no extra setup. What the widget route offers over embedding the map as static HTML: a live Bokeh map you can pan, zoom, and hover, and `DynamicMap` widgets that call back into Python. Add `.opts(responsive=True)` to make the map fill its container. (geoviews 1.15 needs `cartopy<0.26`.)
