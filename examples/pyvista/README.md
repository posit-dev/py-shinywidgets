## pyvista app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fpyvista%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

`@render_pyvista` turns a `pyvista.Plotter` into an interactive 3D view (rotate/zoom/pan in the browser) without running a separate trame server: pyvista's `jupyter_backend="html"` export embeds a self-contained, client-side vtk.js scene in the widget. The trade-off is that no widget state syncs back to Python and every re-render re-sends the whole scene, so for server-driven interactivity (picking, server-side rendering), use pyvista's `jupyter_backend="trame"` behind an iframe instead.
