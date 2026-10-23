## ipyaladin app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fipyaladin%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_ipyaladin` adds over embedding Aladin Lite's HTML/JS yourself: the viewer becomes a reactive citizen of the app — panning and zooming the sky updates Python reactively (via `reactive_read()` on the `_target`/`_fov` traits, e.g. to drive a catalog query for the visible region), and inputs can retarget, re-survey, or re-zoom the rendered viewer in place without re-rendering it.
