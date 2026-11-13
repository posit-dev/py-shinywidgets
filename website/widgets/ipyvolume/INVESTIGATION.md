# Investigation: `Scatter.selected` corrupts the figure (NOTES.md bug #3)

Ran against `shinywidgets` main @ `00f90249`, shared `main-wt` worktree, Python 3.12,
ipyvolume 0.6.3, ipywidgets 8.1.9, shiny 1.9.0. Verified with real Shiny apps driven by
headless Chromium (Playwright, `--use-gl=swiftshader --enable-unsafe-swiftshader`), reading
browser console output and screenshots, not by reasoning alone. Probe apps/screenshots are in
the scratchpad (`scratchpad/ipv_probe/`), not added to the repo.

## Root cause: upstream ipyvolume bug, triggered by an **empty** `selected` array, not by timing

**NOTES.md's working hypothesis ("any effect that runs in a later reactive tick than the
widget's first render") is wrong.** The real trigger is assigning `selected = []` (or any
empty sequence) at all, regardless of when. A later-tick effect assigning a *non-empty*
`selected` works fine; a same-tick/construction-time assignment of an *empty* `selected`
breaks exactly the same way. I confirmed this head-to-head with four minimal probes:

| Probe | When | Value | Result |
|---|---|---|---|
| `app_nonempty_bare.py` | same tick (untied effect, no deps) | `[0]` (non-empty) | **works** — canvas renders, no errors |
| `app_later_tick_nonempty.py` | later tick (button click) | `[0]` (non-empty) | **works** — no errors, canvas intact after the click |
| `app_empty_bare.py` | same tick / construction (untied effect) | `[]` (empty) | **breaks** — `Could not create a view for model id ...` |
| `app_later_tick_empty.py` | later tick (button click) | `[]` (empty) | **breaks** — `Error setting state: Cannot read properties of undefined (reading 'forEach')`, exactly the error NOTES.md reported. A subsequent orbit-drag (forcing a WebGL redraw) then shows the canvas with axes but **zero points** — the "blank figure" NOTES.md described; the stale frame just isn't redrawn until the next interaction. |

This conclusively isolates the variable: **empty vs. non-empty**, not "which tick." NOTES.md's
"later tick" tests happened to all use an empty/no-op selection (`[]` or a `cell_selection()`
result that was empty), while its one "works" test happened to use a non-empty selection —
a confound, not the real mechanism.

### Where it lives (browser-side, upstream ipyvolume JS, not shinywidgets)

Evidence trail from the exact console error down to the line:

1. `WidgetModel.set_state()` (`@jupyter-widgets/base`, vendored into shinywidgets'
   `shinywidgets/static/libembed-amd.js`) wraps `this.set(state)` in a try/catch and logs
   `` `Error setting state: ${e.message}` `` — this is the *only* part of the error that touches
   shinywidgets' vendored bundle (`node_modules/@jupyter-widgets/base/lib/widget.js:256-267`
   in the shinywidgets `js/` build). It does not construct or validate the state; it only
   reports whatever exception bubbles up from `this.set(state)`, which runs ipyvolume's own
   registered model/view change handlers synchronously (Backbone-style).
2. The actual throw is in ipyvolume's own bundled frontend,
   `.venv/share/jupyter/nbextensions/ipyvolume/index.js` (same file ships at
   `.venv/share/jupyter/labextensions/ipyvolume/static/*.js` for JupyterLab) — minified, no
   source map shipped in the wheel, but matching ipyvolume's compiled
   `ipyvolume/js/src/scatter.ts` `ScatterView` class by its variable names
   (`size_selected`/`color_selected`/`sequence_index`). Not anything shinywidgets authored —
   `grep -c "array_or_json\|_get_value" shinywidgets/static/libembed-amd.js` returns `0`, so
   none of this logic exists in shinywidgets' own bundle. The call chain inside that file, on a
   `change:selected` event:
   - `ScatterView.update_()` → `create_mesh()` → `this.get_next("selected", seq_idx, [])` →
     `_get_value(e, t, n)`:
     ```js
     _get_value(e,t,n){return e?o.isArray(e)&&!o.isNumber(e[0])?e[t%e.length]:e:n}
     ```
     For `selected = []`, the **deserialized** value `e` is `[]` — an empty JS array, which is
     **truthy** — so the function takes the truthy branch instead of returning the default `n`.
     It then does `e[t % e.length]`. Since `e.length === 0`, `t % 0` is `NaN` in JS, and
     `e[NaN]` is `undefined`. So `_get_value` returns `undefined` instead of `[]`.
   - That `undefined` flows into `ScatterAttributes.select(e)`:
     ```js
     select(e){ ...; e.forEach((e,o)=>{ ... }) }
     ```
     `undefined.forEach` throws **`Cannot read properties of undefined (reading 'forEach')`**
     — the exact reported message.
3. The Python side feeds this: `selected` is a `traitlets.Array` trait synced via ipyvolume's
   own `array_sequence_serialization`
   (`.venv/lib/python3.12/site-packages/ipyvolume/widgets.py:86`,
   `.venv/lib/python3.12/site-packages/ipyvolume/serialize.py:237-265,356`). For a non-empty
   array, `array_sequence_to_binary_or_json()` returns `[array_to_binary(ar)]` — a one-element
   list wrapping a binary buffer. For an **empty** array it falls into the `dimension == 0`
   branch (indexing `ar[0]` raises immediately) and returns the bare literal `[]` with no
   buffer at all. Nothing wrong here — this is reasonable and expected serialization — but it
   is exactly what produces the `e.length === 0` input that trips the frontend's
   truthy-empty-array bug above. This part is identical in plain Jupyter; nothing here is
   shinywidgets-specific.

### Why "during render" vs. "later tick" looked relevant but wasn't

When `selected=[]` ends up in the model's *very first* full state (e.g. an untied effect that
happens to run before the comm ever opens, or `selected=` passed at construction), the
exception is thrown inside the view's *initial* `render()`/`create_mesh()` call instead of a
later `set_state()` call, which a different piece of generic `@jupyter-widgets/base` code
(`create_view`'s promise chain, `manager-base.js`) catches and logs as
`Could not create a view for model id ...` instead. Same root cause, different wrapper —
confirmed directly (`app_empty_bare.py`'s probe hit this exact message). This is what NOTES.md
separately flagged as a "different symptom" for construction-time `selected=`; it's the same
bug, not a second bug.

## Attribution

**Upstream ipyvolume bug**, not shinywidgets, and not a shinywidgets usage error. Every file
in the reproduction chain above through the point of the throw is either ipyvolume's own
Python serializer or ipyvolume's own bundled frontend JS; shinywidgets' vendored
`libembed-amd.js` only logs whatever exception bubbles up to it (contains zero occurrences of
the implicated `array_or_json`/`_get_value`/`select` identifiers). I did not additionally spin
up a plain-Jupyter kernel to re-confirm live (time budget), but this isn't needed for
attribution: the exact same compiled `ipyvolume/index.js` bundle ships inside the `ipyvolume`
PyPI package and is loaded by *any* frontend (classic notebook, JupyterLab, or shinywidgets'
require.js loader) — nothing about *how* the `change:selected` event reaches the model
(Shiny custom message vs. a real Jupyter comm) affects this purely client-side arithmetic bug.

### Minimal upstream repro (for a GitHub issue)

```python
import ipyvolume as ipv
import numpy as np

ipv.figure()
s = ipv.scatter(*np.random.random((3, 50)), size=3, marker="sphere")
ipv.show()
# In a running kernel, after the widget has displayed once:
s.selected = []  # the moment *any* comm_msg/state update carries this, the view throws
```
Any context that evaluates `s.selected = []` after the view is already live (so it goes
through `set_state`/`_handle_comm_msg`, or even through the view's own initial `render()`
if set before first display) reproduces it — a Shiny app isn't required, just a live frontend
view of a `Scatter`.

## Severity in normal use

**High for the one pattern it blocks (`selected`-driven highlight from a reactive data
source), but narrow and avoidable.** It only fires when `selected` is set to something that
serializes as an empty sequence — which is exactly the common "no selection yet" / "selection
cleared" state that any table-click-driven highlight needs to support. It does **not** affect:
- any non-empty `selected` assignment (works regardless of timing — confirmed above);
- `color`/`size` array updates (the workaround already used in
  `examples/11_table_selection_highlight.py`);
- any other ipyvolume widget feature untouched by this trait.

ipyvolume (last meaningful release 2021, essentially unmaintained) is unlikely to ship a fix;
this needs to be worked around at the call-site, not patched in shinywidgets.

## Recommendation

**Don't change shinywidgets code for this.** The bug is 100% in ipyvolume's own vendored,
minified, unmaintained frontend bundle — shinywidgets has no supported hook to patch another
package's compiled JS at runtime, and doing so would be exactly the kind of fragile,
high-maintenance fix the project should avoid for a third-party, likely-abandoned dependency.

For the guide:
1. Keep (or lightly rephrase) `examples/11_table_selection_highlight.py`'s existing workaround
   — baking the highlight into plain `color`/`size` arrays — as the primary recommendation.
   It sidesteps the bug entirely and was already verified working.
2. **Correct NOTES.md's root-cause framing** before publishing anything derived from it: the
   trigger is "`selected` set to an empty sequence," not "a later reactive tick." If the guide
   or its Gotchas section repeats the "later tick" framing anywhere, fix it to avoid teaching
   readers an incorrect mental model (e.g. that wrapping in `reactive.isolate()` or changing
   effect priority would help — it would not).
3. Optional, low-cost addition if the maintainer wants to keep using ipyvolume's native
   `selected`/`color_selected`/`size_selected` highlight mechanism instead of the color/size
   workaround: use an out-of-range sentinel index (e.g. `[len(x)]`) instead of `[]` to mean "no
   selection." Verified working in `scratchpad/ipv_probe/app_sentinel_workaround.py`: select →
   clear (via the sentinel) → orbit-drag produced zero console errors and the full point cloud
   stayed visible throughout. This is purely a usage pattern for guide text, not a code change.
4. Worth filing a short upstream GitHub issue against `maartenbreddels/ipyvolume` with the
   minimal repro above, mostly for the paper trail (low odds of a fix on a dormant repo, same
   as bug #1 in NOTES.md).

No shinywidgets branch was created — there is no shinywidgets code to change here.

## Probe code

Left in the scratchpad only, not committed:
`scratchpad/ipv_probe/` in the shared worktree's scratch directory — `app_empty_bare.py`,
`app_nonempty_bare.py`, `app_later_tick_nonempty.py`, `app_later_tick_empty.py`,
`app_sentinel_workaround.py`, plus the Playwright drivers (`check.py`, `check_click.py`,
`check_click_drag.py`, `check_sentinel.py`) and their screenshots.
