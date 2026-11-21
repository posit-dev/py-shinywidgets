# NiiVue (`render_niivue`)

## Overview

`pip install 'shinywidgets[niivue]'`. A clinical-grade WebGL2 neuroimaging
viewer — volumes, overlays, and meshes — as a reactive Shiny output, via
[ipyniivue](https://github.com/niivue/ipyniivue). Accepts an
`ipyniivue.NiiVue` widget with volumes/meshes loaded. **Don't pass
`height=` to `NiiVue()` itself** — it sets the canvas's pixel height,
which disagrees with the output's height and causes clipping or dead
space; let the output's filling layout (or `output_widget(height=...)`)
control size instead.

## Quick start

```python
from ipyniivue import NiiVue, SliceType, Volume
from shinywidgets import render_niivue


@render_niivue
def nv():
    nv = NiiVue(slice_type=SliceType.MULTIPLANAR)
    nv.add_volume(Volume(path="mni152.nii.gz", name="mni152"))
    return nv
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `location()` | Crosshair dict: `ax_cor_sag`, `frac`, `mm`, `vox`, `values`, `string`, `xy` | seeded with the viewer's synced position (`frac` only, plus `"seeded": True`) |

Debounced 250ms by default. A seeded value carries only `frac`; the other
keys appear with the next real crosshair move. For every event
un-debounced, register `@nv.on_location_change` inside the render function
and set a session-scoped `reactive.Value` — note exceptions raised inside
that callback are swallowed by ipywidgets, so a failing callback just
looks like "no updates." `nv.frac2mm()`/`nv.mm2frac()` don't work on Shiny
(the coordinate matrices exist only in the browser) — use the millimeter
coordinates from the `location()` payload instead.

## Updating in place

`.widget.set_*()` methods and writable traits — all apply live:

```python
from shiny import reactive


@reactive.effect
def _recolor():
    nv.widget.set_colormap(volume_id, "viridis")
```

`.widget.set_colormap(volume_id, name)`, `.widget.set_opacity(index, value)`,
`.widget.set_gamma(value)`, `.widget.set_slice_type(SliceType.RENDER)`,
`.widget.move_crosshair_in_vox(dx, dy, dz)`.

## Gotchas

- **Re-renders are expensive**: each one resends the JS bundle plus every
  volume (~5 MB bundle plus the whole volume re-uploaded). Prefer
  `Volume(url=...)` for remote data (the browser fetches it directly) and
  in-place `.widget.set_*` updates over re-rendering.
- `reactive_read(nv.widget.scene, "crosshair_pos")` never re-runs —
  ipyniivue syncs that trait silently; use `location()` instead.

**More:** <https://shinywidgets.org/widgets/niivue/>
