# Vitessce guide: verification notes

## Versions / environment

- PR #374 head commit: `99c41ca7cf45268f75e8d87c7db2f18ba0a808ff` (`feat: add render_vitessce() for Vitessce
  single-cell/spatial-omics viewers`, branch `render-vitessce`). Worktree synced `--python 3.12`.
- `vitessce` 3.9.8 (PyPI), bundling vitessce JS/`vit-s` 4.1.2 (CDN-loaded at runtime), `anywidget` 0.11.0, `shiny`
  1.9.0, `zarr` 3.4.2, `json5` 0.17.3 (already in the lockfile -- no `--with` needed).
- Date: 2026-11-02.
- Data: public 10x Genomics Visium human lymph node, served by the Vitessce project
  (`https://data-1.vitessce.io`, `https://vitessce-data.storage.googleapis.com`). Every example needs an internet
  connection (config/zarr data/viewer JS are all remote); noted in each example's header comment.
- Old spike report: `docs/widget-reports/vitessce/report.md` (2026-10-28, pre-PR). Its findings (uid-bump
  requirement, fixed-pixel height, CDN dependency, local-data server) all still apply and are folded into the
  guide; its "deployed local-data proxy" follow-up is noted as a PR body item, not re-verified here (no local-file
  example in this guide -- out of scope given the time budget and that remote/in-memory modes cover the
  teaching goals).
- Spike branches referenced in the PR discussion (`spike/vitessce-inplace`, `spike/vitessce-uid-noremount`,
  `spike/vitessce-noremount-verify`) patch the wrapper ESM or require a plugin-view bridge; they're prototypes for
  upstream proposals, not something a guide reader can use today. The guide instead teaches the two *stock*
  options (default remount vs. `remount_on_uid_change=False`), both achievable with `vitessce` alone, and credits
  the PR discussion for the measured 27-request figure that independently matches this guide's own measurement.

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes (`img/quickstart.webp`) | n/a (static) | Required 3 rounds of fixes -- see "Bugs found (docs)" |
| `examples/02_build_config.py` | yes | yes (`img/build_config.webp`, `img/build_config_selected.webp`) | yes (clicked a cluster row in the Cell Sets legend) | Cluster "2" selection shown highlighted in both spatial + UMAP views |
| `examples/03_dashboard_with_readout.py` | yes | yes (`img/hero.webp`, `img/interaction_after.webp`) | yes (mouse-wheel zoom on the gene-colored spatial view, 8 steps) | `spatialZoom` read back via `reactive_read`, confirmed `-2.6` -> `0.35` |
| `examples/04_gene_picker_inplace.py` | yes | yes (`img/update_default_after.webp`) | yes (`ui.input_select` → `GNLY`) | Canvas DOM identity check: all 3 `<canvas>` elements replaced; 82 data-server requests measured |
| `examples/05_gene_picker_noremount.py` | yes | yes (`img/update_inplace_before.webp`, `img/update_inplace_after.webp`) | yes (zoom gesture + gene change) | Canvas DOM identity check: all 3 `<canvas>` elements preserved; 23-27 data-server requests measured (two separate runs) |
| `gallery/template_dashboard.py` | yes | yes (`img/gallery_dashboard_before.webp`, `img/gallery_dashboard_after.webp`) | yes (`ui.input_select` → `LYZ`) | View-state readout confirmed live in the same app |
| `examples/06_cellset_to_table.py` | yes | yes (`img/cellset_before.webp`, `img/cellset_after.webp`) | yes (expanded "Leiden Cluster" tree, clicked cluster row "2") | Table went from 9 rows (all clusters) to 1 row; cross-checked against the Cell Sets panel's own per-cluster counts |
| re-render cost probe (`app_rerender.py`, scratch-only, not shipped) | yes | no (numbers only) | yes | 132 data-server requests + full canvas teardown for a bare re-render; informs the "Updating the widget from Python" cost ranking, not a guide example itself |

No accessors exist on `render_vitessce` (`_accessor_specs` is absent from the class; confirmed by reading
`shinywidgets/_render_widget.py`), so `accessors: []` in the front matter is correct, and the "Accessor reference"
subsection from the brief's skeleton is replaced by "The `_config` trait" (the `reactive_read` tier), as the brief
anticipates for accessor-less renderers.

## Bugs found

### [docs, shinywidgets] `render_vitessce`'s own docstring example doesn't render anything

`shinywidgets/_render_widget.py` (around line 3246-3267), the `Examples` block:

```python
@render_vitessce
def vit():
    vc = VitessceConfig(schema_version="1.0.15", name="My data")
    dataset = vc.add_dataset(name="d").add_file(
        url="https://data-1.vitessce.io/0.0.33/main/human_lymph_node_10x_visium/human_lymph_node_10x_visium.h5ad.zarr",
        file_type="anndata.zarr",
    )
    vc.add_view("spatial", dataset=dataset)
    return vc
```

Two separate, independently confirmed gaps, found while building `examples/01_quickstart.py`:

1. **No `.layout()` call.** `add_view()` alone leaves the view at its default `w=1` (of 12) grid units, so it
   renders as a sliver a few percent of the panel's width. Screenshotted in the course of debugging (not kept as
   a guide asset, since it's a bug repro, not a docs illustration): the "Spatial" panel occupies roughly 1/12 of
   the card, data-free.
2. **No `options=` on `add_file()`.** Even after fixing (1), the view mounts (toolbar, zoom controls, tooltips --
   everything except visible spots) and the canvas stays solid black. Root cause (read from the browser-console
   view-config dump): Visium-style spot rendering needs `obsSegmentations`, not just coordinates, and the default
   `obsColorEncoding` ("color by cell set") needs an `OBS_SETS` view in the layout to have anything to color by.
   Neither is present in the docstring's example or needed by its plain `vc.add_view("spatial", ...)` call. No
   exception, no console error, no warning -- confirmed by a full console/network capture during a resolved 20s
   wait.

Both are fixed in `examples/01_quickstart.py` (full options dict + `OBS_SETS` view + `.layout()`), which is the
version in the guide. Recommend the docstring either link to the guide's quick start or inline the same fix
before release; as written, a user copy-pasting the docstring gets a near-empty, badly-sized widget with no error
to debug from.

### [up, vitessce/vitessce#2684] `remount_on_uid_change=False` can silently break pristine config writes

Documented in the guide's "Updating the widget from Python" caveat; filed upstream already (referenced in the PR
discussion, not newly found by this guide pass). Re-confirmed the *safe* case works as described:
`examples/05_gene_picker_noremount.py` always derives its new config from the live, already-synced
`vit.widget._config`, and 3/3 manual test runs (gene changes after a zoom gesture) preserved zoom, recolored
correctly, and kept the same `<canvas>` DOM nodes.

## Measurements

| Update path | Data-server requests (one gene change) | Canvas DOM survives? |
|---|---|---|
| Re-render (new `VitessceConfig` from the render function) | 132 | No (new widget entirely) |
| In-place edit, default remount (`uid` bump, `remount_on_uid_change=True`) | 82 | No (all 3 `<canvas>` replaced) |
| In-place edit, no remount (`remount_on_uid_change=False`) | 23-27 (two runs) | Yes (all 3 `<canvas>` preserved) |

All three measured on the same demo dataset/gene list, same machine, one run each for re-render and default
remount, two runs for no-remount (consistent 23 and 27). "Canvas DOM survives" checked by tagging the three
`<canvas>` elements before the edit and testing `document.body.contains()` on the same references after.

Pan/zoom readout: a fixed 8-step mouse-wheel zoom moved `spatialZoom` from the config's default `-2.6` to `0.35`
(consistent across 4 separate test runs with the same gesture parameters) -- used as the guide's measured example
rather than a round/contrived number.

## Judgment calls

- **No local-file or in-memory-zarr example.** The PR body and old report cover these data modes extensively and
  they work (per the old report and PR description), but every example in this guide uses the public remote demo
  data to keep the guide's own verification loop fast and avoid committing a local data file. This trades off
  "fewer data modes shown" for "every example gesture-verified in the time available." Flagged for the
  maintainer: worth a follow-up local-AnnData example if the website wants to show the "no Jupyter server needed"
  story visually.
- **No lasso/box-select example.** Vitessce's spatial/scatterplot views have a lasso tool (the second toolbar
  icon), but it's a canvas-drawn polygon gesture that didn't automate reliably with simple mouse-down/move/up
  sequences in the time available; the "Pointer tool" button also didn't expose a clickable mode-switch menu to
  Playwright's locators. Used the Cell Sets legend checkbox/row-click interaction instead for the
  "selection -> table" and "Vitessce's own coordination" patterns, which is a real, common, and more reliably
  automatable Vitessce gesture (also what a lot of real usage looks like -- picking a named cluster, not drawing
  a free-hand region). Worth a second pass with more time on canvas-gesture automation if the website wants a
  literal lasso screenshot.
- **`obsSetSelection` table shows set *names*, not per-cell data.** Flagged explicitly in the guide prose: a
  "marker genes for this selection" table would need the Python process to load the same zarr/AnnData the browser
  already has, which is a reasonable thing to show for *local* data but adds a second data-loading path and a
  real network round-trip for this guide's remote demo data. Left out under YAGNI; the set-name table is honest
  about what the synced config alone gives you.
- **`accessors: []` in front matter** -- intentional, not an oversight. See "Verification table" note above.

## Editor's notes for the website

- **Strongest visuals**: the hero/dashboard screenshot (`img/hero.webp`) and the cluster-selection before/after
  pair (`img/build_config.webp` / `img/build_config_selected.webp`) are the most immediately legible "this is what
  Vitessce does" shots -- recommend leading the website's gallery or category page with one of these two.
- **Cuttable for a shorter page**: the three-way cost comparison in "Updating the widget from Python" (re-render
  vs. default remount vs. no-remount) could compress to a two-row table (in-place vs. re-render) if the website
  wants less detail; the no-remount option's upstream caveat is the one piece worth keeping regardless, since it's
  a real footgun.
- **What from the old report was dropped and why**:
  - The "3.2 early-write race" finding (writing `_config` at render time can be clobbered by the async
    config-upgrade echo) -- kept, folded into the "Updating the widget from Python" prose as a one-line caveat
    instead of its own numbered finding; didn't re-verify the exact timing window, since the recipe already in
    the PR example avoids it structurally (writes only happen in a `@reactive.event(input.gene)` effect, never at
    render time).
  - The "3.3 local-file shared-port conflict" and "deployed local-data proxy" findings -- mentioned once in
    Gotchas (don't pass `port=`) but not re-verified or expanded, since this guide has no local-file example (see
    Judgment calls).
  - The report's scorecard/star-ratings format -- dropped; the brief's structure (accessor reference, patterns,
    gotchas) already covers the same ground more concretely.
  - The report's "proposed renderer shape" section -- moot, since the renderer now exists; superseded by reading
    the actual `render_vitessce` class and docstring.

## Update 2026-11-11 (main @ 32ca7035)

**Status check only -- this guide was not rewritten.** Per this pass's assignment: check whether
`render_vitessce` exists on current `main` before touching anything else, and if it doesn't, leave the guide
alone beyond a status banner.

- `grep -rn render_vitessce` in the worktree's `shinywidgets/` (detached at `main` @ `32ca7035`): **zero hits**.
  `render_vitessce` does not exist on `main` -- confirmed with `grep -n "vitessce" shinywidgets/__init__.py`
  too (no hits there either).
- `gh pr view 374`: still **OPEN**, not merged. Head commit has moved from `99c41ca7` (this guide's original
  verification commit) to `ee9284bb` as of 2026-11-10 -- the PR is still active, but its current diff was
  **not** re-read or re-verified against for this pass, per the instruction not to rewrite this guide.
- Added a one-line banner immediately under the `# Vitessce in Shiny` heading in `guide.md` stating it
  documents an unmerged renderer from PR #374 and is not on `main`/in a release yet. The front matter's
  existing `status: "PR #374 (unreleased)"` field (from the original pass) already flagged this in metadata;
  the banner makes it visible in the rendered page body too.
- **None of #437's accessor redesign applies here**: `render_vitessce` has no accessors in the PR as last
  verified (`accessors: []`), and its "Reacting to user interaction" story is entirely the `reactive_read()`
  tier (the `_config` trait). Since this renderer isn't merged, there's no current-`main` `.read()` fallback to
  convert the guide's `reactive_read(widget, "_config")` calls to -- that conversion only makes sense once/if
  this PR (or a successor) lands render_vitessce with the current renderer base class. Left every
  `reactive_read()` call in this guide as-is.
- No other changes made. The guide's content, examples, gallery app, and screenshots are untouched from the
  original 2026-11-02 pass and should be re-verified in full against whatever `main` looks like once/if PR
  #374 (or a successor) merges.

## Pairs with (for cross-widget articles)

- itables / reactable (selected cell sets -> styled table, richer than the plain `render.data_frame` shown here)
- Any plotting renderer, for a "selected cells -> marker-gene plot" pattern *if* the Python process also has
  access to the underlying AnnData (not demonstrated here -- see Judgment calls)

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." Classified as "only send what's visible" (chunked
zarr access is the whole point of the architecture), reusing the three data-mode distinction already in the
guide's intro (remote URL / local file server / in-memory zarr over comm). Judgment call: I did not find or
attempt to measure a numeric scale ceiling -- vitessce.io's docs pages 403'd a `WebFetch` attempt this pass, and
there's no existing measurement in this guide's examples to cite, so the section says plainly that no ceiling
was measured rather than inventing one. Links forward to the not-yet-written
`../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) -- expected
`check_docs.py` anchor warning.
