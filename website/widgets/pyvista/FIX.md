# FIX: `@render_pyvista` multi-session breakage with trame-pyvista >= 0.3

## Root cause

A fresh `uv sync` on Python 3.11-3.14 resolves `trame-pyvista 0.3.4` (0.2.3 is only pinned for
`python_full_version < '3.11' or >= '3.15'`). 0.3.x rewrote `EmbeddableWidget` from a plain
`ipywidgets.HTML` subclass into an `anywidget.AnyWidget` whose `_viewer_page` trait references a
process-wide singleton:

- `trame_pyvista/jupyter.py:382-388` (`_get_viewer_page()`) caches one `_ViewerPage` instance in
  the module-level `_shared_viewer_page` global, recreating it only once the cached one is closed.
  Every `EmbeddableWidget` built anywhere in the process (`trame_pyvista/jupyter.py:409-422`,
  `EmbeddableWidget.__init__`) references that same instance -- it holds the ~400 KB-1.2 MB vtk.js
  runtime so it isn't resent on every render.
- shinywidgets' session-ownership model treats every widget as owned by whichever Shiny session
  first constructs it (`shinywidgets/_shinywidgets.py:130-205`, `init_shiny_widget()`). Nothing told
  it that a `_ViewerPage` is different, so it was tracked exactly like the per-render
  `EmbeddableWidget` that references it.

Two concrete failures followed, both reproduced and now covered by regression tests (see below):

- **Concurrent**: a second session's render finds `_ViewerPage` foreign
  (`shinywidgets/_shinywidgets.py:1463-1481`, `foreign_or_closed_widget()`) and raises
  `RuntimeError: _ViewerPage belongs to another Shiny session, so it can't be displayed here.`
- **Sequential**: when the owning session ends, `_cleanup_session_state()`
  (`shinywidgets/_shinywidgets.py:551-568`) closes every widget that session constructed unless it's
  process-global -- so `_ViewerPage` was closed along with it. Every session that connects
  afterwards gets `RuntimeError: _ViewerPage was closed (its render was invalidated, or it was
  closed explicitly), so it can't be displayed again.` This is the more important case: no real
  concurrency needed, just two sequential visitors, which breaks the app for everyone after the
  first one leaves until the process restarts.

## Design chosen

shinywidgets already has the exact right abstraction for "a widget that's process-global even
though it's constructed lazily inside a session" -- `is_process_global_construction()`
(`shinywidgets/_shinywidgets.py`, previously used for ipyreact's registry widgets and for ipyvue/
ipyvuetify/nglview widgets built mid-import). I added a sibling predicate,
`is_pyvista_viewer_page(w)`, and OR'd it into `is_process_global_construction()`:

```python
def is_pyvista_viewer_page(w: Widget) -> bool:
    viewer_page_cls = getattr(
        sys.modules.get("trame_pyvista.jupyter"), "_ViewerPage", None
    )
    return viewer_page_cls is not None and isinstance(w, viewer_page_cls)
```

It checks `sys.modules` + `isinstance` (matching the existing `in_template_registry()` style)
rather than importing `trame_pyvista` or comparing on `widget_pkg()`/class name strings, so apps
that never use pyvista pay no import cost and there's no risk of a name collision.

Once `is_process_global_construction()` returns `True` for a freshly constructed `_ViewerPage`,
the rest of the existing process-global machinery (`SHARED_WIDGETS`, `SharedShinyComm`,
`open_shared_in()`, the skip in `_cleanup_session_state()`) does the rest with zero further
changes: the first session's render-time reference walk upgrades the widget's comm to a
`SharedShinyComm`; `init_session()` eagerly opens every entry already in `SHARED_WIDGETS` in any
newly-connecting session; and process-global widgets are explicitly excluded from the close-on-
session-end sweep. This is unconditional (every `_ViewerPage` instance is meant to be the single
shared one, by trame-pyvista's own design), unlike the `importing_*()` "is this package currently
mid-import" sentinels used for ipyvue/ipyvuetify/nglview, so no extra sentinel plumbing was needed.

Total diff: ~20 lines in `shinywidgets/_shinywidgets.py`, no changes needed to `_as_widget.py`,
`_render_widget_base.py`, or any JS.

### Alternatives rejected

- **The docs agent's Shiny-Core-only workaround** (constructing a throwaway `Plotter` inside
  `shared_lifetime()` at true module scope): works for Core, confirmed broken for Express (the
  module's top-level code always runs under a non-`None` `ExpressStubSession`, so the sessionless
  branch in `init_shiny_widget()` is never reached). Fixing this in user code can't cover both
  Shiny flavors reliably, so it isn't a substitute for a library-level fix.
- **Moving the warm-up into a `@reactive.effect`**: fixes the sequential/reconnect case (a real,
  non-stub session runs it) but not true concurrency, since success then depends on which session's
  code happens to touch trame_pyvista's internal cache first -- a race the app can't control.
  Rejected for the same reason the docs agent rejected it.
- **Adding `trame_pyvista` to `EAGERLY_SHARED_PACKAGES`/`IMPORT_TIME_WIDGET_PACKAGES`**: that path
  requires `is_sessionless(w)` (constructed with no active session, e.g. at import time).
  `_ViewerPage` is always constructed lazily *inside* a session's render, so it would never satisfy
  that predicate; `is_process_global_construction()` is the mechanism built for exactly this
  "constructed inside a session but still process-global" shape (already used by ipyreact's
  registry widgets), so no separate eager-fan-out loop was needed -- the existing `SHARED_WIDGETS`
  loop in `init_session()` already opens *any* registered process-global widget in every new
  session, regardless of how it got registered.

## Tests added

`tests/unit/test_pyvista.py` (new, bottom section), all exercising the real
`trame_pyvista.jupyter.EmbeddableWidget`/`_ViewerPage`/`_get_viewer_page()` and the real
shinywidgets render/ownership pipeline (`render_widget_base`, `foreign_or_closed_widget`,
`ownership_error`) -- no mocks of shinywidgets' own logic:

- `test_viewer_page_is_process_global`: after one render, the `EmbeddableWidget`'s `_viewer_page`
  is in `SHARED_WIDGETS` and `is_process_global()` is `True`.
- `test_viewer_page_reaches_second_concurrent_session`: session A renders, then session B renders
  while A is still open. Before the fix this reproduced the exact production error,
  `RuntimeError: _ViewerPage belongs to another Shiny session, so it can't be displayed here.`
- `test_viewer_page_survives_owning_sessions_close`: session A renders and closes, then session B
  renders. Before the fix this reproduced `RuntimeError: _ViewerPage was closed (its render was
  invalidated, or it was closed explicitly), so it can't be displayed again.`

A new `fresh_viewer_page` fixture resets trame-pyvista's process-level `_shared_viewer_page` cache
before/after each of these tests, since that cache is a genuine process-global (by trame-pyvista's
own design) and would otherwise leak state between tests in either direction.

I used real `pyvista.Plotter`/`trame_pyvista` objects and the real `render_widget_base` render path
(not a bare `as_widget_pyvista()` call) because the ownership rejection
(`foreign_or_closed_widget()`) only runs inside a renderer's `_render()`, not inside widget
coercion itself -- a Playwright test was not needed since this is pure server-side session-
ownership logic with no browser-observable behavior to verify beyond what the unit tests already
pin down.

## Verification

All commands run from a worktree at `fix/pyvista-shared-viewer-page`, Python 3.12, after
`uv sync --all-groups --python 3.12` (confirmed `trame-pyvista==0.3.4` via `uv pip list`).

```
$ uv run ruff check shinywidgets tests --config pyproject.toml
All checks passed!

$ uv run ruff format --check shinywidgets tests --config pyproject.toml
360 files already formatted

$ uv run pyright shinywidgets tests/__init__.py tests/unit/test_version_metadata.py
0 errors, 0 warnings, 0 informations

$ uv run pytest -c pytest.ini --confcutdir .
3 failed, 942 passed, 3 skipped, 1 xfailed  (85.23s)
# the 3 failures are pre-existing and unrelated -- see "Residual/out-of-scope" below;
# confirmed present on main before this fix (git stash + re-run)

$ uv run pytest tests/unit/test_pyvista.py -k viewer_page -v
3 passed

$ uv run playwright install chromium
$ uv run pytest -c tests/playwright/playwright-pytest.ini --confcutdir tests/playwright \
    tests/playwright/render_pyvista tests/playwright/shared_pythreejs tests/playwright/render_nglview \
    -k "not test_pyvista_rerender_lifecycle"
20 passed
# test_pyvista_rerender_lifecycle deselected: pre-existing, unrelated failure (see below),
# confirmed failing on main before this fix with the same assertion
```

## Branch and commit

- Worktree: `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/pyvista-fix`
- Branch: `fix/pyvista-shared-viewer-page` (based on `origin/main` @ `00f90249`)
- Commit: `54c69cec` -- "fix(pyvista): share trame-pyvista's process-wide viewer page across sessions" (not pushed, no PR opened, per instructions)

## Residual limitations / out of scope

- **Pre-existing, unrelated breakage from the same trame-pyvista 0.3.4 bump** (present on `main`
  before this fix, confirmed by `git stash`-ing this patch and re-running): three unit tests
  (`test_as_widget_pyvista_coerces_plotter`, `test_as_widget_coerces_plotter_via_package_map`,
  `test_as_widget_coerces_plotter_subclass_defined_in_app`) assert `isinstance(w, HTML)`, which no
  longer holds now that `EmbeddableWidget` is an `AnyWidget`, not an `ipywidgets.HTML` subclass. One
  Playwright test (`test_pyvista_rerender_lifecycle`) asserts on a `HTMLModel` view count in the
  browser's widget manager, which is also stale for the same reason (`assert 0 == 2`). These are a
  second, distinct bug surface from the same dependency bump -- fixing them is a different task
  (updating test assertions/helpers for the new widget type), not a session-ownership issue, and
  was out of scope for "fix the multi-session breakage." Flagging since they'll show up as CI
  failures on a fresh `uv sync` regardless of this fix.
- **trame-pyvista 0.2.3** (still resolved on Python 3.10 and 3.15+) has no `_ViewerPage` class at
  all, so `is_pyvista_viewer_page()` always returns `False` there (checked via `getattr(..., None)`)
  and this change is a no-op for that version -- consistent with 0.2.3 never having had the bug.
- No change was needed to the docs guide's "Bugs found #1" workaround section beyond noting it's
  now fixed upstream in shinywidgets; I did not edit `guide.md`/`NOTES.md` (out of scope for this
  task, and `AGENTS.md`/CLAUDE.md say not to commit AI-generated planning/design docs -- this
  `FIX.md` is written to the main checkout only, not committed on the fix branch).
