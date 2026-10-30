"""
Accessors for `render_ipydatagrid`.

The grid syncs its selection rectangles to the `selections` trait, and reports
cell clicks/edits through the `on_cell_click`/`on_cell_change` callback
dispatchers. The displayed row map lives in the (upstream-internal)
`_visible_rows` trait, which `visible_data()` observes as its invalidation
trigger (the frame itself comes from `get_visible_data()` at read time).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from ipydatagrid import DataGrid


def attach_selections(widget: DataGrid, emit: Emit) -> Callable[[], None]:
    def on_change(change: dict[str, object]) -> None:
        emit(change["new"])

    widget.observe(on_change, "selections")
    emit(widget.selections)
    return lambda: widget.unobserve(on_change, "selections")


def attach_cell_clicked(widget: DataGrid, emit: Emit) -> Callable[[], None]:
    widget.on_cell_click(emit)
    return lambda: widget.on_cell_click(emit, remove=True)


def attach_cell_edited(widget: DataGrid, emit: Emit) -> Callable[[], None]:
    widget.on_cell_change(emit)
    return lambda: widget.on_cell_change(emit, remove=True)


SELECTIONS = AccessorSpec(
    name="selections",
    kind="state",
    attach=attach_selections,
)

CELL_CLICKED = AccessorSpec(
    name="cell_clicked",
    kind="event",
    attach=attach_cell_clicked,
)

CELL_EDITED = AccessorSpec(
    name="cell_edited",
    kind="event",
    attach=attach_cell_edited,
)


def attach_visible_rows(widget: DataGrid, emit: Emit) -> Callable[[], None]:
    # `_visible_rows` is upstream-internal (like `_predicate` in
    # embedding-atlas); fail loudly if ipydatagrid removes it rather than
    # silently stop invalidating `visible_data()` readers
    if getattr(widget, "_visible_rows", None) is None:
        raise TypeError(
            "`visible_data()` relies on ipydatagrid's (upstream-internal) "
            "`_visible_rows` trait, which this version of ipydatagrid doesn't "
            "have. If ipydatagrid renamed or removed this trait, please report it."
        )

    def on_change(change: dict[str, object]) -> None:
        emit(change["new"])

    widget.observe(on_change, "_visible_rows")
    emit(widget._visible_rows)
    return lambda: widget.unobserve(on_change, "_visible_rows")


# The observed value is only an invalidation trigger; the method reads the
# frame from the widget at read time (no frame per browser message)
VISIBLE_ROWS = AccessorSpec(
    name="visible_data",
    kind="state",
    attach=attach_visible_rows,
)

IPYDATAGRID_ACCESSORS = (SELECTIONS, CELL_CLICKED, CELL_EDITED, VISIBLE_ROWS)
