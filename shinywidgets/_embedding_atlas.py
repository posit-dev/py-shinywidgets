"""
Accessors for `render_embedding_atlas`.

The explorer's cross-filter is synced from the browser to the widget's
(upstream-internal) `_predicate` trait (a DuckDB WHERE expression), so one
state accessor observes it. `predicate()` returns the expression itself;
`selection()` reads the same spec (the invalidation trigger) and asks the
widget for the filtered rows at read time.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Callable, Optional

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    # embedding-atlas requires Python 3.11+, so it's absent from 3.10
    # environments; it's also absent from 3.15+ environments (its duckdb
    # dependency has no cp315 wheels; see pyproject.toml)
    if sys.version_info >= (3, 11):
        from embedding_atlas.widget import EmbeddingAtlasWidget  # pyright: ignore[reportMissingImports]
    else:
        from ipywidgets import Widget as EmbeddingAtlasWidget


# Sentinel: `_predicate` defaults to None (no filter), so a None default
# can't distinguish a missing trait
_MISSING = object()


def attach_predicate(widget: EmbeddingAtlasWidget, emit: Emit) -> Callable[[], None]:
    # `_predicate` is upstream-internal (the renderer already couples to it
    # and to `_connection`); fail loudly if embedding-atlas removes it rather
    # than silently stop invalidating readers
    if getattr(widget, "_predicate", _MISSING) is _MISSING:
        raise TypeError(
            "`predicate()` and `selection()` rely on the EmbeddingAtlasWidget's "
            "(upstream-internal) `_predicate` trait, which this version of "
            "embedding-atlas doesn't have. If embedding-atlas renamed or "
            "removed this trait, please report it."
        )

    def on_change(change: dict[str, object]) -> None:
        emit(change["new"])

    widget.observe(on_change, "_predicate")
    emit(widget._predicate)
    return lambda: widget.unobserve(on_change, "_predicate")


def rows_for_predicate(widget: EmbeddingAtlasWidget, predicate: Optional[str]) -> Any:
    """
    The rows of `widget` passing `predicate` (a mirror of
    `EmbeddingAtlasWidget.selection()`, but for a given predicate rather than
    the live `_predicate`), as the widget's native frame type.

    `selection()` derives from this instead of the widget's own method so it
    always describes the same filter as `predicate()` -- the published,
    debounced one -- even mid-debounce, when the widget's live `_predicate`
    is already ahead.
    """
    # `_connection`/`_table_name`/`_native_namespace` are upstream-internal
    # (like `_predicate`, which attach_predicate also checks); fail loudly if
    # embedding-atlas removes them rather than silently query the wrong table
    missing = [
        name
        for name in ("_connection", "_table_name", "_native_namespace")
        if getattr(widget, name, None) is None
    ]
    if missing:
        raise TypeError(
            "`selection()` relies on the EmbeddingAtlasWidget's (upstream-internal) "
            f"{', '.join(missing)}, which this version of embedding-atlas doesn't "
            "have. If embedding-atlas renamed or removed these attributes, please "
            "report it."
        )
    if predicate is not None:
        result = widget._connection.sql(
            f"SELECT * FROM {widget._table_name} WHERE {predicate}"
        )
    else:
        result = widget._connection.sql(f"SELECT * FROM {widget._table_name}")

    import narwhals as nw

    reader = result.fetch_arrow_reader()
    return nw.to_native(nw.from_arrow(reader, backend=widget._native_namespace))


PREDICATE = AccessorSpec(
    name="predicate",
    kind="state",
    attach=attach_predicate,
    # Brushes and lassos stream predicate updates, and each change can cost a
    # DuckDB query downstream
    rate_policy="debounce",
)

EMBEDDING_ATLAS_ACCESSORS = (PREDICATE,)
