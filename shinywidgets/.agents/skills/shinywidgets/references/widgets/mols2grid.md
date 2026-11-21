# mols2grid (`render_mols2grid`)

## Overview

`pip install 'shinywidgets[mols2grid]'`. Turn a DataFrame of SMILES into a
searchable, sortable grid of 2D chemical structures, with selection and
(optionally) click-to-inspect. Accepts a `mols2grid.MolGrid` or a
DataFrame with a SMILES column (`smiles_col`, `"SMILES"` by default) or an
RDKit molecule column (`mol_col`). **Don't return `mols2grid.display()`'s
result** — it's an IPython HTML object, not a grid. Extra kwargs split the
way `mols2grid.display()` does: rendering options (`subset`, `tooltip`,
`sort_by`, ...) vs. `MolGrid()` constructor options.

## Quick start

```python
import pandas as pd
from shinywidgets import render_mols2grid

df = pd.DataFrame({"SMILES": ["CCO", "c1ccccc1"], "name": ["ethanol", "benzene"]})


@render_mols2grid(subset=["name"], tooltip=["name"])
def grid():
    return df
```

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | Selected rows as a dict, e.g. `{0: "CCO"}` (positional, as rendered) | `{}` |
| `clicked()` | Clicked molecule's row data (needs `clicks=True`) | `None` |
| `.grid` (property) | The underlying `mols2grid.MolGrid` object | — |

`grid.grid.get_selection()` returns the selected rows as a DataFrame.
`clicked()` is opt-in on `listen_to=["clicked"]` and raises without
`clicks=True` (or a Python `callback`); its payload can be wide (`img` is
the full SVG markup) — pick the keys you display rather than stringifying
the whole dict. Reading the underlying `grid.grid.widget.selection` trait
directly with `reactive_read()` needs `ast.literal_eval` — it's a repr
string, not JSON.

## Updating in place

`grid.grid.filter(mask)` (boolean mask, Series, or list) hides
non-matching molecules without re-rendering — positional against the rows
*as rendered*, so pass it in the DataFrame's original row order:

```python
from shiny import reactive


@reactive.effect
def _filter():
    grid.grid.filter(df["solubility"] > input.min_solubility())
```

A filter issued while the grid is still loading is recorded but not
applied by mols2grid's frontend — a grid can't start out filtered; filter
the DataFrame in the render function instead for that.

## Gotchas

- **Network access**: the grid's JS (list.js, jQuery, RDKit MinimalLib)
  loads from CDNs at render time — renders empty, with no error, if
  unreachable.
- **Sizing**: the grid auto-fits its own height to its contents and
  scrolls with the page, rather than filling a container. Pass
  `render_mols2grid(iframe_height="400px")` (paired with `fill=False`) to
  bound it instead of `output_widget(height=...)`.
- Tens of thousands of molecules approach the websocket message size
  (grid data is inlined in the iframe, ~0.5-1 KB/molecule) — expect a slow
  first paint, not an error, since Shiny's `--ws-max-size` only guards
  browser-to-server messages.
- A `MolGrid` you construct directly must have a unique `name` (mols2grid
  keys selections in a process-global registry) — construct it inside the
  render function, not at module scope.
- `as_grid()` is the renderer's coercion hook (DataFrame → `MolGrid`);
  apps don't call it.

**More:** <https://shinywidgets.org/widgets/mols2grid/>
