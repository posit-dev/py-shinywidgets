import asyncio
import subprocess
import sys

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from htmltools import HTMLDependency, div
from shiny.session import session_context


def test_render_embedding_atlas_is_render_widget_base() -> None:
    renderer = rw.render_embedding_atlas()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_embedding_atlas_renders_widget_as_is(widget_session) -> None:
    pytest.importorskip("embedding_atlas")
    import pandas as pd
    from embedding_atlas.widget import EmbeddingAtlasWidget

    r = rw.render_embedding_atlas()
    created = []

    @r
    def _():  # noqa: ANN202
        df = pd.DataFrame({"x": [0.0, 1.0], "y": [1.0, 0.0], "text": ["a", "b"]})
        w = EmbeddingAtlasWidget(df, x="x", y="y", text="text")
        created.append(w)
        return w

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert r.widget is created[0]
    assert res["fill"] is True


def test_render_embedding_atlas_respects_widget_layout_height(widget_session) -> None:
    pytest.importorskip("embedding_atlas")
    import pandas as pd
    from embedding_atlas.widget import EmbeddingAtlasWidget

    r = rw.render_embedding_atlas()

    @r
    def _():  # noqa: ANN202
        df = pd.DataFrame({"x": [0.0, 1.0], "y": [1.0, 0.0]})
        w = EmbeddingAtlasWidget(df, x="x", y="y")
        w.layout.height = "300px"
        return w

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is False


def test_render_ipyaladin_is_render_widget_base() -> None:
    renderer = rw.render_ipyaladin()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipycanvas_is_render_widget_base() -> None:
    renderer = rw.render_ipycanvas()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_itables_is_render_widget_base() -> None:
    renderer = rw.render_itables()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipydatagrid_is_render_widget_base() -> None:
    renderer = rw.render_ipydatagrid()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipydatagrid_exported_from_package() -> None:
    import shinywidgets

    assert shinywidgets.render_ipydatagrid is rw.render_ipydatagrid
    assert "render_ipydatagrid" in shinywidgets.__all__
    assert "render_ipydatagrid" in rw.__all__


def test_render_ipydatagrid_coerces_dataframe(widget_session) -> None:
    pytest.importorskip("ipydatagrid")
    import pandas as pd
    from ipydatagrid import DataGrid

    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    r = rw.render_ipydatagrid()

    @r
    def _():  # noqa: ANN202
        return df

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    assert res["fill"] is True
    assert res["widget_pkg"] == "ipydatagrid"
    assert isinstance(r.widget, DataGrid)
    assert r.widget.data["a"].tolist() == [1, 2, 3]
    assert r.value is df


def test_render_ipydatagrid_coerces_dataframe_subclass(widget_session) -> None:
    # e.g., geopandas.GeoDataFrame, which DataGrid accepts like any DataFrame
    pytest.importorskip("ipydatagrid")
    import pandas as pd
    from ipydatagrid import DataGrid

    class SubFrame(pd.DataFrame):
        pass

    r = rw.render_ipydatagrid()

    @r
    def _():  # noqa: ANN202
        return SubFrame({"a": [1, 2]})

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert isinstance(r.widget, DataGrid)
    assert r.widget.data["a"].tolist() == [1, 2]


def test_render_ipydatagrid_passes_datagrid_through(widget_session) -> None:
    pytest.importorskip("ipydatagrid")
    import pandas as pd
    from ipydatagrid import DataGrid

    with session_context(widget_session):
        grid = DataGrid(pd.DataFrame({"a": [1]}), selection_mode="cell")
        r = rw.render_ipydatagrid()

        @r
        def _():  # noqa: ANN202
            return grid

        assert asyncio.run(r._render()) is not None
    assert r.widget is grid


def test_render_ipydatagrid_rejects_unsupported_value(widget_session) -> None:
    class Unsupported:
        pass

    r = rw.render_ipydatagrid()

    @r
    def _():  # noqa: ANN202
        return Unsupported()

    with session_context(widget_session):
        with pytest.raises(TypeError, match="Don't know how to coerce"):
            asyncio.run(r._render())


def test_render_ipydatagrid_missing_package_error(
    widget_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("pandas")
    import pandas as pd

    monkeypatch.setitem(sys.modules, "ipydatagrid", None)
    r = rw.render_ipydatagrid()

    @r
    def _():  # noqa: ANN202
        return pd.DataFrame({"a": [1]})

    with session_context(widget_session):
        with pytest.raises(
            ImportError, match=r"pip install 'shinywidgets\[ipydatagrid\]'"
        ):
            asyncio.run(r._render())


def test_render_keplergl_is_render_widget_base() -> None:
    renderer = rw.render_keplergl()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_lonboard_is_render_widget_base() -> None:
    renderer = rw.render_lonboard()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_maplibre_is_render_widget_base() -> None:
    renderer = rw.render_maplibre()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_jscatter_is_render_widget_base() -> None:
    renderer = rw.render_jscatter()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_matplotlib_is_render_widget_base() -> None:
    renderer = rw.render_matplotlib()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_plotnine_is_render_widget_base() -> None:
    renderer = rw.render_plotnine()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_plotly_accepts_figure_config_tuple(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        return (go.Figure(), {"displayModeBar": False})

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    assert isinstance(r.widget, go.FigureWidget)
    assert r.widget._config["displayModeBar"] is False  # type: ignore
    # the user's config is merged over shinywidgets' (and plotly's) defaults
    # (plotly's own default config varies by version, so check ours instead)
    assert r.widget._config["responsive"] is True  # type: ignore


def test_render_plotly_accepts_figurewidget_config_tuple(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()
    created = []

    @r
    def _():  # noqa: ANN202
        fw = go.FigureWidget()
        created.append(fw)
        return (fw, {"displayModeBar": False})

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    # a pre-built FigureWidget is passed through as-is (not re-coerced)
    assert r.widget is created[0]
    assert r.widget._config["displayModeBar"] is False  # type: ignore


def test_render_plotly_config_tuple_overrides_shinywidgets_defaults(
    widget_session,
) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        # shinywidgets defaults responsive to True (in filling layouts)
        return (go.Figure(), {"responsive": False})

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert r.widget._config["responsive"] is False  # type: ignore


def test_import_shinywidgets_without_optional_deps() -> None:
    # shinywidgets must import cleanly with every optional widget dependency
    # missing (render_plotly's value-type bound, in particular, must stay a
    # lazy forward reference so plotly remains optional).
    pkgs = [
        "altair",
        "bokeh",
        "holoviews",
        "hvplot",
        "ipycanvas",
        "jscatter",
        "jupyter_bokeh",
        "ipydatagrid",
        "ipympl",
        "keplergl",
        "maplibre",
        "matplotlib",
        "panel",
        "plotly",
        "plotnine",
        "pydeck",
    ]
    script = f"""
import sys
for pkg in {pkgs!r}:
    sys.modules[pkg] = None

import shinywidgets  # noqa: F401
"""
    subprocess.run([sys.executable, "-c", script], check=True)


def test_render_plotly_malformed_tuple_errors(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        return (go.Figure(), "displayModeBar=False")

    with session_context(widget_session):
        with pytest.raises(TypeError, match=r"\(figure, config\) tuple"):
            asyncio.run(r._render())


def test_render_plotly_plain_figure_still_works(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        return go.Figure()

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert isinstance(r.widget, go.FigureWidget)
    assert r.widget._config.get("responsive") is True  # type: ignore


def test_render_bokeh_auto_output_ui_appends_bokeh_dependency(monkeypatch) -> None:
    sentinel = HTMLDependency(
        name="bokeh-inline",
        version="1.0",
        source={"href": "https://example.invalid"},
    )

    monkeypatch.setattr(rwb, "output_widget", lambda *args, **kwargs: div())
    monkeypatch.setattr(rw, "_bokeh_dependency", lambda: sentinel)

    renderer = rw.render_bokeh()
    renderer.output_id = "plot"

    res = renderer.auto_output_ui()

    assert any(dep.name == "bokeh-inline" for dep in res.get_dependencies())


def test_render_panel_and_hvplot_auto_output_ui_append_bokeh_dependency(
    monkeypatch,
) -> None:
    sentinel = HTMLDependency(
        name="bokeh-inline",
        version="1.0",
        source={"href": "https://example.invalid"},
    )

    monkeypatch.setattr(rwb, "output_widget", lambda *args, **kwargs: div())
    monkeypatch.setattr(rw, "_bokeh_dependency", lambda: sentinel)

    for cls in (rw.render_panel, rw.render_holoviews):
        renderer = cls()
        renderer.output_id = "plot"

        res = renderer.auto_output_ui()

        assert any(dep.name == "bokeh-inline" for dep in res.get_dependencies()), cls
