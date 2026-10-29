# Spike: is `remount_on_uid_change=False` safe as a shinywidgets *default*?

Follow-up to `spikes/vitessce-uid-noremount/` (which verified the
maintainer's pattern for coordination edits). This spike tests the update
types a Shiny app might plausibly make, to decide whether shinywidgets
should default `render_vitessce` to `remount_on_uid_change=False`.

## Results (verified in a real browser, Chromium via agent-browser)

| Update type | `remount_on_uid_change=False` + uid bump | Verdict |
|---|---|---|
| 1. Coordination edit (gene picker), config derived from synced `_config` | Viewport preserved (`spatialZoom` -1.98 before/after), echo works, no loops | ✅ Works |
| 2. View *removal* (heatmap), config derived from synced `_config` | View disappears, everything else intact | ✅ Works |
| 3. View *re-add* (raw layout entry from the original config) | **Silently not rendered** — store config has the view, grid shows 5 of 6 children | ❌ Broken |
| 3b. Re-add with an explicit fresh view `uid` | Grid item renders, but the view shows **"A view-level error occurred"** (ErrorBoundary) | ❌ Broken |
| 4. Full reset (write the pristine original config) | **Whole viewer crashes**: `Error: Cannot read properties of undefined (reading 'filter')`, grid unmounts. Store config looks correct; UI dead. Reproduced from a clean page load. | ❌ Broken |

## Root cause: an upstream bug in vit-s (present in 4.1.2 and `main`)

`VitessceGrid`'s adoption effect (the code path that makes
`remountOnUidChange=False` + uid bump work at all) sets the **raw `config`
prop** into the store:

```js
// packages/vit-s/src/VitessceGrid.js
useEffect(() => {
  let newLoaders = null;
  let newConfig = null;
  if (success) {
    newLoaders = createLoaders(config.datasets, ...);   // raw config
    newConfig = config;                                  // raw config!
  }
  setViewConfig(newConfig);
  setLoaders(newLoaders);
}, [success, configKey]);
```

At mount (and on every remount, i.e. always when
`remountOnUidChange=True`), the store is instead created from
`configOrWarning` — the config after **validation, legacy-schema upgrade,
convenience-file expansion, `initStrategy: 'auto'` coordination fill, and
`assignViewUids`**. The in-place path skips all of that. Verified via
React fiber inspection of the live grid: after re-adding a raw view, the
store's layout has the entry but with `uid` undefined (`layouts` item
`i: undefined`, child `key={v.uid}` → `null`), so react-grid-layout drops
it — exactly the DOM symptoms above.

Why upstream never hit this: both existing `remountOnUidChange=False`
users (the spatial_query plugin, the annotation-editing demo) write
**already-initialized** configs — they derive edits from the synced
config, whose views all have uids and full coordination scopes. That's
also why coordination edits (test 1) work fine from Shiny: our writes are
deepcopies of the synced `_config`, i.e. already initialized.

### The likely fix (one line, plus the loaders line)

Use `configOrWarning` (validated/initialized) instead of `config` in the
effect. This would make the in-place path correct for *raw* configs too —
and only then would `remountOnUidChange=False` be safe as a general
default.

## Consequences for shinywidgets

- **Coordination edits derived from the synced `_config` are safe** with
  `remount_on_uid_change=False` — the gene-picker pattern from
  `examples/vitessce/` is a strict improvement with it.
- **Wholesale config replacement is NOT safe** with it today: writing a
  fresh/pristine config (raw, un-initialized) breaks the viewer. Those
  workflows need `remount_on_uid_change=True` (a clean remount) — or the
  upstream fix above.
- Therefore: do **not** flip the shinywidgets default yet. Prefer
  documenting the opt-in + proposing the upstream fix; revisit the
  default if it lands.

## Run

```sh
uv run --with json5 shiny run spikes/vitessce-noremount-verify/app.py
```

Zoom a spatial view, then: (1) change the gene — zoom survives; (2)
toggle the heatmap off/on — off works, on renders an erroring view
(explicit-uid workaround included; without it the view silently doesn't
render); (3) reset to pristine config — the viewer crashes.

## Files

- `app.py` — lymph-node demo with the three update types instrumented,
  plus a layout-position readout and the explicit-view-uid workaround.
