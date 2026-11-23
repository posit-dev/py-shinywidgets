# K3D (`render_k3d`)

## Overview

`pip install 'shinywidgets[k3d]'`. A GPU 3D scene in a Shiny output —
millions of points, real terrain, volumes, and meshes, orbited by the
user. Accepts a `k3d.Plot` (the result of `k3d.plot()` with objects added)
or a bare k3d object (`k3d.points(...)`), placed on a new plot. By default
the plot fills its container; pass `height` to `k3d.plot()` for a fixed
pixel height (512, k3d's default, is treated as unspecified).

## Quick start

```python
import k3d
from shinywidgets import render_k3d


@render_k3d
def scene():
    plot = k3d.plot()
    plot += k3d.points([[0, 0, 0], [1, 1, 1]])
    return plot
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `camera()` | Flat list of 9 floats (position, look-at target, up vector) | cancels until the browser auto-fits |

With `camera_auto_fit=False` and no explicit camera, `camera()` cancels
forever — set `plot.camera` to seed it. Not rate-limited (k3d throttles
camera updates to roughly one per 200ms upstream). **There is deliberately
no `clicked()`** — k3d only reports clicks with `plot.mode = "callback"`,
a user-visible change to the interaction mode. To react to clicks, set the
mode and a `click_callback` on the objects yourself, and set a
`reactive.value` inside it.

## Updating in place

Use `.widget.objects[i].<trait>`:

```python
from shiny import reactive


@reactive.effect
def _recolor():
    scene.widget.objects[0].color = 0xFF0000
```

## Gotchas

- **Gate behind a user action**: a custom message or trait write made
  before a real user gesture may not visibly act — some of k3d's JS has
  browser autoplay-style restrictions, independent of shinywidgets.
- 1M points stayed orbitable at interactive rates even on software
  rendering in measured testing.

**More:** <https://shinywidgets.org/widgets/k3d/>

Written against `k3d` 3.x.
