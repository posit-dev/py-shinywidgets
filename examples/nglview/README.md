## nglview app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fnglview%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_nglview` adds over embedding `nglview.write_html()` output with `ui.HTML` (which has no picking or reactive state): a full interactive 3D molecular viewer (rotate, zoom, pick atoms) that fills its card and sends the picked atom back to Python via `reactive_read()`.
