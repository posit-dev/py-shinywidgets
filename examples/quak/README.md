## quak app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fquak%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_quak` adds over `@render.data_frame`: an interactive table with column histograms for exploring a dataset, whose current sort and filter state you can read back with `reactive_read()` (as a SQL query, or as the matching rows via `.widget.data()`) to drive the rest of your app.
