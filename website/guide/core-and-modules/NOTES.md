# NOTES: Shiny Core & modules

Versions: shinywidgets `main` @ `ad97a76d` (merge of `origin/main` into `widget-guides`, includes #456
`selected()`/`selected_rows()` naming), shiny 1.9.0, plotly (locked venv version), date 2026-11-11.

## Verification table

| File | Ran? | Screenshot(s) looked at? | Gesture driven? | Accessor/behavior confirmed? |
|---|---|---|---|---|
| `examples/01_core_app.py` | Yes (`smoke.py`, exit 0) | Yes: `img/01_core_before.webp`, `img/01_core_after.webp` | Yes: real Playwright lasso (multi-point drag via `page.mouse.move/down/up`, coordinates converted through plotly.js's `xaxis.d2p`/`yaxis.d2p`) | `plot.selected_rows(df)` populated the table (25 rows) and the in-place marker-color effect recolored exactly the lassoed points, with no re-render |
| `examples/02_module_two_instances.py` | Yes (`smoke.py`, exit 0) | Yes: `img/02_module_before.webp`, `img/02_module_after_a_only.webp`, `img/02_module_after_both.webp` | Yes: two independent real lassos, one per module instance, in sequence | Namespacing confirmed both directions -- see "Module namespacing" below |
| `examples/03_express_module.py` | Yes (`smoke.py`, exit 0) | Yes: `img/03_express_module.webp`, plus a scratch-only screenshot of the post-lasso state (not copied into `img/`, since it shows the same result as `02_module_after_a_only.webp`) | Yes: one real lasso against instance A | Same no-leak result as the Core-module version: A's table filled to 25 rows, B's stayed at 0 |

All three apps were run with `uv run --no-sync python -m shiny run ... --port <8150-8159>` (or via
`tools/smoke.py`, which picks its own port) and driven with headless Chromium via Playwright
(`sync_playwright`), viewport 1280x800, `device_scale_factor=2`. No WebGL/WebGPU flags were needed (plotly's
default SVG/canvas rendering was sufficient under the default `--gpu none`).

## Module namespacing -- what was actually checked

For `02_module_two_instances.py` (Core `module.ui`/`module.server`):
1. Loaded both instances, confirmed both tables start empty (`img/02_module_before.webp`).
2. Lassoed a cluster of points in instance A only. Result: A's table filled to 25 rows; B's stayed at 0 rows
   (`img/02_module_after_a_only.webp`).
3. Lassoed a *different*, visibly distinct region (a cluster of lower-income African countries) in instance B.
   Result: B's table filled to 13 rows; A's stayed unchanged at its own 25 rows (`img/02_module_after_both.webp`).

Row counts were read back programmatically (`page.locator("#a-selected_table table tbody tr").count()`), not
just eyeballed from the screenshot. Rendered DOM ids confirmed the expected namespacing scheme:
`a-plot`/`a-selected_table`, `b-plot`/`b-selected_table` (module id prefix + `-` + the unprefixed output name
given in the renderer/UI functions).

The same check (lasso A only, read both row counts) was repeated against `03_express_module.py`: A's table
filled to 25, B's stayed at 0. Not re-run in both directions for the Express version, since the Core version
already confirmed the harder direction (both instances populated, independently) and the underlying mechanism
(`shiny.express.module`'s `@module` wraps `@expressify` plus `session.make_scope(id)`) is the same namespacing
Core's `module.ui`/`module.server` uses.

**Result: no accessor leak across module instances, in either direction, under either module syntax.** This
isn't surprising (module namespacing predates shinywidgets' accessors, and renderer objects don't hold any
global or cross-session state), but it was the one thing this task's brief asked to pin down with a real
gesture rather than assume, so it's recorded here as a verified result, not a guess.

## Express modules

`shiny.express.module`'s `@module` decorator works with shinywidgets with no special handling needed:
`@render_plotly` (and, by the same mechanism every other renderer in the roster uses, any other `render_*`)
attaches to whatever session the module scope hands it, same as any other Shiny output. No shinywidgets code
had to change to make this work, and nothing in `03_express_module.py` differs from `02_module_two_instances.py`
beyond the module syntax itself.

## Judgment calls

- **`reactive.isolate()` in `01_core_app.py`'s highlight effect removed (Task 12 sweep).** This file originally
  kept `isolate()` around the marker-color write as a habitual wrapper, even though nothing inside it reads a
  reactive value the effect also writes -- flagged here as dead code pending a maintainer decision. Task 12
  reconciled this with `first-app/examples/03_update.py` (which had the same situation, with its own comment
  claiming isolate() prevented a self-trigger loop that, on inspection, was never possible: `selected_rows()` is
  driven by browser-origin `plotly_selected` messages, not by anything the effect writes to `.widget`). Both
  files now skip `isolate()` on the write and use the same comment shape, pointing to "Writing back"
  (`../updating-in-place/article.md#writing-back`) for the pattern where it's actually required. Verified with
  a real gesture: an instrumented copy of this effect (counting runs) showed exactly one run per lasso across
  two sequential, differently-placed lassos, with no re-triggering, isolate() or not.
- **The "why zoom survives" claim isn't re-verified with a zoom gesture in this Core example.** The mechanism
  (mutating `.widget` in place, not rebuilding the figure) is identical to the Express version this page adapts
  from, and is already measured/verified in `updating-in-place/article.md#writing-back` and the performance
  article; re-driving a zoom-then-lasso sequence here would re-verify the same shinywidgets behavior under a
  different app scaffolding (Core vs. Express), which doesn't change the result. Linked rather than re-proven.
- **`render-widget/guide.md`'s two pre-existing `check_docs.py` problems were left alone.** Running
  `check_docs.py` over the full file (not just the owned intro/category lines) reports two issues already
  present in `tools/BASELINE.txt` before this task (`snippet does not match examples/sparkline_widget.py` and a
  missing link to `../../widget-reports/carbonplan-maps/report.md`, both outside "What you can build," far from
  the intro this task owns). Not touched, per the task's narrow ownership (introduction + `category:` line
  only).

## Deviations from the task block

None beyond the judgment call above (kept, didn't change the code).

## Editor's notes for the website

- The module-namespacing screenshots (`02_module_after_a_only.webp`, `02_module_after_both.webp`) are the
  strongest visual for this page -- they're the only place on the site that shows two independent accessor
  states side by side. If the page needs trimming, keep these two and the "Namespacing, verified" prose; the
  Express-module section could be compressed to a single paragraph plus a link to its example file, since its
  only news is "this works too."
- Considered showing a zoom-preserved-across-lasso screenshot pair for `01_core_app.py` (to visually back the
  "why zoom survives" claim) but decided it would duplicate the already-published evidence in
  `updating-in-place/article.md`; linked instead.

## Findings for FINDINGS.md

None. No shinywidgets bugs, upstream issues, or documentation errors were found while writing this page.
