# Investigation: two shinywidgets findings from the k3d guide

Ran against `shinywidgets` main @ `00f90249` (same commit as the guide), in the shared
`main-wt` worktree, Python 3.12, k3d 3.2.0, shiny 1.9.0. All claims below were tested with
real Shiny apps driven by headless Chromium (Playwright), reading server logs and/or DOM
state, not by reasoning alone. Probe apps and logs are in the scratchpad
(`scratchpad/probe2/`) and were not added to the repo.

## Finding 1: a widget method/message called synchronously inside the render function is dropped

**Real, and general — confirmed by direct reproduction and by existing precedent in the
codebase.**

Root cause (`shinywidgets/_shinywidgets.py:220-306`, `shinywidgets/_comm.py:305-334`): when a
widget is constructed, `init_shiny_widget()` immediately assigns it a placeholder
`OrphanedShinyComm` (`_shinywidgets.py:223`), whose `send()` is a no-op
(`_comm.py:319-324`). The real `ShinyComm` is installed later, by a
`@reactive.effect(priority=99999)` named `_open_shiny_comm` that is merely *registered*
during construction (`_shinywidgets.py:242-306`) and only runs on a later turn of the same
reactive flush. Any `widget.send(...)`-based call (custom messages; this includes most
"do something now" widget methods, e.g. k3d's `start_auto_play()`) made before that effect
runs is silently swallowed.

I confirmed the asymmetry directly: in one render function, `scene.time = 0.5` (a plain
trait assignment) and `scene.start_auto_play()` (a custom message) were both issued
synchronously before `return scene`. After load, `reactive_read(widget, "time")` reported
`0.50` immediately (the trait survived, via `get_state()` being captured when the comm
*does* open) and then stayed frozen at `0.50` for 9+ seconds (confirming the animation
never started — the message was dropped). This matches the guide's claim exactly.

This generalizes beyond k3d: `when_comm_open()` (`_comm.py:287-297`) already exists
precisely to work around this, and is used internally by `_plotly.py`, `_reactable.py`, and
`_bokeh_accessors.py` to defer their own startup `widget.send(...)` calls. It is not
exported from `shinywidgets/__init__.py`, so an app author writing their own widget
integration (as the k3d guide does) has no public way to use the same fix and must instead
gate the call behind a later-firing event, as the guide does.

**Correction to the guide's secondary claim:** NOTES.md asserts a bare `@reactive.effect`
(no dependency) "runs too early" but that an effect gated on a real UI input — even one
already at its default value — "reliably runs late enough." I tested both forms head to
head (and in isolation) against a k3d time-keyed plot: in every run, `orbits.widget` was
already non-`None` by the time either effect ran, and in every run **both** the bare effect
and the input-gated effect failed to start the animation (`time` stayed at `0.00`
indefinitely). Only a real, later user interaction (a Playwright click on an actual button,
well after startup) reliably worked — `time` advanced immediately after the click. So the
distinguishing factor is not "bare vs. gated," it's "runs during the initial flush vs. runs
later in response to genuine post-startup interaction." The guide's "input-gated effects are
safe" claim is incorrect as written and should not ship; the button-click pattern it already
uses elsewhere is the right guidance.

**Severity / recommendation:** Real footgun for anyone writing their own widget glue code
(the audience most likely to call `widget.send()`-shaped methods directly), but it is also
the kind of forever-startup-race intermediate shinywidgets already has a working internal
fix for. I'd recommend two independent, low-cost changes, either or both:
1. Export `when_comm_open()` publicly (one line in `__init__.py` plus a docstring pass) so
   app authors have the same escape hatch first-party code already relies on. Low complexity,
   clear user value, no new mechanism to maintain.
2. Fix the guide's incorrect "gate on an already-set input" claim before publishing (trivial
   doc edit, prevents giving users a false sense of safety).
I did not open a branch for #1 since it's optional scope here, but it's a small, well-contained change if you want it done.

## Finding 2: `render.data_frame` patches from a widget `on_msg` callback (e.g. k3d's `click_callback`)

**Could not reproduce. Likely not a real, reliable bug as described; recommend not
publishing the `asyncio.sleep(0)` workaround as shipped guidance.**

I rebuilt the exact scenario the guide describes, twice: (1) an async
`@reactive.effect` reading a `reactive.Value` set from inside `click_callback`, calling
`await table.update_cell_selection(...)` with **no** `asyncio.sleep(0)`; and (2) a plain
`@render.data_frame` function reading that same reactive value directly and returning a
freshly styled `render.DataGrid(df, styles=[...])` (the other code path the guide mentions
hitting the same bug). Both were driven with real mouse down/wait/up gestures on the k3d
canvas (per the guide's own note that picking needs that gesture, not a bare `.click()`),
clicking 6 different points in sequence in each run.

Result: **12/12 clicks correctly updated the browser DOM** (row `aria-selected` or the
yellow `background-color` style landed on the right row every time), with no sleep and no
retries. I also traced the dispatch path to understand why a race was plausible: incoming
client messages are handled by `handle_client_comm_msg()` →
`ShinyComm.handle_msg()`/`dispatch_client_msg()` (`_comm.py:250-273`), invoked from a plain
(non-async) `@reactive.effect` in `init_session()` (`_shinywidgets.py:544-549`), which runs
to completion in the ordinary reactive flush — same mechanism as any other input-driven
effect, not a special or out-of-band context. `update_cell_selection()` itself
(`shiny/render/_data_frame.py:1033-1102`) just awaits `session.send_custom_message()`,
which sends directly over the websocket connection (`shiny/session/_session.py:1731-1745`),
with no batching/gating that depends on *how* the triggering reactive value changed.

I can't rule out a narrower timing window I didn't hit (e.g. a click arriving in the same
millisecond as some other in-flight update), but as described — "fails on every click, not
just the first" — it did not reproduce. My best guess is the original observation was a
one-off flake (e.g., a stale browser state from an earlier failed click attempt, since k3d
picking itself is finicky about gesture shape per the guide's own notes) that got
misattributed to the trigger source, especially since the `camera()`-driven case was
confirmed to still need the same `click_callback`-vs-not comparison, not an independent
clean-room test.

**Recommendation:** Pull the `asyncio.sleep(0)` workaround and the bug write-up from the
published guide (or soften it to "we saw this once and couldn't reproduce it," at the
maintainer's discretion) rather than teaching every reader an unnecessary, confusing
workaround for a bug that isn't demonstrably real. If it resurfaces, a minimal repro with a
server-side log showing the message actually being sent-but-not-landing (vs. not sent at
all) would be the next useful piece of evidence.

## Probe code

Left in the scratchpad only (per instructions), not committed: `scratchpad/probe2/` in the
shared worktree's scratch directory, including `bare_effect.py`/`bare_effect2.py`/
`gated_only.py`/`trait_vs_msg.py` (finding 1) and `14_nosleep.py`/`14_styles.py`/
`click_seq.py` (finding 2).
