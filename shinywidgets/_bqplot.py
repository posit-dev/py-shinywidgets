"""
Accessors for `render_bqplot`.

bqplot selections live on the figure's marks (each `Mark.selected`), and the
brushed region on the figure's `interaction` (a brush selector's `selected`).
Both sub-objects can be replaced after render (the toolbar swaps the
interaction; the user can assign ``fig.marks``), so each attach observes its
container trait and re-observes the current sub-objects when it changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Tuple

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from bqplot import Figure as BqplotFigure


def selections_equal(a: List[object], b: List[object]) -> bool:
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


def attach_selection(widget: BqplotFigure, emit: Emit) -> Callable[[], None]:
    # (mark, handler) pairs, so detach can remove every per-mark observer
    observed: List[Tuple[Any, Any]] = []

    def current() -> List[object]:
        return [mark.selected for mark in widget.marks]

    last: List[object] = []

    def publish() -> None:
        # bqplot selectors re-send the same selection during a drag, and the
        # helper's equality check can't compare arrays, so dedup here
        nonlocal last
        sel = current()
        if selections_equal(sel, last):
            return
        last = list(sel)
        emit(list(sel))

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


SELECTION = AccessorSpec(
    name="selection",
    kind="state",
    attach=attach_selection,
    # Brush selectors update during the drag
    rate_policy="debounce",
)

BPLOT_ACCESSORS = (SELECTION,)
