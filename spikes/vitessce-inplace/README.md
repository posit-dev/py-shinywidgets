# Spike: in-place coordination updates for the vitessce widget

Prototype evidence for [vitessce/vitessce-python#524](https://github.com/vitessce/vitessce-python/issues/524).

**Problem**: updating the viewer from Python requires reassigning the
`_config` trait, which the viewer only applies via a full remount of the
view-config store (`VitS.js` keys `ViewConfigProvider` on
`config.uid ?? JSON.stringify(config)`; the store is created once via
`useRef`). The remount resets zoom/pan/selections and re-creates loaders.

**Result**: it works. Picking a gene in the sidebar recolors the spatial
view *in place* — `spatialZoom` is preserved across the update (verified
in a real browser: zoom `-2.6` → wheel to `-1.6`/`-0.61` → gene change →
zoom unchanged, `featureSelection` echoed back to `_config`). Compare with
the `_config` + `uid`-bump approach in `examples/vitessce/`, where the
same action resets the viewport.

## Run

```sh
uv run --with json5 shiny run spikes/vitessce-inplace/app.py
```

(From the repo root of a checkout with `shinywidgets[vitessce]` installed.
Requires internet: config, zarr data, and viewer JS are remote.)

Zoom/pan a spatial view, then change the gene: the view recolors without
resetting the viewport, and the sidebar readout (driven by
`reactive_read(widget, "_config")`) reflects the bridge-applied value,
proving the store→Python echo still works.

## How it works

1. `InplaceVitessceWidget.set_coordination(parameter, value, scope)` sets a
   synced `pending_coordination_edit` trait (with a nonce so repeated
   identical edits still fire).
2. A two-line patch to the wrapper ESM forwards trait changes to a
   `window` CustomEvent. (The wrapper owns the anywidget model but renders
   *outside* the view-config store provider, so it can't touch the store.)
3. A `VitesscePlugin` contributes a `coordination-bridge` plugin **view** —
   plugin views render *inside* the store provider — which listens for the
   window event and applies the edit via the `useCoordination` setters
   (the store's `setCoordinationValue` action). The store's
   `onConfigChange` subscription echoes the updated config back to
   `_config` through the usual path.

## Findings that shape the upstream ask

- **Children of `<Vitessce/>` render only in page mode.**
  `VitessceGridLayout` drops `children` in grid mode ("Not pageMode, so no
  children to render"), so a non-visual bridge component can't be mounted
  as a `<Vitessce/>` child. (The `page_esm`/`PageComponent` mechanism only
  works because page mode renders children.)
- **Plugin views are the only official in-tree extension point**, but they
  are *visual* (a grid panel with a title bar — hence the small
  "coordination bridge (spike)" panel in the app) and have no access to
  the anywidget model, so Python→JS pushes need a side channel (the
  window event here; polling via `invokeCommand` would be the only
  patch-free alternative).
- **Therefore a built-in is the right fix**: a widget command over the
  existing anywidget-command RPC (`_zarr_get`/`_plugin_command` pattern)
  plus a small bridge from the wrapper into the store (e.g. an
  `onStoreReady` prop on `<Vitessce/>`, or rendering the bridge inside
  `CallbackPublisher`'s side of the tree) would make this a first-class,
  non-visual API: `widget.set_coordination("featureSelection", ["CR2"], scope="A")`.
- Bonus finding: the mount-time config echo (`onConfigChange` with the
  upgraded config) always **adds a top-level `uid`** (`assignViewUids` in
  `view-config-utils.js`), so any `_config` read back from the widget has
  one — which is why the uid bump is required in practice for
  remount-style updates.

## Files

- `inplace_widget.py` — `InplaceVitessceWidget` (patched `_esm` + trait +
  `set_coordination()`) and `CoordinationBridgePlugin`.
- `app.py` — the lymph-node demo from `examples/vitessce/`, with the gene
  picker using `set_coordination()` instead of the `_config` + uid bump.
