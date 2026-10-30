from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Callable, Dict, List

import pytest
import shinywidgets._reactable as sr
import shinywidgets._shinywidgets as sw
from shiny.session import session_context
from shinywidgets._accessors import AccessorSpec

PRUNED_STATE = {
    "page": 0,
    "pageSize": 10,
    "pages": 3,
    "sorted": [],
    "filters": [],
    "searchValue": None,
    "selected": [],
}


class FakeReactableWidget:
    """Records on_msg handlers and sent messages, like an ipywidgets Widget."""

    def __init__(self) -> None:
        self.handlers: List[Callable[[Any, Any, Any], None]] = []
        self.sent: List[Dict[str, Any]] = []

    def on_msg(self, fn: Callable[[Any, Any, Any], None], remove: bool = False) -> None:
        if remove:
            self.handlers.remove(fn)
        else:
            self.handlers.append(fn)

    def send(self, content: Dict[str, Any]) -> None:
        self.sent.append(content)

    def message(self, content: Dict[str, Any]) -> None:
        for fn in list(self.handlers):
            fn(self, content, [])


def state_message(**overrides: Any) -> Dict[str, Any]:
    state = {**PRUNED_STATE, **overrides}
    return {"shinywidgets": "reactable-state", "state": state}


def attach(
    spec: AccessorSpec,
) -> tuple[FakeReactableWidget, List[object], Callable[[], None]]:
    w = FakeReactableWidget()
    emitted: List[object] = []
    detach = spec.attach(w, emitted.append)
    return w, emitted, detach


def test_attach_sends_bind_request() -> None:
    w, _, _ = attach(sr.SELECTED_ROWS)
    assert w.sent == [{"shinywidgets": "bind-reactable"}]


def test_selected_rows_emits_its_slice() -> None:
    w, emitted, _ = attach(sr.SELECTED_ROWS)
    w.message(state_message(page=1, selected=[4, 82]))
    assert emitted == [[4, 82]]


@pytest.mark.parametrize(
    ("spec", "key", "value"),
    [
        (sr.PAGE, "page", 2),
        (sr.SORTED, "sorted", [{"id": "price", "desc": True}]),
        (sr.FILTERED, "filters", [{"id": "manufacturer", "value": "Acura"}]),
        (sr.SEARCH, "searchValue", "audi"),
    ],
)
def test_each_accessor_slices_its_key(
    spec: AccessorSpec, key: str, value: object
) -> None:
    w, emitted, _ = attach(spec)
    w.message(state_message(**{key: value}))
    assert emitted == [value]


def test_ignores_foreign_and_malformed_messages() -> None:
    w, emitted, _ = attach(sr.SELECTED_ROWS)
    w.message({"shinywidgets": "event", "event": "plotly_click"})
    w.message({"shinywidgets": "reactable-state", "state": "not-a-dict"})
    w.message({"shinywidgets": "reactable-state"})
    w.message("not a dict")
    assert emitted == []


def test_detach_removes_handler() -> None:
    w, emitted, detach = attach(sr.SELECTED_ROWS)
    detach()
    w.message(state_message(selected=[1]))
    assert emitted == [] and w.handlers == []


def test_specs_are_state_kind_and_cancel_before_first_report() -> None:
    for spec in sr.REACTABLE_ACCESSORS:
        assert spec.kind == "state"
        assert spec.priority == "input"
        assert spec.not_ready(None) is True
        # Once the browser has reported, any concrete value (even an empty
        # one) is ready
        assert spec.not_ready([]) is False


def test_text_streams_debounce_but_clicks_dont() -> None:
    assert sr.FILTERED.rate_policy == "debounce"
    assert sr.SEARCH.rate_policy == "debounce"
    assert sr.SELECTED_ROWS.rate_policy is None
    assert sr.PAGE.rate_policy is None
    assert sr.SORTED.rate_policy is None


# --- renderer integration (needs reactable installed) -----------------------

# Snapshot before importing reactable: the import calls ipyreact.define_module()
# at module level, constructing process-global registry widgets (see
# tests/unit/test_reactable.py for why they must be cleaned up)
SHARED_BEFORE = dict(sw.SHARED_WIDGETS)

pytest.importorskip("reactable")
import shinywidgets._render_widget as rw  # noqa: E402
from reactable import Reactable  # noqa: E402
from shinywidgets._render_widget import render_reactable  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def cleanup_ipyreact_registry() -> Iterator[None]:
    try:
        yield
    finally:
        for model_id, w in list(sw.SHARED_WIDGETS.items()):
            if SHARED_BEFORE.get(model_id) is not w:
                w.close()
                sw.SHARED_WIDGETS.pop(model_id, None)
        import ipyreact.module

        registry = getattr(ipyreact.module, "_module_widgets", None)
        if isinstance(registry, dict):
            registry.pop("reactable", None)


def make_widget(session):  # noqa: ANN001, ANN202
    import pandas as pd

    with session_context(session):
        return Reactable(pd.DataFrame({"a": [1, 2]})).to_widget()


def test_renderer_declares_the_accessors() -> None:
    r = render_reactable()
    assert rw.render_reactable._accessor_specs == sr.REACTABLE_ACCESSORS
    assert set(r._accessors.values) == {s.name for s in sr.REACTABLE_ACCESSORS}
    for name in ("selected_rows", "page", "sorted", "filtered", "search"):
        assert callable(getattr(r, name))


def test_element_id_defaults_to_a_unique_value(widget_session) -> None:  # noqa: ANN001
    w1, w2 = make_widget(widget_session), make_widget(widget_session)
    r = render_reactable()
    r._as_widget(w1)
    r._as_widget(w2)
    id1, id2 = w1.props["elementId"], w2.props["elementId"]
    assert id1.startswith("shinywidgets-reactable-")
    assert id1 != id2


def test_element_id_user_value_wins(widget_session) -> None:  # noqa: ANN001
    w = make_widget(widget_session)
    w.props = {**w.props, "elementId": "my_table"}
    render_reactable()._as_widget(w)
    assert w.props["elementId"] == "my_table"
