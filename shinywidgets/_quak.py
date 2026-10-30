"""
Accessors for `render_quak`, backed by the widget's `sql` trait (the query
for the table's current sort and filter state, which the browser refines as
the user brushes and sorts).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    # quak is excluded from the 3.15 test/dev envs (duckdb has no cp315
    # wheels), so pyright can't resolve it there
    from quak import Widget as QuakWidget  # pyright: ignore[reportMissingImports]


def attach_sql(widget: QuakWidget, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "sql")
    # State accessors seed: publish the query the widget was constructed with
    # (the browser refines it once it initializes)
    emit(widget.sql)
    return lambda: widget.unobserve(on_change, "sql")


SQL = AccessorSpec(
    name="sql",
    kind="state",
    attach=attach_sql,
    # Brushing quak's column histograms fires ~20 updates per drag, and each
    # one typically triggers DuckDB work downstream
    rate_policy="debounce",
    not_ready=lambda raw: raw == "",  # the frontend syncs "" while initializing
)

QUAK_ACCESSORS = (SQL,)
