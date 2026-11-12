"""
Accessors for `render_bqplot`.

bqplot selections live on the figure's marks (each `Mark.selected`), and the
brushed region on the figure's `interaction` (a brush selector's `selected`).
Both sub-objects can be replaced after render (the toolbar swaps the
interaction; the user can assign ``fig.marks``), so each attach observes its
container trait and re-observes the current sub-objects when it changes.

There is deliberately no `clicked()` accessor: bqplot's `element_click`
messages never reach marks while the figure has an `interaction` (the
interaction's overlay intercepts real clicks -- browser-verified), so an
accessor that is silently dead in the common interactive case is worse than
none. `mark.on_element_click()` remains the escape hatch for
interaction-free figures.

The selection attach publishes a `SelectionReport` -- the marks and their
selections, together -- so `selected_rows()` resolves its `mark` against the
same (possibly debounce-lagged) alignment as the selections, never the live
figure, which could pair a mark with another mark's rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from shiny import req

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    import numpy as np
    from bqplot import Figure as BqplotFigure
    from bqplot import Mark


@dataclass(frozen=True)
class SelectionReport:
    """
    One published ``selected`` value: the figure's marks and their
    selections, aligned. The report lags live ``fig.marks`` by the debounce;
    keeping the alignment in the value lets `selected_rows()` resolve a mark
    against the same report the selections came from.
    """

    marks: Tuple["Mark", ...]
    selected: Tuple[Optional["np.ndarray"], ...]


def selections_equal(a: Sequence[object], b: Sequence[object]) -> bool:
    """
    Elementwise equality for per-mark selections (`None` or a numpy array),
    which the helper's `payloads_equal` can't compare (arrays' `==` is
    elementwise).
    """
    if len(a) != len(b):
        return False
    import numpy as np

    for x, y in zip(a, b):
        if x is None or y is None:
            if x is not y:
                return False
        elif not (
            isinstance(x, np.ndarray)
            and isinstance(y, np.ndarray)
            and np.array_equal(x, y)
        ):
            return False
    return True


def pick_mark(
    fig: BqplotFigure,
    reported: Tuple["Mark", ...],
    mark: Optional[Union[int, "Mark"]],
) -> int:
    """
    The index into a `SelectionReport` for `selected_rows()`'s `mark`
    argument: `mark` may be an index or the `Mark` object itself, and may be
    omitted only when the figure has exactly one mark.

    The report lags live ``fig.marks`` by the debounce, so a mark or index
    that exists only in the live figure can't be read yet: cancel
    (``req(False)``) until the report catches up rather than pair it with
    another mark's rows.
    """
    live = tuple(fig.marks)
    if isinstance(mark, int):
        if -len(reported) <= mark < len(reported):
            return mark
        if -len(live) <= mark < len(live):
            req(False)
        raise ValueError(
            f"`mark` index {mark} is out of range for a figure with "
            f"{len(live)} mark(s)."
        )
    if mark is None:
        if len(live) != 1:
            raise ValueError(
                f"The figure has {len(live)} marks; pass `mark=` to "
                "`selected_rows()` (its index in `fig.marks`, or the `Mark` "
                "object itself)."
            )
        mark = live[0]
    try:
        return reported.index(mark)
    except ValueError:
        if mark in live:
            req(False)
        raise ValueError("`mark` is not one of the figure's marks.") from None


def attach_selection(widget: BqplotFigure, emit: Emit) -> Callable[[], None]:
    # (mark, handler) pairs, so detach can remove every per-mark observer
    observed: List[Tuple[Any, Any]] = []

    def report() -> SelectionReport:
        marks = tuple(widget.marks)
        return SelectionReport(marks, tuple(mark.selected for mark in marks))

    # Sentinel for "nothing published yet": the seed publish must always
    # happen, even for a figure with no marks, where the report is empty (an
    # empty baseline would compare equal and suppress the seed, leaving the
    # accessor unseeded -- and a re-rendered figure's stale value in place)
    unset = object()
    last: object = unset

    def publish() -> None:
        # bqplot selectors re-send the same selection during a drag, and the
        # helper's equality check can't compare arrays, so dedup here. The
        # marks must compare too: a swapped-in mark with the same selection
        # (e.g. both None) is still a new alignment to report
        nonlocal last
        rep = report()
        if last is not unset:
            prev = cast(SelectionReport, last)
            if rep.marks == prev.marks and selections_equal(
                rep.selected, prev.selected
            ):
                return
        last = rep
        emit(rep)

    def observe_marks() -> None:
        for mark, handler in observed:
            mark.unobserve(handler, "selected")
        observed.clear()
        for mark in widget.marks:
            # The handler ignores its argument: it republishes the whole
            # alignment, so a change on any mark reports every mark
            def handler(change: Any) -> None:
                publish()

            mark.observe(handler, "selected")
            observed.append((mark, handler))

    def on_marks(change: Any) -> None:
        observe_marks()
        publish()

    widget.observe(on_marks, "marks")
    observe_marks()
    publish()  # state accessors seed

    def detach() -> None:
        widget.unobserve(on_marks, "marks")
        for mark, handler in observed:
            mark.unobserve(handler, "selected")
        observed.clear()

    return detach


def attach_brush(widget: BqplotFigure, emit: Emit) -> Callable[[], None]:
    # The currently observed selector and its handler (at most one pair),
    # so detach can remove the observer
    observed: List[Tuple[Any, Any]] = []

    # bqplot's stubs type Figure.interaction as `object`; the runtime value is
    # an interacts widget (or None)
    def interaction() -> Any:
        return widget.interaction

    def current() -> object:
        sel = interaction()
        # Check the trait by name (not isinstance), so future selector types
        # work; PanZoom and LassoSelector have no region to report
        if sel is None or "selected" not in sel.trait_names():
            return None
        return sel.selected

    def publish(change: Any = None) -> None:
        emit(current())

    def observe_interaction() -> None:
        for selector, handler in observed:
            selector.unobserve(handler, "selected")
        observed.clear()
        sel = interaction()
        if sel is not None and "selected" in sel.trait_names():
            sel.observe(publish, "selected")
            observed.append((sel, publish))

    def on_interaction(change: Any) -> None:
        observe_interaction()
        publish()

    widget.observe(on_interaction, "interaction")
    observe_interaction()
    publish()  # state accessors seed

    def detach() -> None:
        widget.unobserve(on_interaction, "interaction")
        for selector, handler in observed:
            selector.unobserve(handler, "selected")
        observed.clear()

    return detach


SELECTED = AccessorSpec(
    name="selected",
    kind="state",
    attach=attach_selection,
    # The raw value is a SelectionReport; the accessor value is its selections
    payload=lambda report: list(report.selected),
    # Brush selectors update during the drag
    rate_policy="debounce",
)

BRUSH = AccessorSpec(
    name="brush",
    kind="state",
    attach=attach_brush,
    # A brush drag streams ~10 updates
    rate_policy="debounce",
)

BPLOT_ACCESSORS = (SELECTED, BRUSH)
