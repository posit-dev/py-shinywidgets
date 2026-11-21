# pythreejs (`render_pythreejs`)

## Overview

`pip install 'shinywidgets[pythreejs]'`. Build a custom three.js scene
graph in Python — meshes, lights, cameras — that orbits, picks, and
updates in place, for when k3d/ipyvolume/pyvista's higher-level APIs don't
cover what you need. Accepts a `pythreejs.Renderer` widget (a `Scene` plus
a camera). By default the scene fills its container (canvas and camera
aspect resize with it); give the `Renderer` an explicit `width`/`height`
for a fixed pixel size instead.

## Quick start

```python
import pythreejs as p3
from shinywidgets import render_pythreejs


@render_pythreejs
def scene():
    mesh = p3.Mesh(p3.BoxGeometry(1, 1, 1), p3.MeshBasicMaterial(color="#1f77b4"))
    camera = p3.PerspectiveCamera(position=[2, 2, 2])
    return p3.Renderer(
        scene=p3.Scene(children=[mesh]),
        camera=camera,
        controls=[p3.OrbitControls(controlling=camera)],
    )
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `camera()` | The live `pythreejs.Camera` object | the Python-side camera as constructed (not synced until the first orbit) |

With `OrbitControls`/`TrackballControls`, the camera's
`position`/`quaternion`/`zoom` sync back after each orbit finishes. The
returned object is the same mutable instance across reads — copy what you
keep. For a single trait, `reactive_read(scene.widget.camera, "position")`
is the per-trait alternative.

## Updating in place

Use `.widget` — any trait on any object reachable from `scene.widget`:

```python
from shiny import reactive


@reactive.effect
def _recolor():
    mesh.material.color = new_color
```

## Gotchas

- **`mesh.rotation` (Euler) updates don't render** (upstream pythreejs
  bug) — rotate via `mesh.quaternion` instead.
- **Give lights an explicit `target` and `shadow`** — pythreejs creates
  defaults for them in the browser otherwise, and browser-created widgets
  live until the session ends, so every re-render leaks 3 models per light.
- Set `pythreejs.Scene(background=...)` for the scene background (defaults
  to white and overrides `Renderer(background=...)`).

**More:** <https://shinywidgets.org/widgets/pythreejs/>
