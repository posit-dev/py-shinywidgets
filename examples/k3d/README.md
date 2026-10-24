## k3d app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fk3d%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_k3d` adds over a static or exported 3D plot: a live WebGL scene that fills its container, can be edited in place from Shiny inputs without resetting the camera, and reports the camera position back to Python via `reactive_read()`.
