## lonboard app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Flonboard%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_lonboard` adds over embedding a static HTML export (e.g., `@render.ui` with lonboard's `Map.to_html()`): the data stays in the browser while you restyle layers in place (no re-render or re-sending of the points), and the map's view state and the clicked point are available to the rest of the app through `reactive_read()`. lonboard draws hundreds of thousands of points on the GPU from Arrow data, and `@render_lonboard` accepts a GeoPandas `GeoDataFrame` directly.
