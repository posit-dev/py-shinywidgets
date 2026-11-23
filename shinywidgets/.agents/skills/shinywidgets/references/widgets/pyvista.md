# PyVista (`render_pyvista`)

## Overview

`pip install 'shinywidgets[pyvista]'` (Python 3.11–3.14 only; on other
versions the extra silently installs without pyvista). Turn a pyvista `Plotter` into an
interactive, client-side 3D view (VTK meshes/volumes/point clouds for
CFD, geoscience, medical) — rotate, zoom, pan with no server round-trip.
Accepts a `pyvista.Plotter` (coerced via `jupyter_backend="html"`) or the
exported `trame_pyvista.jupyter.EmbeddableWidget` directly. On a headless
server, set `pyvista.OFF_SCREEN = True` before plotting.

## Quick start

```python
import pyvista as pv
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True


@render_pyvista
def plot():
    pl = pv.Plotter()
    pl.add_mesh(pv.Sphere())
    return pl
```

**Return the `Plotter` itself — never call `Plotter.show()`.** Outside
Jupyter, `show()` ignores `jupyter_backend`, returns `None`, and the
output renders nothing. In a filling layout the view fills its container
unless given an explicit `height`.

## Accessors

None — the export is a self-contained, client-side vtk.js view; no widget
state is synced back to Python, so there's nothing to `reactive_read()`.
For server-driven interactivity, use pyvista's `jupyter_backend="trame"`
with a trame server embedded via `shiny.ui.tags.iframe` instead (shinywidgets
can't host trame's own websocket server).

## Updating in place

None — the scene can't be updated via `.widget`; re-render instead. The
vtk.js runtime ships once per session (shared by every pyvista output), so
each re-render only embeds the exported scene, keeping input-driven
re-renders relatively cheap — though very large scenes (millions of cells)
still produce multi-MB exports, so prefer fewer, larger re-renders for
those.

## Gotchas

- **Current regression**: a shared, process-wide viewer widget
  (trame-pyvista 0.3.x) breaks multi-session apps — a fix exists on an
  unmerged upstream branch, not yet on main.
- If you pre-build the widget (`show_trame(pl, mode="html")`), pass
  `width="100%", height="100%"` or it keeps the plotter's pixel
  `window_size` instead of filling the container.

**More:** <https://shinywidgets.org/widgets/pyvista/>

Written against `pyvista` 0.x.
