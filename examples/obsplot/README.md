## obsplot app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fobsplot%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_obsplot` adds over a static chart: [pyobsplot](https://juba.github.io/pyobsplot/)'s browser-side interactions (tooltips, crosshairs) work as-is, and assigning a new specification to `plot.widget.spec` updates the chart in place from Python, without re-rendering the output.
