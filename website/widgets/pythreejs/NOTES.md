# NOTES: pythreejs guide

## Versions and environment

- Date: 2026-10-30
- shinywidgets: `main` (worktree `scratchpad/main-wt`, synced with all groups; `uv run --no-sync` from that
  worktree per the brief's operating rules).
- pythreejs 2.4.2 (bundles three.js r97), shiny 1.9.0, numpy 2.5.4, pandas (for the click-history table), Python
  3.12, Playwright Chromium (headless, no special WebGL flags needed -- see below).
- Ports 9620-9639 (assigned range), all freed on exit.
- Scratch driver scripts: `/private/tmp/claude-502/.../scratchpad/agents/pythreejs/{probe_driver,shoot,smoke_test}.py`
  and several one-off `app_*.py` probes used to isolate specific behaviors (rotation inertness, light leak,
  autoRotate, background default, fixed-size opt-out) before writing the corresponding guide examples.

**WebGL/headless note:** unlike the old report, this environment's headless Chromium (launched plain, no
`--use-angle=swiftshader` flags) rendered WebGL correctly out of the box -- Playwright's bundled
`chrome-headless-shell` already runs with `--use-angle=swiftshader --enable-unsafe-swiftshader` internally in
this environment (confirmed via `ps` on the Chromium subprocess). No launch-flag workaround was needed for any
screenshot in this guide.

## Verification table

Every example and gallery app ran via `uv run --no-sync shiny run ...`, driven with Playwright (real mouse
clicks/drags, not synthetic model.set() calls, except where noted), screenshotted, and every screenshot was
viewed with the Read tool before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | notes |
|---|---|---|---|---|
| `01_quickstart.py` | yes | `01_quickstart.webp`, `hero.webp` | none (static) + a slight orbit for the hero | |
| `02_scene_graph.py` | yes | `02_scene_graph_box.webp`, `02_scene_graph.webp` | real `<select>` change (Torus knot) | |
| `03_parametric_surface.py` | yes | `03_parametric_surface.webp` | none (static; slider not re-screenshotted) | |
| `04_camera_accessor.py` | yes | `04_camera_before.webp`, `04_camera_after.webp` | real orbit drag (mousedown/move/up) | `camera()` position/quaternion/zoom all confirmed changing |
| `05_picker_reactive_read.py` | yes | `05_picker_before.webp`, `05_picker_after.webp` | real click, aimed at a solid lobe of the torus knot (the knot has a hole through its center; a dead-center click misses) | `distance`/`point` confirmed via `reactive_read` |
| `06_inplace_material.py` | yes | `06_material_before.webp`, `06_material_after.webp` | real `<select>` change + keyboard-driven ion.rangeSlider | color change clearly visible; metalness/roughness changes are real (confirmed via DOM) but not very visible under ambient-only lighting -- expected, not a bug |
| `07_inplace_animation.py` | yes | `07_animation_t0.webp`, `07_animation_t1.webp` | none (continuous timer); quaternion value read directly to confirm advance (pixel comparison between nearby frames was inconclusive by itself since 90-degree-interval rotations of a torus knot can look similar -- the quaternion readout settled it) | |
| `08_link_click_history.py` | yes | `08_click_history.webp` | 3 real clicks (box, sphere, box) | table accumulates correctly; `picker.object` distinguished the two meshes by identity |
| `09_link_viewpoint_bookmarks.py` | yes | `09_bookmarks_saved.webp`, `_moved.webp`, `_restored.webp` | real orbit, save, orbit again, restore | restored canvas pixel-identical to the saved one |
| `10_link_picked_marker.py` | yes | `10_marker_before.webp`, `_after.webp` | real click | |
| `11_fixed_size.py` | yes | `11_fixed_size.webp` | none (static) | confirms explicit width/height opts out of fill in a tall card |
| `12_inplace_geometry.py` | yes | `12_geometry_before.webp`, `_after.webp` | real button click | pixel diff confirmed; visual difference is subtle at this camera angle (see Judgment calls) |
| `gallery/template_scene_explorer.py` | yes | `gallery_template.webp` | real click + `<select>` change | |
| `gallery/showcase_orrery.py` | yes | `gallery_orrery_t0.webp`, `_t1.webp`, `_pick.webp` | real click (picked "Earth" correctly) + real orbit + Reset view click | planet positions visibly advance between t0/t1; reset-view pixel-diff confirmed against a dragged-away view |

**Accessor coverage:** `camera()` is the only accessor this renderer declares (`_accessor_specs = (PYTHREEJS_CAMERA,)`
in `shinywidgets/_render_widget.py`). Verified with a real orbit-drag gesture in `04_camera_accessor.py`,
`09_link_viewpoint_bookmarks.py`, and `gallery/showcase_orrery.py`. `Picker` (no accessor; `reactive_read()` tier)
verified with real clicks in `05`, `08`, `10`, and both gallery apps -- including disambiguating multiple meshes
under one `Picker` via `picker.object` identity.

## Bugs and surprises found

Ranked roughly by how likely a user is to hit them in normal use.

1. **Fixed on `main` (regression fix, not new): the old report's resize-loop blocker.** The old report
   (`docs/widget-reports/pythreejs/report.md`, written against PR #324) flagged an infinite ResizeObserver
   feedback loop in content-derived-height containers (plain `page_fluid`, auto-height cards) as a merge-blocking
   regression. On current `main`, `tests/playwright/render_pythreejs/test_render_pythreejs.py::
   test_pythreejs_settles_in_unfillable_containers` exists and passes, and I independently confirmed every
   example in this guide (several using `ui.card(full_screen=True)` with no explicit height) settles to a stable
   canvas size rather than growing. Not re-litigated further here.
   
2. **Shinywidgets, still present: `DirectionalLight`/`SpotLight` default `target`/`shadow` leak browser-created
   models on re-render -- but the *symptom* has changed since the old report.** The old report described a
   server-side `TraitError` traceback on every render of a light-bearing scene. On current `main`, I reproduced
   the underlying leak (model count +3 per re-render of a one-light scene, confirmed via
   `window.widgetManager._models` through `tests/playwright/conftest.py`'s `expose_manager`/`client_models`
   helpers) but saw **zero server-side tracebacks**; instead, one benign browser-console error per re-render
   (`Error setting state: e.on is not a function`). I did not dig further into why the Python-side symptom
   changed (possibly an ipywidgets or traitlets version difference, or a change in how `_handle_msg` swallows the
   bad `IPY_MODEL_` reference) -- flagging this as a precise, re-verified finding rather than assuming the old
   report's exact repro still applies. The underlying leak and its workaround (explicit `target`/`shadow`) are
   unchanged and documented in the guide's Gotchas section.

3. **Upstream (pythreejs/three.js r97), unchanged from the old report: `mesh.rotation` is inert.**
   `convertFloatModelToThree` lowercases the Euler order string (`'XYZ'` &rarr; `'xyz'`), which three.js's
   `Quaternion.setFromEuler` doesn't recognize, so the quaternion never updates and the mesh never visibly
   rotates -- while the `rotation` trait value itself does advance, and each write echoes back a `TraitError`.
   Reconfirmed directly (byte-identical canvas across a rotation change; live `TraitError` tracebacks in the
   server log). The `quaternion`-based animation workaround in the guide is unchanged from the old report's
   recipe.

4. **Upstream, unchanged: `Scene.background` defaults to white and overrides `Renderer(background=...)`.**
   Reconfirmed: a `Renderer(background="black")` with no `Scene.background` set still renders white.
   `Scene(background=...)` is the one that works.

5. **Upstream, unchanged: `OrbitControls(autoRotate=True)` and damping are inert** (no per-frame `controls.
   update()` pump in the bundled JS). Reconfirmed with a byte-identical-canvas test over several seconds.

6. **Upstream, unchanged: `OrthographicCamera`'s frustum isn't managed by fill**, so a non-square container
   visibly stretches the image. Reconfirmed visually.

None of 3-6 are new; they're carried forward from the old report's findings 3.4-3.7 after independently
re-verifying each one still reproduces on current pythreejs/shinywidgets (same pythreejs version, same bundled
three.js r97). I did not re-verify the old report's non-issues list (3.8) since nothing in this pass touched
those code paths.

## Judgment calls

- **`camera()`'s accessor reference table has one row, and the "Rate limiting" section has no runnable example.**
  pythreejs really does only expose one accessor, and its sync policy (once per orbit-drag, on mouse-up) and
  `Picker`'s (once per click) are both inherently discrete -- there's no natural continuous-stream scenario to
  demonstrate `rate_delay` smoothing without fabricating one (e.g., scripting synthetic rapid-fire `camera.
  position` writes the way the ipysigma guide did for its camera-pan case). I chose to explain *why* rate
  limiting doesn't apply here rather than invent a contrived example; flagging this in case the maintainer wants
  a `reactive_read()`-on-a-high-frequency-custom-trait example added for completeness.
- **`12_inplace_geometry.py`'s before/after screenshot pair is a weak visual** (the amplitude change is real and
  pixel-confirmed, but at the chosen camera angle the two states look similar at a glance). I kept the example
  because the *mechanism* -- `BufferAttribute.array` reassignment preserving camera state -- is the point, and a
  more dramatic amplitude swing or camera angle change would start to look like a second parametric-surface demo
  rather than a focused in-place-update one. Low priority; a maintainer who wants a punchier image could swap in
  a bigger amplitude range or an overhead camera.
- **The showcase orrery's "Reset view" button resets `camera.position`/`quaternion`/`zoom` but not `OrbitControls.
  target`.** Since the demo only orbits (left-drag), never pans, `target` never moves from its default `(0,0,0)`
  in practice, so this is invisible in testing -- but a user who pans with a different input method before
  clicking "Reset view" could end up with a camera pose that doesn't look at the scene's center. Matches the
  pattern in `09_link_viewpoint_bookmarks.py`, which has the same limitation; noted here rather than fixed in
  both since handling `target` correctly would add a second snapshot slot for comparatively little payoff in a
  guide example.
- **Pairs with:** itables/reactable (the click-history table pattern could feed into a richer `reactive_read`-
  table guide cross-reference); k3d and ipyvolume (shared `camera()` accessor, explicitly cross-linked in the
  guide body).

## Dropped from the old report

- **The full PR-review framing (blockers/should-fix/nits scorecard).** The old report was reviewing an unmerged
  PR; all of that has either landed, been fixed, or is moot now that `render_pythreejs` is just part of `main`.
  Kept only the still-reproducing upstream/shinywidgets findings, reframed as user-facing gotchas.
- **The require.js global-registration risk and `shim: {}` noise nits** (old report's "nits" 4-5) -- these are
  `_dependencies.py` implementation details with no end-user-visible symptom; out of scope for a usage guide.
- **The detailed root-cause narrative for the resize loop** (old report's finding 3.1) -- it's fixed, so only a
  one-line "this used to be a bug, now it isn't" note remains (see Bugs and surprises #1).
- **Lifecycle/session-isolation stress testing (20 rapid re-renders, two-tab isolation)** -- valuable for a PR
  review, out of scope for a how-to guide; the one lifecycle-relevant fact that matters to a reader (the light
  leak) is kept.

## Editor's notes for the website

- **Strongest sections:** the viewpoint-bookmarks before/moved/restored triptych (very legible, proves the
  round-trip precisely) and the orrery showcase screenshots (genuinely impressive for ~100 lines of code). If the
  page needs to be shortened, these are the two to keep.
- **Cuttable if space-constrained:** the "Beyond the accessor" Picker gotcha paragraph about re-raycasting on
  scene changes is useful but could be trimmed to one sentence; the OrthographicCamera frustum note in Layout and
  sizing is a minor/nice-to-have gotcha that could move entirely into Gotchas and limitations instead of being
  mentioned twice.
- **The parametric-surface and in-place-geometry examples share a lot of code** (same triangulation helper,
  different camera distance). A web-page editor might want to visually pair these two side by side ("build it" /
  "update it live") rather than separating them into different page sections as the source guide does.

## Update 2026-11-11 (main @ 32ca7035)

Versions: shinywidgets `main` @ `32ca7035`, pythreejs 2.4.2, shiny 1.9.0, Python 3.13, run in the shared
`main-wt` worktree. Playwright: Chromium headless with `--use-angle=swiftshader --enable-unsafe-swiftshader
--ignore-gpu-blocklist`.

**What changed in the guide and why:**

- **#405 re-verified end to end.** Re-ran this guide's own "Bugs and surprises found" item 2 (the
  `DirectionalLight`/`SpotLight` default-`target`/`shadow` model leak) against current `main` using the same
  method (`window.widgetManager._models` via a patched `output.js`, same as `tests/playwright/conftest.py`'s
  `expose_manager`): with a **default** light (no explicit `target`/`shadow`), model count now stays flat at
  14 across 4 re-renders (was 14 -> 22 over 3 re-renders on `00f90249`). The one remaining symptom is a
  **benign** `Error setting state: e.on is not a function` browser-console message once per re-render (matches
  #405's PR description: closing a light's browser-created shadow trips an upstream pythreejs bug, now treated
  as expected teardown noise). With the **explicit** `target`/`shadow` recipe the quick start already used,
  there's neither a leak nor a console error (re-confirmed: 0 console errors, flat model count). Updated the
  quick start's framing (leak avoidance -> console-noise avoidance), the three Gotchas bullets that described
  the leak, and the inline comment in `examples/01_quickstart.py` (kept in sync with `guide.md`'s copy, which
  I'd edited first and almost shipped out of sync -- caught by a script-diff check against every example file
  before finishing, see Judgment calls). No server-side `TraitError`s either, matching the original NOTES'
  finding that the Python-side symptom had already changed before this pass.
- **Fixed a real, pre-existing inaccuracy in the accessor table, unrelated to the redesign.** The table said
  `camera()` "reads before the first render cancel like `req(False)`" -- false, and contradicted the guide's
  own prose two lines below it and the renderer's docstring. Verified directly: `scene.camera()` read with no
  prior orbit returns the Python-constructed camera's starting pose immediately (`position: (0.00, 0.00,
  3.50)` for the quick start's camera), never cancels. Rewrote the table row and prose to say so plainly, using
  the new before/after-re-render column format.
- Re-seeding across re-render was already correctly described in prose; restated using the new "inherent
  widget state" framing instead of leftover "state accessor" language (there wasn't any by the time I got
  here -- this guide's original author had already avoided the taxonomy terms).
- **`.read("camera")` is not a substitute for `.camera()` on this renderer, and I almost documented it as one.**
  Tried adding "it can also be read by name: `scene.read('camera')`" (parallel to what I was writing for the
  k3d guide, where it does work) and verified it in a browser first: `scene.read("camera")` returns the raw
  synced snapshot tuple (`(token, position_tuple, quaternion_tuple, zoom)`), not the live `Camera` object
  `camera()` returns -- calling `.position` on it raises `AttributeError`. This matches #437's PR notes
  (`.read()` can't replicate accessors that post-process from the widget, `camera()` named explicitly as one).
  Documented the *difference* instead of a false equivalence -- a useful gotcha in its own right.
- **Picker: kept `reactive_read()`, added why.** The brief asked to check whether `Picker` is a child widget
  (keep `reactive_read`) or not (switch to `.read()`). It's a child: `picker` is constructed separately and
  added to the `Renderer`'s `controls=[...]` list, not the `Renderer` itself (`scene.widget`/`scene.read()`
  refer to the `Renderer`). Added one sentence to the "Beyond the accessor" section explaining this, with the
  ipyleaflet-layers/cytoscape-nodes precedent from the brief's tier-3 rule.
- **Read-on-demand: already present, nothing to add.** `### camera() -> save/restore viewpoint bookmarks`
  already reads `scene.camera()` inside an `@reactive.event(input.save)` button handler -- exactly the
  read-on-demand pattern the brief highlighted as newly safe/natural. It didn't need a warm-up before this
  pass either (`camera()` was already an eager/seeded accessor), so no behavior changed here; left as is
  rather than padding with a second example.

**Re-verified claims (all with a real browser, this pass):**

- Model-leak fix (#405): `scratchpad/agents/threed/probe/pythreejs_default_light.py` /
  `pythreejs_explicit_light.py` + `light_leak_check.py` (not committed). 4 re-renders each; flat model count in
  both; console errors only in the default-light case (5 occurrences, one per render/re-render, text exactly
  `Error setting state: e.on is not a function`); zero server-side tracebacks in either.
- `camera()`'s seeded-not-cancelled initial value: `pythreejs_camera_initial.py`, read immediately after page
  load with no orbit.
- `.read("camera")` vs `.camera()` divergence: same probe file, `scene.read("camera")` vs `scene.camera()`
  compared directly.
- Did not need to re-verify the upstream findings (mesh.rotation, Scene.background, autoRotate, Picker.picked,
  OrthographicCamera frustum) -- none are touched by any commit in the update brief's range, and the brief's
  focus list for this guide was specifically #405 and #437/camera(), both covered above.

## Bugs found (2026-11-11)

None new. #405 (the model leak) is confirmed fixed, closing out this guide's own "Bugs and surprises found"
item 2. No regressions found elsewhere in this guide's claims.

## Judgment calls

- **Caught myself almost shipping `guide.md` and `examples/01_quickstart.py` out of sync.** I edited the quick
  start's inline comment in `guide.md` first, then separately in the example file, and initially used
  different wording in each. Added a script-diff check (extract every ` ```python ` block followed by its
  `[examples/...]` link, compare byte-for-byte against the referenced file) before finishing -- all 12 code
  blocks in this guide matched after fixing the one divergence. Worth doing on every guide touched this pass,
  not just ones with an obvious edit.

## Update 2026-11-11 (Task 8c: Large data section)

Added `## Large data` after "Coordinating multiple views." pythreejs has no large-data mode of its own (every
scene object is a separate synced ipywidget, so cost scales with object count); the section says so and points
to k3d/ipyvolume for point-cloud/volume scale, which is already how this guide's own intro frames the choice
between the three. No new example or measurement needed. Links forward to the not-yet-written
`../articles/performance/article.md#three-approaches-to-large-data` (Task 7, same wave) -- expected
`check_docs.py` anchor warning.
