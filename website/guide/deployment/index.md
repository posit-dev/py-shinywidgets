---
title: Deployment
summary: >
  A shinywidgets app deploys like any Shiny app. List each widget's extra in `requirements.txt`, check which
  widgets load JavaScript from the internet, and know what to expect from Shinylive.
audience: >
  Anyone putting a shinywidgets app on a server, or exporting one to run in the browser with Shinylive.
widgets: [plotly, mols2grid]
description: "A shinywidgets app deploys like any Shiny app. List each widget's extra in `requirements.txt`, check which widgets load JavaScript from the internet, and know what to expect from Shinylive."
---

A shinywidgets app is a Shiny app, so it deploys anywhere Shiny does: Posit Connect, Posit Connect Cloud,
shinyapps.io, or your own server. Shiny's [deployment overview](https://shiny.posit.co/py/get-started/deploy.html)
covers the options. This page covers what's different when widgets are involved.

## List the extras in `requirements.txt`

Most deployment targets install your app's packages from its `requirements.txt`. Name the same extras you
installed locally, so each widget library comes along:

```
shinywidgets[plotly,itables]
```

## Without internet access

Most widget libraries ship their JavaScript inside the Python package, and shinywidgets serves it from your
server. Two kinds of widget instead have the *reader's browser* download JavaScript from a CDN, so on a network
that can't reach the internet they only partly draw, or stay empty (see
[Troubleshooting](../troubleshooting/index.md#the-widgets-javascript-couldnt-load)):

- **Widgets that download part of themselves**, like [mols2grid](../../widgets/mols2grid/index.md), which loads
  its molecule-drawing library from unpkg. That's up to the widget library, so check its docs for an offline
  option.
- **Classic ipywidgets whose package doesn't include their JavaScript**, which shinywidgets loads from a CDN.
  To find them, start your app with the environment variable `SHINYWIDGETS_EXTENSION_WARNING=true`. The
  server then logs a warning for each one:

  ```
  UserWarning: Couldn't find local path to widget extension for <class '...'>.
  Since a CDN fallback is provided, the widget will still render if an internet
  connection is available.
  ```

  To load them from somewhere your readers can reach, such as an internal npm mirror, set `SHINYWIDGETS_CDN`
  to its URL. The default is `https://cdn.jsdelivr.net/npm/`, and files are requested as
  `<url>/<package>@<version>/dist/index.js`, the layout npm CDNs use.

## Shinylive

[Shinylive](https://shiny.posit.co/py/get-started/shinylive.html) runs a Shiny app entirely in the browser, with no
Python server. shinywidgets works there: the first app's
[`01_render.py`](../first-app/examples/01_render.py), exported with `shinylive export`, renders its chart
in the browser.

Shinylive only finds packages on its own for a set of common ones built into it, so add a `requirements.txt`
next to your app that names the rest, including shinywidgets and each widget library:

```
shinywidgets
plotly
pandas
```

A widget works under Shinylive only if its library can be installed in the browser, which rules out libraries
that depend on compiled code the browser's Python doesn't provide. Try yours before you rely on it.
