# NGLView (`render_nglview`)

## Overview

`pip install 'shinywidgets[nglview]'`. A WebGL molecular structure
viewer — proteins, nucleic acids, trajectories — as a reactive Shiny
output. Accepts an `nglview.NGLWidget` (from `nglview.show_file()`,
`show_text()`, or `show_url()`).

## Quick start

```python
import nglview
from shinywidgets import render_nglview

@render_nglview
def viewer():
    return nglview.show_url("rcsb://1crn")
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `camera_orientation()` | Flattened 4x4 camera orientation matrix | `None` (opt-in) |

Opt in with `listen_to=["camera_orientation"]` — nglview streams the
matrix every ~100ms while the camera moves, so the trait is muted unless
declared; debounced 250ms by default once enabled. For other viewer state
(the picked atom, trajectory frame), use `.read(...)`: `viewer.read("picked")`.

## Updating in place

Use `.widget` methods — `add_representation(...)`, `.frame = ...`,
`clear_representations()` — changes reach the browser even though nglview
sends them from a background thread (requires shiny >= 1.9):

```python
from shiny import reactive

@reactive.effect
def _advance_frame():
    viewer.widget.frame = input.frame()
```

## Gotchas

- Camera control is nglview's own "unstable" API — `camera_orientation()`
  is what nglview itself uses to sync cameras between linked views.
- For a one-off read of camera/trajectory state without the streaming
  cost, turn native events on app-wide with
  `shinywidgets.config(native_events=True)`.

**More:** <https://shinywidgets.org/widgets/nglview/>
