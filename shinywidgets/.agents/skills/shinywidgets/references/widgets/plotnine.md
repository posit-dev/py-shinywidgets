# plotnine (`render_plotnine`)

## Overview

`pip install 'shinywidgets[plotnine]'`. Pan, zoom, and click into any
ggplot2-style plot, drawn to a matplotlib figure and coerced to an
`ipympl.backend_nbagg.Canvas`. Accepts a `plotnine.ggplot` or a
composition (`p1 | p2`); the plot you return isn't modified (a copy is
drawn). Also the only path to a true `render.plot`-style plot composition
Shiny's built-in static renderer can't show at all.

## Quick start

```python
from plotnine import aes, geom_point, ggplot
from plotnine.data import penguins
from shinywidgets import render_plotnine

@render_plotnine
def plot():
    return ggplot(penguins, aes("bill_length_mm", "body_mass_g")) + geom_point()
```

In a filling layout, the figure resizes to fit its container (overriding
`theme(figure_size=...)`), and plotnine re-lays out legends/axis labels at
each size. With an explicit `height`, the figure draws at its own
`figure_size` instead (a larger figure gets clipped) — match
`theme(figure_size=...)` to the output size you want.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `clicked()` | A `MouseEvent` (coordinates in plotnine's *transformed* space) | `None` |
| `limits(ax=0)` | `((x0, x1), (y0, y1))` for axes `ax`, transformed space | seeded from current limits |

Under `scale_x_log10()`, `.xdata`/limits are the log10 of the data;
discrete scales use integer positions. With `facet_wrap()`/`facet_grid()`,
`.inaxes`/`ax` names the panel's axes in figure order, but nothing in a
click event names its facet. `limits()` is debounced 250ms by default.

## Updating in place

Use `.widget` to mutate the rendered figure directly — the same
matplotlib-artist technique as `matplotlib.md`, reached through `.widget`.

## Gotchas

- **plotnine computes axis breaks when it draws**, so zooming in with the
  toolbar keeps the original ticks — a close zoom can show none. For
  zoom-aware ticks, set a matplotlib locator/formatter on `.widget.figure`'s
  axes (e.g. `MaxNLocator`) in an effect that reads `.widget`.
- Coordinates in both `clicked()` and `limits()` are plotnine's
  *transformed* space, not the original data scale, under a log or discrete
  scale.

**More:** <https://shinywidgets.org/widgets/plotnine/>
