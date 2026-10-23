## bqplot app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fbqplot%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_bqplot` adds over a static plot: bqplot's interactions (brushing, click selection, panning and zooming) update traits like `Scatter.selected` in the browser, and `reactive_read()` turns those into reactive values that drive the rest of your app, such as a table of the selected rows.
