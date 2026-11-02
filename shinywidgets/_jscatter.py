"""
Accessors for `render_jscatter`.

jupyter-scatter syncs the selected points to the widget's `selection` trait
(row positions, as a numpy array), both on lasso and on click-select, so one
state accessor observes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from jscatter.widget import JupyterScatter


def attach_selection(widget: JupyterScatter, emit: Emit) -> Callable[[], None]:
    def on_change(change: dict[str, object]) -> None:
        emit(change["new"])

    widget.observe(on_change, "selection")
    emit(widget.selection)
    return lambda: widget.unobserve(on_change, "selection")


def is_unreported(raw: object) -> bool:
    # A bare JupyterScatter's selection is None until the browser first
    # reports (a Scatter's starts as an empty array)
    return raw is None


SELECTION = AccessorSpec(
    name="selection",
    kind="state",
    attach=attach_selection,
    not_ready=is_unreported,
)

JSCATTER_ACCESSORS = (SELECTION,)
