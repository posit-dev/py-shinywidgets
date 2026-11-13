# Accessor cheat sheet

Generated from `shinywidgets/_accessors.py`, each renderer's `_accessor_specs` (in the per-library
`shinywidgets/_<lib>.py` modules), and the accessor methods on each `render_*` class in
`shinywidgets/_render_widget.py`. Every accessor attaches the
moment its output renders and records interactions whether or not anything has read it yet -- there is no
warm-up idiom and no "first read" gotcha (see ["The mental model"](index.md#the-mental-model-accessors-are-inputs-that-remember)).

Columns, straight from each `AccessorSpec` (not from memory):

- **Before any interaction**: what the accessor reads before the user has ever done the thing it reports --
  `cancels` (like `req(False)`: nothing to check, the output just doesn't render), `None`, `[]`/`{}`, or a
  real **seeded** value.
- **Across re-render**: whether a re-render **keeps** the last interaction (the payload may then describe
  the *previous* render's widget -- see ["Across re-renders"](index.md#across-re-renders)) or **re-seeds**
  from the newly rendered widget's own current state.
- **Default rate**: a blank means the accessor declares no policy, so the renderer's
  `rate_policy`/`rate_delay` kwargs are a no-op for it (see ["Rate limiting"](index.md#rate-limiting)).

**Renderers with no accessors** (use `reactive_read()` on `.widget` instead): `render_widget`, `render_drawdata`,
`render_ipysigma`, `render_geolibre`, `render_keplergl`, `render_ipycanvas`, `render_nglview`,
`render_obsplot`, `render_holoviews`, `render_ipyfilechooser`, `render_pygwalker`, `render_vizarr`,
`render_pyvista`, `render_vitessce`, and `render_pydeck` (deprecated; pydeck >= 0.9 has no widget to read
from -- see `render_maplibre`). `render_panel` has one dynamic accessor, `param(name)` (below).

## render_altair

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected(name=None)` | `IntervalSelection \| PointSelection \| IndexSelection` | seeded (empty selection; never `None`) | re-seeded | debounce 250ms |
| `selected_rows(name=None, *, df=None)` | a data frame (same type as `df`) | empty frame | derived from `selected` | debounce 250ms |

## render_embedding_atlas

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `predicate()` | `Optional[str]` | `None` (unfiltered) | re-seeded | debounce 250ms |
| `selected()` | native frame (pandas/polars) | all rows | derived from `predicate` | debounce 250ms |

## render_ipyaladin

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `clicked_object()` | `Optional[dict]` (`ra`, `dec`, `data`) | `None` | re-seeded | none |
| `selected()` | `List[astropy.Table]` | `[]` | re-seeded | none |
| `target()` | `SkyCoord \| (Longitude, Latitude)` | seeded (construction-time center) | re-seeded | none |
| `fov()` | `astropy.Angle` | seeded (construction-time fov) | re-seeded | none |

## render_ipyleaflet / render_leafmap

Both share `_IpyleafletAccessors`; on `render_leafmap`, calling any of these on a non-ipyleaflet backend (maplibre,
plotly, ...) raises `TypeError` pointing at `reactive_read()`.

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `bounds()` | `((south, west), (north, east))` | cancels until the browser's first report | re-seeded | none |
| `zoom()` | `float` | seeded (construction-time zoom) | re-seeded | none |
| `center()` | `[lat, lng]` | seeded (construction-time center) | re-seeded | none |
| `clicked()` | `Optional[dict]` (`coordinates: [lat, lng]`) | `None` | **kept** | none |
| `drawn_features()` | `List[GeoJSON Feature dict]` | `[]`, or raises `TypeError` if the map has no `DrawControl` | re-seeded | none |

## render_itables

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected_rows()` | `List[int]` | `[]`. Requires `select=True` | re-seeded | none |

## render_jscatter

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected()` | `numpy.ndarray[uint32]` | cancels until the browser's first report | re-seeded | none |
| `selected_rows(df=None)` | the selected rows of `df` (default: the `Scatter`'s data frame), same type as `df` | empty frame (cancels when `selected()` does) | derived from `selected` | none |

## render_k3d

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `camera()` | `List[float]` (9 floats: position, target, up) | cancels until the browser auto-fits (forever with `camera_auto_fit=False` and no explicit camera) | re-seeded | none (k3d itself throttles to ~1/200ms) |

## render_ipycytoscape

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `clicked_node()` | `Optional[dict]` (`ele.json()`) | `None` | **kept** | none |
| `clicked_edge()` | `Optional[dict]` (`ele.json()`) | `None` | **kept** | none |
| `selected_nodes()` | `List[dict]` (node data) | `[]` | re-seeded | debounce 250ms |
| `selected_edges()` | `List[dict]` (edge data) | `[]` | re-seeded | debounce 250ms |

Renamed from `node_clicked()`/`edge_clicked()` (#441, naming convention: interaction first).

## render_bqplot

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected()` | `List[Optional[np.ndarray]]`, aligned with `fig.marks` | seeded (`None` per mark) | re-seeded | debounce 250ms |
| `selected_rows(df, *, mark=None)` | the rows of `df` (required; same type as `df`) at one mark's selected positions | empty frame (cancels when `selected()` does) | derived from `selected` | debounce 250ms |
| `brush()` | `Optional[np.ndarray \| dict]` | `None` | re-seeded | debounce 250ms |

No `clicked()`: `element_click` messages never reach marks while the figure has an `interaction` (its overlay
intercepts clicks) -- deliberately omitted rather than ship an accessor that's silently dead in the common
case.

## render_ipyvolume

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `camera()` | live `pythreejs.Camera` | cancels while the figure has no camera | re-seeded | none |

## render_lonboard

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `view_state()` | `MapViewState \| GlobeViewState` | seeded (computed from the layers at construction) | re-seeded | debounce 250ms (#400) |
| `selected()` | `Optional[int]` | `None` | re-seeded (seeded from whichever layer retains a pick on its own `selected_index` trait -- `None` again for freshly built layers) | none |
| `selected_rows(df=None)` | the picked row of `df` (default: rebuilt from the single pickable layer's own data; raises with several), in `df`'s own type | empty frame | derived from `selected()` | none |
| `selected_bounds()` | `Optional[(minx, miny, maxx, maxy)]` | `None` | re-seeded | none |
| `clicked()` | `Optional[(lng, lat)]` | `None`. Reading it is what turns on click reporting in the browser | **kept** | none |

**[up]** GlobeView permanently breaks `view_state()` (and `reactive_read()` on the trait): the browser sends
pitch/bearing, which `GlobeViewState` has no fields for, so the first sync throws (swallowed) and it never updates.

## render_maplibre

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `view_state()` | `{center, zoom, bounds, bearing, pitch}` | cancels (`req(False)`) until the browser's first report (the map's `load` event) | kept until the new map reports, then re-seeded | none (the browser reports once per completed gesture, not per frame) |
| `clicked()` | `Optional[{lng, lat}]` | `None` | **kept** | none |
| `drawn_features()` | list of drawn GeoJSON features | `[]` | re-seeded (the new map's empty set) | none |

## render_matplotlib / render_plotnine

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `clicked()` | `Optional[matplotlib.backend_bases.MouseEvent]` | `None` | **kept** | none |
| `picked()` | `Optional[matplotlib.backend_bases.PickEvent]` | `None`. (`render_matplotlib` only.) | **kept** | none |
| `limits(ax=0)` | `((x0, x1), (y0, y1))` | seeded (current view limits) | re-seeded | debounce 250ms |

Every press fires `clicked()` (no dedup -- `MouseEvent` has no equality); a double-click is 3 presses, not 2.
`render_plotnine` has only `clicked()`.

## render_bokeh

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected()` | `List[int]` | `[]` (never `None` -- #437) | re-seeded | debounce 250ms |
| `selected_rows()` | `pd.DataFrame` | empty frame | derived from `selected` + `source_data` trigger | debounce 250ms |
| `tapped()` | `Optional[bokeh.events.Tap]` | `None` | **kept** | none |
| `zoomed()` | `Optional[bokeh.events.RangesUpdate]` | `None` until the first gesture (an auto-fitting or categorical range has nothing to seed) | re-seeded | none |

**[up]** jupyter_bokeh fires the underlying `on_change`/`on_event` callback twice per browser change; the
accessors' input-priority dedup absorbs this (counted once), but a raw `source.selected.on_change(...)` callback
you register yourself will see two calls.

## render_mosaic_widget

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `params()` | `Dict[str, {"value", "predicate"}]` | `{}` | re-seeded | debounce 250ms |
| `data(table=None)` | lazy `duckdb.DuckDBPyRelation` | rows unfiltered | derived from `params` (reads the *live* trait, not the debounced value) | debounce 250ms (inherited) |

## render_perspective

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `filter()` | `List[[col, op, value]]` | `[]` | re-seeded | none |
| `view_config()` | `Dict` (`plugin`, `columns`, `group_by`, `split_by`, `aggregates`, `sort`, `filter`, `expressions`) | seeded (construction-time config) | re-seeded | none |

Row clicks/selections never reach Python.

## render_ipydatagrid

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected()` | `List[{"r1","r2","c1","c2"}]` | `[]` | re-seeded | debounce 250ms (#400) |
| `clicked_cell()` | `Optional[dict]` | `None` | **kept** | none |
| `edited_cell()` | `Optional[dict]` | `None` | **kept** | none |
| `visible_data()` | `pd.DataFrame` | the whole frame | re-seeded (derived trigger) | none |

Renamed from `cell_clicked()` (#441). `selected()` now debounces by default (#400) -- it used to be the
canonical "no policy" example in this article; see ["Rate limiting"](index.md#rate-limiting) for the
current one.

## render_plotly

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `clicked()` | `Optional[pd.DataFrame]` | `None` | **kept** | none |
| `selected()` | `Optional[pd.DataFrame]` | `None` | **kept** (the new plot's own empty selection replaces it once it reports -- see note) | none |
| `selecting()` | `Optional[pd.DataFrame]` | `None` | **kept** | debounce 250ms |
| `brushed()` | `Optional[dict]` (`range` or `lassoPoints`) | `None` | **kept** (same note as `selected()`) | none |
| `brushing()` | `Optional[dict]` | `None` | **kept** | debounce 250ms |
| `relayout()` | `Optional[dict]` | `None` | **kept** (a delta payload; refers to the previous render's plot) | none |
| `hover()` | `Optional[pd.DataFrame]` | `None` | **kept** | debounce 250ms |
| `double_clicked()` | `Optional[bool]` | `None` | **kept** (pulse: re-fires readers on every subsequent double-click even though the value stays `True`) | none |
| `legend_clicked()` | `Optional[pd.DataFrame]` | `None` | **kept** (pulse: re-fires on every click, even of the same item) | none |
| `visible_traces()` | `Optional[pd.DataFrame]` | seeded (the figure's initial trace visibility) | re-seeded | none |
| `selected_rows(df, *, key=None)` | same frame type as `df` | empty frame | derived from `selected` | none |

`selected()`/`brushed()` attach at render like every other accessor (#419): a box or lasso selection made
before the first read is reported, not lost. They don't reset to `None` on their own re-render the instant it
happens -- plotly.js's bridge also rebuilds and re-sends the new graph div's *own* (initially empty)
selection shortly after mount, which is what actually clears them; until that arrives, the old value is
still what reads back. `double_clicked()`/`legend_clicked()` are **pulses** (`priority="event"`): identical
values still re-fire readers, unlike every other accessor here, which dedupes. **[docs]**: a plain click also
resets `selected()`/`brushed()` when `dragmode="select"`/`"lasso"` (a zero-area selection) -- affects apps
combining click-detail with lasso on one figure.

## render_pythreejs

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `camera()` | live `pythreejs.Camera` | seeded (the Python-constructed camera; pythreejs doesn't sync at mount) | re-seeded | none |

Same shape as `render_ipyvolume`'s `camera()`.

## render_quak

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `sql()` | `str` | cancels while the frontend is still initializing (empty string) | re-seeded | debounce 250ms |
| `data()` | lazy `duckdb.DuckDBPyRelation` | the construction query's rows | derived from `sql` (reads the *published*, not live, query) | debounce 250ms (inherited) |

## render_rerun

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected()` | `Optional[rerun.notebook.SelectionChangeEvent]` | `None` until the user first selects something | kept (the new viewer's load-time empty report is ignored) | none |

## render_mols2grid

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected()` | `Optional[Dict[int, str]]` (`{row_index: SMILES}`) | `{}` | re-seeded | none |
| `clicked()` | `Optional[dict]` | `None`. Only exists with `clicks=True` or a Python `callback` | **kept** | none |

Clicking the same molecule twice doesn't re-fire `clicked()` (a mols2grid limitation: the trait only changes
when the payload does -- unlike plotly's `clicked()`, there's no underlying event stream to re-publish from).

## render_niivue

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `location()` | `Optional[dict]` (`ax_cor_sag`, `frac`, `mm`, `vox`, `values`, `string`, `xy`) | `None` (not sent on load) | re-seeded | debounce 250ms |

## render_reactable

All five attach at render and seed from the browser's own `getState()` response (so a sort or selection made
before the first read is reflected), confirmed working on current `main` -- the `_accessor_specs` typo that
broke every one of these (missing leading underscore, `shinywidgets/_render_widget.py`) is fixed.

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `selected_rows()` | `List[int]` | cancels until the browser first reports | re-seeded | none |
| `page()` | `int` | cancels until the browser first reports | re-seeded | none |
| `sorted()` | `List[{"id","desc"}]` | cancels until the browser first reports | re-seeded | none |
| `filtered()` | `List[{"id","value"}]` | cancels until the browser first reports | re-seeded | debounce 250ms |
| `search()` | `str` | cancels until the browser first reports | re-seeded | debounce 250ms |

All five share "0-based, *data*-ordered positions survive sort/filter/paging" for `selected_rows()` and
`page()`/`sorted()`/`filtered()`'s own semantics. **[docs]**: the class docstring says in-place `props["data"]`
updates have no effect; verified they work and preserve sort/filter/page/selection (reactable-py's mounted
component doesn't memoize data).

## render_panel

| Accessor | Returns | Before any interaction | Across re-render | Default rate |
|---|---|---|---|---|
| `param(name)` | the parameter's type | seeded (the parameter's current value) | re-seeded, and **re-fires even on an unchanged value** (`priority="event"`, so following a re-rendered object's identity doesn't get swallowed as a dedup) | none |

`param(name)` is a dynamic accessor (the name isn't known ahead of time): the rendered object must be a
`param.Parameterized` (a panel widget, pane, or `Viewer`), or it raises `TypeError`; an unknown parameter name
raises `ValueError` listing the object's actual parameters.
