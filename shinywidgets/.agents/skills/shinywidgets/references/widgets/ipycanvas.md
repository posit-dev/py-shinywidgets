# ipycanvas (`render_ipycanvas`)

## Overview

`pip install 'shinywidgets[ipycanvas]'`. Draw on a live HTML canvas from
Python, and read mouse and keyboard events straight back into Shiny's
reactive graph. A thin binding to the real HTML5 Canvas API — freehand
sketch pads, pixel editors, cellular automata, click-to-annotate tools.
Accepts a `Canvas`, `MultiCanvas`, `RoughCanvas`, or `MultiRoughCanvas`.
Size the canvas through the constructor's `width`/`height` (drawing-buffer
pixels), not `widget.layout.height` — a `Layout` height opts out of
filling, and since the buffer is fixed, the browser can only rescale the
existing bitmap.

## Quick start

```python
from ipycanvas import Canvas
from shinywidgets import render_ipycanvas


@render_ipycanvas
def canvas():
    c = Canvas(width=300, height=200)
    c.fill_style = "steelblue"
    c.fill_rect(20, 20, 100, 100)
    return c
```

In a filling layout the output fills its container and the canvas is
centered within it (shrinking to fit, aspect preserved, never stretched).

## Accessors

None named — read widget state with `reactive_read()` on `.widget`, or
register event callbacks (`on_mouse_down()`, `on_mouse_move()`) that set
`reactive.value`s.

## Updating in place

Draw on `.widget` from anywhere (an effect, an asyncio task) and the
browser canvas updates in place:

```python
from shiny import reactive


@reactive.effect
def _draw():
    canvas.widget.clear()
    canvas.widget.fill_circle(input.x(), input.y(), 10)
```

## Gotchas

- **`ipycanvas.hold_canvas()` has no effect under shinywidgets** — each
  draw command is sent individually regardless.
- With shiny < 1.9, canvas updates from a background task may not reach
  the browser until the next input event.
- Content is stateless per session — a refresh starts blank, with no
  built-in undo.

**More:** <https://shinywidgets.org/widgets/ipycanvas/>

Written against `ipycanvas` 0.x.
