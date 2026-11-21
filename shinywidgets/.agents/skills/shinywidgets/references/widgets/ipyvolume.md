# ipyvolume (`render_ipyvolume`)

## Overview

`pip install 'shinywidgets[ipyvolume]'`. Orbit real 3D point clouds,
volumes, and surfaces in a Shiny app, with the camera itself as a reactive
accessor. **Unmaintained upstream since 2021-2023** — don't expect
upstream fixes. Accepts an `ipyvolume.Figure`, built either way: the
pylab API (`ipv.quickscatter(...)`, then return `ipv.gcf()`) or direct
construction (`ipyvolume.Figure`, with `Scatter` objects added to
`fig.scatters`). **Call the constructors inside the render function** —
pylab functions draw on a module-level "current figure," so figures built
elsewhere can end up shared across sessions.

## Quick start

```python
import ipyvolume as ipv
from shinywidgets import render_ipyvolume


@render_ipyvolume
def plot():
    return ipv.quickscatter([0, 1, 2], [0, 1, 0], [1, 0, 1])
```

With direct construction, set `size_selected`/`color_selected` explicitly
on scatters (their trait defaults are 0-d numpy arrays, which don't
JSON-serialize), and set `fig.xlim`/`fig.ylim`/`fig.zlim` — a directly
constructed figure defaults to a `[0, 1]^3` box with no auto-fit.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `camera()` | The figure's live `pythreejs.Camera` | the figure's camera as constructed (not synced until the first orbit); cancels only if `fig.camera` is `None` |

Readers invalidate when `position`/`quaternion`/`zoom` change (end of each
orbit) or the camera is replaced. The returned object is the same mutable
instance across reads — copy what you keep. For selections, register
`plot.widget.on_selection(fn)` (selections arrive as custom messages, not
trait changes) and set a `reactive.value` inside it. The payload is
`{"type": ..., "pixel": [[x, y], ...]}`: screen pixels, not point indices,
so mapping back to rows means projecting points through the camera yourself.

## Updating in place

Use `.widget` — any trait on the figure syncs to the browser:

```python
from shiny import reactive


@reactive.effect
def _recolor():
    plot.widget.scatters[0].color = new_colors
```

## Gotchas

- **A per-point string color array hangs the entire server process**, not
  just the output — avoid string color arrays on scatters.
- **Don't drive a changing highlight with `scatter.selected`.** `selected = []`
  crashes the view, and later assignments never move the highlight (upstream
  bugs). Bake the highlight into plain `color`/`size` arrays instead.
- Tens of thousands of GPU-instanced points is the realistic ceiling.

**More:** <https://shinywidgets.org/widgets/ipyvolume/>
