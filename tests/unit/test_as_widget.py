import sys
from types import ModuleType

import pytest
import shinywidgets._as_widget as asw
from ipywidgets import Widget
from shinywidgets._as_widget import (
    as_widget,
    as_widget_altair,
    as_widget_bokeh,
    as_widget_holoviews,
    as_widget_plotly,
    as_widget_pydeck,
)


def _inject_package(monkeypatch: pytest.MonkeyPatch, name: str) -> ModuleType:
    pkg = ModuleType(name)
    pkg.__path__ = []  # mark as a package for submodule imports
    monkeypatch.setitem(sys.modules, name, pkg)
    return pkg


class StubSession:
    def is_stub_session(self) -> bool:
        return True


def test_as_widget_passthrough_widget() -> None:
    # Avoid calling ipywidgets constructors (shinywidgets registers a construction callback
    # that requires an active Shiny session).
    w = Widget.__new__(Widget)
    assert as_widget(w) is w


def test_as_widget_unknown_package_errors() -> None:
    class Unknown:
        __module__ = "unknownpkg.mod"

    with pytest.raises(TypeError) as excinfo:
        as_widget(Unknown())
    msg = str(excinfo.value)
    assert "Don't know how to coerce" in msg
    assert "ipywidget.Widget" in msg


def test_as_widget_unknown_package_with_repr_html_hint() -> None:
    class Unknown:
        __module__ = "unknownpkg.mod"

        def _repr_html_(self):
            return "<div />"

    with pytest.raises(TypeError) as excinfo:
        as_widget(Unknown())
    msg = str(excinfo.value)
    assert "@render.ui" in msg
    assert "output_ui.html" in msg


def test_as_widget_coercer_returning_non_widget_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asw, "AS_WIDGET_MAP", {"fakepkg": lambda x: "not-a-widget"})

    class Fake:
        __module__ = "fakepkg.mod"

    with pytest.raises(TypeError) as excinfo:
        as_widget(Fake())
    msg = str(excinfo.value)
    assert "Failed to coerce" in msg
    assert "package fakepkg" in msg


def test_as_widget_altair_import_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # A module that exists but doesn't provide JupyterChart still triggers ImportError.
    monkeypatch.setitem(sys.modules, "altair", ModuleType("altair"))
    with pytest.raises(RuntimeError, match="pip install -U altair"):
        as_widget_altair(object())


def test_as_widget_altair_success_with_fake_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    altair = ModuleType("altair")
    altair.JupyterChart = lambda x: Widget.__new__(Widget)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "altair", altair)

    class AltairObj:
        __module__ = "altair.something"

    res = as_widget(AltairObj())
    assert isinstance(res, Widget)


def test_as_widget_bokeh_import_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", ModuleType("jupyter_bokeh"))
    with pytest.raises(ImportError, match="Install the jupyter_bokeh package"):
        as_widget_bokeh(object())


def test_as_widget_bokeh_success_with_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    jb = ModuleType("jupyter_bokeh")
    jb.BokehModel = lambda x: Widget.__new__(Widget)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", jb)

    _inject_package(monkeypatch, "bokeh")
    plotting = ModuleType("bokeh.plotting")

    class FakeFigure:
        def __init__(self):
            self.sizing_mode = None

    plotting.figure = FakeFigure  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bokeh.plotting", plotting)

    fig = FakeFigure()
    res = as_widget_bokeh(fig)
    assert isinstance(res, Widget)
    assert fig.sizing_mode == "stretch_both"


def test_as_widget_plotly_success_and_type_check_with_fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_package(monkeypatch, "plotly")
    go = ModuleType("plotly.graph_objects")

    class Figure:
        def __init__(self):
            self.data = {"d": 1}
            self.layout = {"l": 1}

    def FigureWidget(*args, **kwargs):
        w = Widget.__new__(Widget)
        w._args = args  # type: ignore[attr-defined]
        w._kwargs = kwargs  # type: ignore[attr-defined]
        return w

    go.Figure = Figure  # type: ignore[attr-defined]
    go.FigureWidget = FigureWidget  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", go)

    res = as_widget_plotly(Figure())
    assert isinstance(res, Widget)

    with pytest.raises(TypeError, match="plotly.graph_objects.FigureWidget"):
        as_widget_plotly(object())


def _fake_holoviews(monkeypatch: pytest.MonkeyPatch):
    hv_mod = _inject_package(monkeypatch, "holoviews")
    _inject_package(monkeypatch, "holoviews.core")
    dim_mod = ModuleType("holoviews.core.dimension")

    class Dimensioned:
        pass

    dim_mod.Dimensioned = Dimensioned  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "holoviews.core.dimension", dim_mod)

    render_calls = {}

    def render(x, backend=None):
        render_calls["x"] = x
        render_calls["backend"] = backend
        return "bokeh-fig"

    hv_mod.render = render  # type: ignore[attr-defined]
    return Dimensioned, render_calls


def test_as_widget_holoviews_rejects_non_dimensioned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_holoviews(monkeypatch)
    with pytest.raises(TypeError, match="holoviews"):
        as_widget_holoviews(object())


def test_as_widget_holoviews_renders_with_bokeh_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Dimensioned, render_calls = _fake_holoviews(monkeypatch)

    jb = ModuleType("jupyter_bokeh")
    jb.BokehModel = lambda x: Widget.__new__(Widget)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", jb)

    obj = Dimensioned()
    res = as_widget_holoviews(obj)
    assert isinstance(res, Widget)
    assert render_calls["x"] is obj
    assert render_calls["backend"] == "bokeh"


def test_as_widget_holoviews_jupyter_bokeh_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Dimensioned, _ = _fake_holoviews(monkeypatch)
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", ModuleType("jupyter_bokeh"))
    with pytest.raises(ImportError, match="Install the jupyter_bokeh package"):
        as_widget_holoviews(Dimensioned())


def test_as_widget_holoviews_dispatch_via_as_widget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Dimensioned, _ = _fake_holoviews(monkeypatch)

    jb = ModuleType("jupyter_bokeh")
    jb.BokehModel = lambda x: Widget.__new__(Widget)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", jb)

    HvObj = type("Curve", (Dimensioned,), {"__module__": "holoviews.element.chart"})

    res = as_widget(HvObj())
    assert isinstance(res, Widget)


def test_as_widget_holoviews_real_bokeh_model(monkeypatch: pytest.MonkeyPatch) -> None:
    hv = pytest.importorskip("holoviews")
    pytest.importorskip("jupyter_bokeh")

    import shinywidgets._shinywidgets as sw

    monkeypatch.setattr(sw, "get_current_session", lambda: StubSession())

    from jupyter_bokeh import BokehModel

    res = as_widget(hv.Curve([1, 2, 3]))
    assert isinstance(res, BokehModel)


def test_as_widget_pydeck_missing_show_errors() -> None:
    class NoShow:
        __module__ = "pydeck.mod"

    with pytest.raises(TypeError, match=r"\.show\(\)"):
        as_widget_pydeck(NoShow())


def test_as_widget_pydeck_show_returning_non_widget_explains() -> None:
    class Deck:
        __module__ = "pydeck.mod"

        def show(self):
            return "not-a-widget"

    with pytest.raises(TypeError) as excinfo:
        as_widget_pydeck(Deck())
    msg = str(excinfo.value)
    assert "pydeck v0.9 removed ipywidgets support" in msg
    assert "@render.ui" in msg


def test_as_widget_pydeck_show_returning_widget_succeeds() -> None:
    class Deck:
        __module__ = "pydeck.mod"

        def show(self):
            return Widget.__new__(Widget)

    res = as_widget_pydeck(Deck())
    assert isinstance(res, Widget)
