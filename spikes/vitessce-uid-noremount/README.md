# Spike: `remount_on_uid_change=False` + uid bump (the maintainer's pattern)

Verification of the pattern suggested by @keller-mark in
[vitessce/vitessce-python#524](https://github.com/vitessce/vitessce-python/issues/524):
combine `remount_on_uid_change=False` with a `uid` bump when writing
`_config` from Python. Uses the **stock** `VitessceWidget` — no ESM patch,
no plugin (contrast with `spikes/vitessce-inplace/`).

## Why the earlier spike said this couldn't work

The #524 issue text claimed "`remount_on_uid_change=False` doesn't provide
an alternative: with no `key` change the new config is never adopted at
all." That is only true when the `uid` is *unchanged*. Reading the current
vit-s source shows the missing piece:

- `configKey = config.uid ?? JSON.stringify(config)` — change detection
  keys on the `uid` **regardless of `remountOnUidChange`**
  ([VitS.js](https://github.com/vitessce/vitessce/blob/main/packages/vit-s/src/VitS.js)).
- `remountOnUidChange` only controls whether `configKey` is passed as the
  React `key` of `ViewConfigProvider` (full remount) or not.
- `VitessceGrid` has `useEffect([success, configKey])` that adopts a new
  config **in place** via the store's `setViewConfig()` + `setLoaders()`
  ([VitessceGrid.js](https://github.com/vitessce/vitessce/blob/main/packages/vit-s/src/VitessceGrid.js))
  — the "controlled component case."

So `remount_on_uid_change=False` + uid bump = in-place config adoption, no
remount. This is what the
[spatial_query plugin](https://github.com/vitessce/vitessce-python/blob/main/src/vitessce/widget_plugins/spatial_query.py)
(`remount_on_uid_change=False`, returns `{**config, "uid": ...}` from
`on_config_change`) and the JS demo's annotation editor already do.

## Results (verified in a real browser, Chromium via agent-browser)

| Check | Result |
|---|---|
| Zoom to `spatialZoom: -1.98`, then change gene | **Zoom preserved** (`-1.98` before and after) |
| `featureSelection` update | Applied and echoed back to `_config` through the usual `onConfigChange` path |
| Feedback loops | None — update counter incremented exactly once per gene pick |
| Viewer health after 3 updates | Fully intact (both spatial views, heatmap, gene list render; still interactive) |
| Data refetch | **Cache is busted per update**: switching back to CR2 (whose expression data was already fetched at initial load) triggered 27 new data requests (163 → 190 resource-timing entries). Expected from source: `queryClient` is `useMemo(..., [configKey])`, so a uid bump recreates the tanstack-query cache even without a remount. |

The viewport survives because the new config is built from the *synced*
`_config` — which carries the user's current zoom/pan/selections back to
Python on every interaction — so `setViewConfig()` replaces the config
with one that already contains the viewport state.

## What this means for the upstream proposal

The maintainer's pattern covers the headline motivation (no viewport
reset) with zero upstream changes. Remaining advantages of a built-in
`set_coordination_value` command (the original proposal), now narrower:

1. **No read-modify-write race** — the uid-bump pattern replaces the whole
   config; user interactions landing between Python's `_config` read and
   write-back are silently clobbered. `setCoordinationValue` touches one
   value.
2. **No cache busting** — a targeted update wouldn't recreate the
   `queryClient`/loaders, so gene-picker-style updates wouldn't refetch
   already-cached data.
3. **Less traffic, simpler mental model** — no full-config round-trip, no
   validation/init re-run per update.

## Run

```sh
uv run --with json5 shiny run spikes/vitessce-uid-noremount/app.py
```

(From the repo root of a checkout with `shinywidgets[vitessce]` installed.
Requires internet: config, zarr data, and viewer JS are remote.)

Zoom a spatial view (mouse wheel), then change the gene in the sidebar:
the view recolors **without resetting the viewport**, and the sidebar
readout (driven by `reactive_read(widget, "_config")`) reflects the new
`featureSelection`.

## Files

- `app.py` — the lymph-node demo from `examples/vitessce/`, with the gene
  picker using `remount_on_uid_change=False` + deepcopy of synced
  `_config` + uid bump. Stock widget, no patches.
