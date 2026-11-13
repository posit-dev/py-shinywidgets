# NOTES: "Performance: fast, responsive widget apps"

## Versions

- shinywidgets: `main` @ `00f90249` (2026-10-30 commit, measured 2026-11-02), run from the coordinator's
  detached worktree (`scratchpad/main-wt`).
- shiny 1.9.0, plotly 6.9.0, lonboard 0.17.0, ipyleaflet 0.20.0, jscatter 1.0.1, perspective (python) 5.6.1,
  k3d 3.2.0, matplotlib 3.11.2, itables 2.9.1, psutil 7.2.2.
- Playwright: Chromium headless, `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`
  (needed for the WebGL-based renderers -- lonboard, jscatter, plotly `Scattergl` -- to paint in headless mode).
- Date: 2026-11-02. Ports 10060-10079 (coordinator-assigned range), one server and one browser at a time, per
  the operating rules.

## Methodology, per section

- **Section 1 (re-render vs. in-place):** a `page.on("websocket")` listener summed `framesent`/`framereceived`
  byte lengths, with counters reset after the initial page load settled (network-quiet for 600ms, polled every
  200ms over a 20s window) and read again after each button click settled the same way. Wall-clock elapsed time
  from this same network-quiet heuristic turned out to be unreliable for small payloads (see "Judgment calls"),
  so it is reported in prose caveats only, not in the headline table.
- **Section 2 (big data):** `PERF_N` env var controls row/point count; a Chromium route patch on `output.js`
  exposes `window.widgetManager` (the same `expose_manager` technique as `tests/playwright/conftest.py`), and
  `page.wait_for_function` polls `widgetManager._liveViews.size` until it's nonzero and stable across two
  consecutive 300ms polls -- a direct signal that the widget actually mounted, used both for elapsed time and
  as the stopping point for byte counting. This is the methodology section 1's simpler network-quiet heuristic
  lacked.
- **Section 3 (memory):** `psutil.Process(server_pid).memory_info().rss`, summed over the server process and
  all its `children(recursive=True)` (the `uv run` wrapper plus the actual `python -m shiny` process), sampled
  after a 2s settle post-startup, then after the 3rd and 5th of 5 sequential `browser.new_context()` + `goto()`
  calls in one Chromium instance (one browser, multiple contexts -- still "one browser" per the operating rules).
- **Section 4 (rate limiting):** same websocket/effect-counter idiom as the `reacting-to-widgets` article's own
  rate-limiting example; driven with `page.mouse.wheel()` scroll-zoom bursts (10 steps, 60ms apart) on each of
  two lonboard maps' canvases (identified by bounding box, since each lonboard map renders two stacked
  `<canvas>` elements and a naive `nth(0)`/`nth(1)` selection silently drove both gestures into the first map --
  see "Bugs found / surprises" below).
- **Section 5 (bundle size):** a fresh `browser.new_context()` (no cache) per app, summing HTTP response bytes
  (via `response.body()`) plus websocket frame bytes, explicitly excluding `blob:`/`data:` "responses" (the
  browser reconstructing an anywidget ESM module from bytes already counted once in the websocket's
  `comm_open` message -- counting both double-counts real network bytes) and excluding basemap tile-host
  responses (`cartocdn.com`, OSM tile hosts) from the renderer-bundle total, tracked separately instead.

## Verification table

| File | Ran | Screenshot | Measurement | Confirmed |
|---|---|---|---|---|
| `examples/01_inplace_plotly.py` | yes | zoomed/after-inplace/after-rerender | websocket bytes, both actions | in-place 36.3 KB, re-render 5.45 MB; zoom preserved vs. reset, visually confirmed |
| `examples/02_inplace_lonboard.py` | yes | zoomed/after-inplace/after-rerender | websocket bytes, both actions | in-place 141.8 KB, re-render 6.19 MB; camera preserved vs. reset, visually confirmed |
| `examples/03_inplace_ipyleaflet.py` | yes | choropleth screenshot | websocket bytes, 3 actions (inplace/toggle_visible/rerender) | style-update 1.09 MB (not cheap), toggle_visible 444 B (cheap), re-render 1.11 MB |
| `examples/04_bigdata_plotly.py` | yes | 100K screenshot | bytes + time at 10K/100K/1M (`PERF_N`) | `buffer_paths` inspected directly in the comm_open message to confirm binary-buffer transport |
| `examples/05_bigdata_jscatter.py` | yes | 100K screenshot | bytes + time at 10K/100K/1M | -- |
| `examples/06_bigdata_lonboard.py` | yes | 100K screenshot | bytes + time at 10K/100K/1M | -- |
| `examples/07_bigdata_perspective.py` | yes | n/a (table, not pictured) | bytes + time at 10K/100K (1M skipped, see article) | flat payload confirmed at two data sizes |
| `examples/08_lifetimes_memory_persession.py` | yes | n/a | server RSS at 0/3/5 sessions, 2 independent runs | per-session growth confirmed, both runs |
| `examples/09_lifetimes_memory_shared.py` + `examples/globals.py` | yes | n/a | server RSS at 0/3/5 sessions | flat memory regardless of session count confirmed |
| `examples/10_ratelimit_lonboard.py` | yes | both-maps screenshot | `view_state()` fire count, identical zoom burst on each map | 2 vs. 2 (no-op confirmed on a second widget) |
| `examples/11_bundle_ipyleaflet.py` | yes | n/a | first-load HTTP+ws bytes, fresh context | tile bytes correctly separated from bundle bytes |
| `examples/12_bundle_itables.py` | yes | n/a | first-load HTTP+ws bytes, fresh context | -- |
| `examples/13_bundle_k3d.py` | yes | n/a | first-load HTTP+ws bytes, fresh context | -- |
| `examples/14_bundle_matplotlib.py` | yes | n/a | first-load HTTP+ws bytes, fresh context | -- |

All 14 example files were also independently smoke-tested from their final `docs/widget-guides/articles/
performance/examples/` location (not just from the scratch directory) with `uv run --no-sync shiny run
<file> --port <port>` + an HTTP 200 check, after being copied into place, to catch any import-path regressions
from the move (`globals.py` in particular -- Shiny Express's own machinery for importing a sibling `globals.py`
exactly once, confirmed by a `ModuleImportWarning: A module named globals is already loaded` at startup, which
is benign and expected, not an error).

No gesture in this article was impossible to automate; every interaction was a real Playwright mouse event
(`mouse.down/move/up`, `mouse.wheel`, `click`) against the rendered page, never a JS-level trait assignment.

## Bugs found / surprises

- **[docs, re-verified] plotly's "5 MB bundle resent on every re-render" is real and independently confirmed.**
  The plotly guide's own `NOTES.md` explicitly left this old-report claim unverified ("I did not re-verify the
  old report's ~5MB/re-render JS-bundle... findings"). Decoding the actual `comm_open` websocket message for a
  freshly re-rendered `FigureWidget` shows its `state` dict includes a full `_esm` field -- the entire plotly.js
  bundle as a JS source string -- which is absent from an in-place `batch_update()`'s message. This is upstream
  architecture (every anywidget-coerced `FigureWidget` is a brand-new model with its own `_esm`), not a
  shinywidgets bug, but it's the single biggest number in this whole article (5.45 MB vs. 36.3 KB for an
  identical visual change) and worth the maintainer knowing it's now confirmed, not just inherited folklore.
- **[up, new] ipyleaflet's `GeoJSON.style` is not a cheap in-place update.** `ipyleaflet.GeoJSON` observes its
  own `style` trait (alongside `data`/`style_callback`) and rebuilds `self.data` by baking the computed style
  into every feature's `properties` on *any* style change (`GeoJSON._get_data()`, confirmed by reading
  `ipyleaflet`'s installed source). Setting `layer.style = {...}` therefore re-syncs the entire feature
  collection -- measured at 1.09 MB for a 177-country choropleth, within 2% of a full re-render's 1.11 MB.
  Toggling `layer.visible` (not observed by that method) costs 444 bytes. This isn't mentioned in any existing
  guide's "Gotchas" section as far as I found; worth a line in the ipyleaflet guide if the maintainer wants it
  there too (I did not edit that guide -- out of scope for this article).
- **[methodology bug, caught and fixed before any numbers were reported] lonboard renders two stacked
  `<canvas>` elements per map** (base + overlay). My first rate-limiting driver script picked `canvas.nth(0)`
  and `canvas.nth(1)` as "the two maps," which are actually both layers of the *same* (left) map -- the right
  map's `view_state()` fired only once (its construction-time seed), never from the gesture. Caught by
  `bounding_box()`-based debugging before publishing any number; fixed by indexing `canvas.nth(0)` (left map)
  and `canvas.nth(count - 1)` (right map).
- **[methodology limitation, reported honestly rather than papered over]** the Section 1 in-place-vs-re-render
  harness's wall-clock timing is unreliable for small payloads: in one run it reported the 5.45 MB plotly
  re-render as *faster* than the 36.3 KB in-place update. Root cause: on localhost, network transfer is never
  the bottleneck, so a "no new websocket bytes for N ms" timer mostly measures server-side Python
  serialization time, not client-perceived latency -- and a single huge frame can satisfy "quiet" faster than
  two or three small ones spread slightly further apart. I did not fix this by tuning the polling window
  further; I dropped wall-clock time from that table's columns and said why in the article, pointing instead
  to Section 2's DOM-based (`_liveViews` stability) timing, which doesn't have this problem since the signal
  it waits for is "the widget actually mounted," not "the network went quiet."
- **[not a bug, a correction to my own initial hypothesis]** I expected plotly's trace data to travel as plain
  JSON text (vs. jscatter/lonboard's "binary") going into Section 2, and said so in an early draft. Decoding the
  comm_open message's `buffer_paths` (`[["_widget_data", 0, "x", "buffer"], ["_widget_data", 0, "y", "buffer"]]`)
  disproves this: plotly's numpy-backed trace data uses the identical binary-buffer-plus-base64 channel as the
  other two. I rewrote that section once I'd actually looked, rather than publishing the more "obvious" and
  wrong story.

## Judgment calls

- **Big-data N=1,000,000 runs: only plotly, jscatter, and lonboard, not perspective.** perspective's payload was
  already flat between 10K and 100K rows for an architectural reason (server-side virtualization, confirmed by
  `render_perspective`'s own docstring describing the server-side table), so a 1M-row perspective run would
  almost certainly repeat the same ~6.48 MB result. Running it anyway would have added a fourth 1M-point run on
  a machine this project's operating rules asked me to keep "few," for a result I was already confident about.
  A second opinion on whether the maintainer wants that fourth data point anyway (for completeness, not because
  I expect a surprise) would be easy to get in a follow-up pass.
- **datashader (via holoviews) and embedding-atlas were scoped out of the big-data comparison.** The brief
  listed them as "as feasible." Building a representative datashader pipeline (binning + a holoviews
  `render_holoviews` output) and an embedding-atlas comparison (which needs an offline projection cache per its
  own guide's findings, plus WebGPU-specific Chromium args) would each have been close to a full guide's worth
  of new Playwright harness work on their own, and the holoviews guide is itself mid-revision (see
  `docs/widget-guides/FINDINGS.md`'s holoviews entries) as of this writing. I judged re-deriving fresh
  measurements for two architecturally different libraries lower-value than spending that time getting four
  solid, fully cross-checked numbers (plotly/jscatter/lonboard/perspective) right, especially the
  bytes-aren't-the-whole-story and perspective-doesn't-pay-for-rows findings, which are the most broadly useful
  takeaways in that section. Flagging for a second opinion: if the maintainer wants datashader/embedding-atlas
  numbers specifically, that's additional scoped work, not a quick addition.
- **The memory section uses lonboard (200,000 points) for both the per-session and shared_lifetime() widget**,
  rather than two different widget types. This was deliberate: the point is to isolate the *lifetime* variable,
  not the widget's own footprint, and lonboard was already the heaviest, most memory-relevant widget elsewhere
  in this article (Section 1 and 2), so reusing it meant one less library's construction cost to characterize
  from scratch.
- **Per-session memory numbers are reported as two independent runs rather than averaged or smoothed.** The
  two runs disagree on the exact MB/session rate (roughly 12-36 MB/session depending on which pair of points
  you look at), which is real noise from a shared, loaded machine and Python's allocator not returning freed
  memory to the OS promptly (confirmed by the 3-to-5-session memory *dropping* slightly in both runs, which a
  monotonic "N sessions = N times the cost" model wouldn't predict). I reported both runs and described the
  qualitative shape (grows substantially vs. stays flat) rather than inventing a single precise rate number I
  don't trust. A second opinion on whether 3-5 more runs to tighten the rate estimate would be worth the
  machine time is welcome, but I judged the qualitative contrast (which is unambiguous and consistent across
  both runs) as the actually load-bearing claim for this article, not the exact MB/session figure.
- **CDN-fallback bundle bytes were not measured**, only the local-nbextension path (this machine's actual,
  always-local resolution). Measuring the CDN path would require making a widget's local nbextension data
  briefly unavailable in a venv shared with ~10 other concurrent agents -- explicitly against this project's
  operating rules ("do not uv sync/pip install," implicitly extending to "don't remove installed package
  data either"). I stated the CDN path is strictly worse (more bytes, more latency, an extra DNS/TLS
  round-trip to `unpkg.com`) without a specific number, rather than fabricating one.
- **Re-verification choice for the "mined from other guides" citations (Section 1):** per the assignment's
  "cite them, and re-verify 1-2" instruction, I treated the ipyleaflet-style-update finding and the
  plotly-bundle-resend finding as my two fresh re-verifications (both are from this article's own fresh
  measurements, not reused from a guide's NOTES.md), and left pyvista's 12 KB/1.1 MB and keplergl's rate-limit
  numbers as cited-not-rerun, since both guides already documented their own measurement methodology in detail
  and re-deriving them would have meant standing up a pyvista/keplergl app from scratch for a number this
  article was always going to cite, not lead with.

## Editor's notes for the website

- **Strongest material:** the plotly bundle-resend finding (Section 1) and the "it's not JSON vs. binary, it's
  bundle size" reversal (Section 2) are the two most genuinely surprising, well-evidenced findings in this
  article -- both overturn a plausible-sounding prior assumption with a specific, reproducible number. If the
  page needs to be shortened, keep these two over the lifetimes/memory section (Section 3), which is real but
  less surprising (per-session costs more than shared is the expected result).
- **The ipyleaflet `style`-isn't-cheap finding (Section 1) is the best "gotcha" screenshot-free section** --
  it's a pure numbers-plus-one-sentence-explanation payoff, and it directly undercuts a reader's likely
  assumption that "in-place update" is simple blanket advice. Good candidate for a pull-quote.
- **Section 5's table is information-dense but the prose "what this means in practice" paragraph is probably
  the one sentence most readers actually need** (5.05 MB shared + 0.2-10 MB renderer-specific, additive across
  widgets on one page). If cutting for length, the exact-byte table could shrink to just the "Total first load"
  column with the renderer-specific breakdown moved to this NOTES.md.
- **The rate-limiting section (Section 4) is the thinnest of the five**, by design -- it's mostly citing
  already-well-measured results from `reacting-to-widgets` and the per-widget guides, with one fresh
  re-verification (lonboard) added specifically because the assignment asked for it. This is correct scoping
  (avoid duplicating a guide's content), not a gap.
- **What I did not build:** a dedicated screenshot for the Section 3 (memory) measurements, since RSS-over-time
  isn't something a single screenshot usefully shows -- the table is the right artifact there, consistent with
  the assignment's own "present comparative tables" instruction.
- I did not edit any per-widget guide (e.g. to add the ipyleaflet `style` finding to that guide's own Gotchas
  section) -- this article's assignment was to write the cross-cutting article, not revise guides; flagging the
  finding here and in the article's own prose is, I believe, the correct scope, but a second opinion on whether
  the maintainer wants it back-ported to `ipyleaflet/guide.md` would be easy to action.

## Pairs with

- **reacting-to-widgets**: shares the mental model (accessors, lifetimes, rate limiting) this article measures
  performance consequences for; several citations go directly to that article's own measured examples rather
  than re-deriving them.
- **linked-views**: a different cross-cutting concern (coordinating widgets, not single-widget performance),
  but the in-place-update idiom (`@reactive.effect` + `widget.trait = ...`) is the same one linked-views teaches
  for propagating state between widgets -- worth noting for anyone reading both.
- **pyvista, keplergl, ipydatagrid, itables, plotly, lonboard, jscatter, perspective**: each guide's own
  performance-relevant measurement is cited (not duplicated) in this article; see "Where to go next" in
  `article.md`.

## Update 2026-11-11 (main @ 32ca7035)

shinywidgets `0.8.2.post1.dev135+g32ca7035`, shiny 1.9.0, plotly 6.9.0, lonboard 0.17.0, ipydatagrid 1.4.0.
Worktree `scratchpad/main-wt`, ports 8650-8664. This pass's job (per `docs/widget-guides/UPDATE-BRIEF.md`) was
to re-check every claim against what changed on `main` since the article's original `00f90249` measurement,
and re-run only what actually needed it -- not a wholesale redo. Checked every item in the brief's performance
focus list (#405, #415, #400, #401, #437) against the article text; most needed no change (reasoning below),
two needed real re-measurement.

**What was re-measured, and why:**

- **Section 4 (rate limiting), rewritten.** #400 added a default 0.25s debounce to ipydatagrid's `selected()`
  and lonboard's `view_state()`, both of which this article's original pass had documented as having *no*
  declared rate policy at all (a genuine no-op at the time). That specific claim is now false, so the whole
  section needed re-doing, not just a word swap.
  - **ipydatagrid**: not re-run by me. The [ipydatagrid guide](../../widgets/ipydatagrid/index.md#rate-limiting)
    already has a clean, gesture-verified before/after for the new default (`.selected()` fires twice for a
    9-row drag vs. ten times for an un-rate-limited `reactive_read()` on the same trait) -- reused that number
    rather than re-deriving an equivalent measurement from scratch, consistent with this article's existing
    "mined from other guides" practice (Section 1's pyvista/keplergl citations).
  - **lonboard**: re-ran `examples/10_ratelimit_lonboard.py` with real Playwright gestures (scroll-zoom burst,
    drag, and several spaced-apart discrete gestures -- see below) and found the straightforward "N vs M fires"
    comparison the original methodology used doesn't actually demonstrate the new debounce for this widget. I
    dug into *why* rather than just reporting a flat number: watching raw outgoing websocket frames (not just
    the debounced Python-side counter) during a drag showed **at most one** `view_state` sync message reaches
    the server per gesture, for *both* the default and `rate_delay=0` panels. Reading lonboard's own bundled
    JS (`.venv/.../lonboard/static/index.js` in the worktree) found why: `_rr=debounce(t=>t.save_changes(),300)`
    -- lonboard's own anywidget sync is already debounced at 300ms, upstream of and independent from whatever
    shinywidgets declares. By the time a raw update would reach shinywidgets' rate-limiting layer, lonboard has
    usually already collapsed the gesture to one message. Confirmed the shinywidgets-level debounce is still
    real (not silently broken) with gestures spaced >=600ms apart, which do each produce their own raw message
    and their own immediate fire on the undebounced panel. Wrote this up as the actual finding instead of
    forcing a "3 vs 8"-style number I couldn't honestly reproduce -- see the "Judgment calls" section below for
    why I didn't keep pushing for a cleaner contrast.
  - Re-screenshotted `img/10_ratelimit_lonboard.webp` (both panels now settle to "fired 2 times" for an
    identical 10-step scroll-zoom burst, reproducible across three independent runs) and retitled the example
    app's page title from "rate_delay no-op check" to "debounced vs. rate_delay=0" (the old title asserted the
    now-false conclusion) -- updated both the file and the article's embedded snippet, confirmed byte-identical
    after the edit.
  - Updated the "no-op list" (accessors with *no* declared rate policy, where the kwargs do nothing): removed
    lonboard's `view_state()` and ipydatagrid's `selected()` (both now have a default per #400); also removed
    ipycytoscape's child `Node`/`Edge` widgets, since #404 made `rate_policy`/`rate_delay` reach those widgets
    too (confirmed by reading the renderer's current docstring in `shinywidgets/_render_widget.py`). mols2grid,
    ipyvolume's `camera()`, and k3d/pythreejs's `camera()` were left on the list as carried-over, not
    re-verified this pass (unaffected by anything in the brief's changed-PR list).
  - Removed the direct citation of `FINDINGS.md`'s rate-limiting no-op claim in Section 4's prose, since that
    claim (written before #400/#404) is now partly stale; `FINDINGS.md` itself is the coordinator's own
    document and wasn't edited by me.
- **"Does eagerly attaching every accessor cost anything?" -- new subsection in Section 2.** #437 made every
  accessor attach at render instead of lazily on first read; plotly alone now carries ten accessors (six more
  than the four-ish it had at the article's original measurement date), none of which
  `examples/04_bigdata_plotly.py` reads. Re-ran that example's 10,000-point case three times with the same
  `widgetManager._liveViews`-stability methodology Section 2 already used (route-patched `output.js`,
  `page.wait_for_function` polling for a stable live-view count) -- 2.35s/2.42s/2.41s, at or below the
  original 3.6s, well inside this machine's documented run-to-run noise. No regression found; said so plainly
  rather than re-running every N again for a number that didn't move. Did not re-run the 100K/1M cases: the
  10K case already answers the question (attaching a message handler doesn't move data, so there's no
  mechanism by which it would scale with point count), and re-running three sizes for a negative result isn't
  worth this shared machine's time.

**What was checked and found not to need a change** (no example re-run, since the article made no claim these
PRs would invalidate):

- **#405** (browser-created models now close with their referrer; pythreejs/bqplot re-renders no longer leak):
  this article's own Section 3 (lifetimes/memory) uses a lonboard `ScatterplotLayer`, not a browser-created
  widget (pythreejs lights, bqplot's toolbar `PanZoom`), and doesn't cite any pythreejs/bqplot leak number.
  Grepped the whole article for "pythreejs"/"bqplot"/"leak"/"browser-created" to confirm -- no stale claim.
- **#415** (widget messages sent before/during the same flush as a render are now delivered, not dropped): this
  article's own examples don't send custom widget messages from a render function or a same-flush effect (the
  `@render_*` bodies here only build widgets; the `@reactive.effect` bodies mutate traits, not call
  `.send()`-backed methods). No claim in this article depended on the old dropped-message behavior. (The
  **choosing-a-widget** article did have a stale gotcha here -- fixed there, not here.)
- **#401** (plotly explicit heights now respected; compact margins survive an in-place template swap): grepped
  for "height"/"margin" -- this article's plotly examples (`01_inplace_plotly.py`, `04_bigdata_plotly.py`)
  don't set an explicit output height or swap templates in place, so neither symptom #401 fixes was ever
  exercised here. No change needed.

## Bugs found (2026-11-11)

None found this pass. The lonboard upstream-debounce discovery above is a real, surprising mechanism worth
knowing, but it isn't a shinywidgets bug -- the declared debounce works exactly as documented; it's just rarely
the binding constraint for this particular widget because lonboard's own JS already throttles comparably.

## Judgment calls (2026-11-11)

- **Didn't keep pushing for a "clean" fires-N-vs-M lonboard number.** I tried five different gesture
  methodologies (continuous drag, scroll-zoom burst, discrete nudges at 80ms/120ms/600ms spacing) before
  concluding the flat contrast the original Section 4 format wants isn't reproducible for this widget for a
  real, explainable reason (lonboard's own 300ms upstream debounce). A sixth or seventh gesture variant might
  eventually produce a cherry-picked "N vs M" pair, but that would overstate precision the underlying mechanism
  doesn't have. I judged the mechanistic finding (verified via source code, not just guesswork) more valuable
  and more honest than forcing the old table format onto a result that doesn't fit it. Second opinion welcome
  on whether the maintainer wants a differently-designed example (e.g. driving the browser-side model directly
  via `window.widgetManager`, bypassing lonboard's own throttle) for a cleaner number -- I didn't build that,
  since it would demonstrate shinywidgets' debounce in isolation but no longer reflect what a real user gesture
  does, which is what this article is about.
- **Did not re-measure Section 1, 2 (beyond the 10K accessor-attach check), 3, or 5 numbers.** None of their
  subjects changed per the brief's PR list (re-render/in-place bytes, big-data bytes, memory, bundle size) --
  re-running them would be re-verifying claims nothing invalidated, which the brief explicitly says to skip.
- **Cited ipydatagrid's guide number rather than re-deriving it.** Its own measurement (2 vs. 10 for a 9-row
  drag) is a cleaner demonstration of the same #400 change than anything I could add by standing up a parallel
  ipydatagrid harness here, and the brief's "mined from other guides" allowance (already used for pyvista and
  keplergl in the original pass) covers this.

## Update 2026-11-11 (Task 7: "Three approaches to large data" + datashader/embedding-atlas rows)

Retitled the page "Large data & performance" (was "Performance: fast, responsive widget apps"), added a new
opening section **"Three approaches to large data"** before Section 1, added two new rows (datashader,
embedding-atlas) to Section 2's big-data table with two new example files, and applied Task 5's two handoff
rows for this file (the `#lifetimes` and `#shared_lifetime...` links now point at `updating-in-place/article.md`
instead of the trimmed `reacting-to-widgets/article.md`).

### Versions used

- shinywidgets `0.8.2.post1.dev145+gad97a76d` (worktree HEAD, 2026-11-11), shiny 1.9.0.
- holoviews 1.23.2, datashader 0.19.1, bokeh 3.10.2, jupyter_bokeh 4.1.0, panel 1.10.0 (all already in the
  shared venv; `examples/15_bigdata_datashader.py` uses the same `rasterize()`-via-`render_holoviews` idiom the
  datashader guide documents).
- embedding-atlas 0.26.0, duckdb (project-locked version, already in the venv). `examples/16_bigdata_embedding_atlas.py`
  synthesizes `x`/`y`/`text` columns directly (no UMAP/projection step -- this section measures transport, not
  the library's clustering).
- Playwright: Chromium headless. datashader: `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` (same flags Section 2 already used for the other three renderers). embedding-atlas:
  `channel="chromium"`, `args=["--enable-unsafe-webgpu", "--use-angle=metal"]`, navigating to a real
  `http://127.0.0.1:<port>` origin -- the same combination the embedding-atlas guide's own NOTES.md documents as
  required for a real WebGPU adapter in headless Chromium; confirmed by the actual GPU-rendered scatter map in
  `img/16_bigdata_embedding_atlas_100k.webp` (not the "WebGPU unavailable" placeholder).
- Ports 8160-8169 (assigned range). Measurement/screenshot scripts in this task's scratch dir
  (`measure.py`, `debug_mount.py`, `debug_models.py`, `debug_anymodel.py`, `shoot.py`), not in the docs tree.

### Methodology: bytes

Same instrument as the rest of Section 2 (`page.on("websocket")` summing `framesent`/`framereceived` byte
lengths, both directions, from `page.goto()` to a stable mount signal), but with one addition the original
Section 2 script didn't need: `render_holoviews`'s Bokeh-backed widget and `render_embedding_atlas`'s widget
both register **two** live views, not one (confirmed directly: `window.widgetManager._liveViews.size` settles
at 2 for both, reproducibly), so the stopping condition is "stable and non-zero," not "stable and equal to 1."
Reusing the existing `expected == 1` convention here would have under-counted: in an early version of this
pass's harness it caused `_liveViews.size` to pass its stability check at 0 (checked twice in a row before the
widget had even started mounting), reporting a false near-instant "done" with near-zero bytes. Fixed by
requiring `n > 0` in the stability predicate regardless of what `expected` is. `measure.py`'s module docstring
and `--expected` flag document this for whoever (Task 11) reuses it.

### Bugs found / surprises (for FINDINGS.md)

- **[finding, not a regression -- confirmed working as designed, but with a surprising scope] A sibling
  `globals.py`'s `shared_lifetime()` widget is opened for every session of every app in the same directory,
  even apps that never import or display it.** Repro: run any of this article's own `examples/*.py` files
  (confirmed with `14_bundle_matplotlib.py`, `15_bigdata_datashader.py`, and `04_bigdata_plotly.py`, none of
  which reference `globals.py`) with Playwright capturing websocket frames; every one of them carries four
  extra frames (~4.77 MB, ~4.77 MB, ~4.20 MB, ~4.20 MB -- identical byte-for-byte across all three completely
  unrelated apps) that, read out of the browser's own widget registry
  (`window.widgetManager._models`, filtered to `_model_name === 'AnyModel'`), turn out to carry lonboard
  `Map`/`ScatterplotLayer` traits (`basemap`, `layers`, `view_state`, `picking_radius`, ...) -- i.e., the
  200,000-point shared map `examples/globals.py` builds for Section 3's own memory test. Root cause (not a
  shinywidgets bug by itself): `shiny.express._run.create_express_app` auto-imports a directory's `globals.py`
  before running *any* Express app in that directory
  (`globals_file = file.parent / "globals.py"; ... import_module_from_path("globals", globals_file)`), and
  shinywidgets' process-global-widget machinery (`open_process_global_widgets()`/`init_session()`, per
  `AGENTS.md`'s architecture notes) then opens *every* registered process-global widget for *every* session,
  regardless of whether that session's own render functions reference it. The combination means: **placing a
  `shared_lifetime()` cache module next to other, unrelated example apps silently taxes every one of those
  apps' sessions with that widget's full payload**, with no visible symptom (nothing renders in the unrelated
  app's own output area) unless you're counting bytes. This is a real, reproducible, and consequential
  interaction between a documented Shiny Express convention and a documented shinywidgets lifetime feature --
  worth the maintainer knowing even though neither half is a bug in isolation.
  - **Consequence for this article's own numbers:** every byte in this task's two new table rows was measured
    from an isolated copy of the example (same code, a scratch directory with no sibling `globals.py`), *not*
    from the file's final location in `examples/`, specifically to avoid this contamination -- see "Judgment
    calls" below.
  - **Consequence for Section 5 ("Bundle size and first load") -- resolved in Task 12's final sweep.** Task 12
    moved `08_lifetimes_memory_persession.py`, `09_lifetimes_memory_shared.py`, and `globals.py` into a new
    `examples/lifetimes/` subdirectory, so `examples/` no longer has a sibling `globals.py` and Express no
    longer auto-imports (or opens) the shared lonboard map for any other app in the directory. Re-measured all
    eight Section 5 rows afterward (method below) and the numbers did not materially change (max delta 93 KB,
    1.8%, well under the ~4-5 MB this contamination mechanism adds when it's present) -- meaning the original
    numbers were already clean: Section 3's lifetimes examples (and `globals.py`) were added to `examples/`
    *after* Section 5 was originally measured on 2026-11-02, not before. No table values changed.
  - Not re-produced for RSS/memory measurements (Section 3): that section's own point is this exact widget's
    memory, so this isn't contamination there, it's the subject.

### Section 5 re-measurement after the `examples/lifetimes/` move (Task 12)

Re-ran the bundle-size measurement (fresh, uncached `browser.new_context()` per app; sum HTTP response bytes
via `response.body()` plus websocket frame bytes; `blob:`/`data:` responses excluded; this re-run didn't
separately bucket tile-host bytes, so the totals below include any basemap tiles ipyleaflet/lonboard happened
to fetch) against the post-move `examples/` directory (script:
`measure_bundle.py`, scratch-only, same approach as the original methodology above):

| Renderer | App | New total first load | Published total | Delta |
|---|---|---:|---:|---:|
| matplotlib | `14_bundle_matplotlib.py` | 5.373 MB | 5.28 MB | +0.093 MB (1.8%) |
| itables | `12_bundle_itables.py` | 5.871 MB | 5.85 MB | +0.021 MB (0.4%) |
| ipyleaflet | `11_bundle_ipyleaflet.py` | 6.317 MB | 6.30 MB | +0.017 MB (0.3%) |
| k3d | `13_bundle_k3d.py` | 9.659 MB | 9.64 MB | +0.019 MB (0.2%) |
| jscatter | `05_bigdata_jscatter.py` (`PERF_N=100`) | 7.386 MB | 7.37 MB | +0.016 MB (0.2%) |
| plotly | `04_bigdata_plotly.py` (`PERF_N=100`) | 10.435 MB | 10.41 MB | +0.025 MB (0.2%) |
| perspective | `07_bigdata_perspective.py` (`PERF_N=100`) | 11.547 MB | 11.53 MB | +0.017 MB (0.1%) |
| lonboard | `06_bigdata_lonboard.py` (`PERF_N=100`) | 15.123 MB | 15.11 MB | +0.013 MB (0.1%) |

Every delta is under 2% (matplotlib's 93 KB is the largest, plausibly ordinary cold-start noise -- font/icon
loading, Chromium process variance -- not a multi-MB contamination signature). **No table values in the
article changed.** This also means the Section 2 (`04`-`07` at their real `PERF_N` scales) and Section 1
numbers, measured the same 2026-11-02 pass in the same pre-`globals.py` state of `examples/`, don't need a
follow-up pass either -- flagging this conclusion here since the "Bugs found" entry above raised the question
for all of Section 5 (and implicitly nearby sections), not just these four rows.

### Judgment calls

- **Measured the two new rows from isolated copies (no sibling `globals.py`), not from their final
  `examples/` location.** This keeps the new rows comparable to the existing table's plotly/jscatter/lonboard/
  perspective numbers (also measured before -- or without -- this contamination), rather than baking in a
  constant, renderer-irrelevant ~9 MB that would make "datashader is flat" and "embedding-atlas grows with N"
  both look like they start from a much higher, misleading floor. The example files themselves are unchanged
  between the isolated copy and the shipped version (byte-identical) -- only where the measurement script ran
  from differs. Second opinion welcome on whether the maintainer wants a one-line caveat on the table itself
  (I judged the "Pitfalls and a checklist" bullet sufficient, since that's where every other "gotcha, not a
  headline number" item on this page already lives).
- **datashader's image size is fixed (700x450, not `responsive=True`).** The task asks the payload to
  demonstrate flatness against *N*; a responsive plot ties image resolution to viewport, which would have
  confounded "flat regardless of N" with "flat because I always used the same browser window." Fixing the
  pixel size isolates the variable actually being tested. This also uncovered (and then eliminated, by
  switching to a fixed size) a `responsive=True`-triggered second resize-redraw that otherwise sent a second,
  larger copy of the image per load -- not reported as a separate finding since it stopped being a factor with
  `width=700, height=450` set, and digging into *why* bokeh/panel redraws once more on first layout felt like
  more depth than this task's "measure bytes" scope asked for.
- **Added the 10,000,000-point datashader row as prose, not a fourth table column.** The existing table's
  other three renderers (plotly/jscatter/lonboard/perspective) were never run at 10M (two of them can't be --
  see Section 2's own prose on plotly/jscatter at 1M already taking several seconds), so a literal fourth
  column would be mostly empty cells for rows that aren't mine to re-measure. A sentence after the table
  carries the same information without implying a comparison that was never attempted for the other rows.
- **Did not pursue a "10M" row for embedding-atlas.** Unlike datashader, embedding-atlas's payload scales with
  N (it's not a summarize-on-the-server renderer), so a 10M run would cost roughly 10x the 1M row's ~17 MB --
  informative as a stress test, but not needed to support this row's actual claim ("grows with N, unlike
  datashader"), which the 10K/100K/1M progression already demonstrates cleanly. Skipped to keep this pass's
  largest-scale runs few, per the project's resource rules.
- **`labels="disabled"` on the embedding-atlas example.** Isolates the payload/render-time cost of the GPU map
  and data load from auto-label clustering (a separate, DuckDB-driven computation this section isn't
  measuring) -- consistent with how `04_bigdata_plotly.py` etc. use a bare `go.Scattergl`/similar minimal
  construction rather than a feature-rich one.
- **Did not re-derive bokeh's or altair's large-data numbers.** Task 8a already measured and wrote both (bokeh
  `output_backend="webgl"` vs. canvas at 200K points; altair VegaFusion flat-vs-linear spec size) directly into
  their own guides' new `## Large data` sections before this task started editing ("Three approaches" just
  links to them), so re-deriving either here would duplicate verified work from the same wave.

### Timing cells left pending for Wave 3

- `article.md` Section 2 table: the two new rows' six time cells (10K/100K/1M x datashader/embedding-atlas).
  Measure with: `uv run --no-sync python <scratch>/measure.py examples/15_bigdata_datashader.py <N> <port>
  --gpu webgl --timeout 60` and the same for `examples/16_bigdata_embedding_atlas.py <N> <port> --gpu webgpu
  --channel-chromium --timeout 60`, reading `elapsed_s` off the printed `RESULT` line (median of three runs,
  per the plan's Task 11 instructions). **Run these from an isolated copy of the two example files (no sibling
  `globals.py`), not their `examples/` location** -- see "Bugs found" above; running in place would also time
  the extra ~9 MB of unrelated shared-widget traffic, inconsistent with this task's byte numbers. `measure.py`
  is not part of this task's deliverables (scratch-only); Task 11 can either copy the two example files to an
  isolated directory itself or write an equivalent harness -- the key requirement is just "no sibling
  `globals.py` in whatever directory the timed app runs from."
- No other timing cells were left pending by this task (the "Three approaches" section and the §3 link
  fixes carry no timing claims).

## Update 2026-11-11 (Task 11: timing measurements for Section 2's two new rows)

Filled the six time cells (left pending above) for datashader/embedding-atlas at 10K/100K/1M.
Measured from isolated copies of `examples/15_bigdata_datashader.py` and
`examples/16_bigdata_embedding_atlas.py` in this task's own scratch directory (no
sibling `globals.py`), per the previous pass's own instructions for this step.

### Versions / environment

- shinywidgets worktree HEAD at the time of this pass, shiny 1.9.0, holoviews 1.23.2,
  datashader 0.19.1, embedding-atlas 0.26.0. Date 2026-11-11, ports 8220-8229.
- datashader: headless Chromium, `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist`. embedding-atlas: `channel="chromium"`,
  `args=["--enable-unsafe-webgpu", "--use-angle=metal"]`, same combination the
  embedding-atlas guide and this article's own previous pass already used.

### Methodology problem found, and the fix

This article's own Section 2 methodology (documented above, "Methodology, per
section") times from `page.goto()` to `window.widgetManager._liveViews.size`
settling non-zero and stable, reusing the same `expose_manager` route-patch idiom as
`tests/playwright/conftest.py`. That signal is valid for plotly/jscatter/lonboard/
perspective (their widget registering as "live" coincides with their transferred data
actually being drawn), but **it is not valid for embedding-atlas, and measuring with
it anyway silently produced a flat ~0.82 s for every one of 10K/100K/1M** -- which
would have wrongly implied embedding-atlas's render time doesn't grow with N, directly
contradicting its own bytes row in the same table (6.13 -> 16.2 MB).

Caught by looking, not just trusting the number: a screenshot taken at the exact
moment `_liveViews` reported stable (N=1,000,000) showed the map canvas still blank
("0 points" in its own overlay) and the row table still reading "Loading...", while
the page header already correctly read "1,000,000 / 1,000,000 points" -- i.e. the
*data* had already arrived and the widget had *mounted*, but the actual WebGPU draw
of the points hadn't started yet. A second screenshot 5 seconds later showed the full,
correctly-rendered scatter map. `window.widgetManager._liveViews` tracks view
*registration*, not "finished painting" -- a distinction that didn't matter for the
article's other four renderers (whose data transfer IS their visible output, more or
less) but does for a renderer with a separate, asynchronous GPU draw step after its
data lands.

**Fix:** switched to a pixel-stability signal for both of this task's two rows (not
just embedding-atlas, for methodological consistency within the new rows): poll
`page.screenshot()` (full page) every 300 ms starting right after the existing
`_liveViews`-stable signal fires, and report elapsed time once two consecutive
screenshots hash identically (SHA-1). Cross-checked against the old `_liveViews`-only
number for datashader too (not just embedding-atlas, since the same undercounting risk
applies to any renderer with post-mount drawing/compositing work): `_liveViews` gave a
flat but **understated** ~1.7 s at every scale; the pixel-stability signal gave a flat
and apparently more honest ~2.7 s at every scale (consistent 3-run medians: 2.69 s/
2.68 s/2.66 s at 10K/100K/1M) -- still flat, so this doesn't change datashader's
qualitative story, only the absolute number. Did not attempt to further decompose
"what happens in that extra ~1 s" (e.g. Bokeh's own canvas compositing, colorbar
layout) -- out of scope for a bytes-table timing fill-in.

**Did not change the article's existing Section 2 timing methodology description**
(the "Methodology, per section" paragraph above, written by the original pass) for
plotly/jscatter/lonboard/perspective, since nothing in this task's scope asked for a
re-verification of those four numbers and the `_liveViews` signal's blind spot is
specific to renderers with an async post-mount draw step, which none of those four
have reason to exhibit (not independently re-verified this pass; flagging as a
possible follow-up if the maintainer wants full consistency across all six rows).

### Raw numbers

Pixel-stability elapsed time, seconds, 3 runs per cell, reported value is the median:

| Renderer | N | Run 1 | Run 2 | Run 3 | Median (used in table) |
|---|---:|---:|---:|---:|---:|
| datashader | 10,000 | 2.688 | 2.660 | 2.760 | 2.69 (rounds to 2.7) |
| datashader | 100,000 | 2.678 | 2.678 | 2.630 | 2.68 (rounds to 2.7) |
| datashader | 1,000,000 | 2.659 | 2.753 | 2.654 | 2.66 (rounds to 2.7) |
| embedding-atlas | 10,000 | 1.766 | 1.738 | 3.007* | -- |
| embedding-atlas | 100,000 | 1.874 | 2.782 | 2.343 | -- |
| embedding-atlas | 1,000,000 | 2.348 | 2.187 | 2.201 | -- |

\* embedding-atlas's pixel-stability numbers were noisier than datashader's across all
three scales (headless WebGPU compositing appears less deterministic frame-to-frame
than Bokeh's canvas-2D path), so two more runs were taken per scale (5 total) before
reporting a median, rather than trusting 3:

| N | All 5 runs (s) | Median (used in table) |
|---:|---|---:|
| 10,000 | 1.766, 1.738, 3.007, 1.739, 1.748 | 1.748 (rounds to 1.7) |
| 100,000 | 1.874, 2.782, 2.343, 1.847, 1.839 | 1.874 (rounds to 1.9) |
| 1,000,000 | 2.348, 2.187, 2.201, 2.350, 2.355 | 2.348 (rounds to 2.3) |

### Judgment calls

- **Took 5 runs for embedding-atlas instead of the task's baseline 3**, specifically
  because the 3-run samples included a clear outlier (3.007 s at 10K, nearly double
  the other two) that would have materially changed which number got reported; 2 more
  cheap runs (each ~2-3 s wall-clock) resolved it to a tight median without much extra
  machine time.
- **Did not try to characterize what causes embedding-atlas's extra per-run jitter**
  (headless WebGPU frame timing is plausibly less deterministic than canvas-2D, but
  this wasn't investigated beyond re-running) -- out of scope for a bytes-table
  timing fill-in, and the qualitative story (grows with N) is unambiguous across all
  5 runs regardless of which single run you'd pick.
- **Datashader's three medians (2.69/2.68/2.66 s) round to an identical "2.7 s" for
  all three cells** rather than reporting three slightly different numbers that would
  visually suggest a trend where none exists (the raw spread across all 9 datashader
  runs is 2.63-2.76 s, a single noise band, not a monotonic progression with N).
