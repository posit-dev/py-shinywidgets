import asyncio
import subprocess
import sys

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from htmltools import HTMLDependency, div
from ipywidgets import Layout
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


def _duckdb_settings(widget, *names: str) -> dict:  # noqa: ANN001, ANN202
    quoted = ", ".join(f"'{name}'" for name in names)
    rows = widget._connection.execute(
        f"SELECT name, value FROM duckdb_settings() WHERE name IN ({quoted})"
    ).fetchall()
    return dict(rows)


def _render_embedding_atlas_widget(renderer, make_widget, session):  # noqa: ANN001, ANN202
    created = []

    @renderer
    def _():  # noqa: ANN202
        widget = make_widget()
        created.append(widget)
        return widget

    with session_context(session):
        asyncio.run(renderer._render())

    return created[0]


def test_render_embedding_atlas_restricts_connection_by_default(widget_session) -> None:
    pytest.importorskip("embedding_atlas")
    import pandas as pd
    from embedding_atlas.widget import EmbeddingAtlasWidget

    def make_widget():  # noqa: ANN202
        df = pd.DataFrame({"x": [0.0, 1.0], "y": [1.0, 0.0]})
        widget = EmbeddingAtlasWidget(df, x="x", y="y")
        assert _duckdb_settings(widget, "lock_configuration") == {
            "lock_configuration": "false"
        }
        return widget

    widget = _render_embedding_atlas_widget(
        rw.render_embedding_atlas(), make_widget, widget_session
    )

    # Without the lockdown, any visitor could send SQL that reads/writes server
    # files (or re-enables external access) through the widget's connection
    assert _duckdb_settings(widget, "enable_external_access", "lock_configuration") == {
        "enable_external_access": "false",
        "lock_configuration": "true",
    }
    # The widget's own queries (e.g., selection()) still work
    assert len(widget.selection()) == 2


def test_render_embedding_atlas_allow_unrestricted_connection(widget_session) -> None:
    pytest.importorskip("embedding_atlas")
    import pandas as pd
    from embedding_atlas.widget import EmbeddingAtlasWidget

    def make_widget():  # noqa: ANN202
        df = pd.DataFrame({"x": [0.0, 1.0], "y": [1.0, 0.0]})
        return EmbeddingAtlasWidget(df, x="x", y="y")

    widget = _render_embedding_atlas_widget(
        rw.render_embedding_atlas(allow_unrestricted_connection=True),
        make_widget,
        widget_session,
    )

    assert _duckdb_settings(widget, "enable_external_access", "lock_configuration") == {
        "enable_external_access": "true",
        "lock_configuration": "false",
    }


def test_render_embedding_atlas_respects_author_locked_connection(
    widget_session,
) -> None:
    pytest.importorskip("embedding_atlas")
    import duckdb
    import pandas as pd
    from embedding_atlas.widget import EmbeddingAtlasWidget

    def make_widget():  # noqa: ANN202
        df = pd.DataFrame({"x": [0.0, 1.0], "y": [1.0, 0.0]})
        con = duckdb.connect()
        widget = EmbeddingAtlasWidget(df, x="x", y="y", connection=con)
        # An author that locks the configuration themselves (here, deliberately
        # leaving external access on) keeps their configuration: a locked
        # connection rejects further SET commands
        con.execute("SET lock_configuration = true")
        return widget

    widget = _render_embedding_atlas_widget(
        rw.render_embedding_atlas(), make_widget, widget_session
    )

    assert _duckdb_settings(widget, "enable_external_access", "lock_configuration") == {
        "enable_external_access": "true",
        "lock_configuration": "true",
    }


def test_render_bqplot_is_render_widget_base() -> None:
    renderer = rw.render_bqplot()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipyaladin_is_render_widget_base() -> None:
    renderer = rw.render_ipyaladin()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_k3d_is_render_widget_base() -> None:
    renderer = rw.render_k3d()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipycanvas_is_render_widget_base() -> None:
    renderer = rw.render_ipycanvas()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipyvolume_is_render_widget_base() -> None:
    renderer = rw.render_ipyvolume()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_itables_is_render_widget_base() -> None:
    renderer = rw.render_itables()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipydatagrid_is_render_widget_base() -> None:
    renderer = rw.render_ipydatagrid()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipyfilechooser_is_render_widget_base() -> None:
    renderer = rw.render_ipyfilechooser()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipyfilechooser_exported_from_package() -> None:
    import shinywidgets

    assert shinywidgets.render_ipyfilechooser is rw.render_ipyfilechooser
    assert "render_ipyfilechooser" in shinywidgets.__all__
    assert "render_ipyfilechooser" in rw.__all__


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


def test_render_ipysigma_is_render_widget_base() -> None:
    renderer = rw.render_ipysigma()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipycytoscape_is_render_widget_base() -> None:
    renderer = rw.render_ipycytoscape()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_keplergl_is_render_widget_base() -> None:
    renderer = rw.render_keplergl()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_lonboard_is_render_widget_base() -> None:
    renderer = rw.render_lonboard()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipyleaflet_is_render_widget_base() -> None:
    renderer = rw.render_ipyleaflet()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_ipyleaflet_renders_map_and_exposes_widget(widget_session) -> None:
    ipyleaflet = pytest.importorskip("ipyleaflet")

    r = rw.render_ipyleaflet()

    @r
    def _():  # noqa: ANN202
        return ipyleaflet.Map(center=(52, 360), zoom=4)

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert isinstance(r.widget, ipyleaflet.Map)
    assert r.widget.zoom == 4


def test_render_ipyleaflet_fills_unless_map_height_is_set(widget_session) -> None:
    ipyleaflet = pytest.importorskip("ipyleaflet")
    r = rw.render_ipyleaflet()

    with session_context(widget_session):

        @r
        def _():  # noqa: ANN202
            return ipyleaflet.Map()

        res = asyncio.run(r._render())
        assert res is not None and res["fill"] is True

        @r
        def _():  # noqa: ANN202
            return ipyleaflet.Map(layout=Layout(height="300px"))

        res = asyncio.run(r._render())
        assert res is not None and res["fill"] is False


def test_render_maplibre_is_render_widget_base() -> None:
    renderer = rw.render_maplibre()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_jscatter_is_render_widget_base() -> None:
    renderer = rw.render_jscatter()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_pygwalker_is_render_widget_base() -> None:
    renderer = rw.render_pygwalker()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_matplotlib_is_render_widget_base() -> None:
    renderer = rw.render_matplotlib()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_nglview_is_render_widget_base() -> None:
    renderer = rw.render_nglview()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_perspective_is_render_widget_base() -> None:
    renderer = rw.render_perspective()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_pythreejs_is_render_widget_base() -> None:
    renderer = rw.render_pythreejs()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_quak_is_render_widget_base() -> None:
    renderer = rw.render_quak()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_quak_coerces_dataframe(widget_session) -> None:
    quak = pytest.importorskip("quak")
    pd = pytest.importorskip("pandas")

    r = rw.render_quak()

    @r
    def _():  # noqa: ANN202
        return pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None

    assert r.widget is not None
    assert isinstance(r.widget, quak.Widget)
    assert r.widget.sql == 'SELECT * FROM "df"'


def test_render_quak_coerces_arrow_table(widget_session) -> None:
    quak = pytest.importorskip("quak")
    pa = pytest.importorskip("pyarrow")

    r = rw.render_quak()

    @r
    def _():  # noqa: ANN202
        return pa.table({"a": [1, 2, 3]})

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert isinstance(r.widget, quak.Widget)


def test_render_quak_passes_widget_through(widget_session) -> None:
    quak = pytest.importorskip("quak")
    pa = pytest.importorskip("pyarrow")

    r = rw.render_quak()
    created = []

    @r
    def _():  # noqa: ANN202
        w = quak.Widget(pa.table({"a": [1]}), table="mytable")
        created.append(w)
        return w

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert r.widget is created[0]


def test_render_quak_rejects_unsupported_value(widget_session) -> None:
    pytest.importorskip("quak")

    r = rw.render_quak()

    @r
    def _():  # noqa: ANN202
        return 42

    with session_context(widget_session):
        with pytest.raises(ValueError):
            asyncio.run(r._render())


def test_render_quak_missing_quak_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "quak", None)

    r = rw.render_quak()
    with pytest.raises(ImportError, match=r"pip install 'shinywidgets\[quak\]'"):
        r._as_widget(object())


def test_render_mosaic_widget_is_render_widget_base() -> None:
    renderer = rw.render_mosaic_widget()
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
        "bqplot",
        "holoviews",
        "hvplot",
        "ipycanvas",
        "jscatter",
        "jupyter_bokeh",
        "ipydatagrid",
        "ipympl",
        "k3d",
        "keplergl",
        "ipyleaflet",
        "maplibre",
        "matplotlib",
        "mosaic_widget",
        "panel",
        "perspective",
        "plotly",
        "plotnine",
        "pydeck",
        "pythreejs",
        "quak",
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


def test_render_leafmap_is_render_widget_base() -> None:
    renderer = rw.render_leafmap()
    assert isinstance(renderer, rwb.render_widget_base)


def _leafmap_backend_map(base, module: str, **kwargs):
    # leafmap's backends are subclasses of another package's widget, defined in
    # leafmap, so mimic one without needing leafmap installed
    return type("Map", (base,), {"__module__": module})(**kwargs)


def test_render_leafmap_treats_leafmaps_default_height_as_unset(widget_session) -> None:
    ipyleaflet = pytest.importorskip("ipyleaflet")
    r = rw.render_leafmap()

    with session_context(widget_session):
        # leafmap.Map sets Layout.height to 600px itself, which is leafmap's
        # default rather than user intent, so the map should still fill
        @r
        def _():  # noqa: ANN202
            return _leafmap_backend_map(
                ipyleaflet.Map,
                "leafmap.leafmap",
                layout=Layout(height="600px"),
            )

        res = asyncio.run(r._render())
        assert res is not None and res["fill"] is True
        assert r.widget.layout.height == "100%"

        # A height the user actually asked for is respected
        @r
        def _():  # noqa: ANN202
            return _leafmap_backend_map(
                ipyleaflet.Map,
                "leafmap.leafmap",
                layout=Layout(height="300px"),
            )

        res = asyncio.run(r._render())
        assert res is not None and res["fill"] is False
        assert r.widget.layout.height == "300px"


def test_render_leafmap_maplibre_backend_default_height_is_unset(
    widget_session,
) -> None:
    pytest.importorskip("maplibre")
    from maplibre.ipywidget import MapWidget

    r = rw.render_leafmap()

    with session_context(widget_session):

        @r
        def _():  # noqa: ANN202
            return _leafmap_backend_map(MapWidget, "leafmap.maplibregl", height="600px")

        res = asyncio.run(r._render())
        assert res is not None and res["fill"] is True
        assert r.widget.height == "100%"
