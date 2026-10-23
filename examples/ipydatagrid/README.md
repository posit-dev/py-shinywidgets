## ipydatagrid app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fipydatagrid%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_ipydatagrid` adds over `@render.data_frame` and `@render.table`: a canvas-based grid that stays smooth with very large tables, plus spreadsheet-style interactions (click-and-drag cell, row, or column selection, in-place editing, and per-column renderers for things like bar charts and heatmap colors) whose state, such as `selections`, you can read reactively with `reactive_read()`.
