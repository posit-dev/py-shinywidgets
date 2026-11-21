# Matplotlib (`render_matplotlib`)

## Overview

`pip install 'shinywidgets[matplotlib]'`. Turns any matplotlib figure into
a live, zoomable, clickable widget without leaving Python — unlike
`@render.plot` (a static image), the figure stays alive on the server.
Accepts a `Figure`, an `Axes` (rendered via its figure), or an
`ipympl.backend_nbagg.Canvas` directly — also works with seaborn or
`DataFrame.plot()`, which build on matplotlib. Prefer creating figures
explicitly (`Figure(layout="constrained")`, `plt.subplots()`) over
pyplot's implicit current figure (`plt.plot()`, `plt.gca()`), which is
shared by every output and session in the process.

## Quick start

```python
import matplotlib.pyplot as plt
from shinywidgets import render_matplotlib


@render_matplotlib
def plot():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    return fig
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `clicked()` | A `MouseEvent` (`.xdata`/`.ydata`, `.inaxes`) | `None` |
| `picked()` | A `PickEvent` (`.artist`, `.ind`) — only artists created with `picker=` | `None` |
| `limits(ax=0)` | `((x0, x1), (y0, y1))` for axes `ax` | seeded from current limits (cancels before first render) |

`clicked()`/`picked()` keep their value across re-renders. Every mouse
press fires `clicked()` — a double-click arrives as three presses.
`limits()` is debounced 250ms by default and updates after every zoom/pan,
including ones made from Python. For anything else, matplotlib's own
callbacks (`fig.canvas.mpl_connect("motion_notify_event", f)`) still work
and may set `reactive.value`s.

## Updating in place

Modify the artists of `.widget.figure` and call `.widget.draw_idle()` —
this preserves the user's zoom, unlike re-rendering:

```python
from shiny import reactive


@reactive.effect
def _update_line():
    line.set_ydata(new_y)
    plot.widget.draw_idle()
```

## Gotchas

- Create figures with a non-interactive backend (`agg`, the default with
  no display) — a figure created under a GUI backend (Qt, Tk, macOS) can
  still render but is supported best-effort only, and warns at render time.
- A figure created through pyplot is closed (like `plt.close()`) once
  rendered — don't keep a reference expecting to reuse it.
- With a filling layout the figure resizes to its container; with an
  explicit `height`, it keeps its `figsize` unless the output is also
  `fillable=True`.

**More:** <https://shinywidgets.org/widgets/matplotlib/>
