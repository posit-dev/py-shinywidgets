## PyGWalker app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fpygwalker%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_pygwalker` adds over embedding PyGWalker's static HTML export: a Tableau-style drag-and-drop explorer that fills its card, runs its queries in the Python process (so the data doesn't have to be shipped to the browser), and can be re-rendered reactively, here whenever the selected dataset changes.

Because PyGWalker's queries are SQL sent from the browser and run in your Python process, this app turns off PyGWalker's telemetry and locks down DuckDB's default connection so that visitors can't read or write files on the server. Read the security note in the `render_pygwalker` documentation before deploying an app like this to people you don't trust.
