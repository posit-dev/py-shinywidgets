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
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Tuple, cast

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

    # Sentinel for "nothing published yet": the seed publish must always
    # happen, even for a figure with no marks, where the selection list is []
    # (an [] baseline would compare equal and suppress the seed, leaving the
    # accessor unseeded -- and a re-rendered figure's stale value in place)
    unset = object()
    last: object = unset

    def publish() -> None:
        # bqplot selectors re-send the same selection during a drag, and the
        # helper's equality check can't compare arrays, so dedup here
        nonlocal last
        sel = current()
        if last is not unset and selections_equal(sel, cast(List[object], last)):
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


SELECTION = AccessorSpec(
    name="selection",
    kind="state",
    attach=attach_selection,
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

BPLOT_ACCESSORS = (SELECTION, BRUSH)
