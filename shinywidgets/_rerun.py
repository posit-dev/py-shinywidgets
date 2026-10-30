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
    def on_raw(json_str: str) -> None:
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
            emit(event)

    # Private API, pinned by tests (see the module docstring)
    widget._on_raw_event(on_raw)

    def detach() -> None:
        # rerun's _on_raw_event has no remove API (upstream TODO). The
        # helper's generation guard drops stale callbacks on re-render, and
        # stacked no-op callbacks on a cached widget are the accepted cost.
        pass

    return detach


# Eager: the viewer sends an empty (items: []) selection at load, which only
# an attach before the view exists catches -- so selection() reflects "nothing
# selected" soon after mount rather than staying None
SELECTION = AccessorSpec(
    name="selection", kind="event", attach=attach_selection, eager=True
)
