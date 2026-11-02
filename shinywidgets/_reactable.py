"""
Accessors for `render_reactable`, backed by shinywidgets' reactable state bridge.

reactable-py's widget never calls `model.send()` itself, but its JavaScript
bundle exports R reactable's state API (`getState`/`onStateChange`), keyed by
the table's `elementId` prop (which `render_reactable` defaults to a unique
value when the user didn't set one). When an accessor attaches, the bridge in
`js/src/reactable.ts` subscribes to that API and forwards a pruned table state
(page, sort, filters, search, selection) as custom messages, so nothing is
subscribed and no traffic flows until an accessor is read.
"""

from __future__ import annotations

from typing import Any, Callable

from ._accessors import AccessorSpec, Attach, Emit
from ._comm import when_comm_open

# Sent when an accessor attaches; the JS bridge binds once per model.
BIND_MESSAGE = {"shinywidgets": "bind-reactable"}


def unreported(raw: object) -> bool:
    """No state has arrived from the browser yet (it seeds right after binding)."""
    return raw is None


_USE_NATIVE = object()


def state_attach(key: str, none_as: object = _USE_NATIVE) -> Attach:
    """
    Attach for one slice of the table state.

    The bridge always reports the full pruned state, so every accessor shares
    a single subscription; each emits only its `key` slice. `none_as`
    replaces a null value (an accessor must never emit None: the helper
    reads that as "not reported yet"), e.g. the empty search box reports
    "".
    """

    def attach(widget: Any, emit: Emit) -> Callable[[], None]:
        # ipywidgets swallows exceptions raised here, so this must not raise.
        def on_msg(_widget: object, content: object, _buffers: object) -> None:
            if (
                not isinstance(content, dict)
                or content.get("shinywidgets") != "reactable-state"
            ):
                return
            state = content.get("state")
            if isinstance(state, dict) and key in state:
                value = state[key]
                if value is None and none_as is not _USE_NATIVE:
                    value = none_as
                emit(value)

        widget.on_msg(on_msg)
        # Idempotent on the JS side, so several accessors may each send it.
        # The send must wait for the widget's comm: a widget built during a
        # render only gets its real comm after the render's flush, and until
        # then sends are silently dropped (e.g. on every re-render, where the
        # helper re-attaches during _render()).
        when_comm_open(widget, lambda: widget.send(dict(BIND_MESSAGE)))
        return lambda: widget.on_msg(on_msg, remove=True)

    return attach


SELECTED_ROWS = AccessorSpec(
    name="selected_rows",
    kind="state",
    attach=state_attach("selected"),
    not_ready=unreported,
)
PAGE = AccessorSpec(
    name="page",
    kind="state",
    attach=state_attach("page"),
    not_ready=unreported,
)
SORTED = AccessorSpec(
    name="sorted",
    kind="state",
    attach=state_attach("sorted"),
    not_ready=unreported,
)
FILTERED = AccessorSpec(
    name="filtered",
    kind="state",
    attach=state_attach("filters"),
    rate_policy="debounce",
    not_ready=unreported,
)
SEARCH = AccessorSpec(
    name="search",
    kind="state",
    attach=state_attach("searchValue", none_as=""),
    rate_policy="debounce",
    not_ready=unreported,
)

REACTABLE_ACCESSORS = (SELECTED_ROWS, PAGE, SORTED, FILTERED, SEARCH)
