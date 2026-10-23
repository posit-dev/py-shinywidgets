## ipyvolume app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fipyvolume%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_ipyvolume` adds over embedding a static HTML export (e.g., `@render.ui` with `ipv.embed.embed_html()`): the plot participates in Shiny's reactive graph (re-render on input changes, or update traits in place via `.widget`), the WebGL canvas fills and resizes with its container (including `full_screen` cards), and interaction state — rectangle/lasso selections and the camera — round-trips to Python (`on_selection` callbacks and `reactive_read()`), which a static export can't do.
