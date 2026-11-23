# Updating a widget in place

## Overview

A render function that reads a changed input re-runs and returns a brand
new widget: new zoom, new selection, another full copy of the JS bundle.
When the change is naturally "update this one thing" (recolor a trace,
toggle a layer, scrub a frame), mutate the *existing* widget from a
`@reactive.effect` instead — don't make the render function depend on the
input just to force a rebuild. Only the changed trait crosses the wire, and
everything else (camera, zoom, pan, other in-progress selections) stays
exactly where the user left it. Measured cost: a plotly marker-color update
is 36.3 KB in place vs. 5.45 MB on re-render (146x); lonboard is 141.8 KB vs.
6.19 MB (43x) — see `performance.md`.

## Writing back

```python
from ipyleaflet import Map, Marker
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

clicks = reactive.value(0)

ui.page_opts(title="Writing back", fillable=True)


@render_ipyleaflet
def map():
    return Map(center=(45.5, -122.6), zoom=9)


@reactive.effect
def _add_marker():
    pt = map.clicked()
    if pt is None:
        return
    lat, lng = pt["coordinates"]
    map.widget.add(Marker(location=(lat, lng), draggable=False))
    with reactive.isolate():
        clicks.set(clicks() + 1)  # see "The isolate() trap" below
```

The same `Map` instance keeps running in the browser, so pan/zoom the user
already made survives every marker added.

## The `isolate()` trap

**Skip `reactive.isolate()` around a read-then-write of the same reactive
value inside an effect, and the app silently hangs — no error, no visible
sign anything is wrong.** `clicks.set(clicks() + 1)` first *reads* `clicks()`
(making the effect depend on it), then sets it (invalidating every reader of
it, including this same effect). The effect reschedules, reads `clicks()`
again, sets it again, forever: a tight loop that pins a CPU core. The rule:
**any time an effect reads and writes its own reactive state (a counter, an
accumulator, anything shaped like `x.set(x() + ...)`), wrap the read in
`reactive.isolate()`.**

## What each widget calls in-place

Every renderer exposes a read-only `.widget` (or `.value`) once rendered —
the live object the browser already shows. What's worth mutating is
different per library; the widget reference's "Updating in place" section
has the verified call. A few widgets have **no** in-place path at all
(pygwalker, embedding-atlas, pyvista, ipysigma) — their browser code never
listens for Python-driven trait changes, or has nothing left to mutate once
rendered, so re-rendering is the only option; the widget reference says what
state (if any) is worth carrying forward to soften the reset.

## When in-place doesn't save bytes

Not every trait write is cheap. On an 819 KB GeoJSON choropleth, toggling
ipyleaflet's `layer.visible` costs 444 bytes, but setting `layer.style` costs
1.09 MB — almost exactly what a full re-render costs, because ipyleaflet's
`GeoJSON` rebuilds its entire `data` trait from scratch whenever `style`
changes. "In-place" means "only the changed trait crosses the wire" only
when the trait you're setting is actually small on the wire — verify before
assuming it's automatically the cheap path.

## Lifetimes

A widget built directly inside a render function lives exactly as long as
that render — the next run closes the old widget and builds a new one. Two
other lifetimes exist:

- **`session_lifetime()`** — build the widget once per session, cache it
  (typically in a `@reactive.calc`), and keep returning that same instance.
  Use this when a render would otherwise rebuild a widget the user is
  actively interacting with.
- **`shared_lifetime()`** (experimental) — build the widget once for the
  whole *process*, before any session connects, and show it to every
  session. Every user sees, and can change, the same object; it is never
  freed, and reading an accessor on it reports whichever session's gesture
  arrived most recently — not scoped to the reading session. Don't use it
  for state that should mean something different per user.

Caching in a `@reactive.calc` alone isn't enough: a widget the calc builds is owned by whichever render
first called it. If that render re-runs for a reason the calc doesn't share (e.g. it also reads another
input), its re-run closes the widgets it built last time, including the one the calc cached — so the calc
hands back an already-closed widget, raising `... was closed (its render was invalidated, or it was closed
explicitly), so it can't be displayed again...`. Build the widget inside `with session_lifetime():` (below)
to decouple it.

```python
from shiny import reactive
from shinywidgets import render_ipyleaflet, session_lifetime


@reactive.calc
def cached_map_calc():
    with session_lifetime():
        return Map(center=(45.5, -122.6), zoom=9)


@render_ipyleaflet
def cached_map():
    return cached_map_calc()
```

**`shared_lifetime()` and Shiny Express**: Express re-runs an app file's
entire top-level body for every new session. `with shared_lifetime():
THE_MAP = Map(...)` directly in the Express script gets rebuilt — and
re-shown as a fresh, independent map — on every session; it never actually
shares. Put the shared widget in a sibling `globals.py` that Express imports
before any session connects instead:

```python
# globals.py
from ipyleaflet import Map
from shinywidgets import shared_lifetime

with shared_lifetime():
    THE_SHARED_MAP = Map(center=(48.85, 2.35), zoom=11)
```

`globals.py` can run more than once before the first session connects (once
while Express builds the static UI, again per session's module import), so
write idempotent setup there — anything that must happen exactly once (a
lock, an unsettable flag) needs its own guard. Also keep a
`shared_lifetime()` cache module in its own directory: Express auto-imports
a directory's `globals.py` before running *any* app file in that directory,
so every app there *constructs* the shared widget in the process (memory
and startup cost), even apps that never display it. Delivery itself is
lazy — a session is only *sent* a shared widget it displays or references,
except for eagerly-shared packages (`ipyvue`, `ipyvuetify`, `nglview`),
which open at session start
([#461](https://github.com/posit-dev/py-shinywidgets/issues/461)).

## Common mistakes

- Making a render function read `input.*()` just to recolor/restyle — write
  to `.widget` from an effect instead.
- Forgetting `reactive.isolate()` around a counter/accumulator update inside
  the same effect that triggered it — causes a silent infinite loop, not an
  error.
- Assuming every in-place trait write is cheap — some (a style trait that
  rebuilds a whole GeoJSON `data` trait) cost as much as a re-render.
- Building a `shared_lifetime()` widget directly in an Express script instead
  of a sibling `globals.py` — it silently stops being shared.

**More:** <https://shinywidgets.org/guide/updating-in-place/>
