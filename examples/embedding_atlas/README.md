## Embedding Atlas app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fembedding_atlas%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_embedding_atlas` adds over embedding-atlas's own standalone viewer (`embedding-atlas` CLI): the explorer lives inside your Shiny app, and the filter a user builds in the browser (by selecting points, clicking chart bars, or writing SQL predicates) is synced to Python through `reactive_read()`, so other outputs can react to the selected rows. The embedding view needs a browser with WebGPU support.
