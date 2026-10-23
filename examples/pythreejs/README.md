## pythreejs app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fpythreejs%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_pythreejs` adds over a static 3D render (e.g., pyvista's screenshots) or a heavier 3D server (e.g., trame): a live three.js scene that fills its container, traits you can update in place from Python (geometry, materials, lights), and orbit-controls camera state synced back to Python via `reactive_read()` — no extra server or JavaScript required.
