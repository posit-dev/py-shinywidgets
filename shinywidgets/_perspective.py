"""
Accessors for `render_perspective`, backed by the viewer's config traits
(which the browser syncs back to Python as the user edits the viewer).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from perspective.widget import PerspectiveWidget

# The structural keys of PerspectiveViewer.save(): what determines the rows a
# view produces. Cosmetic keys (settings, theme, title, plugin_config,
# columns_config) are excluded so the settings panel doesn't invalidate.
CONFIG_KEYS = (
    "plugin",
    "columns",
    "group_by",
    "split_by",
    "aggregates",
    "sort",
    "filter",
    "expressions",
)


def attach_filter(widget: PerspectiveWidget, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "filter")
    emit(widget.filter)
    return lambda: widget.unobserve(on_change, "filter")


def attach_view_config(widget: PerspectiveWidget, emit: Emit) -> Callable[[], None]:
    def current() -> Dict[str, Any]:
        return {key: getattr(widget, key) for key in CONFIG_KEYS}

    def on_change(change: Any) -> None:
        emit(current())

    for key in CONFIG_KEYS:
        widget.observe(on_change, key)
    emit(current())

    def detach() -> None:
        for key in CONFIG_KEYS:
            widget.unobserve(on_change, key)

    return detach


FILTER = AccessorSpec(name="filter", kind="state", attach=attach_filter)
VIEW_CONFIG = AccessorSpec(name="view_config", kind="state", attach=attach_view_config)
PERSPECTIVE_ACCESSORS = (FILTER, VIEW_CONFIG)
