"""
Accessors for `render_mosaic_widget`, backed by the widget's `params` trait
(the dashboard's current selection params, which the browser updates as the
user brushes).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    # mosaic-widget is excluded from the 3.15 test/dev envs (duckdb has no
    # cp315 wheels), so pyright can't resolve it there
    from mosaic_widget import MosaicWidget  # pyright: ignore[reportMissingImports]


def attach_params(widget: MosaicWidget, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "params")
    # State accessors seed: {} until the first brush
    emit(widget.params)
    return lambda: widget.unobserve(on_change, "params")


PARAMS = AccessorSpec(
    name="params",
    kind="state",
    attach=attach_params,
    # A brush drag fires ~11 params updates; each one usually means a DuckDB
    # query downstream
    rate_policy="debounce",
)

MOSAIC_ACCESSORS = (PARAMS,)
