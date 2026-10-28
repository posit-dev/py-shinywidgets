## vizarr app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fvizarr%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_vizarr` adds: a pan/zoom WebGL viewer for OME-NGFF (zarr) bioimages. Point `add_image()` at a local zarr store and chunks are served to the browser on demand over the widget comm — no tiling server needed — or at a remote URL, which the browser fetches directly. The camera (`view_state`) syncs both ways: read it with `reactive_read()` to drive reactives from pan/zoom, or set it to fly the viewer to a region of interest. Note the viewer loads its JavaScript from a CDN, so it requires an internet connection.
