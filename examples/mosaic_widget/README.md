## mosaic_widget app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fmosaic_widget%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_mosaic_widget` adds over a static plot: linked views that cross-filter each other as you brush them (Mosaic runs the queries against DuckDB, so large tables stay responsive), while `reactive_read()` and `widget.data()` give your Python code the current selection, as a filtered DuckDB relation, to drive other Shiny outputs.
