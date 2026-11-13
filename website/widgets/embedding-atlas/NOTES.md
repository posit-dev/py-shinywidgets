# NOTES: Embedding Atlas guide

## Versions and environment

- Date: 2026-10-30
- shinywidgets: `main` @ `00f90249`, sourced from an isolated worktree detached at `origin/main`
  (`/private/tmp/claude-502/.../scratchpad/main-wt`) -- the shared main checkout changed branches mid-session
  (another agent switched it to a mols2grid port branch), so every `uv run` after that point used
  `uv run --no-project --python 3.12 --with-editable <worktree> --with embedding-atlas --with "duckdb==1.5.6"
  --with plotly --with pillow --with scikit-learn --with playwright --with pytest --with umap-learn ...` instead
  of the shared checkout's venv, to guarantee the code under test was actually `main`.
- embedding-atlas 0.26.0, **duckdb 1.5.6 (the project's locked version, per `uv.lock`)**, shiny 1.9.0, pandas,
  scikit-learn (ephemeral, for the digits examples only), umap-learn (ephemeral, for `02_compute_projection.py`
  only). An earlier pass of this guide pinned no duckdb version in the overlay, which silently resolved duckdb
  2.0.0 (not what the project ships) and led to a false bug report that `.sql(...).fetchone()` was removed --
  retracted below; duckdb 1.5.6 supports it fine, and all examples use `.sql(...).fetchone()`/`.df()` as originally
  natural.
- Browser: Playwright Chromium, headless, **`channel="chromium"`, `args=["--enable-unsafe-webgpu",
  "--use-angle=metal"]`, navigating to a real `http://127.0.0.1:<port>` origin**. This combination gives a real
  WebGPU adapter with the `shader-f16` feature the embedding view needs (confirmed via
  `navigator.gpu.requestAdapter()`), and every screenshot in this guide shows the actual GPU-rendered map. An
  earlier pass of this guide incorrectly reported no WebGPU in this environment; that was a probing error on my
  part (I'd tested via `page.goto("data:text/html,...")`/`about:blank`, and `navigator.gpu` only exists in a
  secure context -- data: and about:blank URLs don't count, but `http://127.0.0.1` does). Real hardware: Apple M4
  Pro (`system_profiler` confirms Metal 4). This correction came from the coordinator, who verified it
  independently and asked me to redo the WebGPU-dependent content; I re-shot every screenshot in the guide with
  this launch configuration for consistency, not just the ones that strictly needed it.
- Ports 9340-9359 (assigned range). Driver scripts and probes in
  `/private/tmp/claude-502/.../scratchpad/agents/embedding-atlas/` (`common.py` + `shoot_*.py` / `reshoot_all.py` +
  `probe_*.py` + `debug_08.py` + `test_widget_self_read.py`).

## Verification table

Every example and gallery app was run with `shiny run` (via the overlay env above, with the WebGPU-enabled
browser) and screenshotted with Playwright; every screenshot was viewed with the Read tool before being referenced
in `guide.md`.

| file | ran | screenshot(s) | gesture driven | accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `quickstart.webp` | none (static) | n/a |
| `examples/02_compute_projection.py` | yes (both the offline cache-build and the viewer) | `compute_projection.webp` | none (static) | n/a |
| `examples/03_auto_labels.py` | yes | `auto_labels.webp` | none (static) | n/a |
| `examples/04_images.py` | yes | `images.webp` | none (static) | n/a |
| `examples/05_predicate_query.py` | yes | `predicate_before.webp`, `predicate_after.webp` | bar click ("closed") | `predicate()` confirmed: stat text changes from 6,088/0.26/2.38 to 4,149/0.13/2.60 |
| `examples/06_selection_table.py` | yes | `selection_table_before.webp`, `selection_table_after.webp`, plus `map_drag_before.webp`/`map_drag_after.webp` | bar click ("py-shinywidgets"), **and a real shift-drag box on the WebGPU embedding canvas** | `selected()` confirmed both ways: bar click narrows 6,088 -> 139 rows; the canvas box-drag narrows 6,088 -> 1,723 rows, with the linked table updating to match |
| `examples/07_update_in_place.py` | yes | `update_in_place_before.webp`, `update_in_place_after.webp` | bar click + `<select>` change (repo dropdown, triggers re-render) | n/a directly, but verifies the `_state`/`initial_state` round trip: the "closed" filter and its highlighted bar survive the re-render onto new (139-row) data |
| `examples/08_predicate_to_plotly.py` | yes | `predicate_to_plotly_before.webp`, `predicate_to_plotly_after.webp` | bar click ("shinychat") | `predicate()` confirmed via the plotly chart narrowing to one bar |
| `examples/09_selection_to_cards.py` | yes | `selection_to_cards_before.webp`, `selection_to_cards_after.webp` | bar click ("shinytest2") | `selected()` confirmed via the linked card list (257 rows, all shinytest2) |
| `examples/10_selection_summary_stub.py` | yes | `selection_summary_before.webp`, `selection_summary_after.webp` | bar click ("bslib") | `selected()` confirmed: summary changes to "651 issues, mostly about: theme, bs, sidebar" |
| `examples/11_layout.py` | yes | `layout.webp` | none (static) | n/a |
| `gallery/template_atlas_explorer.py` | yes | `gallery_template_before.webp`, `gallery_template_after.webp` | bar click ("py-shinywidgets") | both accessors confirmed together |
| `gallery/showcase_digits_atlas.py` | yes | `gallery_showcase_before.webp`, `gallery_showcase_after.webp` | bar click ("3") | `selected()` confirmed: average-image panel changes from an indistinct blur to a clear "3" |

**Accessor coverage: both of the renderer's accessors (`predicate()`, `selected()`) were exercised with a real
browser gesture -- a chart-bar click in most examples, and a real shift-drag box on the WebGPU embedding canvas
itself in `06_selection_table.py` -- and confirmed against an independently computed expected value in at least 7
of the 13 files above.** This is complete coverage for this renderer -- it has no other accessors.

### Not independently re-verified (carried as documented facts)

- **DuckDB lockdown blocking file read/write via browser-sent SQL** (brief's security note): I read the renderer
  source (`restrict_embedding_atlas_connection`, `restrict_duckdb_connection`) and the existing
  `tests/playwright/render_embedding_atlas/test_render_embedding_atlas.py::test_embedding_atlas_browser_sql_cannot_touch_server_files`,
  which already exercises this exact attack (a `COPY ... TO` and a `SELECT * FROM '<secret file>'` sent the way
  the explorer's own JS sends them) and asserts `Permission Error`. I did not re-run that test myself in this
  pass -- it's recent, already in the suite, and re-deriving the same probe would have cost significant time for
  no new information. I did independently verify the *positive* side (the lockdown doesn't break the explorer):
  every example above renders and cross-filters correctly with the default (locked-down) connection.
- **Multi-session isolation and one-session-blocks-all-sessions** (old report §3.2): not retested. It's an
  architectural fact (shinywidgets dispatches comm messages on Shiny's event loop; DuckDB's Python API blocks
  synchronously), not something that could have changed between the old report and now, and retesting it needs a
  deliberately slow query held open across two sessions -- an expensive, disruptive probe on a shared, loaded
  machine for a fact that's already correctly attributed. Not included in the guide (see "dropped" below).

## Retracted finding (from an earlier pass of this guide)

An earlier pass reported "DuckDB 2.0 removed `DuckDBPyRelation.fetchone()`/`.fetchall()`" as a bug, based on
`con.sql(...).fetchone()` raising `Relations no longer have fetchone()`. That was an artifact of my own test
environment resolving an **unpinned** `duckdb` dependency to version 2.0.0, which the shinywidgets project does
not actually use or test against (`uv.lock` pins 1.5.6). Once I pinned `duckdb==1.5.6` in the overlay to match the
project, `.sql(...).fetchone()` worked exactly as originally written, repeatedly, with no error. I reverted
`examples/05_predicate_query.py` and `gallery/template_atlas_explorer.py` back to `con.sql(...).fetchone()` and
removed the corresponding Gotchas bullet and code-comment from `guide.md`. Lesson for future passes: always pin
dependency versions explicitly in an ephemeral `--with` overlay rather than letting `uv` resolve latest, or verify
against the project's own `uv.lock`/synced venv before reporting a version-specific behavior as a finding.

## Bugs and surprises found

1. **Upstream bug, verified in depth: the `labels=` option's documented `"automatic"`/`"disabled"` strings don't
   work, and no equivalent Python control exists.** `render_embedding_atlas`'s docstring and
   `EmbeddingAtlasWidget`'s own docstring both say `labels="automatic"` generates labels and `labels="disabled"`
   turns them off. Neither is true. I tested all of: no `labels=` argument (labels appear, matching quick start),
   `labels="automatic"` (zero labels), `labels="disabled"` (zero labels, identical to `"automatic"`'s result), and
   a custom label dict shaped exactly like the docstring's own example (`{"x":, "y":, "text":}`, a JS page error
   `Cannot read properties of undefined (reading 'width')`, also zero labels). I then traced the anywidget JS
   bundle (`embedding_atlas/widget_static/anywidget/index.js`): the literal strings `"automatic"` and `"disabled"`
   do not appear in it anywhere. The real automatic-label on/off switch is
   `embeddingViewConfig.autoLabelEnabled` (a boolean, default on/null per the bundle's own JSON-schema comment:
   "By default labels are generated automatically ... Set this to `false` to disable"), which
   `make_embedding_atlas_props()` in `embedding_atlas/options.py` never sets from any Python option.
   `labels=`/`embeddingViewLabels` is a *different*, independent prop meant for a custom label-list override;
   passing it any non-`None` value (even a nonsense string) appears to suppress the automatic generator as a side
   effect of "the user is managing labels themselves now," without the custom value being used successfully
   either (at least not in the shape the docstring documents). **Net effect for a shinywidgets user: leave
   `labels=` unset if you want labels; there is currently no working way through the Python API to turn them off
   or supply your own.** This is an upstream (apple/embedding-atlas) bug/doc mismatch, not a shinywidgets one --
   shinywidgets passes the option straight through (`set_prop("embeddingViewLabels", options.get("labels"))`,
   unchanged since the design doc). Repro scripts (all against the real `issues.parquet` data, WebGPU on):
   `probe_labels_explicit.py` (`"automatic"` -> 0 labels), `probe_labels_disabled.py` (`"disabled"` -> 0 labels),
   `probe_labels_custom.py` (custom dict -> page error, 0 labels), all in the scratch agents directory.
2. **shinywidgets docs gap, verified, worth fixing: `.widget` read inside its own render function returns last
   render's *stale* widget on every render after the first, not `None`.** The old report's finding (3.5) only
   describes the first-render case ("blanks the output silently"). I instrumented `render_embedding_atlas._render()`
   directly (three consecutive renders, each reading `atlas.widget` at the top of its own render function):
   render 1 sees `None` (as documented), but renders 2 and 3 both see the *previous* render's widget object, with
   no error and no indication it's stale. This is because `_render()` only sets `self._widget = None` *after*
   `self.fn()` returns, so a re-entrant read during `self.fn()` always sees the prior value once there's been at
   least one successful render. This generalizes to every `@render_widget_base` subclass, not just
   embedding_atlas -- I picked this widget because `examples/07_update_in_place.py`'s "read the previous state
   before re-rendering" pattern is exactly the shape that invites this mistake. `predicate()`/`selected()` (and
   presumably other `_read_accessor`-backed accessors across the roster) are *not* vulnerable: they explicitly
   check `rendering_renderer.get() is self` and raise a clear `RuntimeError` instead. Repro:
   `/private/tmp/claude-502/.../scratchpad/agents/embedding-atlas/test_widget_self_read.py`.
3. **Confirmed, not a bug: `compute_projection()` cannot run inside a Shiny app's event loop.** It calls
   `asyncio.run()` internally and raises `RuntimeError: asyncio.run() cannot be called from a running event loop`
   the moment a `shiny run` process (which always has one) imports a module that calls it at module scope. This
   isn't documented anywhere I could find (the function's own docstring only mentions Jupyter). I restructured
   `examples/02_compute_projection.py` into an offline cache-building script (`if __name__ == "__main__"`) plus a
   normal viewer app, matching the real pattern `docs/showcase/issues/embed.py` + `app.py` already use. The guide
   section frames this as the correct, expected workflow rather than a bug to route around invisibly.
4. **Confirmed: the old report's "400px non-fillable default is too short" complaint is resolved on current
   main.** `shinywidgets.css` now has an Embedding-Atlas-specific rule (search "Embedding Atlas hard-codes a
   650px") that fits the explorer to an *explicit* output/widget height when one is given, and otherwise leaves it
   at its own 650px default -- confirmed in `examples/11_layout.py`'s screenshot (the fixed-height card shows
   exactly 650px, and a non-fillable context with no explicit height keeps 650px rather than being squeezed to
   400px as in the old report).
5. **Verified from the anywidget JS bundle, not just the docstring:** `_predicate` and `_state` are written
   browser-to-Python via `model.set(...)` + `model.save_changes()`, and the *only* `model.on("change:...")`
   listener registered client-side is for an unrelated theme-detection concern -- there's no listener that would
   apply a Python-driven `_predicate`/`_props`/`_state` change to the live view. This independently confirms (by
   reading the actual runtime code, not just trusting the docstring) the "ignores Python-driven changes" claim in
   the class docstring and in the old report's finding 3.4.
6. **Observed, likely intentional: automatic labels need sufficient point density to appear at all.** The
   139-row py-shinywidgets-only subset (`examples/07_update_in_place.py`'s "after" state, and an early attempt at
   a smaller `03_auto_labels.py`) shows zero cluster labels even with `labels` correctly left unset, while the
   full 6,088-row dataset shows many. No error either way; consistent across repeated renders. Likely the
   `autoLabelDensityThreshold` concept visible in the JS bundle (a density cutoff relative to the max density) --
   with few, scattered points, no region clears the threshold. Documented as a Gotcha, not reported as a bug.

## Judgment calls for the maintainer to revisit

- **Reused the release showcase's real dataset (`docs/showcase/issues/data/issues.parquet`, copied into
  `examples/data/issues.parquet`, 2.9 MB) for the quick start and most examples**, instead of a smaller synthetic
  one. It's real, topical (Shiny-ecosystem GitHub issues), already has a genuine precomputed text projection, and
  lets "computing a projection" point at a real script (`embed.py`) instead of hand-waving. The tradeoff: it's a
  3 MB file inside the guide's own `examples/` directory, and several examples now share one large dataset rather
  than each being fully self-contained with a tiny inline one. I think this is a net win for a guide whose whole
  point is "explore a real corpus," but flagging the file-size tradeoff explicitly.
- **`examples/02_compute_projection.py` is not a typical `shiny run` app -- it's an offline script with a Shiny
  app bolted onto its `else` branch.** This is a deliberate, verified response to `compute_projection()`'s
  event-loop restriction (see Bugs found #3), and it mirrors the real `embed.py`/`app.py` split, but it's a
  different shape from every other example file in this guide (and the roster's convention generally). If the
  maintainer would rather keep every example a pure `shiny run` target, the alternative is dropping this example
  entirely and only describing the offline step in prose with a link to `embed.py` -- I chose to keep a runnable
  example because "my `compute_projection()` call doesn't work" is a very likely first stumble for a new user.
- **Only 1 accessor-adjacent example uses a synthetic/small dataset (`02`'s topic clusters); everything else uses
  the real issues data.** This was a deliberate choice for "recognizable, compelling" data per the brief, at the
  cost of every predicate/selection example now reading the same `issues.parquet` rather than varying with
  `sklearn.datasets` or similar, the way some other guides in this roster do.
- **The labels bug (finding #1) consumed significant verification time** (bundle tracing, three separate repro
  apps) for a single Gotchas bullet. I judged it worth it because it directly contradicts a docstring claim the
  guide would otherwise have taught as fact (my first draft of `03_auto_labels.py` did exactly that, with a
  toggle switch between `"automatic"`/`"disabled"` that silently never showed a label in either position -- that
  app is why I went looking). Flagging in case the maintainer wants a shorter version of this bullet for the
  website; the full mechanism (the autoLabelEnabled vs. embeddingViewLabels distinction) may be more detail than
  a guide reader needs, versus just "don't pass `labels=`."

## Editor's notes for the website

- **Strongest sections:** "Updating the widget from Python" (the before/after screenshot pair is a clean,
  unambiguous demonstration of the `_state`/`initial_state` round trip, now with the real map and cluster labels
  visible), "Driving it from the map itself" (a genuine shift-drag box gesture on the WebGPU canvas, not just a
  bar-click stand-in), and the digits gallery showcase (the average-image payoff is immediately legible even as a
  static screenshot -- a blurry "3" is obviously a 3).
- **Hero image:** `quickstart.webp` now shows the real GPU-rendered map with automatic cluster labels over 6,088
  real GitHub issues -- a strong, specific hero rather than a generic scatter.
- **Could cut for a shorter page:** the `reactive_read()` subsection is thin (one trait, `_state`, already fully
  covered by the "Updating the widget from Python" section) and could be folded into that section instead of
  standing alone. The "Rate limiting" subsection is also thin (one shared policy, no per-accessor nuance) and
  could become a single sentence in the accessor reference's intro paragraph instead of its own heading.
- **Security note placement:** I put the DuckDB lockdown warning in Gotchas (now the first bullet) rather than its
  own top-level section, since `@render_embedding_atlas` handles it by default and the guide's intro paragraph
  already calls it out. If the maintainer wants it more prominent (the old report treated it as the #1 finding),
  promoting it to its own `## Security` section between Installation and Quick start would be an easy edit.
- **The labels Gotcha is the longest bullet in the page** by a wide margin. Could be trimmed to 2-3 sentences for
  the website if the full mechanism is too much detail; I kept the long version in this pass because it's a novel,
  well-evidenced finding that directly contradicts the upstream docstring.

## What I dropped from the old report, and why

- **Performance tables (construction time, websocket bytes, query latency at 10k/100k/1M rows).** Real
  measurements, but they're PR-review material about the renderer's transport cost in general (anywidget's
  `_esm` bundle size), not something specific to teaching this widget's features; the brief says to drop stale
  PR-review content.
- **The one-session-blocks-all-sessions finding (§3.2).** Still true (architectural, not retested -- see "Not
  independently re-verified" above), but it's a deployment/robustness caveat better suited to a cross-cutting
  "deploying shinywidgets apps" article than a single widget's feature guide, and re-demonstrating it convincingly
  needs a deliberately disruptive slow-query probe I didn't think was worth running on a shared machine.
  Mentioned nowhere in this guide; worth a one-line callout in a cross-cutting deployment doc if one exists.
- **`selection(format="predicate")` raises (§3.9).** This is `EmbeddingAtlasWidget.selection()`'s own `format=`
  parameter (upstream, unrelated to shinywidgets' `render_embedding_atlas.selected()` accessor, which doesn't
  take a `format` argument at all) -- out of scope for a guide about the shinywidgets integration.
  An upstream-library detail, not rechecked.
- **Narrow-width/percentage-height stacking specifics (§3.11) beyond what I re-verified.** I kept the
  re-verified, still-true part (the side panel collapses below ~600px, confirmed in `11_layout.py`'s screenshot)
  and dropped the more exhaustive old measurements (286px exact breakpoint, `layout.height="50%"` exact pixel
  result) as excess detail for a guide.
- **The gesture-convention nit list (⌘-click replaces vs. adds, lasso predicate byte size, etc., §3.12).** Mostly
  true but hyper-specific UI trivia better suited to upstream's own docs than this guide; linked to upstream docs
  instead via "Learn more." (The box/lasso gesture itself -- shift-drag / shift+⌘-drag -- is now demonstrated
  directly in "Driving it from the map itself.")
- **Dark mode / `input_dark_mode()` bridge recipe.** Real and still presumably true (I didn't retest), but it's a
  general bslib-theming concern that applies to several widgets in this roster, not specific to Embedding Atlas;
  better suited to a cross-cutting theming article than repeated per-widget.

## Update 2026-11-11 (main @ 32ca7035)

Brought up to date against `main` @ `32ca7035` (33 commits ahead of the `00f90249` base this guide was verified
against on 2026-10-30). This guide needed the least structural change of the four DuckDB/table guides in this
round: `render_embedding_atlas`'s connection lockdown predates this release and was already correct and already
had its own Security bullet (quak's and mosaic's new Security sections were written to match this guide's
existing wording, not the other way around). Relevant commits: #437 (`.read()`), no accessor-semantics change
(`predicate()`/`selected()` were already "state" accessors, re-seeded every render -- #437 unifies vocabulary
across renderers, not behavior here).

- **Accessor reference table**: reformatted to the new standard columns (`returns | before any interaction |
  across re-render | default rate policy`). No behavior change.
- **`reactive_read(atlas.widget, "_state")` → `atlas.read("_state")`** (#437's `.read()` fallthrough, which
  this release adds as the taught tier-2 fallback everywhere a renderer output exists, replacing
  `reactive_read(x.widget, "trait")`). Changed in `examples/07_update_in_place.py` (dropped the now-unused
  `reactive_read` import) and in the guide's "Beyond the accessors" heading/body, the inline code copy in
  "Updating the widget from Python," and the "Rate limiting" paragraph's closing sentence.
  - **Verified**: unit-level, `.read("_state")` on a freshly rendered (unbrowsed) widget returns `None`, same as
    `reactive_read()` would (confirmed side by side in a scratch pytest). Then re-ran
    `examples/07_update_in_place.py` end to end in a real WebGPU browser (`--enable-unsafe-webgpu
    --use-angle=metal`, `http://127.0.0.1:8112`): clicked the "closed" bar (4,149/6,088), switched the repo
    dropdown to "py-shinywidgets," and confirmed the "closed" filter carried forward (119/139) -- identical
    numbers to this guide's existing `update_in_place_before/after.webp`. Took fresh screenshots to confirm;
    didn't replace the existing ones in `img/` since the rendered result is pixel-equivalent in content (same
    counts, same chart shape) and the brief only asks to replace screenshots that show *old* behavior or names.
- **Security section**: left the substance alone (it was already accurate and already the template the other
  three guides in this round were asked to match) -- added one sentence cross-linking quak, mosaic, and
  pygwalker's security postures for a reader comparing renderers, now that all four guides use consistent
  wording.
- **New example, "read on demand" (the brief's headline new pattern for this release)**:
  `examples/12_export_selection.py` + a new "Export the current selection, read on demand" subsection in
  Coordinating multiple views -- a download button that reads `atlas.selected()` only when clicked, mirroring
  quak's and mosaic's new/existing CSV-export patterns. Every other pattern in this guide already reads
  `selected()`/`predicate()` continuously (re-rendering as the filter changes); this is the first one that
  reads on a discrete user action instead.
  - **Verified** with a real gesture: clicked the "py-shinywidgets" bar (139/6,088 selected), clicked "Download
    CSV," and inspected the downloaded file directly -- 139 data rows, every `repo` value exactly
    `py-shinywidgets`, matching the explorer's own count. Screenshots `img/12_export_selection_before.webp` and
    `img/12_export_selection_after.webp`, both looked at (Read tool) before citing.
- No other accessor semantics needed updating: `predicate()`/`selected()` were already documented as re-seeding
  fully on every render (no "kept across re-render" case here, unlike click/selection accessors on other
  renderers), which is exactly what #437 formalizes as the "inherent widget state" rule.
- CHANGELOG.md's `@render_embedding_atlas` bullet does already mention the lockdown and
  `allow_unrestricted_connection` (unlike the quak and mosaic bullets -- see their NOTES.md for that gap), so
  nothing to flag here.

### Verification table (new/edited files)

| File | Ran | Screenshot | Gesture driven | Verification |
|---|---|---|---|---|
| `examples/07_update_in_place.py` (edited: `.read()` swap) | yes (WebGPU browser, port 8112) | before/after, both looked at | yes -- bar click + repo dropdown switch | Filter carried forward across re-render (119/139), matching pre-existing guide claim |
| `examples/12_export_selection.py` (new) | yes (WebGPU browser, port 8113) | before/after, both looked at | yes -- bar click + download | Downloaded CSV: 139 rows, all `py-shinywidgets`, matching the explorer's count |

### Bugs found (2026-11-11)

None new. No shinywidgets or docs issues found in this pass -- the `.read()` conversion and the lockdown
cross-reference were both confirmed to behave identically to what the guide already documented.

## Update 2026-11-11 (B1 rename: selection() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.
- `img/selection_table_*.webp` re-shot.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example (this guide's own examples use a deliberately modest 6,088-row dataset for fast gesture verification). Described the combined GPU-map + DuckDB-crossfilter architecture and pointed to jscatter's and quak's/mosaic's own measured ceilings for each half, rather than inventing a combined number that wasn't measured.
