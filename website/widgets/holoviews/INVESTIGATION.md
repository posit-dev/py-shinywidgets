# Root-cause investigation: `render_holoviews` bugs #1, #2, #4

Scope: the three bugs the docs-writing agent flagged in `NOTES.md` ("Bugs found" items 1,
2, 4), plus a look at whether #3 (Tap + link_selections) shares a cause. Versions matched
`NOTES.md`: shiny 1.9.0, holoviews 1.23.2, hvplot 0.12.2, panel 1.10.0, bokeh 3.10.1,
jupyter_bokeh 4.1.0, shinywidgets worktree at `00f90249`.

Headline for the release decision: **none of these are release blockers.** #1 and #2 did
not reproduce once the test methodology was corrected (see below) -- they look like a
false positive in the original investigation, not a real regression. #4 is real and
root-caused; a follow-up investigation (see the correction note in the #4 section)
refuted the detached-asyncio-task mechanism first proposed here, pinned the real
(synchronous, in-render) mechanism, and landed a shinywidgets code fix. The
documentation advice from the original investigation still stands as good practice.

## Bug #1 and #2: did not reproduce -- likely a test-harness artifact, not a real bug

**Claim in NOTES.md:** `ui.sidebar()` (#1) or a second unrelated `@render_holoviews` output
(#2) silently breaks `hv.link_selections` box-select on another output, verified via the
server-side `reactive.Value`.

**What I did:** ran the exact repro files
(`repros/sidebar_breaks_linksel_repro.py`, `repros/two_widgets_breaks_linksel_repro.py`)
under Shiny with a real Playwright-driven mouse drag (box-select tool clicked, then
`mouse.down/move/up`), reading the result from a `hv.link_selections.instance().param.watch`
callback and/or the exposed `reactive.Value` -- not a screenshot. Also rebuilt the fuller
3-panel `gallery/showcase_tips_explorer.py` with its sidebar restored (it currently avoids
the sidebar specifically because of this bug) to match the richer app where the bug was
first seen, and reran it with and without the sidebar.

**Result:** selection fired correctly and `selection_expr`/the watched reactive value
changed in every run:
- `two_widgets_breaks_linksel_repro.py`: 10/10 sequential sessions correctly computed a
  real `selection_expr` (e.g. `(dim('x')>=-2.629)&(dim('x')<=1.342)`), with a second,
  unrelated `@render_holoviews` output present the whole time.
- `sidebar_breaks_linksel_repro.py`: selection fired correctly, both as given and with an
  added re-render trigger (a checkbox in the sidebar that forces `charts()` to re-execute
  2 more times before selecting) -- ruling out the "re-render invalidates the stream"
  hypothesis from the task brief as well.
- `showcase_tips_explorer.py` with the sidebar restored: box-select correctly took
  "Rows selected" from 244/244 to 216/244, identically to the no-sidebar baseline.

**Why the original investigation likely got a false positive:** my first attempt at this
also "failed" -- using a box-select drag from roughly 20% to 80% of the plot area. For
`plotly.express.data.tips()` (a right-skewed, fairly dense scatter), that region excludes
almost no points, so "Rows selected: 244 of 244" **before and after** looks identical to
"the callback never fired," even though box-select is working correctly. Tightening the
drag region to a corner that visibly excludes points (and rechecking) gave a real, changed
count both with and without the sidebar. Reading a real `selection_expr` value (not just
"did the value change") is what caught this -- NOTES.md's own methodology was right in
principle, but I believe the specific drag geometry used produced a selection box that
didn't meaningfully subset the data, making a working callback look broken. I could not
find any code path in shinywidgets, panel, or holoviews that treats `ui.sidebar()` or a
second `@render_holoviews` output specially, which is consistent with this being a
methodology issue rather than a real defect.

**Classification:** not a bug (unconfirmed / likely false positive). **Severity:** none.
**Recommendation:** downgrade from the guide's gotchas list; don't block the release on
this. If it resurfaces, get a reproduction that checks a drag region which visibly and
substantially subsets the plotted data, and watch for the same false-positive shape.

I did not chase bug #3 (`Tap` + `link_selections` on the same element never fires) further:
since #1/#2 turned out not to share a confirmed mechanism, there's nothing to extend to #3,
and I didn't have the budget to independently re-verify it with a corrected methodology.
It's plausible #3 is a real, narrower holoviews wiring quirk (tap attached to the original
element vs. the possibly-transformed element `link_selections()` returns) -- worth a quick,
careful re-check with a real tap coordinate and the same "does the server-side value
actually change" discipline, but I can't say more without doing that work.

## Bug #4: `hv.streams.RangeXY` causes a real, confirmed infinite re-render loop

> **Correction (follow-up investigation, superseding the mechanism below).** The
> detached-`asyncio.create_task` mechanism proposed in this section was **refuted as the
> cause**. Instrumented live runs show the subscriber firing **synchronously, inside the
> render's own live reactive Context**, with no asyncio task involved: every `plot()`
> render builds a new `RangeXY`, and holoviews' `get_plot()` calls `Stream.trigger()`
> synchronously (`renderer.py:314`), so the subscriber runs mid-render. Its reactive
> **read** registers the render's Context as a dependent; its **write** then invalidates
> the render in progress, the re-render fires the trigger again, and the ever-changing
> counter sustains the loop (55 renders / 55 `BokehModel was closed` errors in 6s). The
> browser-event dispatch path never mattered: shinywidgets' dispatch effect is
> `@reactive.event`-wrapped, which already isolates it.
>
> Also **did not reproduce**: this section's claim that a write-only subscriber
> (`unread.set(n+1)`, no read) still loops. Re-tested live, a write-only subscriber
> renders exactly once -- consistent with the corrected mechanism (the subscriber's own
> read is what pollutes; a read+write like `v.set(v()+1)` on an otherwise-unread value
> does loop).
>
> **Fix (landed in shinywidgets):** `render_widget_base._render` now runs both
> `_as_widget()` coercion and `set_layout_defaults()` under `reactive.isolate()` (the
> same pattern `_as_widget.py` already used for ipympl coercion), so callbacks fired by
> third-party code during coercion can no longer register dependencies on the render.
> Verified: 55 renders/55 errors -> 1 render/0 errors, full unit suite green, plus a
> unit regression test (`tests/unit/test_panel_lifecycle.py`). The documentation advice
> below (store the idempotent range tuple; avoid counter subscribers) remains good
> practice regardless of the fix.
>
> The original (refuted) analysis is kept below for the record.

**Confirmed real** (166+ `RuntimeError: BokehModel was closed...` in ~4s of server log on
page load, zero interaction) and **root-caused**, via `rangexy_render_loop_repro.py` plus a
series of controlled variants (all built in the scratchpad, not committed).

**Mechanism, in order (REFUTED -- see the correction note above; kept for the record):**

1. `shinywidgets/_as_widget.py:1014`, `panel_to_widget()`: every `@render_holoviews` render
   builds a brand-new, bare `bokeh.document.Document()` (`document = Document()`) that is
   never attached to a real bokeh server session. `document.session_context` is `None` for
   it, always (verified directly: `Document().session_context -> None`).
2. HoloViews dispatches a browser-originated bokeh event (e.g. a box's current pan/zoom
   range) back to Python via
   `holoviews/plotting/bokeh/callbacks.py:425-430` (`Callback._schedule_event`):
   ```python
   if self.plot.comm or not self.plot.document.session_context or state._is_pyodide:
       task = asyncio.create_task(self.on_event(event))
   else:
       self.plot.document.add_next_tick_callback(partial(self.on_event, event))
   ```
   Because the document's `session_context` is always `None` in shinywidgets, this
   condition is always true, so every stream callback runs as a detached
   `asyncio.create_task(...)` rather than through `document.add_next_tick_callback`. This
   is true for every stream type, not just `RangeXY` -- it's just that `RangeXY` is the one
   whose Bokeh JS reports its value **immediately on mount, with no user action**, so it's
   the one that can self-sustain a loop.
3. Isolated with controlled variants of the repro (same file, only the subscriber body
   changed), all run via a single Playwright page load:
   - Subscriber does nothing reactive (just logs): `plot()` renders once, `on_range` fires
     once, no loop.
   - Subscriber does `some_unread_reactive_value.set(n + 1)` (a value nothing reads):
     `plot()` still renders ~168 times in a runaway loop.
   - The same kind of reactive write, but triggered from a normal Shiny input handler
     (`@reactive.effect @reactive.event(input.bump)` wired to a button click) instead of
     from the stream's async task: the **unrelated** `@render_holoviews` output does **not**
     re-render (count stays at 1).
   - Subscriber stores the actual, naturally-unchanging value instead of a counter
     (`range_val.set((x_range, y_range))`): `plot()` renders exactly once. Shiny's
     `reactive.Value.set()` already skips invalidation when the new value equals the old
     one, and the range truly is identical on every mount absent user interaction, so this
     alone breaks the cycle.

   This isolates the trigger precisely: a reactive write performed by code running on a
   loose `asyncio.create_task()` that HoloViews spawned (not through Shiny's own
   request/flush scheduling) appears to over-invalidate and re-run the *same*
   `@render_holoviews` output that has no actual dependency on the written value, whereas
   an identical write driven through Shiny's normal input-handling path does not. I was not
   able to pin down, inside shiny's reactive core, exactly why an async-task-originated
   write has this broader effect in the time available -- this is as far as I got on that
   specific sub-question. It may be related to the project's existing note on
   `on_flush`/`on_flushed` being self-requesting on shiny >= 1.9 dev builds, but I did not
   confirm that link.

**Classification:** sits at the shinywidgets/holoviews/shiny boundary. shinywidgets'
choice of a bare, session-context-less `Document()` is necessary for its jupyter_bokeh
based architecture (it isn't a real bokeh server), but it's what pushes HoloViews down the
"detached asyncio task" branch for every callback; HoloViews' choice of that branch
(reasonable for actual Jupyter use) is what exposes the loop when combined with a stream
that self-reports on mount and a naive, ever-changing subscriber.

**Severity:** real, but narrow and easily avoided once documented. It only bites users who
(a) use `RangeXY` (not `BoundsXY`/`Tap`, which only fire on user gestures) and (b) write an
ever-different value (like a counter) in the subscriber instead of the stream's own value.
`RangeXY`'s only real use case in this guide is "read the current zoom/pan range," which
naturally wants pattern (storing the tuple), not a counter -- so the *correct* usage
pattern for the one thing users would actually do with this stream already avoids the bug.

**Recommended fix (as originally written; superseded).** Documentation only, no
shinywidgets code change: show the idempotent recipe (`range_val.set((x_range, y_range))`,
relying on `reactive.Value`'s built-in equality check) as the only supported pattern for
`RangeXY`, and add a short, explicit warning against accumulator/counter-style
subscribers on auto-firing streams. **Update from the follow-up:** once the real
(synchronous, in-render) mechanism was identified, a small code fix turned out to be both
safe and general -- `reactive.isolate()` around coercion in `render_widget_base._render`,
matching the existing ipympl precedent -- and it landed (see the correction note above).
The docs advice here was kept in the guide as good practice even with the fix in place.

## What I did not do

- Did not open any upstream issues (holoviews/panel/bokeh/jupyter_bokeh) since #1/#2 didn't
  reproduce and #4 has a non-code mitigation. **Update:** a py-shiny tracking issue about
  the broader design question (reactive reads in library-invoked callbacks / detached
  tasks silently registering on unrelated live Contexts) is drafted in
  `PYSHINY-ISSUE-DRAFT.md`, pending maintainer review.
- No branch/commit was created: there is no shinywidgets code change to make here. All
  debugging scripts lived under the scratchpad, not in this repo.
- Bug #3 (Tap + link_selections) was not independently re-verified with a corrected
  methodology; see above.
