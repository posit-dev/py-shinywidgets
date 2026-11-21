# ipyaladin (`render_ipyaladin`)

## Overview

`pip install 'shinywidgets[ipyaladin]'`. A real-sky atlas (Aladin Lite)
that pans, zooms, and clicks its way into your Shiny app's reactive
graph. Accepts an `ipyaladin.Aladin` widget. The richest accessor set
among the Scientific widgets. Needs an internet connection — it loads its
JS from a CDN and sky imagery (HiPS tiles) from CDS servers at render
time.

## Quick start

```python
from ipyaladin import Aladin
from shinywidgets import render_ipyaladin


@render_ipyaladin
def sky():
    return Aladin(target="M31", fov=5)
```

In a filling layout the viewer fills its container unless the `Aladin` has
an explicit height. Prefer a coordinate string (`"83.63 22.01"`, parsed
locally) or a `SkyCoord` over a `target=` object name for anything set
programmatically — resolving a name blocks on CDS's Sesame service, and an
unresolvable name raises and fails the render outright.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `clicked_object()` | The catalog source most recently clicked (`ra`, `dec`, `data`) | `None` |
| `selected()` | Catalog sources in the current box selection (needs `.widget.selection("rectangle")` armed) | `[]` |
| `target()` | Sky position at the view center, as a `SkyCoord` | seeded from the viewer's state at render |
| `fov()` | The view's field of view | seeded from the viewer's state at render |

All four follow every click, pan, zoom, or selection — and Python-side
`.widget.target = ...` assignments too. A re-render starts
`clicked_object()` over at `None`. With two or more ipyaladin viewers on
the same page, `fov()` follows only the last-rendered one (an ipyaladin
frontend limitation).

## Updating in place

Mutate `.widget` (`.widget.target = "M31"`, `.widget.fov = 5`):

```python
from shiny import reactive, req


@reactive.effect
def _pan():
    req(sky.read("_is_loaded"))
    sky.widget.target = "M31"
```

**ipyaladin queues method calls** (`.widget.add_table()`) until the viewer
has loaded, but **property assignments are not queued** — gate effects that
set them on `sky.read("_is_loaded")`, not on the `_ready` trait (ipyaladin
doesn't reliably set it).

## Gotchas

- **`.widget.set_listener()` is a shared, cross-session-unsafe class-level
  dict** in ipyaladin 0.8.x — use the accessors above instead in a
  multi-user app.
- Setting `.widget.target` in place needs a `"ra dec"` string or a
  `SkyCoord` — a plain float tuple raises in ipyaladin's setter.
- An unresolvable `target=` name (or unreachable CDS service) raises
  `NameResolveError`, or a misleading `WidgetNotReadyError` in ipyaladin
  0.8.x.

**More:** <https://shinywidgets.org/widgets/ipyaladin/>
