## perspective app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fperspective%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_perspective` adds over a plain `@render.data_frame`: an interactive [Perspective](https://perspective-dev.github.io) viewer where users pivot, sort, filter, and switch between grid and chart views, with that viewer state readable from Python via `reactive_read()` and new rows streamed into the live viewer with `.widget.update()`.
