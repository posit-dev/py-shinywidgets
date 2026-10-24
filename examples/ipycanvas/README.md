## ipycanvas app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fipycanvas%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_ipycanvas` adds over the alternatives: unlike `@render.plot`/`@render_matplotlib`, you draw on a raw browser canvas directly from Python -- pixel buffers (`put_image_data()`), shapes, and free-form sketches -- and unlike a static canvas in `@render.ui`, mouse and touch events fire Python callbacks and Python can keep drawing after render (e.g., animations and games driven by `asyncio` tasks).
