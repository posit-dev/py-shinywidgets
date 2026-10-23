## datashader app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fdatashader%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_holoviews` adds for [datashader](https://datashader.org) over a static datashader image (e.g., via `@render.image`) or a regular scatter plot: you can plot millions of points, since only an image-sized aggregate is sent to the browser (not every point), and zooming or panning re-runs datashader on the server for just the visible region, so detail keeps emerging as you zoom in rather than the image getting blurry.
