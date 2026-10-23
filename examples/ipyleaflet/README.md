## ipyleaflet app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fipyleaflet%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_ipyleaflet` offers over a static map or an embedded HTML export: a fully interactive [ipyleaflet](https://ipyleaflet.readthedocs.io) map whose state (e.g., `zoom`, `center`, `bounds`) is readable with `reactive_read()`, and whose traits, layers, and controls can be updated in place from the server without re-rendering. It also works with ipyleaflet-based packages like [leafmap](https://leafmap.org).
