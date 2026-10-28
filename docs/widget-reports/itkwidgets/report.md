# itkwidgets feasibility spike (2026-10-28)

**Verdict: FEASIBLE — with caveats. itkwidgets 1.0a can render inside Shiny today via an
imjoy-rpc-over-Shiny-messages bridge.** The earlier assessment (batch 2, `docs/plans/batch2/
itkwidgets-pr-body.md`) concluded "BLOCKED: no ipywidgets comm to bridge." That was correct
about the ipywidgets protocol, but it turns out the ipywidgets comm is not the only bridgeable
transport: the imjoy-rpc Jupyter protocol (comm target `imjoy_rpc`) is a small JSON protocol
that maps cleanly onto Shiny custom messages/inputs. A working implementation now lives in
`shinywidgets/experimental/_itkwidgets.py` (+ `shinywidgets/static/imjoy-bridge.js`), with an
example app in `examples/itkwidgets/app.py`.

All browser evidence below is real Chromium (Playwright, ANGLE Metal WebGL2), with
`itkwidgets 1.0a55`, `itk-vtk-viewer 14.51.0` (self-hosted), Python 3.12.

## What was built

- `shinywidgets/experimental/_itkwidgets.py` — Python side of the bridge. Re-implements the
  Python half of `imjoy_rpc.connection.jupyter_connection` (`JupyterCommManager` /
  `JupyterCommConnection`) over `session.send_custom_message` + a session input, plus the
  monkeypatches itkwidgets needs to run outside a Jupyter kernel.
- `shinywidgets/static/imjoy-bridge.js` — browser side. Mirrors
  `imjoy-jupyterlab-extension/src/comm-connection.js` (buffer packing, MessageEmitter,
  connection class), loads `imjoy-core`'s basic app from CDN, and mounts the viewer iframe
  inline in the Shiny output container.
- Public API: `sw_itk.imjoy_head()` (script deps), `sw_itk.register_imjoy_session(session,
  input)` (once per session), `sw_itk.render_viewer(session, viewer)` (returns the container
  div for a `@render.ui` output).
- No changes to shinywidgets' core were needed; the bridge uses its own message names
  (`imjoy_connect`, `imjoy_rpc_msg`, `imjoy_rpc_send`) and coexists with normal
  `@render_widget` outputs on the same page (`evidence_coexist_ipywidgets.png`).

## How it works (and why the "BLOCKED" verdict was wrong)

itkwidgets 1.0a is an **ImJoy plugin**, not an ipywidget. In Jupyter, the frontend half is
`imjoy-jupyterlab-extension`, which (a) loads imjoy-core, (b) opens a kernel comm named
`imjoy_rpc`, and (c) runs a ~120-line connection class that shuttles JSON + binary buffers
between the comm and imjoy-core. The kernel half (`JupyterCommManager` in imjoy-rpc) speaks a
tiny handshake: `imjoyRPCReady` → `initialize` → `initialized` → `setInterface` →
`interfaceSetAsRemote`, after which `Viewer.run()` calls `api.createWindow(src=ITK_VIEWER_SRC)`
and the viewer iframe (itk-vtk-viewer) joins the RPC mesh. Volume data flows as zarr chunks:
the iframe calls `getItem(".zattrs" | "scale0/image/.zarray" | "scale0/image/0/0/0")` on a
Python-side zarr store object exposed via imjoy codecs; responses carry binary buffers.

None of that is Jupyter-specific. The bridge swaps the comm for Shiny messages (base64 for
binary, same as `_comm.py`). Confirmed working end-to-end: handshake completes in ~1.5 s,
`getItem` traffic streams chunks, the viewer volume-renders, and `captureImage` round-trips.

## Coverage

| Area | Result | Evidence |
|---|---|---|
| Volume render (numpy → zarr → browser) | ✅ | `gallery_initial.png` |
| Python→browser: colormap, view mode (X/Y/ZPlane), slices, rotate, background color | ✅ | `gallery_interactive.png`, `evidence_zplane.png` |
| `set_image` (replace data in place) | ✅ | ex_06 (rerun during spike) |
| Label image overlay + `set_label_image_blend` | ✅ (order quirk, see F9) | `evidence_label_in_zplane_ok.png` |
| Point sets (`set_point_set`) | ✅ | `evidence_zplane.png` (dots), spike shots |
| `compare_images(method='checkerboard')` | ✅ | `evidence_compare_checkerboard.png` |
| Getters (`get_image_color_map`, `get_view_mode`, `get_layer_names`, `get_current_scale`) | ✅ (with F4 pattern) | spike logs |
| Browser→Python events (`zSliceChanged`, `imageColorMapChanged`) | ✅ (with F5 pattern) | spike logs |
| Two viewers on one page | ✅ | spike (viewer1+viewer2 independently rendered) |
| Re-render lifecycle (new Viewer → new connection) | ✅ | spike (render fired, fresh iframe mounted) |
| Multi-session isolation (2 tabs) | ✅ | `evidence_session_tab1.png` / `evidence_session_tab2.png` |
| Coexists with regular ipywidgets outputs | ✅ | `evidence_coexist_ipywidgets.png` |
| Sizing: fill page, fixed-height card, full_screen, viewport resize | ✅ (F10 note) | probe: iframe is 100%/100%, follows resizes |
| `view()` / `Viewer()` | ✅ | same code path |

## Findings (ranked by severity)

**F1 — Upstream viewer hosting is broken today (critical for users).**
`itkwidgets.viewer_config.ITK_VIEWER_SRC` points at an `ipfs.dweb.link` URL. That gateway is
being sunset: it returns HTTP 429 with "This IPFS gateway is switching to a service worker
gateway only" — including inside a real browser iframe (screenshot: iframe full of the sunset
notice). `ipfs.io` also 429s; `gateway.pinata.cloud` refuses to serve HTML; `w3s.link`,
`cf-ipfs.com`, `nftstorage.link`, `4everland`, `storry.tv` all failed. Upstream has already
moved gateways twice (fleek.co → dweb.link Jan 2025; main branch has a third CID, also on
dweb.link). **Workaround (verified): self-host `itk-vtk-viewer@14.51.0` (npm, `dist/`, 108 MB)
as static assets and set `ITK_VIEWER_SRC=/itk-vtk-viewer/index.html`** — the bridge absolutizes
root-relative URLs. Note the npm 14.51.0 publish date (2024-06-21) matches the itkwidgets
commit that introduced the a55 CID, so it is almost certainly the same build. Even when
self-hosting, the viewer's UI options still load from jsdelivr
(`itk-viewer-bootstrap-ui@0.30.0`), so fully-offline use needs more vendoring.

**F2 — itkwidgets 1.0a55 has serious dependency rot (critical for installability).**
A working 2026 install requires, on top of `itkwidgets>=1.0a55`:
- `numcodecs<0.13` — itkwidgets pins `zarr<3`; zarr 2.18 imports `cbuffer_sizes` from
  `numcodecs.blosc`, removed in numcodecs 0.13. numcodecs 0.12.1 has **no cp313/cp314/cp315
  wheels** (source build fails on 3.15) — Python 3.12 (or older) is effectively required.
- `ngff-zarr<0.15` — ngff-zarr ≥0.15 refuses zarr-2 in-memory stores
  ("ngff-zarr writes to local directory paths"), which is exactly how itkwidgets streams.
- `urllib3` — imported unconditionally in `itkwidgets/standalone_server.py` at package
  import, but not declared (ModuleNotFoundError otherwise).
- itkwidgets itself has no `__version__` attribute (minor).
Because uv resolves the whole workspace into one lock, these pins make itkwidgets a poor
candidate for `pyproject.toml` dev/test extras (CI is Python 3.10–3.14). As an optional
user-facing extra for pip installs (`pip install shinywidgets[itkwidgets]` with
`itkwidgets>=1.0a55, numcodecs<0.13, ngff-zarr<0.15, urllib3`) it is fine. Install weight of
the 1.0a55 stack (imjoy-rpc, itkwasm, ngff-zarr, zarr 2, numcodecs, ...): ~349 MB
site-packages; the self-hosted viewer adds 108 MB of static assets (one-time, shareable
across apps).

**F3 — itkwidgets 0.32.x is still dead for us (re-confirmed).**
`itkwidgets==0.32.6` hard-pins `ipywidgets<8.0.0` — unsatisfiable with our `ipywidgets>=8.1`
(re-ran the resolver). Skip the 0.32 line entirely.

**F4 — Getters deadlock if awaited inside a reactive effect (product pattern, documented).**
While an async effect awaits, Shiny does not dispatch the input effect that delivers the RPC
response → `await viewer.get_image_color_map()` inside `@reactive.effect async def ...` hangs
forever (root-caused with websocket-frame captures; the response frame arrives but is never
dispatched). Not unique to this bridge (any response-over-inputs protocol hits it). Pattern
that works (in the example + docstring): fire-and-forget —
`fut = asyncio.ensure_future(collect()); fut.add_done_callback(...)` — or
`reactive.ExtendedTask`. Note ViewerRPC.run works fine because imjoy RPC handlers run as
plain asyncio tasks, not Shiny effects. This may deserve a general note in shinywidgets docs.

**F5 — imjoy-rpc event callbacks are single-use (documented; workaround in example).**
`registerEventListener("zSliceChanged", cb)` consumes the callback on first firing; the second
event throws "Callback function can only called once" in the browser console and the event is
lost. Workaround: re-register inside the handler (shown in `examples/itkwidgets/app.py` and in
our patched `ViewerRPC.run`). The same limitation exists in Jupyter — upstream bug territory.

**F6 — Global export registry replaced with per-connection binding (design fix in bridge).**
`imjoy_rpc.api.export()` is process-global; naive porting (mirror the Jupyter singleton
manager) makes every new connection adopt the *latest* exported ViewerRPC, so with two viewers
both iframes drive viewer #2's data and viewer #1's `has_viewer` stays False forever. The
bridge binds each connection to the export made by its render call (`export_id` passed through
the handshake). Multi-viewer and multi-session now work.

**F7 — Shiny serializes custom-message dispatch (documented).**
An `async` `Shiny.addCustomMessageHandler` that awaits a long operation blocks delivery of
*subsequent custom messages* — observed as every imjoy handshake frame stalling for exactly
15 s (the `connectPlugin` timeout). Websocket frames arrived promptly; they were just never
dispatched. Fix: handlers must return immediately (fire-and-forget IIFE). Worth remembering
for any future custom-message protocol work in shinywidgets proper.

**F8 — Asyncio tasks created in render functions capture the reactive context (documented).**
`asyncio.create_task()` inside a render function copies contextvars, including Shiny's
reactive context; a task that later *reads* a reactive value silently registers it as a
dependency of that render — observed as a self-sustaining re-render loop firing every ~0.21 s
(27 re-renders before catching it). Fix: `with reactive.isolate():` around reactive reads in
the task (in the example). This is a general Shiny gotcha that bit us here first.

**F9 — `set_label_image` while in a plane view mode blanks the slice (upstream quirk).**
Setting a label image while `view_mode` is `ZPlane` makes the slice go blank
(`evidence_label_points.png`). Setting it in `Volume` mode first and *then* switching to
`ZPlane` renders the overlay correctly (`evidence_label_in_zplane_ok.png`). Order-dependent
upstream (itk-vtk-viewer) bug; transport-independent.

**F10 — Sizing works, with one note.**
The viewer iframe is `width/height:100%` and follows container resizes (verified by viewport
resize probe: 868→459 px reflowed correctly) and card `full_screen`. In a fixed-height card,
use `ui.output_ui(..., fill=True)` — without it the output div does not constrain height and
the iframe can overflow the card. No 0-height-collapse issues observed (unlike many
ipywidgets), since we control the container div directly.

**F11 — Headless-Chromium flakiness (test-harness note).**
Playwright Chromium crashed twice mid-session (TargetClosedError) under load (108 MB viewer +
WebGL). Restarting the run fixed it. Worth knowing before writing Playwright tests for this
widget (also seen in the pyvista report).

**F12 — Monkeypatching surface (maintenance risk).**
The bridge patches itkwidgets internals: `ENVIRONMENT` (→ fake JUPYTER so `Viewer` takes the
ViewerRPC path), `_cell_watcher` (real one imports pyzmq), `display` (IPython display
publishes notebook screenshots), `Viewer._setup_queueing` (IPython BackgroundJobManager
crashes without a shell), and `ViewerRPC.run` (skips notebook screenshot embedding + a
hard-coded `asyncio.sleep(10)`). All are runtime module-global patches, applied once. This is
inherently fragile across itkwidgets releases — a strong argument for upstreaming a
first-class "custom transport" hook (imjoy-rpc already has the seam: `api.export` just needs a
connection factory).

## Scorecard

| Dimension | Score | Notes |
|---|---|---|
| First-render reliability | ★★★☆☆ | Perfect *with self-hosted viewer*; 0/10 with the default IPFS URL (F1) |
| Python→browser updates | ★★★★★ | setters all work: colormap, view mode, slices, rotate, set_image, label, points, bg color |
| Browser→Python reactivity | ★★★☆☆ | Events work but are single-use (F5); getters need the F4 pattern |
| Sizing/layout | ★★★★☆ | 100%/100% iframe, reflows, full_screen OK; `fill=True` note (F10) |
| Multi-session | ★★★★★ | Per-session viewers/connections; verified with 2 tabs |
| Installability | ★☆☆☆☆ | Dependency rot (F2): pins, no new-Python wheels, undeclared urllib3; ~460 MB total |
| Upstream stability | ★★☆☆☆ | 1.0a line is alpha, last release 2025-02; hosting has broken twice already; viewer JS pinned by content hash |

**Fit verdict:** Good fit *technically* — the bridge is ~400 lines Python + ~250 lines JS,
needs no shinywidgets core changes, and every major viewer feature works. The blockers are
upstream, not architectural: broken default hosting (F1), dependency rot (F2), alpha-line
maintenance. Recommendation: ship as `shinywidgets.experimental.itkwidgets` (as done here)
with the self-hosting recipe documented, and engage upstream about (a) restore reliable
viewer hosting (or publish the viewer to npm with a declared version), (b) relax the `zarr<3`
pin, (c) declare `urllib3`, and (d) a supported non-Jupyter transport hook. Revisit promotion
to a first-class `@render_itkwidgets` once any of F1/F2 improves.

## The magic

1. **Full GPU volume rendering of your numpy arrays, in Shiny, in ~15 lines of app code.**
   Ray-cast 3D rendering with transfer functions, 100+ colormaps, and slice planes — no
   JavaScript to write.
2. **Segmentation overlays and landmarks.** A label image blended over the volume plus 3D
   point sets — the radiology review workflow (`set_label_image_blend` live from a slider).
3. **Image registration review in one call.** `compare_images(fixed, moving,
   method="checkerboard")` fuses two volumes in a checkerboard — instantly shows
   misalignment (`evidence_compare_checkerboard.png`).
4. **Big-data friendly streaming.** itkwidgets converts arrays to a multiscale OME-Zarr
   pyramid in memory; the browser fetches chunks on demand over RPC — multi-GB volumes
   stream progressively instead of shipping wholesale to the browser.
5. **It plays well with others.** The imjoy bridge rides alongside regular ipywidgets outputs
   in the same Shiny app — mix a vtk.js volume with ipyleaflet, plotly, etc.

## API patterns & recipes

- **Install (2026 recipe):**
  `pip install 'itkwidgets>=1.0a55' 'numcodecs<0.13' 'ngff-zarr<0.15' urllib3` on Python ≤3.12
  (numcodecs 0.12.1 lacks newer wheels).
- **Self-host the viewer (required today):**
  `npm pack itk-vtk-viewer@14.51.0 && tar xzf itk-vtk-viewer-14.51.0.tgz`, serve `package/dist`
  as static assets, `ITK_VIEWER_SRC=/itk-vtk-viewer/index.html`. The example app's docstring
  has the full commands.
- **Constructor kwargs** that worked: `image`, `label_image`, `point_sets=[...]`,
  `ui_collapsed`, `rotate`, `bg_color=[r,g,b,a]`, `compare` (via `compare_images()`).
- **Colormap names** come from vtk.js presets (112 of them; e.g. `"Viridis (matplotlib)"`,
  `"X Ray"`, `"Cool to Warm"`). Invalid names are silently ignored.
- **View modes**: `"Volume"`, `"XPlane"`, `"YPlane"`, `"ZPlane"`. Set label images in Volume
  mode first (F9).
- **Getters**: never `await` them inside an effect (F4) — use `asyncio.ensure_future` +
  done-callback or `reactive.ExtendedTask`.
- **Events**: `viewer.viewer_rpc.itk_viewer.registerEventListener(name, cb)` after
  `viewer.has_viewer`; re-register inside `cb` (F5). Useful events: `zSliceChanged`,
  `imagePicked`, `imageColorMapChanged`, `viewModeChanged`, `renderedImageAssigned`.
- **Reactive hygiene**: wrap reactive reads in asyncio tasks with `reactive.isolate()` (F8);
  keep the `Viewer` alive on the session (e.g. `session._v = v`); call
  `sw_itk.register_imjoy_session(session, input)` once in `server()`.

## Follow-ups

- **Upstream issues to file**: (1) dweb.link sunset broke the default `ITK_VIEWER_SRC` for
  every itkwidgets install — needs a new hosting story (they've moved gateways twice in a
  year); (2) `zarr<3` pin + old numcodecs blocks modern Python; (3) undeclared `urllib3`
  dependency; (4) `registerEventListener` callbacks single-use (or document the re-arm
  pattern); (5) `set_label_image` in plane view mode blanks the render; (6) `__version__`
  missing.
- **Product**: consider a generic "custom-message RPC channel" helper in shinywidgets (the
  on_flush/direct-send, base64 buffer, and async-handler lessons in F4/F7 are reusable);
  decide whether `experimental/` is the right long-term home; a Playwright test exists as
  `examples/itkwidgets` driver scripts in this spike but needs the headless-flake mitigation
  (F11) and the static viewer (F1) to run in CI.
- **Gallery/example candidates**: the phantom gallery app (this dir), a real CT/MRI dataset
  via itk-io (heavy), a two-tab "radiology review" with linked slice sliders.

## Appendix: repro commands

Environment: `~/.cache/itk-spike/setup.sh` (venv recipe + viewer download).
Run example: `ITK_VIEWER_SRC=/itk-vtk-viewer/index.html shiny run examples/itkwidgets/app.py`
with the dist mounted as static assets at `/itk-vtk-viewer`.
Gates: `make check` passes in the worktree (format, pyright, 466 unit tests).
