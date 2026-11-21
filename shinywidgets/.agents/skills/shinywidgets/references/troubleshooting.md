# Troubleshooting

## Overview

When a widget doesn't show up, it's almost always one of two things: the
widget library isn't installed, or its JavaScript couldn't load in the
browser. Don't assume it's a shinywidgets bug — check these first.

## The widget library isn't installed

shinywidgets doesn't install widget libraries itself; each one is an extra
(`pip install 'shinywidgets[<name>]'`, e.g. `shinywidgets[plotly]`).
Without it, the import that needs the library raises an ordinary
`ModuleNotFoundError`. If shinywidgets itself is the one importing it (e.g.
coercing a data frame to a table), the error names the exact extra to
install:

```
Install the itables package to use data frames with shinywidgets (pip install 'shinywidgets[itables]').
```

## The widget's JavaScript couldn't load

Every widget has a JS half that runs in the reader's browser. shinywidgets
usually serves it from the Python environment, but two kinds of widget need
*internet access* for it instead:

- **Widgets that download part of themselves from a CDN**, in Jupyter too —
  mols2grid loads its molecule-drawing library from unpkg.
- **Classic ipywidgets whose package doesn't include their JavaScript** —
  shinywidgets loads those from a CDN itself.

If the reader's browser can't reach that CDN, the widget only partly draws
or stays empty, and the browser console shows a failed resource load (e.g.
`Failed to load resource: net::ERR_FAILED`). On a deployment target without
internet access, find which widgets need a CDN by starting the app with
`SHINYWIDGETS_EXTENSION_WARNING=true` (or `shinywidgets.config(extension_warning=True)`
before the first render) — the server then logs, per widget class:

```
UserWarning: Couldn't find local path to widget extension for <class '...'>.
Since a CDN fallback is provided, the widget will still render if an internet
connection is available.
```

Point that fallback at a reachable mirror with `SHINYWIDGETS_CDN=<url>` (or
`shinywidgets.config(cdn=...)`, called before the UI is built) — the default
is `https://cdn.jsdelivr.net/npm/`, requested as
`<url>/<package>@<version>/dist/index.js`.

## Deploying an app with widgets

A shinywidgets app deploys like any Shiny app (Posit Connect, shinyapps.io,
your own server). List every widget's extra in `requirements.txt`:

```
shinywidgets[plotly,itables]
```

**Shinylive** (running the app entirely in the browser, no Python server)
works for widgets whose library can install in the browser — anything
depending on compiled code the browser's Python doesn't provide won't. Add
a `requirements.txt` next to the app naming shinywidgets and each widget
library explicitly; Shinylive only auto-resolves a small built-in set.

## Common mistakes

- Assuming a blank widget is a shinywidgets bug before checking the extra is
  installed and the browser console for a failed CDN request.
- Deploying without listing every widget's extra in `requirements.txt`.
- Relying on a CDN-dependent widget (mols2grid, a classic ipywidget with no
  bundled JS) on a network with no internet access, without first checking
  `SHINYWIDGETS_EXTENSION_WARNING` or setting `SHINYWIDGETS_CDN`.

**More:** <https://shinywidgets.org/guide/troubleshooting/>,
<https://shinywidgets.org/guide/deployment/>
