# NOTES: nglview guide

## Versions

- Date: 2026-10-30 through 2026-11-02 (session was interrupted by a coordinator restart partway through;
  scratchpad/worktree were recreated and work resumed from survived output).
- nglview 4.0.1, ipywidgets 8.1.x, mdtraj (latest via `uv run --with mdtraj`, resolved fresh, no pin conflict --
  mdtraj is not a dependency of shinywidgets so there was nothing to silently override), plotly (worktree's
  pinned version), shiny 1.9.0.
- shinywidgets: `main` @ `00f90249` (fix(plotly) commit) for the second half of the session; the first half was
  against the same commit before the environment reset. No shinywidgets/nglview-relevant commits landed on
  `main` between the two halves (confirmed by re-reading `_nglview.py`, `_render_widget_base.py`'s
  `nglview_layout_defaults`, and `js/src/nglview.ts` after the restart -- unchanged).
- Python 3.12.13, Playwright Chromium headless on macOS, `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` used defensively throughout (not strictly required on this macOS host -- WebGL also
  rendered with no extra flags -- but harmless and matches the brief's Linux-CI guidance).
- Ports used: 9660-9678 (within the assigned 9660-9679 range). All background servers/browsers were started and
  killed by this agent; no `pkill -f shiny` or similar broad kills were used.

## Verification table

Every file was run via `uv run --no-sync shiny run <file> --port <9660-9678>` (or `uv run --no-sync --with
mdtraj python -m shiny run ...` for the three trajectory files -- see "Judgment calls" for why `-m shiny run`
instead of the `shiny` console script). All screenshots were read back with the Read tool before being
referenced in `guide.md`.

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | |
| `examples/02_sources.py` | yes | yes (both options) | select-option to "rcsb" | confirmed live fetch from `files.rcsb.org` renders hemoglobin |
| `examples/03_representations.py` | yes | yes (before/after) | select-option x2 | in-place restyle confirmed (no page reload) |
| `examples/04_selection_highlight.py` | yes | yes (before/after) | dragged both range-slider handles | highlight moved, camera unchanged |
| `examples/05_trajectory_playback.py` | yes | yes | n/a (slider default position; animate button present) | needs `--with mdtraj` |
| `examples/06_click_atom_highlight.py` | yes | yes (before/after) | real canvas click | atom record read back verified field-by-field |
| `examples/07_trajectory_rmsd_linked.py` | yes | yes (initial + after click) | clicked a specific plotly point (frame 40) via its bounding box | slider, vline marker, and 3D frame all moved together |
| `examples/08_camera_orientation.py` | yes | yes (before/after) | real mouse drag-rotate on canvas | `_camera_orientation` matrix changed from drag |
| `examples/09_inplace_vs_rerender.py` | yes | yes (drag/restyle/rerender, 3 shots) | drag + 2 button clicks | camera preserved across restyle, reset on rerender |
| `gallery/template_structure_explorer.py` | yes | yes | n/a (static capture) | |
| `gallery/showcase_md_explorer.py` | yes | yes (initial + interactive) | clicked chart point + clicked an atom | both linked-view directions plus highlight confirmed together |

**No accessors exist on `render_nglview`** (confirmed by reading its class body in `_render_widget.py`: it's a
docstring only, no methods, unlike every other `render_*` class in that file), so there's no accessor-coverage
table to fill in beyond the reactive-read traits documented in the guide (`picked`, `frame`,
`_camera_orientation`), each verified with a real gesture as described above.

## Bugs found

**None currently open in shinywidgets for this widget.** Every blocker/should-fix in the old report
(`docs/widget-reports/nglview/report.md`, dated 2026-10-22, written against PR #290) is fixed on current `main`:

- **Background-thread delivery delay** (old report finding 3.1): method calls nglview makes from its own
  `RemoteCallThread` (e.g. `add_representation()` right after construction) used to wait for an unrelated input
  on released shiny. Fixed: shinywidgets now requires `shiny>=1.9.0` (confirmed in `pyproject.toml`), and the
  `CHANGELOG.md` entry under "Bug fixes" explicitly credits this to "Widget updates made from a background
  thread ... are now delivered to the browser promptly." All nine of this guide's examples make such calls
  (`add_representation`, `clear_representations`, `view.frame = ...`) immediately after construction or in
  effects, and all rendered correctly on the first try with no heartbeat workaround.
- **Thread/widget leak** (old report finding 3.2): fixed by `_nglview.py`'s `stop_threads_on_close()` /
  `stop_nglview_threads()`, hooked into widget close via `_shinywidgets.py`. Verified by reading the
  implementation (it hooks `widget.close`, finds `RemoteCallThread`s by `isinstance` + `t.view is w`, and queues
  a `SystemExit`-raising callback) rather than independently re-measuring thread counts across dozens of
  re-renders -- the old report's own repro (bare `NGLWidget()` instances held in memory) is exactly what this
  code targets, and the fix is narrowly scoped and easy to read; a live re-measurement felt like low marginal
  value for the time it would cost on a shared, heavily loaded machine. Flagging this as a judgment call below.
- **`layout.height` losing width tracking** (old report finding 3.3) and **`NGLWidget(height=)` ignored in fill
  layouts** (finding 3.4): both fixed -- `js/src/nglview.ts`'s `setupNglviewAutoSize(..., trackHeight)` and
  `_render_widget_base.py`'s `nglview_layout_defaults()` now handle both cases, and the shipped
  `tests/playwright/render_nglview/test_render_nglview.py` has dedicated tests for each
  (`test_nglview_with_own_height_tracks_output_width`, `test_nglview_own_height_wins_over_explicit_output_height`).
  Not independently re-driven this session (read the implementation and the passing-by-design shipped tests
  instead); see "Layout and sizing" in `guide.md` for what ships.
- **Import-time widget crash** (old report finding 5): fixed by `importing_nglview()` in `_nglview.py`, wired
  into `_shinywidgets.py` alongside `importing_lonboard()`. Not independently re-tested (would require a core,
  non-Express app with a specific import order -- a narrow, already-documented edge case that the fix directly
  targets).

**New, still-open (upstream, not shinywidgets):**

- **The NGL GUI (`view.gui_style = "ngl"`) still renders unstyled** -- re-verified this session with a fresh
  screenshot (not just citing the old report): stacked plain-HTML controls ("File", "Open...", "PDB", checkboxes,
  "Screenshot", "Export image...", "View", etc., all unstyled). This is a result of nglview's theme CSS only
  being loaded implicitly by a notebook, not something shinywidgets can reasonably fix by itself (the CSS is
  page-wide), so I kept it in Gotchas as "build your own GUI with Shiny inputs instead" rather than suggesting a
  built-in fix.
- **`show_file(..., gui=True)` is a no-op** (the stored flag is never read upstream) -- not independently
  re-verified this session (low value: `view.gui_style = "ngl"` is the documented, working alternative, and the
  old report already traced this to `_init_gui` never being read).
- **`nglview.show_pdbid()` still blocks the server synchronously** via `urlopen()` inside `PdbIdStructure`
  (confirmed by reading `nglview/adaptor.py` this session) -- documented as a Gotcha, with `show_url()` as the
  non-blocking alternative (verified working, fetches from `files.rcsb.org`, see `examples/02_sources.py`).

**Behavior worth documenting precisely (not a bug, but easy to get wrong):** `picked` fires twice per click --
`{}` first, then the atom record -- verified this session by logging every change server-side
(`PICKED_EVENT: {}` immediately followed by `PICKED_EVENT: {'atom1': {...}, 'component': 0}`). Code using
`picked.get("atom1")` (as every example in this guide does) handles this correctly without extra guarding.

## Judgment calls

- **`uv run --no-sync --with mdtraj shiny run ...` silently ignored the `--with` overlay** (the `shiny` console
  script resolved from the base venv's `.venv/bin/shiny`, not the overlay, so `import mdtraj` failed with
  `ModuleNotFoundError` even though `uv run --no-sync --with mdtraj python -c "import mdtraj"` worked fine in
  the same invocation). Worked around by using `uv run --no-sync --with mdtraj python -m shiny run ...`
  instead, which does pick up the overlay. This is a `uv`/`shiny`-console-script interaction, not a
  shinywidgets issue, but worth a note for other agents using `--with` for a Shiny app specifically (as opposed
  to a plain `python -c` check).
- **Chose not to add a dedicated example for nglview's built-in trajectory player** (`.widget._iplayer`, a
  `Play`+`IntSlider` box nglview constructs automatically and links to `frame` via `ipywidgets.jslink`).
  Verified in a scratch diagnostic that displaying it and dragging its slider does update `frame` on the Python
  side (confirmed via `reactive_read`), which is why the guide's "`frame`: scrub or stream a trajectory" section
  states this as fact -- but promoting it to a full numbered example felt like diminishing returns next to the
  Shiny-native slider pattern every other example already uses, so it's mentioned in prose only.
- **Swapped in real structures over synthetic ones everywhere**: nglview ships genuine PDB data
  (`nglview.datafiles.PDB` = rhodopsin 1U19, `datafiles.XTC` = its 1 ns MD trajectory) that needs no network,
  so the quickstart and most examples use it; the hero and the "any structure source" example additionally
  fetch hemoglobin (4HHB) live from RCSB via `show_url()`, both to demonstrate that path and because the
  four-chain tetramer with heme groups makes a more compelling hero image than a single rhodopsin monomer.
- **Root-caused what looked like a severe shinywidgets hang, and it wasn't one.** A throwaway diagnostic script
  (a bare `@reactive.effect` that both read a widget trait and called `some_reactive_value.set(...)`, with a
  `@render.text` depending on that value) reliably hung every session at startup (no canvas, ever) -- reproduced
  identically before and after the environment reset, which initially looked like a real, reportable bug tied
  to reading `.widget` before first render. Bisecting line-by-line traced it to a self-referential reactive
  loop in *my own test code* (`count.set(count.get() + 1)` inside an effect that, via `count.get()`, had also
  made itself depend on `count` -- an infinite invalidate-rerun loop with no connection to nglview, confirmed
  by reproducing the identical hang with the nglview/`reactive_read` call removed entirely). Not a shinywidgets
  or nglview bug; flagging only so the coordinator isn't surprised if this pattern shows up in another agent's
  scratch files from the same session family.
- **Did not re-measure the thread-leak fix's effectiveness with a live multi-rerender count** (see "Bugs
  found" above) -- read the implementation instead, given machine load and time spent on the environment
  reset. If the coordinator wants this independently measured, it's a 20-line script (re-render N times,
  `threading.enumerate()`, filter by `isinstance(t, RemoteCallThread)`).

## Editor's notes for the website

- **Strongest sections**: the trajectory + RMSD linked-view pattern (`07_trajectory_rmsd_linked.py` /
  `showcase_md_explorer.py`) is the best material in this guide -- it's a genuine, verified bidirectional
  cross-widget link (plotly click -> 3D frame -> plotly marker), not just two things sharing a slider. The
  in-place-vs-rerender three-shot sequence (`09`) is also unusually concrete evidence (most guides can only
  assert "the camera is preserved"; this one shows it, then shows it being lost on rerender for contrast).
- **Candidate for cutting if the page runs long**: the `_camera_orientation` subsection is real and verified,
  but it's the least actionable of the three reactive-read traits (nobody's building a feature on a raw 4x4
  matrix without more scaffolding). Could compress to a single paragraph with no code snippet if space is
  tight.
- **Hero image**: used the RCSB-fetched hemoglobin screenshot (`img/hero.webp`, same file as
  `img/02_sources_rcsb.webp`) rather than the bundled rhodopsin, since the four-chain tetramer with visible heme
  groups reads better at a glance than a single monomer.

## What was dropped from the old report, and why

- **The thread-leak measurement methodology** (killing threads, counting across 40 re-renders) -- the fix
  already exists and is narrowly scoped; re-measuring felt lower-value than spending the time on new content
  (the linked-view patterns, which didn't exist in the old report since accessors/this pass's patterns are new).
- **The PR-review framing entirely** (blockers/should-fix/nits scorecard, rebase conflicts, "what's good") --
  obsolete now that the PR merged; this guide only documents current `main` behavior.
- **The heartbeat workaround recipe** (`reactive.invalidate_later(0.25)` for shiny<1.9) -- no longer needed
  since shinywidgets pins `shiny>=1.9.0`.
- **The "import nglview before shinywidgets" caveat** -- fixed by `importing_nglview()`; no longer a gotcha.
- **The thread-count scorecard numbers** -- superseded by the fix; kept only a one-line mention that it's fixed.

## Pairs with

- **plotly**: the trajectory + RMSD example uses `render_plotly`'s `clicked()` accessor to drive the viewer's
  frame in the reverse direction. Worth featuring in a cross-widget "linked views" article.
- **matplotlib**: mentioned as an alternative plotting backend with its own `clicked()` accessor, for anyone who
  prefers ipympl over plotly for the RMSD-style chart.

## Update 2026-11-11 (main @ 32ca7035)

Versions: shinywidgets `main` @ `32ca7035`, nglview 4.0.1, mdtraj (via `uv run --no-sync --with mdtraj`,
unpinned -- not in the lockfile, nothing to shadow), plotly (worktree's locked version), shiny 1.9.0, Python
3.13, shared `main-wt` worktree. Playwright: Chromium headless with `--use-angle=swiftshader
--enable-unsafe-swiftshader --ignore-gpu-blocklist`.

**What changed in the guide and why:**

- **Converted every `reactive_read(x.widget, "trait")` to `structure.read("trait")`**, per the brief: nglview
  has no accessors, and all three traits this guide reads (`picked`, `frame`, `_camera_orientation`) live on
  the rendered `NGLWidget` itself (`structure.widget` *is* the object `structure()` returns), so they're a
  tier-2 case, not tier-3 -- there's no child/nested widget here the way ipyleaflet layers or cytoscape
  nodes are. Updated: the intro paragraph, the "Accessor reference" lead-in, the "Rate limiting" section,
  `examples/06_click_atom_highlight.py`, `examples/08_camera_orientation.py`,
  `gallery/template_structure_explorer.py`, and `gallery/showcase_md_explorer.py` (and `guide.md`'s copies of
  each code block, kept byte-identical).
- **Added `examples/10_read_on_demand.py`** ("Read on demand: log picks from a button"), new this pass: click
  atoms, then a button reads `structure.read("picked")` on demand to append the current pick to a growing
  table. This is the capability the brief specifically called out as newly worth demonstrating -- previously,
  the "event vs. state" split meant a reader like this risked missing a click that happened before the first
  read; now every accessor/trait is live from render, so a cold read in a button handler just works. Added one
  sentence of text explaining why, matching the brief's "don't pad all five" guidance (one example, not a
  whole new section elsewhere).

**Re-verified claims (all with a real browser, this pass):**

- `structure.read("picked")`, `structure.read("frame")`, `structure.read("_camera_orientation")` all fire
  correctly: verified directly with a probe app reading all three
  (`scratchpad/agents/threed/probe/ngl_read_test.py`) -- `frame` reads `0` at start, `_camera_orientation`
  updates after a real drag, and `picked` returns the correct atom record after a real click (grid-searched
  the canvas for a hit, same technique the original NOTES used for picking).
- `examples/06_click_atom_highlight.py` (converted): real click, correct atom info text AND the in-place
  spacefill highlight both confirmed (screenshot: `GLY 329 chain B`, orange highlight visible).
- `examples/08_camera_orientation.py` (converted): real drag-rotate, matrix changed from the identity-ish
  starting value to a new one.
- `gallery/template_structure_explorer.py` and `gallery/showcase_md_explorer.py` (converted): both re-run with
  a real click; both produced correct atom info text, zero console/page errors.
- `examples/10_read_on_demand.py` (new): real click + button click, logged row matches the clicked atom
  (`SER 38 B` in one run, `VAL 138 B` in the screenshot run); table empty before any log, one row after.
- Did not need to touch `examples/01-05, 07, 09` -- none of them use `reactive_read()` on the rendered widget
  in a way the brief's conversion applies to (01-04 are static/select-driven with no trait reads; 05 only
  writes `frame`; 07 reads `frame` indirectly through a `reactive.value`, never via `reactive_read()` directly;
  09 is the in-place-vs-rerender camera-preservation demo, no trait reads either).

## Bugs found (2026-11-11)

None new.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." No per-atom or per-structure scale number is measured
anywhere in this guide or upstream that I could find, so the section stays qualitative (WebGL rendering cost is
NGL's own, linked to its docs rather than a number) and leans on the one thing this guide *did* verify: frame
scrubbing streams only changed coordinates, not the whole structure. No new example or measurement added this
pass. Links forward to the not-yet-written
`../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) -- expected
`check_docs.py` anchor warning.
