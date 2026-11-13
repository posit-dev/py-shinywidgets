# py-shiny tracking issue — DECIDED NOT TO FILE

**Decision (2026): do not post.** Kept here as a record of the investigation.

Reasoning:

- The bug we actually hit (holoviews `Stream.trigger()` firing subscribers
  synchronously during widget coercion inside a `@render_*` render) is fixed
  shinywidgets-side (`fix/holoviews-render-isolate`: `reactive.isolate()` around
  `_as_widget()` + `set_layout_defaults()`). That sync-callback case was never
  fixable in py-shiny anyway — a same-task synchronous read is indistinguishable
  from an ordinary read in the render body; only the dispatching library/adapter
  can isolate.
- For the detached-task case, a behavioral py-shiny fix is *not* sensible:
  contextvars inheritance is **correct** for child tasks an effect/render
  actually awaits (e.g. `asyncio.gather` of reactive-reading coroutines — the
  effect genuinely depends on those reads). Detached vs. awaited is unknowable
  at `create_task()` time, so py-shiny cannot automatically distinguish the bad
  case from the good one.
- The realistic py-shiny outcome would have been documentation only, and
  maintainers may reasonably read the whole thing as "that's how contextvars
  work" — `asyncio.create_task()` copying context is Python semantics, not a
  Shiny defect.
- Repro below verified against shiny 1.9.0 AND py-shiny `main`
  (`bfabcff39`, post-#2549 effects-runner rework); both print the spurious `2`.

The one observation worth remembering if this area comes up again: py-shiny's
own `ExtendedTask` already takes the strong stance — it wraps its body in
`DenialContext` (`shiny/reactive/_extended_task.py`), which **raises** on any
reactive read from the detached task. Raw `asyncio.create_task()` from inside a
reactive context silently mis-registers instead. If a future maintainer revisits
detached-task semantics, that inconsistency is the concrete design question.
Also note: an opt-in "warn on cross-task registration" strict mode would
false-positive on the legitimate awaited-child-task pattern, so it could only
ever be opt-in.

Fallback if the guidance ever proves needed: document the pattern for widget
adapter authors in shinywidgets' own docs ("if your library synchronously fires
user callbacks during widget construction, wrap it in `reactive.isolate()`"),
which doesn't require py-shiny to do anything.

---

## Original draft (not posted)

Below is the issue text as it would have been posted to
[posit-dev/py-shiny](https://github.com/posit-dev/py-shiny/issues).

---

**Title:** Reactive reads inside detached `asyncio` tasks or library-invoked callbacks silently register on whatever Context happens to be live

**Body:**

Shiny tracks the current reactive `Context` in a `ContextVar`
(`ReactiveEnvironment._current_context`). Two common situations leak that Context into
code that has no business depending on it:

1. **Detached tasks.** `asyncio.create_task()` copies the current contextvars context,
   so a task spawned inside a reactive Effect/render inherits its `Context`. Any
   reactive read in the task registers that Context as a dependent
   (`Dependents.register`); a later write invalidates an Effect that has no legitimate
   dependency.
2. **Synchronous third-party callbacks.** When library code synchronously invokes a
   user callback while a Context is active, reads in the callback register on that
   Context. Real-world instance: shinywidgets + holoviews — holoviews' `get_plot()`
   fires `Stream.trigger()` subscribers *synchronously* while shinywidgets is coercing
   the element into a widget inside a `@render_*` render. A subscriber doing
   `count.set(count() + 1)` registered the in-progress render as a dependent of
   `count`, so its own write invalidated the render mid-flight, and the re-render fired
   the trigger again: an infinite re-render loop with no user interaction. (Fixed
   shinywidgets-side by running coercion under `reactive.isolate()`, but the class of
   problem is general.)

**Minimal repro** (pure shiny 1.9.0, no browser, no third-party libs):

```python
import asyncio

from shiny import reactive

val = reactive.value(0)
runs = 0


@reactive.effect
def _():
    global runs
    runs += 1

    async def reader():
        # This read registers the *effect's* Context as a dependent of `val`,
        # even though the effect body never reads `val`.
        val()

    asyncio.create_task(reader())


async def main():
    await reactive.flush()
    await asyncio.sleep(0.1)  # let the detached task run
    assert runs == 1, runs
    val.set(1)  # nothing the effect does depends on val ...
    await reactive.flush()
    print(f"effect runs after unrelated val.set(): {runs} (expected 1)")


asyncio.run(main())
```

Output: `effect runs after unrelated val.set(): 2 (expected 1)` — the effect re-runs
purely because a detached task inherited its Context and read a value the effect itself
never read.

**Design question.** Should a detached task (or any code re-entered by a third-party
library) ever inherit a live reactive Context? Inheritance is almost never intended —
the resulting dependency is invisible to the user, and invalidation re-runs the wrong
thing. Shiny already defends one seam: `@reactive.event` wraps the decorated body in
`with isolate():`, so event handlers can't accidentally register on their own effect's
Context. And `isolate()`'s throwaway-Context semantics (reads allowed, dependencies
discarded) are exactly right for these seams. But today every library adapter and every
app author who spawns a task inside a reactive context must remember to isolate — a
silent failure mode with no warning. Is "everyone must remember to isolate" the
intended steady state, or should shiny offer something stronger — e.g. a documented
pattern/helper for "run this callback outside any reactive context", an opt-in strict
mode that warns when a read registers on a Context from a copied contextvars context,
or simply official guidance that callback-dispatching library adapters must isolate?

---

## Reviewer notes (not part of the issue text)

- Repro verified against shiny 1.9.0 in the shinywidgets dev environment
  (`uv run python` on the script above prints the spurious `2`).
- The original investigation's repro scripts lived in `/tmp/sw-ctx-investigation/scratch/`,
  which has since been deleted; the inline repro above is a faithful reconstruction and
  was re-verified.
- Deliberately left out: the (also real) "write-only callbacks are harmless" nuance and
  the full holoviews stack trace — the draft already links the real-world instance
  compactly; happy to add a collapsible details block if the maintainer prefers.
- Related shinywidgets-side fix: branch `fix/holoviews-render-isolate` (isolate around
  `_as_widget()` + `set_layout_defaults()` in `render_widget_base._render`).
