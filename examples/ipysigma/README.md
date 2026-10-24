## ipysigma app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fipysigma%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

What `@render_ipysigma` adds for network graphs (and for [pyvis](https://pyvis.readthedocs.io) users, who have no widget route into Shiny): a WebGL renderer ([sigma.js](https://www.sigmajs.org)) that stays responsive on graphs with thousands of nodes, filling layouts, and `reactive_read()` access to the selected node so clicking a node in the graph can drive the rest of the app.
