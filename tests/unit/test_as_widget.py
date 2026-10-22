import sys
from types import ModuleType

import pytest
import shinywidgets._as_widget as asw
from bokeh.document import Document
from ipywidgets import Widget
from shinywidgets._as_widget import (
    as_widget,
    as_widget_altair,
    as_widget_bokeh,
    as_widget_maplibre,
    as_widget_mpl,
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


def _fake_matplotlib(monkeypatch: pytest.MonkeyPatch):
    mpl = _inject_package(monkeypatch, "matplotlib")
    setattr(mpl, "use", lambda backend: None)

    figure_mod = ModuleType("matplotlib.figure")

    class FigureCanvasBase:
        device_pixel_ratio = 1.0

    class Figure:
        def __init__(self):
            self.canvas = FigureCanvasBase()
            self.dpi = 100.0

        def set_dpi(self, dpi: float) -> None:
            self.dpi = dpi

    class SubFigure:
        pass

    figure_mod.Figure = Figure  # type: ignore[attr-defined]
    setattr(figure_mod, "SubFigure", SubFigure)
    monkeypatch.setitem(sys.modules, "matplotlib.figure", figure_mod)

    axes_mod = ModuleType("matplotlib.axes")

    class Axes:
        def __init__(self, figure=None):
            self.figure = figure if figure is not None else Figure()

    axes_mod.Axes = Axes  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "matplotlib.axes", axes_mod)

    return Figure, Axes


def _fake_ipympl_canvas(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    _inject_package(monkeypatch, "ipympl")
    nbagg = ModuleType("ipympl.backend_nbagg")

    class Canvas(Widget):
        def __init__(self, figure):
            # Deliberately skip Widget.__init__() (it requires an active session)
            captured["figure"] = figure
            self.manager: object | None = None
            self.comm = None

    class FigureManager:
        def __init__(self, canvas, num):
            captured["num"] = num
            captured["canvas"] = canvas
            canvas.manager = self

    nbagg.Canvas = Canvas  # type: ignore[attr-defined]
    nbagg.FigureManager = FigureManager  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ipympl.backend_nbagg", nbagg)
    return captured


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


@pytest.mark.parametrize("value", ["x", 1, 1.5, None, {}, [], (1, 2), object()])
def test_as_widget_builtin_value_raises_helpful_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="Don't know how to coerce"):
        as_widget(value)


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


def test_as_widget_bokeh_stretches_unsized_figure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bokeh.plotting import figure

    _fake_jupyter_bokeh(monkeypatch)

    fig = figure()
    res = as_widget_bokeh(fig)
    assert isinstance(res, Widget)
    assert fig.sizing_mode == "stretch_both"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"height": 200},
        {"width": 250},
        {"width": 250, "height": 150, "sizing_mode": "fixed"},
        {"height": 200, "sizing_mode": "stretch_width"},
        {"aspect_ratio": 2},
    ],
)
def test_as_widget_bokeh_respects_user_sizing(
    monkeypatch: pytest.MonkeyPatch, kwargs: dict[str, object]
) -> None:
    from bokeh.plotting import figure

    _fake_jupyter_bokeh(monkeypatch)

    fig = figure(**kwargs)
    as_widget_bokeh(fig)
    assert fig.sizing_mode == kwargs.get("sizing_mode")
    for name, value in kwargs.items():
        assert getattr(fig, name) == value


def test_as_widget_plotly_success_and_type_check_with_fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_package(monkeypatch, "plotly")
    go = ModuleType("plotly.graph_objects")

    class Figure:
        def __init__(self):
            self.data = {"d": 1}
            self.layout = {"l": 1}
            self.frames = ()

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

    # Frames (i.e., animations) aren't supported by FigureWidget, so they're
    # dropped with a warning (#156)
    fig = Figure()
    fig.frames = ({"data": []},)  # type: ignore[assignment]
    with pytest.warns(UserWarning, match="does not support frames"):
        res = as_widget_plotly(fig)
    assert isinstance(res, Widget)


def _fake_maplibre(monkeypatch: pytest.MonkeyPatch):
    _inject_package(monkeypatch, "maplibre")

    class Map:
        def __init__(self):
            self._state = {
                "mapOptions": {"style": "dark-matter"},
                "calls": [["addSource", ("src", {"type": "geojson"})]],
            }

        def to_dict(self):
            return self._state

    map_mod = ModuleType("maplibre.map")
    map_mod.Map = Map  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "maplibre.map", map_mod)

    ipywidget_mod = ModuleType("maplibre.ipywidget")

    def MapWidget():
        return Widget.__new__(Widget)

    ipywidget_mod.MapWidget = MapWidget  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "maplibre.ipywidget", ipywidget_mod)

    return Map


def test_as_widget_maplibre_rejects_non_map(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_maplibre(monkeypatch)
    with pytest.raises(TypeError, match="maplibre"):
        as_widget_maplibre(object())


def test_as_widget_maplibre_anywidget_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Map = _fake_maplibre(monkeypatch)
    # maplibre.ipywidget exists, but MapWidget isn't defined (e.g., because
    # anywidget isn't installed)
    monkeypatch.setitem(
        sys.modules, "maplibre.ipywidget", ModuleType("maplibre.ipywidget")
    )
    with pytest.raises(ImportError, match=r"maplibre\[anywidget\]"):
        as_widget_maplibre(Map())


def test_as_widget_maplibre_transfers_map_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Map = _fake_maplibre(monkeypatch)

    m = Map()
    res = as_widget_maplibre(m)
    assert isinstance(res, Widget)
    assert res.map_options == m.to_dict()["mapOptions"]  # type: ignore[attr-defined]
    assert res._message_queue == m.to_dict()["calls"]  # type: ignore[attr-defined]


def test_as_widget_maplibre_dispatch_via_as_widget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Map = _fake_maplibre(monkeypatch)

    MlMap = type("Map", (Map,), {"__module__": "maplibre.map"})

    res = as_widget(MlMap())
    assert isinstance(res, Widget)


def test_as_widget_mpl_rejects_non_figure(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_matplotlib(monkeypatch)
    with pytest.raises(TypeError, match="matplotlib"):
        as_widget_mpl(object())


def test_as_widget_mpl_import_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    Figure, _ = _fake_matplotlib(monkeypatch)
    # A module that exists but doesn't provide backend_nbagg still triggers ImportError.
    monkeypatch.setitem(sys.modules, "ipympl", ModuleType("ipympl"))
    with pytest.raises(ImportError, match="pip install ipympl"):
        as_widget_mpl(Figure())


def test_as_widget_mpl_success_with_fake_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Figure, _ = _fake_matplotlib(monkeypatch)
    captured = _fake_ipympl_canvas(monkeypatch)

    fig = Figure()
    res = as_widget_mpl(fig)
    assert isinstance(res, Widget)
    assert captured["figure"] is fig


def test_as_widget_mpl_axes_coerced_to_parent_figure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Figure, Axes = _fake_matplotlib(monkeypatch)
    captured = _fake_ipympl_canvas(monkeypatch)

    fig = Figure()
    res = as_widget_mpl(Axes(fig))
    assert isinstance(res, Widget)
    assert captured["figure"] is fig


def test_as_widget_mpl_dispatch_via_as_widget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Figure, _ = _fake_matplotlib(monkeypatch)
    _fake_ipympl_canvas(monkeypatch)

    MplFigure = type("Figure", (Figure,), {"__module__": "matplotlib.figure"})

    res = as_widget(MplFigure())
    assert isinstance(res, Widget)


def test_as_widget_maplibre_real_map_widget(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("maplibre")
    pytest.importorskip("anywidget")

    import shinywidgets._shinywidgets as sw

    monkeypatch.setattr(sw, "get_current_session", lambda: StubSession())

    from maplibre import Map
    from maplibre.ipywidget import MapWidget

    m = Map()
    m.add_source(
        "src",
        {"type": "geojson", "data": {"type": "FeatureCollection", "features": []}},
    )

    res = as_widget(m)
    assert isinstance(res, MapWidget)
    assert res.map_options == m.to_dict()["mapOptions"]
    assert res._message_queue == m.to_dict()["calls"]


def test_as_widget_mpl_real_ipympl_canvas(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("ipympl")

    import shinywidgets._shinywidgets as sw

    monkeypatch.setattr(sw, "get_current_session", lambda: StubSession())

    import matplotlib.pyplot as plt
    from ipympl.backend_nbagg import Canvas

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])

    res = as_widget(fig)
    assert isinstance(res, Canvas)
    plt.close(fig)


def test_as_widget_mpl_pyplot_figure_closed_at_render_retirement(
    widget_session,
) -> None:
    plt = pytest.importorskip("matplotlib.pyplot")
    pytest.importorskip("ipympl")

    from shiny.reactive._core import Context
    from shiny.session import session_context
    from shinywidgets._render_widget_base import WidgetRenderContext

    with session_context(widget_session):
        context = Context()
        with context():
            with WidgetRenderContext():
                fig, ax = plt.subplots()
                ax.plot([1, 2, 3])
                as_widget_mpl(fig)

        assert fig.number in plt.get_fignums()
        context.invalidate()
        # Retiring the render deregisters the figure from pyplot (otherwise
        # repeated renders leak figures in pyplot's global registry)
        assert fig.number not in plt.get_fignums()


def test_as_widget_mpl_non_pyplot_figure_retirement_is_noop(
    widget_session,
) -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("ipympl")

    from matplotlib.figure import Figure
    from shiny.reactive._core import Context
    from shiny.session import session_context
    from shinywidgets._render_widget_base import WidgetRenderContext

    with session_context(widget_session):
        context = Context()
        with context():
            with WidgetRenderContext():
                # A bare Figure() isn't registered with pyplot, so there's
                # nothing to clean up at retirement
                as_widget_mpl(Figure())

        # Retirement should be a clean no-op for this figure
        context.invalidate()


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


def _fake_panel(monkeypatch: pytest.MonkeyPatch, root: object) -> None:
    panel = ModuleType("panel")

    class FakePane:
        def get_root(self, doc: Document | None = None) -> object:
            return root

    panel.panel = lambda x: FakePane()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "panel", panel)


def _fake_jupyter_bokeh(monkeypatch: pytest.MonkeyPatch) -> None:
    jb = ModuleType("jupyter_bokeh")
    jb.BokehModel = lambda x: Widget.__new__(Widget)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", jb)


def test_as_widget_panel_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_panel(monkeypatch, root=object())
    _fake_jupyter_bokeh(monkeypatch)

    class PanelObj:
        __module__ = "panel.widgets.tables"

    res = as_widget(PanelObj())
    assert isinstance(res, Widget)


def test_as_widget_holoviews_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_panel(monkeypatch, root=object())
    _fake_jupyter_bokeh(monkeypatch)

    class HVObj:
        __module__ = "holoviews.element.chart"

    res = as_widget(HVObj())
    assert isinstance(res, Widget)


def test_as_widget_hvplot_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_panel(monkeypatch, root=object())
    _fake_jupyter_bokeh(monkeypatch)

    class HvPlotObj:
        __module__ = "hvplot.plotting"

    res = as_widget(HvPlotObj())
    assert isinstance(res, Widget)


def test_as_widget_panel_without_panel_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "panel", None)

    class PanelObj:
        __module__ = "panel.widgets.tables"

    with pytest.raises(ImportError, match="pip install panel"):
        as_widget(PanelObj())


def test_as_widget_holoviews_without_panel_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "panel", None)

    class HVObj:
        __module__ = "holoviews.element.chart"

    with pytest.raises(ImportError, match="pip install panel"):
        as_widget(HVObj())


def test_as_widget_panel_without_jupyter_bokeh_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_panel(monkeypatch, root=object())
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", ModuleType("jupyter_bokeh"))

    class PanelObj:
        __module__ = "panel.widgets.tables"

    with pytest.raises(ImportError, match="Install the jupyter_bokeh package"):
        as_widget(PanelObj())
