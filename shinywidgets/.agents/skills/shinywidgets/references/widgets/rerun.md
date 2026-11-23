# Rerun (`render_rerun`)

## Overview

`pip install 'shinywidgets[rerun]'` (Python 3.11+ only; on 3.10 the extra
silently installs without rerun-sdk). Stream multimodal, time-indexed data
(3D scenes, images, plots, text logs) from Python into a scrubbable
timeline viewer. Accepts a `rerun.notebook.Viewer` (recommended, coerced
to its inner widget) or a `rerun_notebook.Viewer` directly.

```python
import rerun as rr
from rerun.notebook import Viewer
from shinywidgets import render_rerun


@render_rerun
def viewer():
    recording = rr.RecordingStream("my_app")
    recording.log("points", rr.Points2D([[0, 0], [1, 1]]))
    return Viewer(recording=recording)
```

**Create the `RecordingStream` inside the render function** and pass it as
`Viewer(recording=...)` — rerun's usual `rr.init()` + `rr.log()` pattern
writes to a single process-global recording, which would leak one
session's data into every other session's viewer. **`rr.notebook_show()`
doesn't work in Shiny** — it renders through Jupyter's display machinery
and drains the recording to a one-shot snapshot with no live updates.
Always return a `Viewer` instance instead.

## Accessors

| Accessor | Returns | Before first interaction |
|---|---|---|
| `selected()` | A `SelectionChangeEvent` (`.items`: `EntitySelectionItem`/`ViewSelectionItem`/etc.) | `None` |

The viewer's empty load-time selection is ignored, so a kept selection
survives re-renders (its items then refer to the previous recording); a
later empty report is a real deselection. For play/pause, timeline
scrubbing, and other interactions with no accessor, register a callback
with `Viewer.on_event()` and set a `reactive.Value` inside it — these
interactions reach Python as one-off messages, not synced trait state, so
`reactive_read()` can't see them.

## Updating in place

Log more data to the recording after the render — it streams live to the
browser, no re-render needed. Trait updates on `.widget` (e.g.
`widget._width = 800`) also stream:

```python
from shiny import reactive


@reactive.effect
def _log_more():
    recording.log("points", rr.Points2D(new_points))
```

Keep a reference to the `rerun.notebook.Viewer` wrapper (not just
`.widget`, the low-level widget) if you want to call its methods
(`update_panels()`, `set_time_ctrl()`) from later reactive updates.

## Gotchas

- **`rr.init()`'s default recording is process-global** — use a
  per-session `RecordingStream`, or one session's data leaks into every
  other session's viewer.
- Ships a ~55 MB bundle from rerun's CDN by default (self-hostable: set
  `RERUN_NOTEBOOK_ASSET=serve-local` for local dev or `inline` for remote
  deployments).

**More:** <https://shinywidgets.org/widgets/rerun/>

Written against `rerun-sdk` 0.x.
