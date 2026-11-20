---
name: adding-shinywidgets-integrations
description: Use when adding a new widget integration (@render_* decorator) to the py-shinywidgets repo, spiking the feasibility of supporting an ipywidget/anywidget/visualization library, or writing or updating a widget guide or website/widgets/ article for an integration.
---

# Adding shinywidgets integrations

## Overview

A new integration moves through three phases, each producing a durable artifact the next phase builds on:

1. **Spike** — a feasibility report: does the widget render, size, and round-trip interaction under shinywidgets?
2. **Integration + widget guide** — the renderer itself, plus browser-verified teaching material.
3. **Website article** — the guide compressed into a page in `website/widgets/<slug>/`.

Don't skip the spike to "save time": past spikes surfaced core shinywidgets bugs (dropped sends before the comm opens, missing `isolate()` around coercion, broken dependency lookup for app-module widget subclasses) that improved every integration, not just the one being spiked. Keep a findings log as you go and feed real product bugs back as PRs.

**Follow the repo's `AGENTS.md`** (dev setup, `make check`, TDD) throughout.

## The blueprint: what a good integration ships

Judge every integration against these four pillars. All four must be verified in a real browser, not just reasoned about.

### 1. Renderer and coercion

- Subclass `render_widget_base[ValueT, WidgetT]` in `shinywidgets/_render_widget.py`; put library-specific helpers in `shinywidgets/_<lib>.py`. Add the class to `__all__` in `_render_widget.py` and to the import + `__all__` in `shinywidgets/__init__.py`.
- If users naturally produce a non-widget object (e.g. `plotly.Figure`), add coercion in `_as_widget.py` (`as_widget()`).
- Add a matching extra to `[project.optional-dependencies]` in `pyproject.toml` (and to the test/dev dependency groups that mirror the extras), and point the docstring + install-error messages at `pip install 'shinywidgets[<extra>]'`. Check whether the README documents per-integration extras (it had a table historically) and update it if so.
- JS dependencies load through `require_dependencies()` (nbextension lookup, CDN fallback). A widget subclassed in the user's app module must still resolve its JS — check this if the library encourages subclassing.

### 2. Responsive sizing

- `set_layout_defaults()` (`_render_widget_base.py`) gives each renderer fill-friendly defaults without overriding user-specified sizes; add per-package handling there (precedent: plotly margins, altair `"container"` sizing).
- Verify the sizing matrix in a browser: fill card, `full_screen` card, explicit `height=`, `output_widget(height=)`, unfillable page, sidebar/tabs. A widget that renders at 0 height in a fill layout is the most common integration defect.

### 3. Reactive accessors

Three tiers, in the order you should teach and prefer them:

1. **Named accessors** on the renderer (`fig.selected()`, `tbl.selected_rows()`), declared via `_accessor_specs` (`AccessorSpec` in `shinywidgets/_accessors.py`).
2. **`x.read("trait")`** for synced traits without a named accessor.
3. **`reactive_read(x.widget, "trait")`** for child/nested widgets.

Per accessor, nail down and document: what it returns (coordinate/index space!), when it fires, what `None` means before interaction, behavior across re-render, and its default rate policy. Accessor semantics:

- `kind="state"` retains the last value across re-renders (the user-facing norm); `kind="event"` resets to `None` (internal plumbing, e.g. bokeh's `source_data`).
- `priority="input"` dedups identical values; `"event"` republishes (repeated identical clicks each fire).
- Names can't be `value` or start with `_`.
- An accessor computed from the widget itself must read `self.widget`, not `self._widget`, so readers follow a re-render.
- Verify **every accessor with a real Playwright gesture** (click, drag, lasso, scroll-zoom) and confirm the Python side saw it (e.g. render the value in a `@render.code` output, screenshot it). A plain `@reactive.effect` reading `widget.trait` does NOT refire on trait changes — use `reactive_read()`/`.observe()` when testing sync.

### 4. Mutation support

- Trait changes on `renderer.widget` sync to the browser. The canonical pattern is a `@reactive.effect` that sets traits in place, with `reactive.isolate()` where needed to avoid re-render loops.
- Document when in-place beats re-render: it preserves view state (zoom, camera, selection) and avoids re-sending the widget's full state (for anywidgets the `_esm` module alone can be ~98% of the payload).
- Know the trap: messages sent before the comm opens are dropped (bit k3d and mapwidget). If the library queues calls at construction time, test first render carefully.
- Don't add a second lifecycle/sweep mechanism — browser-created models are handled by the existing `claim_browser_created()` sweep (see `_shinywidgets.py`).

## Phase 1: Spike (feasibility)

Use `docs/plans/widget-reports-archive/prompt-template.md` as the brief. The essentials:

1. **Review before testing**: read the library's widget code and any shinywidgets diff; run `make check`.
2. **Survey the API surface by introspection** (accepted input types, `sync=True` traits, experimental vs stable) — let that drive the test matrix, not guesswork.
3. **Build throwaway Shiny apps and drive them in a real browser** (Playwright, screenshots — look at each one): every accepted input type, both directions of interactivity, the sizing matrix, re-render lifecycle, two simultaneous browser tabs (multi-session isolation).
4. **Attribute bugs correctly**: shinywidgets bug / upstream bug / harness artifact. For suspected upstream bugs, build a control without shinywidgets (static export or Jupyter-style usage). First suspect your own test app.
5. **Deliver a report**: coverage table, findings ranked by severity with attribution, a scorecard (first-render reliability, browser→Python reactivity, Python→browser updates, sizing/layout, multi-session, upstream stability) with a verdict, "the magic" (3–5 demo-able capabilities), API patterns & recipes, and a gallery-worthy example app.

The verdict gates phase 2. A library with no synced traits and no widget (e.g. pydeck ≥ 0.9) may be better served by an existing renderer or a static path — say so.

## Phase 2: Integration + widget guide

Implement the renderer TDD-style (unit tests in `tests/unit/`, a Playwright app fixture in `tests/apps/` driving the key gestures). Then write the guide as verified source material. Structure that has worked (`docs/widget-guides/<slug>/` pattern):

- **Quick start** (minimal app + screenshot) → **feature tour** (4–8 highlights, short snippets) → **Reacting to user interaction** (accessor reference table: accessor | returns | before any interaction | across re-render | default rate policy; one verified snippet per accessor) → **Updating from Python** (in-place vs re-render, what's preserved) → **Coordinating multiple views** (2–4 complete linked-view patterns, e.g. lasso → filtered table) → **Layout and sizing** → **Gotchas and limitations** (verified only, no hypotheticals).
- Every snippet is a runnable file in `examples/`, run in a browser and screenshotted; look at every screenshot before referencing it. Keep a `NOTES.md` verification log (versions, what ran, bugs found, judgment calls).
- Shiny Express, real datasets, 10–40 line snippets, no marketing fluff.

## Phase 3: Website article

Turn the guide into `website/widgets/<slug>/`: `index.md` (front matter: `title`, `decorator`, `extra`, `category`, `upstream`, `hero`, `tagline`, `accessors`), `examples/`, `img/`, `gallery/`.

- Add the page to the Widgets sidebar group in `website/_quarto.yml` and the `render_<x>` function to the matching quartodoc `contents:` list; `make docs` re-syncs the landing-page counts automatically.
- `website/_tools/check_docs.py` must report nothing (snippets match example files byte-for-byte; links resolve). Bump the hardcoded sidebar-link count in `website/_tools/check_site.py` (checked by `make docs-check`).
- Code blocks name their file: ` ```{.python file="examples/x.py"} `. Reshoot screenshots rather than reusing stale ones.

## Common mistakes

- Claiming something works without seeing it rendered — screenshot everything, and look.
- Testing browser→Python sync with a plain `@reactive.effect` on a trait (never refires) instead of `reactive_read()`/`.observe()`.
- Documenting accessor semantics from docstrings or design docs instead of verifying them live — both have been stale.
- Padding thin libraries to hit section quotas; fewer sections is fine.
- Fixing upstream bugs inline instead of reporting them with a control repro; conflating harness artifacts with product bugs.
- Adding the integration but forgetting the extra or `__all__` export, or shipping without rebuilding served artifacts (`cd js && yarn build`) when JS changed.
