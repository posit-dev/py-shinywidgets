"""
Accessors for `render_rerun`, backed by rerun's raw event stream.

Both hooks used here are private rerun APIs, pinned by
tests/unit/test_rerun_accessors.py so an upstream rerun update fails loudly:
`rerun_notebook.Viewer._on_raw_event` (whose lack of a remove API is why the
detach is a no-op) and `rerun.notebook._viewer_event_from_json_str` (the raw
JSON event parser).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    # rerun requires Python 3.11+, so it's absent from 3.10 environments
    if sys.version_info >= (3, 11):
        from rerun_notebook import Viewer as RerunNotebookViewer
    else:
        from ipywidgets import Widget as RerunNotebookViewer


def attach_selection(widget: RerunNotebookViewer, emit: Emit) -> Callable[[], None]:
    # The viewer sends an empty (items: []) selection once when it loads.
    # Emitting it would clobber a selection kept across a re-render (the new
    # viewer's load message arrives ~1s after the re-render), and it carries
    # no information -- the slot already starts out None/empty. Only the
    # *first* empty event per attach is the seed; a later empty event is a
    # real deselection. The seed always precedes any user interaction.
    seed_pending = True

    def on_raw(json_str: str) -> None:
        nonlocal seed_pending
        # The raw stream includes high-frequency time_update events (every
        # timeline tick during playback), so filter on the JSON string before
        # parsing
        if '"selection_change"' not in json_str:
            return
        # Private API, pinned by tests (see the module docstring)
        from rerun.notebook import (
            SelectionChangeEvent,
            _viewer_event_from_json_str,  # pyright: ignore[reportPrivateImportUsage]
        )

        event = _viewer_event_from_json_str(json_str)
        # The substring prefilter can false-positive (e.g., an application_id
        # of "selection_change"); only the parsed event's type decides
        if isinstance(event, SelectionChangeEvent):
            is_seed = seed_pending
            seed_pending = False
            if is_seed and not event.items:
                return
            emit(event)

    # Private API, pinned by tests (see the module docstring)
    widget._on_raw_event(on_raw)

    def detach() -> None:
        # rerun's _on_raw_event has no remove API (upstream TODO). The
        # helper's generation guard drops stale callbacks on re-render, and
        # stacked no-op callbacks on a cached widget are the accepted cost.
        pass

    return detach


SELECTION = AccessorSpec(name="selection", kind="state", attach=attach_selection)
