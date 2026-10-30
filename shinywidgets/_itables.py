"""
Accessors for `render_itables`.

itables syncs the selected rows to the widget's `selected_rows` trait (row
positions into the table's data frame), so one state accessor observes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from itables.widget import ITable


def attach_selected_rows(widget: ITable, emit: Emit) -> Callable[[], None]:
    def on_change(change: dict[str, object]) -> None:
        emit(change["new"])

    widget.observe(on_change, "selected_rows")
    emit(widget.selected_rows)
    return lambda: widget.unobserve(on_change, "selected_rows")


SELECTED_ROWS = AccessorSpec(
    name="selected_rows",
    kind="state",
    attach=attach_selected_rows,
)

ITABLES_ACCESSORS = (SELECTED_ROWS,)
