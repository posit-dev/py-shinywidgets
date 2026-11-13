# NOTES: "Updating in place" article

## Versions

- shinywidgets: `main` @ `4f98bec0` (worktree `docs/site-content-gaps`, based on `widget-guides`), 2026-11-11.
- shiny: 1.9.0, ipyleaflet: 0.20.0 (same environment as the reacting-to-widgets and performance articles this
  page draws from).
- Playwright: Chromium, headless, 1280x800 viewport, `device_scale_factor=2`.

## Provenance

This article is built mostly from content moved out of `articles/reacting-to-widgets/` ("Writing back" and
"Lifetimes"), per the site design doc. The moves:

| From | To |
|---|---|
| `reacting-to-widgets/examples/06_writing_back.py` | `examples/01_writing_back.py` |
| `reacting-to-widgets/examples/07_lifetimes.py` | `examples/03_lifetimes.py` |
| `reacting-to-widgets/examples/globals.py` | `examples/globals.py` |
| `reacting-to-widgets/img/06_writing_back_{before,after}.webp` | `img/01_writing_back_{before,after}.webp` |
| `reacting-to-widgets/img/07_lifetimes_{zoomed,after_rerender}.webp` | `img/03_lifetimes_{zoomed,after_rerender}.webp` |
| `reacting-to-widgets/img/07_shared_tab{A,B}_{before,after}.webp` | `img/03_shared_tab{A,B}_{before,after}.webp` |

Confirmed before moving: no other `reacting-to-widgets/examples/*.py` imports `globals.py` except
`07_lifetimes.py` (`grep -rln "from globals import\|import globals" articles/reacting-to-widgets/examples/`
returned only that one file).

The code in both moved examples is otherwise byte-for-byte unchanged, except `examples/globals.py`'s comment,
which named the sibling file `07_lifetimes.py` -- updated to `03_lifetimes.py` to match the rename (a comment
fix, not a behavior change). Both example files' own in-file comments that said "see the article text" / "see
'Lifetimes' in the article" still correctly describe this article (the whole section moved with them); the
`globals.py` comment's "see 'Lifetimes' in the article" was changed to "see 'Lifetimes' above" since it's now a
same-page reference, not a cross-article one.

The "Why update in place" lead section and "When in-place doesn't save bytes" link out to
`articles/performance/article.md` rather than repeating its measured numbers, per the plan's instruction not to
duplicate measured claims. The "What each widget calls in-place" table was not copied from any single existing
source; it's new, built by reading every one of the 44 guides' own "Updating the widget from Python" section
(`grep -rln "## Updating the widget from Python" */guide.md`) and summarizing each into one line. `pydeck` has
no such section (deprecated, no live widget to mutate -- `render_maplibre` is its replacement) and is excluded
from the table.

No new example file (`02_inplace_vs_rerender.py`) was written. The plan allowed linking to
`articles/performance/examples/01_*` instead if it already shows the comparison; it does (`01_inplace_plotly.py`,
`02_inplace_lonboard.py`, `03_inplace_ipyleaflet.py`, with real measured bytes and before/after screenshots), so
the lead section links there rather than duplicating a fourth copy of the same demonstration.

## Verification table

| File | Ran | Screenshot | Gesture driven | Confirmed |
|---|---|---|---|---|
| `examples/01_writing_back.py` | yes (re-smoked after the move) | before/after | 3 map clicks | 3 markers added in place; zoom level unchanged after all 3 writes; counter correct (`reactive.isolate()` prevents the self-trigger loop) |
| `examples/03_lifetimes.py` | yes (re-smoked after the move) | zoomed / after-rerender | zoom-in x3 on two panels, then click "Re-render" | default-lifetime map visibly resets to its construction-time view; `session_lifetime()` map visibly keeps the zoomed view |
| `examples/03_lifetimes.py` + `examples/globals.py` (shared_lifetime, 2 browser contexts, one running server) | yes -- re-verified fresh after the move with a dedicated two-context Playwright script (not reused screenshots for this check) | tabA/tabB before+after | zoom-in x3 (3 leaflet zoom-button clicks) in tab A only | tab B's shared map visibly mirrors tab A's zoom (same Paris view, Châtelet-Les Halles close-up) with zero interaction of its own; tabs A and B both start on the wide Paris view and end on the identical zoomed-in view |

Every screenshot referenced in `article.md` (including the ones moved from `reacting-to-widgets`) was read back
with the Read tool in this pass before being cited, not assumed correct from the prior article's verification.

The two-tab check used a standalone script (`two_tab_check.py`, run from the agent's scratch dir, port 8120 --
this task's assigned range) rather than `smoke.py`, since `smoke.py` only drives one browser context. It started
one server, opened two separate Playwright browser *contexts* (simulating two independent sessions) against it,
drove only context A, and screenshotted both before and after.

Every example's in-file comments were read in full and still describe this article accurately after the move
(no behavioral claim needed updating, only the one file-name reference in `globals.py` noted above).

## Bugs found / surprises

Nothing new this pass. Everything below was already reported by the original `reacting-to-widgets` article pass
and carries forward unchanged with the moved examples:

- **[authoring hazard, not a shinywidgets bug]** An effect that both reads and sets its own reactive value
  (`clicks.set(clicks() + 1)`) without `reactive.isolate()` loops forever (pinned CPU, no error, no visible
  symptom). Matches the itables guide's independently-discovered finding in `docs/widget-guides/FINDINGS.md`.
  Not re-triggered live (would pin a CPU core on a shared machine for no useful screenshot).
- **[sharp edge in Shiny Express, not a shinywidgets bug]** `shared_lifetime()` constructed directly in an
  Express script's top-level body is silently rebuilt per session (Express re-runs the whole file body per
  session), so two tabs never actually share state even though nothing errors. The fix (a sibling `globals.py`,
  imported before any session connects) is demonstrated and re-verified in this pass. See the original
  `reacting-to-widgets/NOTES.md`'s "Bugs found" section for the full original repro with the broken version.

## Judgment calls

- Added a "before" screenshot (`01_writing_back_before.webp`) to "Writing back" that the original
  `reacting-to-widgets` article didn't reference, even though the file already existed on disk (unused,
  committed alongside `01_writing_back_after.webp` -- now used). A before/after pair is more in keeping with
  this plan's screenshot convention than the single "after" shot the original article used, and the file only
  needed to be looked at and cited, not generated.
- Kept the "Writing back" and "Lifetimes" sections' prose essentially verbatim from `reacting-to-widgets`
  (only renaming example/screenshot paths and one cross-reference from "in the article" to "above"), since the
  content itself doesn't need to change -- only its address. Rewriting working, previously-verified prose for
  its own sake would add risk (a reworded claim that quietly drifts from what was actually verified) without
  adding value.
- The "What each widget calls in-place" table lists all 44 guides with an "Updating the widget from Python"
  section rather than a curated subset. This is more exhaustive than the brief's usual "keep each snippet
  short" guidance suggests for prose, but a cross-reference table is exactly where exhaustive coverage is cheap
  (one line per widget, no new verification burden -- each guide already verified its own claim) and useful (a
  reader scanning for "what does my widget do" benefits from completeness here more than from a shorter,
  curated list). A second opinion on trimming this to a representative dozen would be reasonable if the
  website wants a shorter page; I'd lean toward keeping it complete since the Reference section's per-renderer
  pages (per the design doc) won't have anything like it.
- `widgets:` front matter lists 8 widgets (the ones with a dedicated example or screenshot in this article:
  plotly, ipyleaflet, lonboard, k3d, bokeh, itables, mosaic, matplotlib), not all 44 referenced from the table,
  matching how `performance/article.md` and `reacting-to-widgets/article.md` scope their own `widgets:` lists to
  what the article itself demonstrates rather than everything it links to.

## Findings for FINDINGS.md

Nothing new to add. The two carried-forward items above (the `reactive.isolate()` authoring hazard and the
`shared_lifetime()` + Express sharp edge) were already reported by the original `reacting-to-widgets` pass.

## Editor's notes for the website

- The two-tab `shared_lifetime()` demonstration (`img/03_shared_tabA_after.webp` +
  `img/03_shared_tabB_before.webp` / `img/03_shared_tabB_after.webp`) is the strongest material on this page --
  it's the one thing here that's surprising rather than merely useful, and it's a genuine "sharp edge" worth a
  reader's attention before they reach for `shared_lifetime()` in Express.
- If the page needs to be shorter, "What each widget calls in-place" is the easiest section to collapse (e.g.
  to only the `widgets:` front-matter subset) without losing the article's argument; the full table would move
  cleanly into a Reference appendix instead.
