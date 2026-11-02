from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
import shinywidgets._shinywidgets as sw
from shiny.session import session_context
from shinywidgets._as_widget import as_widget
from shinywidgets._serialization import json_packer

# Snapshot before importing reactable: the import calls ipyreact.define_module()
# at module level, constructing a process-global Module widget (and ipyreact's own
# ImportMap widget) that our hook registers in SHARED_WIDGETS
SHARED_BEFORE = dict(sw.SHARED_WIDGETS)

pytest.importorskip("reactable")
from reactable import Reactable  # noqa: E402
from reactable.widgets import ReactableWidget  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def cleanup_ipyreact_registry() -> Iterator[None]:
    # Don't let the import-time registry widgets leak into other test modules
    # (they would be opened in every session those modules create)
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


def make_table(**kwargs: object) -> Reactable:
    import pandas as pd

    return Reactable(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}), **kwargs)  # type: ignore[arg-type]


def render_one(
    renderer: rwb.render_widget_base, value: object, session
) -> dict[str, object]:  # noqa: ANN001, ANN202

    @renderer
    def _() -> object:
        return value

    with session_context(session):
        res = asyncio.run(renderer._render())

    assert isinstance(res, dict)
    return res


def test_render_reactable_is_exported() -> None:
    assert "render_reactable" in rw.__all__
    assert "render_reactable" in shinywidgets.__all__
    assert shinywidgets.render_reactable is rw.render_reactable


def test_render_reactable_coerces_reactable(widget_session) -> None:  # noqa: ANN001
    r = rw.render_reactable()
    res = render_one(r, make_table(), widget_session)

    assert res["fill"] is True
    assert res["widget_pkg"] == "reactable"
    assert isinstance(r.widget, ReactableWidget)
    assert r.value is not r.widget


def test_render_reactable_accepts_widget_as_is(widget_session) -> None:  # noqa: ANN001
    with session_context(widget_session):
        widget = make_table().to_widget()
    r = rw.render_reactable()
    res = render_one(r, widget, widget_session)

    assert res["fill"] is True
    assert isinstance(r.widget, ReactableWidget)
    assert r.widget is r.value


def test_render_reactable_height_prop_disables_fill(widget_session) -> None:  # noqa: ANN001
    # A reactable `height=` prop loses to the fill CSS, so it opts out of filling
    # (like an explicit ipywidgets Layout height)
    r = rw.render_reactable()
    res = render_one(r, make_table(height=250), widget_session)

    assert res["fill"] is False


def test_as_widget_sanitizes_nan(widget_session) -> None:  # noqa: ANN001
    import pandas as pd

    with session_context(widget_session):
        widget = as_widget(Reactable(pd.DataFrame({"a": [1.5, None], "b": ["x", "y"]})))

        assert isinstance(widget, ReactableWidget)
        assert widget.props["data"]["a"] == [1.5, None]
        # Widget state must survive shinywidgets' strict JSON serialization
        # (allow_nan=False); unsanitized NaNs raise ValueError here
        json_packer(widget.get_state())


def test_render_reactable_rejects_other_types(widget_session) -> None:  # noqa: ANN001
    r = rw.render_reactable()
    with pytest.raises(TypeError, match="coerce"):
        render_one(r, object(), widget_session)


def test_reactable_stylesheet_dependency() -> None:
    from shinywidgets._dependencies import reactable_dependency

    dep = reactable_dependency()
    assert dep.name == "reactable"
    assert any(s["href"] == "reactable-py.esm.css" for s in dep.stylesheet)


def test_reactable_widget_open_includes_stylesheet(widget_session) -> None:  # noqa: ANN001
    from shinywidgets._shinywidgets import widget_open_extras

    with session_context(widget_session):
        widget = make_table().to_widget()

    deps, _ = widget_open_extras(widget, widget_session, [])
    assert any(d.name == "reactable" for d in deps)
