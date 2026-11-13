# NOTES: ipyfilechooser guide

## Update 2026-11-11 (main @ 32ca7035)

shinywidgets commit `32ca7035` (worktree `main-wt`); ipyfilechooser/shiny/Python versions unchanged from the
original pass. No commit in 00f90249..32ca7035 touches `ipyfilechooser` or `render_ipyfilechooser`
(`grep ipyfilechooser CHANGELOG.md` finds only the original feature entry); `_accessor_specs` still has no
`ipyfilechooser` entry.

**Explicitly re-verified the update brief's specific question: does `chooser.read("selected")` work now that
`.read()` exists on every renderer output?** No. Confirmed two ways:
1. Source: `ipyfilechooser.FileChooser().has_trait("selected")` is `False` (same for `selected_path` and
   `selected_filename`) -- they're plain `@property` getters, not traitlets traits, so `.read()`'s fallback path
   (`reactive_read()` on a bare trait) has nothing to read.
2. Browser: a scratch probe app with both `register_callback()` (mirrored into a `reactive.value`) and
   `chooser.read("selected")` side by side showed the callback correctly reporting the picked file's path after
   a real pick, while `.read("selected")` raised `AttributeError: render_ipyfilechooser has no accessor or
   synced trait named 'selected'. Accessors: []; bare synced-trait names also work.` both before *and after* the
   pick -- not a stale value, a hard failure every time, exactly as the pre-existing `reactive_read()` guidance
   predicted.

**What changed in the guide:** `register_callback()` + `reactive.value` remains the only correct pattern --
nothing to replace, no simplification available. Added one explicit bullet to "Reacting to user interaction"
confirming `chooser.read("selected")` fails the same way as `reactive_read(chooser.widget, "selected")`, with
the exact verified error text, since the roster's new narrative teaches `.read()` as the default fallback
everywhere else and a reader would otherwise reasonably wonder why this guide doesn't use it. Added a matching
one-clause update to the Quick start intro sentence. No other prose, code, or screenshots needed changes --
this guide gets correctness confirmation only, no new capability.

## Versions

- ipyfilechooser 0.6.0
- shiny 1.9.0
- shinywidgets 0.8.2.post1.dev102+g00f90249 (worktree `main-wt`, detached at `origin/main` 00f90249, 2026-10-30)
- Python 3.12.13
- Date of this pass: 2026-11-02 (resumed after a scratchpad/process restart; all claims below were
  re-verified from scratch against the recreated worktree, not carried over from the interrupted run)

## Accessor coverage

`render_ipyfilechooser` has **no reactive accessors**. Confirmed by reading the class body in
`shinywidgets/_render_widget.py` (it is a docstring only, no methods) and grepping
`shinywidgets/_accessors.py` for any `ipyfilechooser`/`FileChooser` entry (none). The guide documents the
`register_callback()` + `reactive.value` pattern in its place, and explains why `reactive_read()` can't work
(`selected`/`selected_path`/`selected_filename` are plain `@property` getters over private fields, not traits --
confirmed by reading ipyfilechooser 0.6.0's `filechooser.py` source directly).

## Verification table

| File | Ran? | Screenshot? | Gesture driven? | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | before/after | yes (open dialog, select `report.csv`, confirm) | clean |
| `examples/02_data_preview.py` | yes | before/after | yes (filter confirmed excludes `README.txt`; pick CSV; table + plot both render) | plot needs ~1.5-2s after confirm to paint in headless Chromium -- not a bug, just plotly.js load time |
| `examples/03_directory_listing.py` | yes | before/after | yes (navigate into `data/`, confirm directory) | initial layout used `fillable=True` + `full_screen` card, which pushed the table to the bottom of a tall empty card; switched to a plain non-fillable card, matching this widget's natural-size design |
| `examples/04_python_controlled.py` | yes | before/after | yes (toggle hidden, change filter, jump bookmark -- all three confirmed via the rendered `<option>` list in the open dialog) | confirmed `.reset(path=...)` closes an open dialog; screenshot pair reopens it to show the result |
| `gallery/template_data_explorer.py` | yes | yes | yes (pick `gapminder.csv`) | clean; plotly animation frame (by `year`) renders fine |
| `gallery/showcase_file_inspector.py` | yes | before/after (README text preview; CSV table+plot after jump+pick) | yes | required two real fixes during verification -- see "Bugs found" |
| sandbox-escape probe (`scratch/probe/app.py`, not shipped) | yes | `img/sandbox_escape_blocked.webp` | yes (typed `../secret.txt` into the filename field) | Select/Change button verified disabled in a real browser; Playwright's own `.click()` timed out with "element is not enabled" |

All screenshots were read back with the Read tool before being referenced in guide.md.

## Bugs found

None in shinywidgets itself on current `main`. Three things worth flagging, none of them shinywidgets bugs:

1. **(ipyfilechooser interaction, not a bug, but a sharp edge)** `FileChooser.reset(path=...)` silently
   re-applies `select_default`'s selection (updating `fc.selected`) without invoking the `register_callback()`
   callback. Combined with the fact that Shiny `@reactive.effect`s run once at startup, a plain (non-event-gated)
   effect that calls `.reset(path=...)` in response to an input will fire at app start and immediately clobber a
   `select_default`-seeded `reactive.value`, before the user does anything. Fixed in the showcase gallery app
   with `@reactive.event(input.jump, ignore_init=True)`. This is now documented as a named gotcha and shown
   working correctly in `gallery/showcase_file_inspector.py`. Not a regression -- this is the first guide to
   combine `select_default=True` with a Python-driven `reset()`, so nothing regressed; it just hadn't been
   exercised before.
2. **(ipyfilechooser behavior, verified, not a bug)** `.reset(path=...)` closes the dialog if it was open.
   Documented as a gotcha; verified with Playwright (dialog listing `is_visible()` goes `False` immediately
   after a Python-triggered reset).
3. **(docs-adjacent judgment call, not a shinywidgets bug)** My own first draft of the showcase app used
   `ui.panel_conditional("output.kind == 'csv'", ...)` with a hidden `@render.text` output to switch between a
   table+plot view and a text-preview view. This does not work in py-shiny: `panel_conditional` only evaluates
   client-side JavaScript conditions over **input** values, and the output's own container was hidden via CSS,
   which triggers Shiny's `suspend_when_hidden` default and the output never computes a value in the first
   place. py-shiny's own bundled skill doc (`shiny/.agents/skills/shiny-for-python/references/dynamic-ui.md`)
   says explicitly: "Using `panel_conditional` when the shown/hidden content depends on server-side data -> use
   `@render.ui`". I did not chase a `@render.ui`-based dynamic-swap architecture further, because nesting other
   `@render_*`-decorated shinywidgets outputs (itables/plotly) inside a dynamically recomputed `@render.ui`/
   `@render.express` block isn't an established, verified pattern, and the showcase doesn't need it: both
   preview cards are always mounted, each gated with `req()`, and the non-matching one just renders as an empty
   card (confirmed harmless and already the behavior shown in `02_data_preview.py`'s "before" state).

## Judgment calls for the maintainer

- Used a 2-card "always mounted, `req()`-gated" layout for the showcase's CSV-vs-text preview instead of
  conditionally hiding/showing one or the other. The inactive card is just an empty bordered box. If this reads
  as unpolished on the website, the fix is a `@render.ui` that returns plain HTML (e.g. `df.head(20).to_html()`,
  a static Plotly `to_html(include_plotlyjs="cdn")`) instead of nesting `render_itables`/`render_plotly`, trading
  the shinywidgets integration for true conditional display. I left it as the simpler, fully-verified option.
- Categorized this guide as "Input & drawing" per the roster list in BRIEF.md.
- `accessors: []` in the frontmatter (empty list, not omitted) to make the "no accessors" fact explicit and
  machine-checkable for the website generator.
- Cross-links: pairs with `itables` and `plotly` (used in the "pick a CSV, preview it" pattern, the template
  gallery app, and the showcase). No other agent's app was inspected; these are generic, well-known APIs
  (`px.scatter`, `render_itables`) so the pairing should stay valid regardless of what those guides end up
  saying.

## What was dropped from the old report (`docs/widget-reports/ipyfilechooser/report.md`)

- The PR-review framing (gate results, scorecard, "merge verdict") -- not relevant to a user-facing guide.
- The two-session isolation check -- true and still worth knowing, but not guide material; shinywidgets'
  per-session isolation is a roster-wide property, not specific to this widget.
- The `importing_ipyfilechooser()`/`own_ipyfilechooser_layout()` fix is still mentioned (users should know
  `FileChooser()` just works), but compressed to one gotcha bullet instead of the old report's multi-paragraph
  implementation walkthrough -- the exact mechanism isn't something a guide reader needs.
- Kept and re-verified from the old report: the properties-not-traits fact, `select_default` not firing the
  callback, and the single-click-navigates behavior. All three were re-confirmed against current `main` rather
  than taken on faith.

## Pairs with

- `itables` (table preview of a picked CSV)
- `plotly` (plot preview of a picked CSV)
- `render-widget` (generic `@render_widget`, linked from "Learn more")
