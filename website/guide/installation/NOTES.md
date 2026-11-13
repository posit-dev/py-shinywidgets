# NOTES: Installation

## Update 2026-11-12: page split

The troubleshooting content moved to `../troubleshooting/` and the Shinylive content to `../deployment/`; this
page now only covers install commands. The mols2grid diagnosis below was wrong: mols2grid loads RDKit from
unpkg itself (its own HTML template), not through shinywidgets' CDN fallback, which defaults to jsdelivr.

## Update 2026-11-11: item 2 removed (fixed by #414)

#414 ("fix: resolve JS dependencies for app-module widget subclasses via MRO walk") fixes the root cause this
item documented: `jupyter_extension_destination()` now walks `type(w).__mro__` (`installed_widget_pkg()`) to
the first ancestor class defined in an installed package, instead of trusting the subclass's own
`__module__`. Verified directly in a browser (not just at the unit level): `anywidget`, `ipyreact`, and
`ipyleaflet` subclasses defined in an app module, built with ipyreact's normal `_esm`/`setValue` idiom (`import
* as React from "react"`, not a bare `React` global -- see the judgment-call note below), all render and the
ipyreact one responds correctly to a real click (`clicked 0 times` -> `clicked 1 times`, no console errors). No
new `RuntimeError` fires either, since the MRO walk finds `ipyreact` before falling through to the "couldn't
resolve any ancestor" error path #414 also adds.

Removed item 2 ("A widget subclass defined in your own app file") from "Widget not showing?" and renumbered
item 3 to item 2. Moved `examples/subclass_in_app.py` and `img/subclass_error.webp` out of this directory
(plain `mv`, not deleted) since they're now unused. Fixed the front-matter `summary` (dropped the subclass
clause) and `widgets` list (dropped `ipyleaflet`, which was only used by the removed example). See
`../../FINDINGS.md`, `../../README.md`, and `investigations/narrow-canvas-and-subclass/INVESTIGATION.md` Item B
for the matching updates elsewhere.

**Judgment call, new this pass:** the original `examples/subclass_in_app.py` (inherited verbatim from the
investigation's own repro) used `React.createElement(...)` with no `import * as React from "react"` -- a bare
global reference. Confirmed independently that this fails with "React is not defined" even for a plain,
*non-subclassed* `ipyreact.ValueWidget` using the same `_esm` string (i.e., regardless of #414): ipyreact does
not expose `React` as a global, only as an importable specifier. The investigation's demo happened to still
"work" as a demonstration of the pre-#414 bug only because, before the fix, the subclassed widget's dependency
resolution failed anyway (so the missing import was never the operative cause); once the dependency bug is
fixed, that same `_esm` string would still show the error, for an unrelated, pre-existing reason. This is why
the fix was verified with a *corrected* `_esm` (`render-widget/guide.md`'s existing idiom), not with the
original example's JS, before concluding #414 works. Not itself a shinywidgets bug -- it's a bug in the
docs-only demo code -- and moot now that item 2 is removed rather than repaired.

## Versions

- shinywidgets: worktree `site-content-gaps` @ `943183cd` (branch `docs/site-content-gaps`), shiny 1.9.0,
  mols2grid 2.2.0, ipyreact, anywidget, ipyleaflet (latest in the venv). Date: 2026-11-11.
- Playwright: Chromium headless, viewport 1280x800, `device_scale_factor=2`.
- Shinylive: 0.8.13 (`uv run --no-sync --with shinylive==0.8.13 shinylive export`).

## Verification table

| Item | Method | Result |
|---|---|---|
| 1. JS couldn't load | Found mols2grid by probing `shinywidgets._dependencies.jupyter_extension_path()` against every widget's declared `_model_module` across the roster (script in scratch, not committed): mols2grid's module name (`"mols2grid"`) has no matching nbextension directory anywhere on `jupyter_path()`, so `require_dependencies()` always returns `[]` for it and it always depends on the unpkg CDN fallback. Ran its own [quickstart](../../widgets/mols2grid/index.md) twice: once normally, once with `page.route("**unpkg.com/**", lambda r: r.abort())`. | Normal: full grid of molecule structures. Blocked: the grid's pagination/search chrome renders (plain server-sent HTML), every cell empty, one console error `Failed to load resource: net::ERR_FAILED`. Screenshots `img/js_normal.webp` / `img/js_blocked.webp`, both looked at. |
| ~~2. Subclass in app module~~ (removed 2026-11-11, fixed by #414) | Adapted `investigations/narrow-canvas-and-subclass/repros/itemB_subclass/app.py` into `examples/subclass_in_app.py` (fixed: that repro used a bare module docstring, which Shiny Express renders as visible page text -- converted to `#` comments). Ran via `smoke.py` and directly with Playwright. | Reproduced deterministically (3/3 runs) prior to #414: exit 1, server-side `ModuleNotFoundError: No module named 'app'` raised from `shinywidgets/_dependencies.py:951` (`jupyter_extension_destination`), surfaced in the browser as a visible "Error: No module named 'app'" card for the ipyreact subclass only; the anywidget and ipyleaflet subclass cards rendered normally alongside it. On current main (post-#414), re-verified with a corrected example (real `import * as React from "react"` idiom) that all three subclasses render and the ipyreact one responds to a real click with no errors; item removed from the article (see "Update 2026-11-11" above), example/screenshot moved to scratch. |
| 2. Extra not installed | Built a throwaway app (`pd.DataFrame` returned from `@render_itables`, no `import itables`) and ran it in a fresh env built from `uv run --no-project --with-editable <worktree> --with shiny --with pandas` (itables confirmed absent via an in-app debug check). | `render_itables`'s `_as_widget()` catches the `ModuleNotFoundError` and re-raises `ImportError("Install the itables package to use data frames with shinywidgets (pip install 'shinywidgets[itables]').")`, shown in the output card. Screenshot `img/no_extra_error.webp`, looked at. |
| Shinylive | `shinylive export` on `../first-app/examples/01_render.py` (copied to a scratch `app.py` + a `requirements.txt` listing `shinywidgets`, `plotly`, `pandas`), served with `python -m http.server`, loaded in headless Chromium, waited up to 100s. | Works: the scatter plot renders correctly. Screenshot `img/shinylive_works.webp`, looked at. |

## Judgment calls

- **Item 1 reproduction target.** The task names no specific widget; I picked mols2grid after checking every
  widget's `_model_module`/`_view_module` against installed nbextension directories (`jupyter_path()`), since
  most of the roster *does* ship a local extension and would have made a weak demo (unpkg would never even
  be hit). mols2grid is the cleanest: it has no local extension at all under any circumstance, so the
  CDN-fallback path is exercised every time, not just when something's missing by accident. `pydeck` also
  relies on the CDN by this same check but is deprecated, so I didn't use it.
- **Item 2's exact symptom differs from the investigation's conclusion.** `investigations/narrow-canvas-and-subclass/INVESTIGATION.md`
  (Item B) concludes this specific crash text (`ModuleNotFoundError: No module named 'app'`) does **not**
  reproduce under a real `shiny run`, because by render time `sys.modules["app"]` is supposedly already the
  live module object; it reports a different, silent symptom instead (`ReferenceError: React is not defined`
  in the browser console, no server-side exception). Under this task's exact repro conditions -- `smoke.py`'s
  invocation (`python -m shiny run FILE.py --port 0`, no `--reload`) and a fresh Playwright page load -- the
  crash reproduced instead, consistently, 3 out of 3 runs, with a visible "Error: No module named 'app'" card
  server-side. I did not re-root-cause why the two investigations differ (most likely something timing- or
  reload-flag-dependent in when `sys.modules["app"]` gets populated relative to the first render pass); flagging
  as a discrepancy worth a second look rather than silently picking one story. Recorded below under Findings.
- **Item 3's widget.** Used itables (a plain-DataFrame return path with no `import itables` needed) rather
  than plotly, specifically because it's one of the renderers with a shinywidgets-authored
  `ImportError("... pip install 'shinywidgets[x]'")` message (`_render_widget.py:1372-1382`). plotly has no
  such guard: its import failure is an ordinary `ModuleNotFoundError` from the user's own `import plotly...`
  line, before shinywidgets ever runs, which is a less interesting repro of "the install-error message."
- **Shinylive export used a `requirements.txt`, not auto-detection.** `shinylive export` only auto-detects
  packages in Pyodide's built-in index; shinywidgets and plotly aren't in it (they're ordinary PyPI wheels,
  which micropip can fetch at runtime, but only if named explicitly). Without `requirements.txt`, nothing was
  tested here since the app would fail to build its package list with an unhelpful exception; not pursued
  further since this is a known shinylive requirement, not a shinywidgets gap, and it's already how the task
  block frames the attempt ("try ... export").
- **Pyodide resolved shinywidgets 0.8.2 (the last PyPI release), not this worktree's dev build.** `shinylive
  export`'s package resolution goes through PyPI/micropip, which has no way to see an unreleased, uncommitted
  worktree. For `01_render.py` specifically this doesn't matter (it uses no accessor, so the pre-redesign vs.
  post-redesign API surface is identical for this file), but it does mean this result doesn't confirm
  Shinylive support for anything added since 0.8.2 (the accessors, `selected()`/PR #456, etc.) -- only that
  shinywidgets' core comm-over-Shiny mechanism works unchanged under Pyodide. Didn't test further (out of
  this task's scope, which names only `01_render.py`).
- **`--no-project` picked up the ambient venv when nested inside an outer `uv run`.** First attempt at item 3
  (launching the ephemeral-env server via a Python script itself run with `uv run --no-sync python script.py`,
  which itself spawned `uv run --no-project --with-editable ...` as a subprocess) showed itables as
  "importable" even though it should have been excluded -- almost certainly because the outer `uv run`'s
  `VIRTUAL_ENV` leaked into the child's environment. Running the `--no-project` command directly (no
  wrapping `uv run`) gave the correct, itables-absent result every time. Not itself a shinywidgets finding;
  noting it because it cost real time and might trip up a later agent doing something similar.

## Findings for FINDINGS.md

- [investigation, follow-up -- **fixed by #414, see "Update 2026-11-11" above**]
  `investigations/narrow-canvas-and-subclass/INVESTIGATION.md` Item B's "verdict"
  (the literal `ModuleNotFoundError: No module named 'app'` crash does not reproduce under a real `shiny run`)
  did not hold here: it reproduced deterministically (3/3) under `smoke.py`'s plain `python -m shiny run
  FILE.py --port 0` invocation, as a visible per-card error, not the investigation's silent
  `ReferenceError: React is not defined`. Root cause (the `widget_pkg()`/`jupyter_extension_destination()`
  MRO-blind fallback importing the app's own module) is the same either way; only the *manifestation* differs,
  apparently based on something timing-sensitive around when Shiny's loader populates `sys.modules["app"]`
  relative to the first render. Not re-root-caused further here. Repro (historical; moved to scratch):
  `examples/subclass_in_app.py`.

## Editor's notes for the website

- ~~`img/subclass_error.webp` is the single most useful screenshot on this page...~~ No longer applicable:
  #414 fixed the bug this screenshot demonstrated, so the item (and the screenshot) were removed 2026-11-11.
- Kept the "Widget not showing?" list to the two remaining items; didn't add a third for "wrong Python
  version" or similar, since none of those are shinywidgets-specific and the section is already near its line
  budget.
