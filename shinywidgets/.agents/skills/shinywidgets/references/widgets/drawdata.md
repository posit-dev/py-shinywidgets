# drawdata (`render_drawdata`)

## Overview

`pip install 'shinywidgets[drawdata]'`. Draw a dataset with your mouse and
watch Python — and a live model — respond to every stroke. Accepts a
`drawdata.ScatterWidget` or `drawdata.BarWidget`. The constructor's
`width`/`height` define the drawing's *data coordinate space* (with `y`
pointing up), not the display size — choose them for the coordinate range
you want, not pixels; the widget itself fills the output's width while
preserving its aspect ratio.

## Quick start

```python
from drawdata import ScatterWidget
from shinywidgets import render_drawdata

@render_drawdata
def canvas():
    return ScatterWidget()
```

## Accessors

None named — read drawn points reactively with `canvas.read("data")`:
each point is a dict with `x`, `y`, `color` (hex string), and `label`. The
widget's own `data_as_X_y` property reports hex colors as `y` for
classification — build class labels from the `data` trait (or
`data_as_pandas["label"]`) instead.

## Updating in place

`ScatterWidget`: `canvas.widget.data = [...]`. `BarWidget` ignores
Python-side trait writes after its first render — re-render it instead to
change `n_bins`, `y_max`, etc.

## Gotchas

- **Drawn data syncs one batch behind** (`ScatterWidget` only, upstream
  [drawdata#40](https://github.com/koaning/drawdata/issues/40)): the
  *first* drawing batch doesn't sync to Python — nothing is readable until
  a second batch is drawn. Undo and reset sync immediately.
- **`BarWidget` always starts empty** — its frontend overwrites any `data`
  passed to the constructor, so seeding initial data is impossible, even
  via re-render.
- **Don't put two `BarWidget`s on the same page** — clicking one's
  collection buttons silently switches the other's active collection
  (upstream [drawdata#43](https://github.com/koaning/drawdata/issues/43)).

**More:** <https://shinywidgets.org/widgets/drawdata/>
