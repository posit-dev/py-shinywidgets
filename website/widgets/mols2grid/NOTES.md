# NOTES: mols2grid guide

## Versions

- `mols2grid` 2.2.0, `rdkit` 2026.09.1, `pandas` 3.1.0, `anywidget` 0.11.0, `shiny` 1.9.0, Python 3.12.
- shinywidgets commit: `main` at `00f90249` (the worktree I ran everything in is detached there). `@render_mols2grid`
  landed via PR #340 (merged commit `e661cd65`, "Add `@render_mols2grid` for mols2grid molecule grids"); the
  `selected()`/`clicked()` accessors are already on `main` as part of that same commit (not a separate
  follow-up), alongside `fa28de39` which added the shared accessor helper used by several other renderers.
- **Important for the maintainer**: the main checkout (`/Users/cpsievert/github/py-shinywidgets`) is on a branch
  porting `render_mols2grid` to mols2grid 3.0 (open PR **#375**, not yet merged to `main`). Per my assignment, this
  guide documents **`main`'s mols2grid 2.x behavior only** and was verified entirely in an isolated worktree
  pinned to `origin/main`, never the 3.0 branch. mols2grid 3.0 (upstream PR
  [cbouy/mols2grid#71](https://github.com/cbouy/mols2grid/pull/71)) renames `MolGridWidget.grid_id` to `name` and
  may change whether the grid still needs the iframe-stacking trick at all -- several comments in `main`'s own
  source (`as_grid`, `_cleanup_selection_registry`) already flag exactly these spots as needing updates once 3.0
  lands. Nothing in this guide should be merged to the website until #375 (or its successor) is resolved one way
  or the other; if it merges first, this guide will need a pass to re-verify every screenshot and the "Gotchas"
  bullet about the mols2grid<3 pin.
- Playwright: Chromium, default headless launch (no WebGL/GPU flags needed -- mols2grid draws with inline SVG, no
  canvas/WebGL).
- The scratchpad was wiped mid-task by a coordinator restart (see the final "Session interruption" note below);
  the worktree was recreated at the same path and the same commit, with an identical `uv sync --all-groups`, so no
  previously-verified claim needed re-checking for a version drift reason. I did re-verify the one example
  (`09_plotly_scatter_link.py`) whose screenshots were lost in the wipe.
- I never ran `uv run --no-sync --with <pkg>` for mols2grid, rdkit, plotly, or pandas at any point -- every run
  used the worktree's own locked `.venv` as-is (`uv run --no-sync python -I script.py`), so there's no overlay-version
  risk for this guide's findings.

## Verification table

All apps run via `shiny.run.run_shiny_app` (ports 9700-9719) and screenshotted with Python Playwright, Chromium,
1280x800 (wider for 3-column layouts), `device_scale_factor=2`. Every screenshot referenced in `guide.md` was read
with the Read tool before being cited.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes (+2 search variants) | yes -- typed into the text search box and the SMARTS box (`.m2g-searchbar`, `page.keyboard.type`, since `.fill()` doesn't dispatch the `keyup` mols2grid listens for) | confirmed match counts (4 text, 18 SMARTS) via `window.mols2grid_lists` |
| `examples/02_fields_style_transform.py` | yes | yes | n/a (static) | confirmed `transform` affects only display text |
| `examples/03_prerender.py` | yes | yes | n/a | confirmed RDKit's JS/wasm *still* load with `prerender=True` (see Bugs found / docs) |
| `examples/04_accessor_selection.py` | yes | before/after pair | yes -- clicked two grid cells | `selected()` seeded `{}`, then `{0: 'CCC(C)CC', 2: 'CCCC=C'}` |
| `examples/05_accessor_clicked.py` | yes | before/after pair | yes -- clicked the `.m2g-callback` play-icon target | `clicked()` `None` -> parsed row dict; found the `img`/`SMILES` always-included quirk here |
| `examples/06_filter_from_python.py` | yes | before/after pair | yes -- dragged the MW slider's upper ion.rangeSlider handle | 253 -> 133 matching items, confirmed via `window.mols2grid_lists` |
| `examples/07_selection_to_views.py` | yes | before/after pair | yes -- checked 4 cells, then clicked the download button | table/histogram showed exactly the 4 rows; downloaded SDF had exactly 4 `$$$$` records matching the selection |
| `examples/08_click_detail_card.py` | yes | before/after pair | yes -- clicked a `.m2g-callback` target | depiction + 6 descriptors rendered from the clicked row's SMILES |
| `examples/09_plotly_scatter_link.py` | yes | before/after pair | yes -- dragged a lasso path (6 waypoints) over the plot's `.nsewdrag` layer | 253 -> 187 matching items; re-verified after the scratchpad wipe, same result both times |
| `examples/10_layout_sizing.py` | yes | yes (3-panel) | n/a | measured `getBoundingClientRect()` on the output div and the iframe directly: iframe 150px, output div 259px (`fill` default) vs 163px (`fill=False`) -- see Bugs found (docs) |
| `gallery/template_grid_explorer.py` | yes | before/after pair | yes -- checked 3 cells | |
| `gallery/showcase_chem_explorer.py` | yes | before/after pair | yes -- clicked a molecule, checked 2 cells, lassoed the scatter (via `.nsewdrag`), dragged the MW slider | all four interactions landed together: detail card, "2 molecule(s) selected", grid narrowed 253->63->60, SDF download had exactly 2 `$$$$` records |

Also read (not run, since Playwright tests are the project's own record, not mine to re-verify from scratch):
`tests/playwright/render_mols2grid/`, `tests/playwright/mols2grid_accessors/`, `tests/playwright/mols2grid_express/`
in the worktree -- these confirmed my selector choices (`.m2g-cell:not(.m2g-phantom)`, `.m2g-callback`,
`wait_for_cell_handlers`'s jQuery-events poll) before I wrote my own driver, per the brief's advice to check
existing Playwright tests for a widget's known-good gestures.

## Accessor coverage

- `selected()`: verified with a real gesture (two checkbox clicks), both directly
  (`examples/04_accessor_selection.py`) and through every downstream pattern that reads it
  (`examples/07_selection_to_views.py`, `gallery/showcase_chem_explorer.py`). Confirmed it seeds `{}` at mount
  (state-accessor seeding) and survives a check/uncheck round trip.
- `clicked()`: verified with a real gesture (clicking the `clicks=True` play-icon target), directly
  (`examples/05_accessor_clicked.py`) and in the detail-card pattern (`examples/08_click_detail_card.py`,
  `gallery/showcase_chem_explorer.py`). Confirmed it's `None` until the first click (no seeding, matching
  "event" semantics) and that the payload includes keys beyond what the docstring's "every displayed column"
  phrasing implies (see Bugs found / docs).

Both accessors behaved exactly as the class docstring describes, with one documented-but-imprecise detail (the
`clicked()` payload's extra keys) and one undocumented-but-verified-inert interaction (`rate_policy`/`rate_delay`)
-- both below.

## Bugs found

### shinywidgets

None found that I'd call a product bug. The two items below are both docs-precision gaps, not incorrect behavior.

### Upstream (mols2grid 2.2.0)

- **`prerender=True` does not remove the RDKit WebAssembly dependency.** I expected (and the class docstring's
  wording doesn't contradict) that `prerender=True` would make the grid's JavaScript dependency smaller, since
  depictions are now server-side SVGs. Instead, `mols2grid/templates/html/interactive_header.html` unconditionally
  includes `<script src=".../RDKit_minimal.js">` regardless of `prerender`, because RDKit still powers the SMARTS
  search box client-side. Confirmed directly: captured every network request while running
  `examples/03_prerender.py` and both `RDKit_minimal.js` and `RDKit_minimal.wasm` were fetched. This matches a
  finding in the earlier investigation report (`docs/widget-reports/mols2grid/report.md`, finding 5/"dependency
  risk"), re-verified independently here rather than trusted on faith. Long-standing upstream behavior, not a
  regression -- I documented it plainly in the "What you can build" prerender section and in Gotchas rather than
  treating it as something shinywidgets should paper over.
- **`MolGrid()` logs its own `repr()` to the server console on construction** (a leftover `IPython.display.display()`
  call with no guard for running outside a kernel). Confirmed in every example's terminal output
  (`<mols2grid.widget.MolGridWidget object at 0x...>`, once per render). Matches the earlier report's finding 2;
  still true on 2.2.0. Harmless noise, documented in Gotchas, not fixed in shinywidgets (nothing in our layer can
  suppress another process calling `display()`).

### Docs (shinywidgets, current main)

- **The `clicked()` docstring's "every displayed column plus `mols2grid-id`" undersells what's actually in the
  payload.** Verified directly (`examples/05_accessor_clicked.py`, before I trimmed the demo's own output): a
  clicked row's dict also always includes `img` (the full multi-line SVG markup for that cell) and `SMILES`, even
  when neither is in `subset`/`tooltip`. This isn't wrong, exactly -- `img` and `SMILES` are both "columns" in
  mols2grid's internal sense -- but a reader acting only on the docstring's phrase would not expect a large SVG
  string to show up in the dict, and might `str()` the whole thing into a UI (as my own first draft did) before
  noticing. I'd suggest the docstring explicitly name `img` and `SMILES` as always-present keys. Low cost to fix,
  moderate value (saves every new user one "why is there a giant SVG string in here" moment).
- **`rate_policy`/`rate_delay` are accepted by `render_mols2grid()` but have no observable effect on anything a user
  would reactively read**, and the docstring's generic parameter description (shared boilerplate across renderers:
  "How to rate-limit `reactive_read()` on the widget") doesn't flag this renderer-specific exception. Verified by
  inspecting the `Accessors`/`AccessorSpec` runtime directly (`shinywidgets/_accessors.py`): a per-accessor limiter
  is only installed when the `AccessorSpec` itself declares a default `rate_policy`, and neither `selection` nor
  `clicked` does (both fire at most once per discrete gesture, so there's nothing to debounce/throttle) --
  confirmed with a small script asserting `renderer._accessors._slots["selection"].limiter is None` after
  constructing `render_mols2grid(rate_policy="throttle", ...)`. Separately, `register_rate_policy(widget, ...)` in
  `render_widget_base._render()` applies to `self._widget` -- the *composite* `Box` -- not `.grid.widget` (the
  `MolGridWidget` that actually carries `selection`/`callback_kwargs`), confirmed the same way
  (`rate_policy_for(r.widget)` returns the policy; `rate_policy_for(r.grid.widget)` returns `None`). Since the Box
  has no public trait worth `reactive_read()`-ing, the parameters are currently inert for this renderer end to
  end. I'd call this low-value to "fix" (there's nothing to rate-limit here; the parameters existing at all is
  just interface consistency with every other `@render_*`), but worth one sentence in the docstring so a reader
  doesn't go looking for an effect that isn't there. I wrote this up in the guide's own "Rate limiting" subsection
  rather than silently omitting the parameters.
- **The "Sizing" docstring bullet doesn't mention that `iframe_height` needs `fill=False` alongside it for a
  compact (non-stretching) card.** Verified with `getBoundingClientRect()`: with `iframe_height="150px"` alone,
  in a fillable page, the output `<div>` (which carries `html-fill-item html-fill-container` classes because
  `render_mols2grid` defaults `fill=True`) measured 259px tall against a 150px iframe; adding `fill=False` dropped
  it to 163px. This is a real, somewhat surprising interaction (bounding the *iframe* doesn't bound the *output*),
  and the fix is simple once you know to look for it, so I think it's worth a one-line addition to the docstring's
  Sizing bullet. Moderate value, essentially free to document.

I did not re-verify the two cost/scale findings from the earlier report (the ~1.2 KB/molecule iframe payload size,
and the four-CDN-origin offline failure mode) as fresh numbers, since the current docstring already states
measured ranges for the first (the "0.5-1 KB per molecule... tens of thousands... approach Shiny's websocket
limit" language, which reads as already independently verified by an earlier pass per the plan docs) and the
second is a one-line, easily reproduced claim I did spot-check qualitatively (an unreachable CDN origin produces a
toolbar with zero cells, no console error visible to the Python side) without re-measuring exact KB/molecule
numbers myself.

## Judgment calls (flag for the maintainer)

1. **Dropped the "approved drugs" dataset idea from the assignment text** in favor of using mols2grid's own
   bundled solubility (ESOL/Delaney) SDF for every example. It's real, recognizable data (a standard
   cheminformatics benchmark dataset), ships with the package (no network download, no extra file to maintain),
   and is already the dataset `examples/mols2grid/app.py` on `main` uses -- reusing it kept every example
   self-contained and consistent with the shipped example app's own choices.
2. **Chose `prerender=True` as its own short "What you can build" highlight even though the resulting screenshot
   is visually identical to the default**, specifically *because* the interesting finding (RDKit still loads) is
   a "looks the same, but isn't what you'd assume" result -- I called this out explicitly in the prose rather than
   silently matching a screenshot to a surprising claim.
3. **Picked "lasso the scatter to filter the grid" (not "grid selection highlights points in the scatter") for the
   plotly pairing**, per the brief's "or" framing. Highlighting points from a mols2grid selection would need
   mutating the scatter's marker array from Python in place, which is a `render_plotly`-pattern question more than
   a mols2grid one; filtering the grid from a lasso is the more natural "mols2grid is the thing being searched"
   direction and reuses the same `filter()` mechanism as the Shiny-inputs pattern, keeping the guide's "Updating
   the widget from Python" and "Coordinating multiple views" sections consistent with each other.
4. **The showcase gallery app combines sliders *and* a lasso by intersecting two independent boolean masks**
   (rather than letting the lasso simply override the sliders, or vice versa). I think this is the more honest,
   more impressive demonstration of `filter()` as a single idempotent operation driven by multiple reactive
   sources, but it's also the one place in this guide where the "why" (two masks, `&`-combined) needs a code
   comment to not look arbitrary -- flagging in case a simpler single-driver version is preferred for the
   showcase bucket.
5. **No dedicated example for `size=`, `useSVG`, `removeHs`, `coordGen`, `MolDrawOptions`, or `callback=<a custom
   Python function>`** (beyond the `clicks=True` no-op). These are real `MolGrid()`/RDKit draw options, but they
   felt like an API-surface tour rather than a "highlight," per the brief's "pick the library's most compelling
   capabilities, not an API dump" -- the `addStereoAnnotation=True`-style draw-option passthrough is mentioned in
   prose (Installation/Quick-start lead-in references the docstring's kwarg-splitting behavior) but not given its
   own snippet.
6. **Category: "3D & scientific"**, per the brief's roster (mols2grid is listed there explicitly), even though a
   2D structure grid isn't 3D -- I didn't second-guess the brief's categorization.

## Editor's notes for the website

- **Strongest screenshots**: `img/gallery_showcase_after.webp` (used nowhere as hero, but arguably the single most
  impressive image in the guide -- sliders, lasso, click-detail, and a selection count all agreeing in one
  screenshot) and `img/search_smarts.webp` (the red substructure-match highlighting is immediately legible even to
  a non-chemist, and is mols2grid's single most distinctive capability). I used `img/quickstart.webp` as the hero
  per the brief's convention of a clean, representative first impression, but a website editor might prefer
  `search_smarts.webp` or `gallery_showcase_after.webp` as the hero instead, since they show *why* mols2grid is
  worth using, not just that it renders.
- **Candidate to cut for a shorter page**: "Beyond the accessors: reactive_read" is one short paragraph saying
  there's nothing else to read (same shape as the quak guide's equivalent section) -- could be folded into a
  footnote on the accessor reference table instead of its own heading.
- **The three-panel `layout_sizing.webp` screenshot is dense** (three stacked cards) and the prose explaining it
  leans on exact pixel measurements from `getBoundingClientRect()` rather than something visible at a glance in
  the image itself -- a shorter page could cut the third (`fill=False`) panel and state the fix in one sentence
  without the screenshot proving it pixel-by-pixel.
- **Cross-widget pairing**: `examples/09_plotly_scatter_link.py` and `gallery/showcase_chem_explorer.py` both pair
  with [plotly](../plotly/index.md) (lasso-select -> `selected_rows()` -> filter). No other pairings in this
  guide; mols2grid doesn't naturally compose with maps, tables-of-non-chemical-data, or large-scale-scatter
  widgets the way a generic DataFrame-backed widget would.

## What I dropped from the old report and why

- **The whole "is this feasible" framing and scorecard** (`docs/widget-reports/mols2grid/report.md` sections 1,
  7): moot -- the feature shipped and is on `main`; a teaching guide doesn't need a feasibility verdict.
- **The `grid_name()` session-scoping implementation narrative and the `SelectionRegister` cross-session-leak
  repro** (report sections 4-5, and the entire `docs/plans/2026-10-26-*-followups-handoff.md` document): this is
  implementation history (already resolved on `main` -- default-named grids are now a hard `ValueError`, not a
  silent leak) rather than something a guide reader needs; I kept only the user-facing consequence ("your own
  `MolGrid` needs a unique name, or construction raises") in Gotchas.
- **The exact websocket-payload byte/molecule measurements** (report section 5, finding 6): the current docstring
  already states a measured range ("0.5-1 KB per molecule... tens of thousands... approach the websocket limit"),
  which reads as more current and more precisely verified than the old report's "~1.2 KB/molecule, 5k+ molecules"
  estimate -- I didn't re-measure and re-state a third version of the same number, and don't repeat it verbatim
  in the guide to avoid it going stale independently of the docstring.
- **The upstream-issue filing suggestions** (report section 6, "file two small upstream issues"): out of scope for
  a user-facing guide; left for whoever owns upstream relations.
- **`use_iframe=False`/manual templating discussion**: `@render_mols2grid` always forces `use_iframe=True` now (with
  a warning if you pass `False`), so this is no longer a user-facing choice worth explaining.

## Update 2026-11-11 (main @ 32ca7035)

- **`clicked()`'s re-render behavior was wrong in the old guide (fixed).** The original pass (written against
  `00f90249`, before #437) classified `clicked()` as an "event" accessor that "resets to `None` on every
  re-render and never gets seeded." Re-read the current source (`shinywidgets/_render_widget.py`,
  `render_mols2grid._accessor_specs`): `clicked` is `kind="state"` like `selection`, and its docstring now says
  it "keeps its value across re-renders until the user clicks the new grid." Verified live: clicked a cell,
  forced a re-render with no data change (an action button read inside the render function), and `clicked()`'s
  dict was byte-for-byte unchanged after the re-render -- it was not reset. Fixed the accessor reference table,
  the `clicked()` prose section, and the inline code comment in both `guide.md` and
  `examples/05_accessor_clicked.py` (the `if row is None` *logic* was already correct and needed no code change,
  only the comment calling it "event"/"resets to None").
- **`selected()`'s re-render behavior, and the opt-in `clicked()` exception, made explicit.** Verified live:
  checked a cell, forced a re-render with no data change, and `selected()` was also byte-for-byte unchanged --
  confirmed this is because the seed-at-attach mechanism re-seeds from the *new* grid's `selection` trait, and
  that trait is itself restored by mols2grid's own `cache_selection=True` default (the renderer keeps a stable
  generated grid name across re-renders of the same output, which is what makes the cache hit). Rewrote the
  table's "across re-render" column and the `selected()` prose to say *why* it looks preserved, rather than
  implying the accessor itself retains it. Added an explicit callout (accessor reference section) that
  `clicked()` is the one deliberate exception to "every accessor attaches at render" in this roster -- it only
  exists with `clicks=True`/a `callback`, and raises `RuntimeError` (exact message quoted) rather than returning
  `None` otherwise. Verified the raise live: `render_mols2grid()` with neither `clicks=True` nor `callback=`, read
  `.clicked()` in a `@render.code` function, confirmed the exact message.
- No other `render_mols2grid` behavior changed between `00f90249` and `32ca7035`; every other claim in the guide
  (search, styling/transform, prerender, filter(), rate-limiting inertness, layout/sizing, Gotchas) was re-read
  against current `main` source and still matches -- not re-screenshotted, since none of it was edited.
- `accessors:` front matter unchanged (`[selection, clicked]`).

### Verification (this update)

All via a scratch probe app (two grids: one with `clicks=True` + a re-render button, one without `clicks=True`
to trigger the raise), driven with the selectors from `tests/playwright/mols2grid_accessors/test_mols2grid_accessors.py`
(`.m2g-cell:not(.m2g-phantom)`, `.m2g-cell .m2g-callback`, the jQuery-events-bound poll). No `guide.md` example or
gallery file's *code* changed (only comments), so none needed new screenshots; the behavioral claims above were
verified directly against the live app, not inferred from source alone.

| Check | Result |
|---|---|
| `clicked()` without `clicks=True`/`callback` | raises `RuntimeError: clicked() needs the grid's click channel, which the document only renders when asked: add clicks=True (or a Python callback=) to the @render_mols2grid decorator.` |
| `selected()` before any check | `{}` |
| `clicked()` before any click | `None` |
| `selected()` after checking cell 0 | `{0: 'CCC(C)CC'}` |
| `clicked()` after clicking cell 1's image | full row dict (`mols2grid-id`, `img`, `ID`, `SOL`, `SMILES`) |
| `selected()` after a re-render with unchanged data | `{0: 'CCC(C)CC'}` -- unchanged |
| `clicked()` after the same re-render | identical dict -- unchanged |

### Bugs found (2026-11-11)

None new. The docs-precision gaps already on record in this file (payload extra keys, inert `rate_policy`,
`iframe_height` + `fill=False`) are unchanged on current `main` and still apply; they're PR #437-unrelated so I
didn't re-verify them a second time this pass.

## Session interruption (for the record, not for the website)

Partway through this pass, the coordinator's process restarted and the scratchpad (including my driver scripts and
two screenshots for `examples/09_plotly_scatter_link.py`) was wiped; the run worktree was recreated at the same
path, same commit, same locked dependency versions. I rebuilt the driver script from the same working gesture
logic already proven in this session and re-ran `examples/09_plotly_scatter_link.py` once more (253 -> 187
matching items, identical to the pre-wipe result), then continued with the remaining examples and the gallery
apps. No other deliverable content was lost; everything under `docs/widget-guides/mols2grid/{examples,img}/`
survived the restart untouched.

## Update 2026-11-11 (B1 rename: selection() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.
- `img/selection_*.webp` re-shot.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." Judgment call: mols2grid doesn't cleanly fit any of
the three large-data approaches (GPU draw / server summary / only-send-visible) -- every row is inlined into
the iframe up front regardless of pagination, which I said plainly rather than force-fitting one of the three.
Used the already-measured figure from the renderer's own docstring (0.5-1 KB/molecule, tens of thousands
approaching the 16 MiB websocket limit) instead of re-measuring; that number reads as independently verified by
an earlier pass per this guide's own NOTES above. No new example needed. Links forward to the not-yet-written
`../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) -- expected
`check_docs.py` anchor warning.

## Update 2026-11-11 (Task 12: final sweep)

Corrected the "Large data" section's websocket-limit claim: `shiny run --ws-max-size` (uvicorn/`websockets`'
`max_size`) only limits messages the server *receives* from the browser. mols2grid's grid HTML is pushed
server-to-browser as widget state, so raising that flag would not help a grid that's too large -- reworded to
say the real lever is filtering server-side before constructing the grid. Verified via `websockets.serve`'s
own docstring ("Maximum size of incoming messages") and `shiny`'s `ws_max_size` passthrough in
`shiny/_main/_run.py`.
