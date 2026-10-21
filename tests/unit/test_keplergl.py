from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.session import session_context
from shinywidgets._render_widget_base import set_layout_defaults

keplergl = pytest.importorskip("keplergl")
gpd = pytest.importorskip("geopandas")


class Unsupported:
    pass


def points() -> pd.DataFrame:
    return pd.DataFrame({"lat": [37.7, 37.8], "lon": [-122.4, -122.3], "n": [1, 2]})


def as_widget(widget_session: Session, value: object) -> keplergl.KeplerGl:
    with session_context(widget_session):
        return rw.render_keplergl()._as_widget(value)


def test_dataframe_becomes_keplergl_widget(widget_session: Session) -> None:
    df = points()
    widget = as_widget(widget_session, df)
    assert isinstance(widget, keplergl.KeplerGl)
    assert list(widget.data) == ["data"]
    assert widget.data["data"] is df


def test_geodataframe_becomes_keplergl_widget(widget_session: Session) -> None:
    df = points()
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
    )
    widget = as_widget(widget_session, gdf)
    assert isinstance(widget, keplergl.KeplerGl)
    assert widget.data["data"] is gdf


def test_keplergl_widget_passes_through(widget_session: Session) -> None:
    with session_context(widget_session):
        w = keplergl.KeplerGl(data={"pts": points()}, height=300)
    assert as_widget(widget_session, w) is w


def test_unsupported_value_errors(widget_session: Session) -> None:
    with pytest.raises(TypeError, match="ipywidget"):
        as_widget(widget_session, Unsupported())


def test_dataframe_without_keplergl_gives_install_hint(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "keplergl", None)
    with pytest.raises(ImportError, match=r"pip install 'keplergl>=0\.4\.0rc4'"):
        as_widget(widget_session, points())


def test_keplergl_failing_on_pkg_resources_points_to_newer_release(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # keplergl 0.3.x imports pkg_resources, which setuptools >= 81 no longer
    # ships; the fix is a newer keplergl, not (re)installing keplergl
    (tmp_path / "keplergl").mkdir()
    (tmp_path / "keplergl" / "__init__.py").write_text(
        "from pkg_resources import resource_string\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "keplergl", raising=False)
    monkeypatch.setitem(sys.modules, "pkg_resources", None)

    with pytest.raises(ImportError, match=r"keplergl>=0\.4\.0rc4") as exc_info:
        as_widget(widget_session, points())
    assert "pkg_resources" in str(exc_info.value)


def test_keplergl_older_than_0_4_is_rejected(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rw, "package_version", lambda name: "0.3.7")
    with pytest.raises(ImportError, match=r"requires keplergl>=0\.4\.0rc4"):
        as_widget(widget_session, points())


def test_layout_defaults_fill_unless_widget_has_explicit_height(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        default = keplergl.KeplerGl(data={"data": points()})
        explicit = keplergl.KeplerGl(data={"data": points()}, height=640)
        default_fill = set_layout_defaults(default)[1]
        explicit_fill = set_layout_defaults(explicit)[1]

    assert default_fill is True
    assert explicit_fill is False


def test_layout_defaults_keep_filling_after_browser_sets_height(
    widget_session: Session,
) -> None:
    # The browser writes the measured size into the `height` trait, so a widget
    # that was auto-sized the first time it was displayed must stay auto-sized
    # when the same instance is displayed again
    with session_context(widget_session):
        widget = keplergl.KeplerGl(data={"data": points()})
        first = set_layout_defaults(widget)[1]
        widget.height = 466
        second = set_layout_defaults(widget)[1]

    assert first is True
    assert second is True
