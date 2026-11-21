# Large data & performance

## Overview

Every widget that handles genuinely large data uses one of three
strategies; picking the right one matters more than which specific library
you reach for within it. `updating-in-place.md` covers re-render vs.
in-place cost for a single widget — this reference is about choosing a
renderer and a widget-count budget for an app's overall payload.

## Three approaches to large data

1. **Draw it with the GPU in the browser.** Send the real points and let
   the GPU handle rendering/hit-testing: plotly's `Scattergl`, `jscatter`,
   `lonboard`. Payload and render time both scale with point count, but you
   get real per-point interaction (lasso, hover, pick).
2. **Summarize on the server.** Aggregate before anything crosses the wire,
   so the payload is sized by the *output* (screen pixels, bin count), not
   the input: `datashader`'s `rasterize()` (via `render_holoviews`),
   VegaFusion for altair. The only strategy that stays flat into the tens of
   millions of rows.
3. **Only send what's visible.** Keep data server-side and ship only the
   current page/view/query result: `perspective`'s virtualized table,
   `mosaic`/`quak` via DuckDB, itables' `maxBytes` downsampling.

These combine — `linked-views.md`'s "brushing large data" pattern pairs a
GPU-drawn raster for the dense view with server-summarized histograms for
linked controls. The principle behind all three: **an interaction step's
cost should be a function of what it ships, not what it's computed from.**

## Measured: bundle vs. per-point cost

Three GPU scatter renderers (plotly `Scattergl`, jscatter, lonboard) pay a
**fixed one-time bundle cost** (jscatter ~2.3 MB, lonboard ~4.8–5.1 MB,
plotly ~5.4 MB) plus ~20–21 bytes/point afterward — the per-point rate is
essentially identical across all three (the binary-buffer-plus-base64
comm channel every traitlets-synced numpy array gets, not a plotly-specific
inefficiency). For a few hundred thousand points, jscatter's lighter bundle
wins on cold-start bytes even though its marginal rate is no better; plotly
also took ~2x as long to render 1M points client-side (8.8s vs. 3.1–3.7s)
because plotly.js's setup is slower per point.

**perspective doesn't pay for row count at all** — identical payload at
10,000 and 100,000 rows, because the browser only queries the visible rows
of a server-side engine. **datashader's payload is an image, not the
data** — 2.19 MB at 10K points, 2.36 MB at 1M (7.7% growth for 100x the
data), because `rasterize()` bins points into a fixed-size grid on the
server before anything crosses the wire.

## Bundle size and first load

Every app pays a shared static framework cost (~5.05 MB: Shiny's own JS/CSS,
Bootstrap, shinywidgets' loader) regardless of widget choice. On top of
that, each renderer adds its own bundle, even for a near-empty widget:
matplotlib ~0.23 MB, itables ~0.81 MB, ipyleaflet ~1.25 MB, jscatter
~2.32 MB, k3d ~4.59 MB, plotly ~5.37 MB, perspective ~6.48 MB, lonboard
~10.06 MB. This is **additive across renderers on one page** and paid once
per browser, not once per server — five heavy widgets on one dashboard
means five renderer-specific bundles for every new visitor.

## Lifetimes and memory

`session_lifetime()`/`shared_lifetime()` (see `updating-in-place.md`) trade
functionality for memory differently: a 200,000-point lonboard layer built
per-session costs roughly 15–35 MB of server RAM per concurrent session;
the same layer built once via `shared_lifetime()` is flat regardless of
session count (its baseline is paid up front, at import time, instead of
amortized per session). For N concurrent sessions viewing the same
heavy, read-mostly dataset, `shared_lifetime()` turns an O(N) memory cost
into O(1) — at the cost that every session sees, and can move, the same
shared state.

## Checklist before shipping a widget-heavy page

1. Does every update to this widget *need* to re-render, or can an effect
   mutate a trait in place?
2. At your expected data size, have you actually measured the renderer's
   payload and render time, or are you assuming?
3. If the widget is shown to many concurrent users with the same data, is
   it a `shared_lifetime()` candidate?
4. Does a hot-path accessor declare a default rate policy, and can one
   gesture send it a burst of changes? If so, read an accessor that
   collects the burst, or debounce the expensive step yourself (see
   `reacting-to-widgets.md`).
5. How many renderer-specific bundles does one page load, and does that
   match your target audience's connection?

## Common mistakes

- Choosing a GPU scatter renderer for data that's actually tabular
  (sort/filter/browse) — a virtualized table (perspective, itables)
  sidesteps the scaling problem a point cloud can't.
- Driving a heavy downstream recompute from a continuously-streaming,
  unrated accessor — rebuilds a figure on every tick of a drag; update a
  companion view in place instead.
- Loading several heavy renderers on one page without budgeting their
  bundles as additive.

**More:** <https://shinywidgets.org/guide/performance/>
