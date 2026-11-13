# NOTES: ipyaladin guide

## Versions and environment

- Date: 2026-10-30 (session resumed 2026-11-02 after a coordinator/scratchpad reset; worktree state and
  commit were unchanged across the reset)
- shinywidgets: `main` @ `00f90249` (fix(plotly): bind accessor events when Plotly draws after the bind
  request and display, #392)
- ipyaladin 0.8.1, astropy 8.0.2, shiny 1.9.0, jupyter-scatter (`jscatter`) (already in the worktree venv),
  mocpy (installed ephemerally via `uv run --with mocpy` for one example only -- not otherwise in the venv)
- Python 3.12.13, Playwright Chromium headless (no special launch flags needed -- ipyaladin's canvas
  rendering, markers, and overlays all work under default headless Chromium; the existing
  `tests/playwright/ipyaladin_accessors` suite also passes unmodified in this environment)
- Ports 9720-9739 (assigned range; used 9720 throughout, one app at a time, killed by PID between runs)
- Driver scripts (scratch, not in the guide dir):
  `/private/tmp/claude-502/.../scratchpad/agents/ipyaladin/driver.py` and `run_all.py`

### Operational note: `uv run --with <pkg> shiny run ...` does not pick up the overlay package

Discovered while building the footprints/MOC example. `uv run --no-sync --with mocpy shiny run app.py` failed
with `ModuleNotFoundError: No module named 'mocpy'` even though `uv run --no-sync --with mocpy python -c
"import mocpy"` succeeds. Root cause: the `shiny` console-script entry point doesn't inherit uv's ephemeral
`--with` overlay the same way a plain `python` invocation does. Fix used throughout this pass: launch via
`uv run --no-sync --with <pkg> python -m shiny run ...` instead of `... shiny run ...`. This is a uv/shiny
CLI interaction, not an ipyaladin or shinywidgets issue -- noting it here since another agent in this swarm
may hit the same thing with a different optional package.

### Note on a mid-task coordinator message (relayed, not applied)

A coordinator message during this pass warned that an unpinned `--with duckdb` had silently overlaid a
different duckdb version in another guide's verification. I checked: this guide's only `--with` usage is
`mocpy` for one example (`05_footprints_moc.py`), and mocpy is not otherwise present in the worktree venv
(confirmed via `ls .venv/lib/python3.12/site-packages`), so there is no version-shadowing risk to re-check
here. `pandas` and `jscatter`, which earlier draft run commands also mentioned adding via `--with`, are
already in the locked venv -- I removed the unnecessary `--with pandas` from my own verification commands
(the showcase gallery app's in-guide run command still mentions installing pandas, correctly, since
`shinywidgets[ipyaladin]` does not pull in pandas for an end user's fresh install).

## Verification table

Every example and gallery app was launched with `uv run --no-sync python -m shiny run ... --port 9720`,
driven with Playwright (sync API, headless Chromium), and screenshotted; every screenshot was viewed with the
Read tool before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | accessor confirmed |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | `quickstart.webp` | none (static) | n/a |
| `examples/02_navigate_from_input.py` | yes | `navigate_before.webp`, `navigate_after.webp` | dropdown select | `target()`/`fov()` readout updates (ra/dec changed, fov preserved at 2.754 from zoom-step snapping) |
| `examples/03_survey_colormap_switch.py` | yes | `survey_before.webp`, `survey_after.webp` | 2 dropdown selects | n/a (no accessor; survey/cmap label and tile URL both confirmed changed) |
| `examples/04_catalog_overlay.py` | yes | `catalog_overlay.webp` | none (static) | n/a |
| `examples/05_footprints_moc.py` | yes | `footprints_moc.webp` | none (static) | n/a |
| `examples/06_clicked_object.py` | yes | `clicked_object_before.webp`, `clicked_object_after.webp` | click | `clicked_object()` confirmed: detail card shows the clicked star's full catalog row (name/ra/dec/vmag) |
| `examples/07_selected_objects.py` | yes | `selected_objects_before.webp`, `selected_objects_after.webp` | button + rectangle drag | `selected()` confirmed: table lists the 4 stars inside the drawn box |
| `examples/08_whats_in_view.py` | yes | `whats_in_view_before.webp`, `whats_in_view_after.webp` | scroll-zoom | `target()`/`fov()` confirmed: table narrows from 2 Messier objects (90 deg fov) to 1 (after zooming in) |
| `examples/09_rate_limiting.py` | yes | `rate_limiting.webp` | 10-step drag | `target()`/`fov()` with `rate_policy="debounce"` confirmed: counter advanced by 4 for a drag that advanced an undebounced counter (same app without the kwarg) by 11 |
| `examples/10_update_in_place_vs_rerender.py` | yes | `update_in_place_before.webp`, `update_in_place_after.webp`, `rerender_after.webp` | scroll-zoom + 2 button clicks | n/a (no accessor; demonstrates in-place vs. re-render via `fov()` readout: 0.205 deg preserved after in-place update, reset to 0.918 after re-render) |
| `examples/11_jscatter_stars_on_sky.py` | yes | `jscatter_before.webp`, `jscatter_after.webp` | long-press lasso on the jscatter plot | n/a on the ipyaladin side (no ipyaladin accessor read here -- the pairing reads jscatter's `selected()`; confirmed the lassoed points' sky positions are marked on the viewer) |
| `examples/12_layout.py` | yes | `layout.webp` | none (static) | n/a |
| `gallery/template_sky_explorer.py` | yes | `gallery_template_before.webp`, `gallery_template_after.webp` | click | `clicked_object()` confirmed (Pleiades detail card) |
| `gallery/showcase_messier_explorer.py` | yes | `gallery_showcase_before.webp`, `gallery_showcase_click.webp`, `gallery_showcase_zoomed_out.webp`, `gallery_showcase_flyto.webp` | click, scroll-zoom (12 wheel ticks), table-row click | all four accessors confirmed: `clicked_object()` (M45 detail card), `target()`/`fov()` (in-view table: 1 object at fov=5 -> 27 at fov=180), row-select-to-fly (`.widget.target`/`.fov` set from a selected row, viewer reframes on M31 + its satellites M32/M110) |

**Accessor coverage: all four of `render_ipyaladin`'s accessors (`clicked_object()`, `selected()`,
`target()`, `fov()`) were exercised with a real Playwright-driven gesture, confirmed via a `@render.code` or
`@render.data_frame` output screenshotted before and after.** `selected()`'s box-selection gesture and
the "arm" button are both driven programmatically, not just asserted.

### Not independently re-verified this pass

- **VizieR/SIMBAD/astroquery queries against real CDS catalogs.** The brief suggested covering catalog
  overlays "via `astroquery` if `--with` works". I tried: `uv run --no-sync --with astroquery python -c
  "from astroquery.simbad import Simbad; Simbad.query_object('M31')"` failed with a `pyvo.dal.exceptions.
  DALServiceError` (`Connection failed`) against `simbad.cds.unistra.fr`, for the same reason noted below
  (CDS unreachable from this machine all session). The guide documents this as a "Learn more" pointer rather
  than a verified example, and all catalog examples use small, hardcoded, real astronomical data instead (per
  the brief's "or a bundled table" fallback).

## Bugs found

All of the below are **upstream ipyaladin behaviors or pre-existing limitations**, not shinywidgets
regressions; none were introduced by the current `render_ipyaladin`/accessor implementation, which worked
exactly as its docstring describes in every scenario tested.

1. **`target`'s in-place setter rejects a plain float tuple** (upstream, long-standing). Already documented
   in `render_ipyaladin`'s class docstring and in the old `docs/widget-reports/ipyaladin/report.md`
   (finding 3.3); re-verified this pass by triggering it directly (`AttributeError: 'float' object has no
   attribute 'deg'`). Documented in the guide's Gotchas with the correct workaround (string or `SkyCoord`).
2. **`_ready` is never set in ipyaladin 0.8.1** (upstream, long-standing; same as old report finding 3.4).
   Re-verified: grepped the installed package for any write to `_ready` and found none; the shinywidgets
   docstring already warns against gating on it. Documented in Gotchas.
3. **`set_listener()`'s callback registry is a class-level dict, shared across every `Aladin` instance**
   (upstream, long-standing; same as old report finding 3.1). Not independently re-reproduced with two
   browser sessions this pass (the old report's reproduction stands and the code is unchanged -- `grep
   listener_callback` in the installed 0.8.1 package confirms it's still a `ClassVar`), but re-stated in
   Gotchas since it's directly relevant to why this guide recommends `clicked_object()` over
   `set_listener()`.
4. **Constructor `fov` is approximate** (upstream, long-standing; same as old report finding 3.5).
   Re-verified with fresh numbers this pass (constructor `fov=3` → rendered 2.754 deg; `fov=1` → rendered
   0.918 deg), both from live screenshots, not reused from the old report.
5. **New finding this pass: constructing `Aladin(target="<name>")` performs a blocking Sesame HTTP call at
   render time, and raises if it fails.** Not explicitly called out as a *render-time crash risk* in the old
   report (which only noted "resolution is a blocking HTTP call" as a latency concern). During this guide's
   entire verification window, CDS's Sesame endpoints (`cds.unistra.fr/cgi-bin/nph-sesame`) were unreachable
   or returning `Bad Gateway` from this machine, which meant every example that originally passed a bare
   object name to the constructor (e.g. `Aladin(target="M42")`) **failed outright** with
   `WidgetNotReadyError`/`NameResolveError`, crashing the render function. I fixed every affected example
   (`02`, `03`, `10`, `12`) to use coordinate tuples/strings in constructors and in-place assignments instead
   (coordinate strings parse locally -- confirmed via `_coordinate_parser.py`'s `_is_coordinate_string`
   check, which short-circuits before any network call). This is a real, user-facing failure mode worth a
   docstring mention (`render_ipyaladin` already warns about name-resolution latency, but not about the
   render function raising outright on a name it can't resolve) -- flagging as a judgment call below rather
   than fixing the docstring myself.

## Judgment calls for the maintainer to revisit

- **Whether `render_ipyaladin`'s docstring should explicitly warn that a bare name in the constructor can
  raise and fail the render**, not just add latency. The current docstring's "Network access" note mentions
  latency; it doesn't mention that an unreachable or slow Sesame service turns into an uncaught exception in
  the render function itself (as opposed to an in-place `.widget.target = "name"` assignment in a
  `@reactive.effect`, which at least fails inside an effect rather than breaking the whole output). I
  addressed this in the guide's prose and Gotchas rather than touching the docstring, per the brief's
  "report, don't fix" instruction.
- **The "Rate limiting" numbers (11 vs. 4 updates for a comparable drag) are Playwright-timing-dependent**,
  not a clean architectural guarantee. I verified the direction and rough magnitude of the reduction
  honestly rather than claiming "debounce always publishes exactly once per gesture" (it doesn't -- a
  synthetic drag with enough IPC latency between steps can still cross the debounce window more than once).
  If the maintainer wants a cleaner "fires once" story for the website copy, a real mouse gesture (not
  Playwright-synthesized) would likely show fewer intermediate publishes; I'd rather report the measured
  number than guess at what a human drag looks like.
- **The jscatter pairing example (`11_jscatter_stars_on_sky.py`) needed a long-press-then-drag gesture to
  trigger the lasso**, even with `.lasso(initiator=True)` set. My first attempt (immediate drag, no pause)
  silently did nothing (the plot's default "move" tool stayed active). Fixed by copying the exact gesture
  shape from `tests/playwright/jscatter_accessors/test_jscatter_accessors.py` (mouse down, 1200ms wait,
  *then* move in steps). Noting this in case it surprises another guide's agent writing a jscatter-paired
  example.
- **Gallery showcase's "zoom out" step needed 12 repeated small wheel scrolls, not one large one.** A single
  large `page.mouse.wheel(0, N)` call (tried at several magnitudes) produced a much smaller zoom change than
  the same total magnitude split across repeated smaller calls with short pauses between them -- Aladin
  Lite's zoom handling appears to treat a single large wheel event similarly to a single small one rather
  than scaling with delta magnitude. Not investigated further (cosmetic to the verification driver, not a
  guide-worthy finding), but noted in case another agent hits the same thing driving Aladin Lite's zoom.

## Editor's notes for the website

- **Strongest material**: the gallery showcase's four-screenshot sequence
  (`gallery_showcase_before.webp` -> `..._click.webp` -> `..._zoomed_out.webp` -> `..._flyto.webp`) is the best
  "wow" sequence in this guide -- it's the only place that shows all four accessors working together, and
  the zoomed-out view (27 Messier objects, fov=180 deg) followed by a table-driven fly-to M31 (revealing its
  satellite galaxies) is genuinely compelling. Recommend leading any ipyaladin marketing excerpt with those
  two images.
- **The update-in-place-vs-rerender sequence** (`update_in_place_before/after.webp` + `rerender_after.webp`) is
  the clearest *mechanistic* demonstration (concrete, measured fov numbers proving state preservation vs.
  reset) -- worth keeping even in a trimmed page, since "why update in place" is otherwise just assertion.
- **What to cut for a shorter page**: the "Footprints and MOCs" section is the most niche (requires
  `mocpy`, a separate install) -- could be demoted to a single screenshot + one paragraph, or moved into
  "Learn more" as a pointer rather than a full worked example, if space is tight. The "Beyond the accessors"
  section is intentionally thin (`_is_loaded` is the only trait worth calling out) and could be folded into
  "Updating the widget from Python" as a one-sentence aside instead of its own heading.
- **What from the old report (`docs/widget-reports/ipyaladin/`) I deliberately dropped, and why**:
  - The PR-review scorecard, "blockers/should-fix/nits" review structure, and the specific PR #325 framing:
    that material was reviewing a pull request before merge; this guide teaches the shipped, current-`main`
    feature, which supersedes it entirely.
  - The old report's `examples/ipyaladin/app.py:44-46` "hidden re-render" finding: re-checked against the
    current `examples/ipyaladin/app.py` on `main` and it's already fixed (the render function reads inputs
    under `reactive.isolate()`); nothing to repeat.
  - The old report's `ui.output_text_verbatim()` deprecation nit: also already fixed on `main`'s example
    app (uses `ui.output_code()`/`@render.code` throughout); not applicable to current code.
  - The old report's Messier-explorer gallery app is the direct ancestor of this guide's
    `showcase_messier_explorer.py` -- kept the catalog data and the "what's in view" concept (good, reusable
    material), rewrote every interaction to go through the new accessors (`clicked_object()`,
    `selected()`, `target()`, `fov()`) instead of raw `reactive_read()` on private traits, which is
    the entire point of this pass.
  - The old report's CORS-console-error non-issue and the two-canvases-per-viewer non-issue: both
    environmental/non-issues already correctly dismissed by the old report; not worth repeating since they
    weren't bugs to begin with.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: jscatter** -- `examples/11_jscatter_stars_on_sky.py` lassos a color-magnitude diagram and
  marks the selected stars' real sky positions on the ipyaladin viewer, in place (`remove_overlay()` +
  `add_table()` per selection change).
- The showcase gallery app's "row selection flies the viewer" pattern (table -> `.widget.target`/`.fov`) is
  the same shape as jscatter's and ipyleaflet's "table row selection -> map/plot focus" pattern documented in
  those guides; worth a shared mention in the linked-views cross-cutting article.

## Update 2026-11-11 (main @ 32ca7035)

- **Accessor reference table and prose rewritten for #437's new narrative.** The old guide already got the
  *outcome* right for all four accessors (it independently described `clicked_object()` resetting on
  re-render and `target()`/`fov()` being seeded), but used the pre-#437 "event" vs. "state" taxonomy
  language the brief asks to delete, and the table didn't have the new `before any interaction` /
  `across re-render` columns. Replaced the table and its explanatory paragraph with the new framing: all four
  accessors attach at render and re-seed from the new viewer on every re-render (none of the four is a "kept"
  accessor on this renderer).
- **Verified live, not just re-read from source** (`shinywidgets/_ipyaladin.py`, `_render_widget.py`): clicked
  a catalog source, panned, zoomed, then forced a re-render with the same target/fov/catalog passed to the
  constructor. `clicked_object()` went from the clicked row's data back to `None`; `target()`/`fov()` went
  from the panned/zoomed values (`ra=57.004, fov=0.401`) back to the constructor's seed (`ra=56.871,
  fov=0.730`) -- confirming all three are re-seeded from the new widget, not carried forward. (The existing
  `tests/playwright/ipyaladin_clicked_seed` suite already covers the render-time-seed half of this; this pass
  additionally confirmed the re-render reset, which that suite doesn't exercise.)
- **New section "Reading on demand: save the current view"** (`examples/13_save_view.py`): a button handler
  reads `sky.target()`/`sky.fov()` with no prior reader anywhere in the app, demonstrating the no-warm-up
  headline capability from #437 using the two accessors that are always populated (no `req()` needed).
  Verified: panned between two saves, the two recorded bookmarks have different `ra` values confirming each
  read captured the view at press time.
- **CDS still unreachable from this machine** (re-checked 2026-11-11): the new screenshot
  (`img/save_view_after.webp`) shows the same "https://alaskybis.unistra.fr/.../... loading..." placeholder as
  every other screenshot in this guide. Per this pass's instructions, left as-is rather than re-attempting a
  full re-verification of imagery loading.
- No other `render_ipyaladin` behavior changed between `00f90249` and `32ca7035`; the rest of the guide
  (navigation, survey/colormap switching, catalog overlays, MOCs/footprints, update-in-place vs. re-render,
  layout, Gotchas, gallery) was re-read against current `main` source and still matches -- not
  re-screenshotted, since none of that code was edited.
- `accessors:` front matter unchanged (`[clicked_object, selected_objects, target, fov]`).

### Verification (this update)

| Check | Result |
|---|---|
| `clicked_object()` after click, then pan, then zoom (same render) | unchanged (click data persists across pan/zoom within one render) |
| `clicked_object()` after a forced re-render (same constructor args) | `None` -- re-seeded |
| `target()`/`fov()` after pan + zoom | follow the gesture (`ra=57.004`, `fov=0.401`) |
| `target()`/`fov()` after the same re-render | back to the constructor's values (`ra=56.871`, `fov=0.730`) -- re-seeded |
| `examples/13_save_view.py` (new) | ran, screenshotted, two saves after an intervening pan produced two distinct bookmarks |

### Bugs found (2026-11-11)

None. Behavior matches the current docstrings exactly; the only thing that needed fixing was this guide's
own vocabulary (event/state taxonomy -> before-interaction/across-re-render), not any shinywidgets behavior.

## Network/imagery caveat (per the assignment's explicit instruction)

**CDS's sky-imagery and web-service servers (`alasky.cds.unistra.fr`, `alaskybis.unistra.fr`,
`aladin.cds.unistra.fr`, `simbad.cds.unistra.fr`, `vizier.cds.unistra.fr`) were unreachable from this machine
for the entire verification session** (both on 2026-10-30 and re-checked on 2026-11-02 after the session
resumed; `curl` against any of these hosts times out or fails DNS/connection). esm.sh (the CDN serving
ipyaladin's JavaScript bundle) was reachable throughout, so the viewer's UI, canvas, markers, catalogs, MOCs,
footprints, and all four accessors render and function correctly -- **every screenshot in this guide shows
the sky background stuck at "https://alaskybis.unistra.fr/.../... loading..." (a dark grey placeholder)
instead of actual DSS/2MASS/allWISE tiles.** This affects literally every screenshot in `img/` (all 26 of
them), since every example points the viewer at the sky. None of the functional behavior documented in this
guide depends on the imagery itself loading -- markers, overlays, and accessors are all independent of tile
fetch success -- but the hero and gallery screenshots would look more compelling with real imagery. Retry
from a machine with CDS access before publishing if a more visually complete hero/gallery shot is wanted;
I did not find a CDN mirror or fallback for the tile servers themselves (unlike the JS bundle, which esm.sh
serves independently of CDS).

## Update 2026-11-11 (B1 rename: selected_objects() -> selected())

- The primary selection accessor was renamed to `selected()` (one rule across renderers; unreleased API, no
  shims). Guide, examples, and front matter updated; widget *trait* names (e.g. jscatter's `selection`,
  lonboard's layer `selected_index`, ipyaladin's `_selected_objects`) are unchanged, and references to those
  or to upstream widget methods (`plot.value.selection()`, `EmbeddingAtlasWidget.selection()`,
  `Aladin.selection()`) were deliberately left alone.
- `examples/07_selected_objects.py` was renamed to `examples/07_selected.py` and re-verified in the browser
  (armed rectangle selection, dragged a box over the Pleiades: the table listed Alcyone/Atlas/Pleione).

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." Split into two stories: HiPS imagery (tiled,
"only send what's visible" by construction -- no number needed, that's the protocol) and `add_table()` catalogs
(every row shipped in one message, same mechanism as mols2grid's grid data). Judgment call: I did not measure an
exact row-count ceiling for `add_table()` this pass (would need a scratch Playwright/websocket probe at several
catalog sizes) -- said so plainly rather than inventing a number, and only cited the general, already-documented
16 MiB Shiny websocket limit as the mechanism. No new example needed. Links forward to the not-yet-written
`../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) -- expected
`check_docs.py` anchor warning.
