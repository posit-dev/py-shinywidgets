## PyGWalker app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fpygwalker%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_pygwalker` adds over embedding PyGWalker's static HTML export: a Tableau-style drag-and-drop explorer that fills its card, runs its queries in the Python process (so the data doesn't have to be shipped to the browser), and can be re-rendered reactively, here whenever the selected dataset changes.
