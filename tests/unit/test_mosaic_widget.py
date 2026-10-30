from __future__ import annotations

import asyncio

import ipywidgets as widgets
import pytest
import shinywidgets
import shinywidgets._render_widget as rw
from shiny.session import session_context

pytest.importorskip("mosaic_widget")
from mosaic_widget import MosaicWidget  # noqa: E402

SPEC = {"plot": [{"mark": "dot", "data": {"from": "t"}, "x": "x", "y": "y"}]}


def test_render_mosaic_widget_is_exported() -> None:
    assert "render_mosaic_widget" in rw.__all__
    assert "render_mosaic_widget" in shinywidgets.__all__
    assert shinywidgets.render_mosaic_widget is rw.render_mosaic_widget


def test_render_mosaic_widget_fills_by_default(widget_session) -> None:
    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC)

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is True
    assert res["widget_pkg"] == "mosaic_widget"
    assert isinstance(r.widget, MosaicWidget)
    assert r.widget is r.value


def test_render_mosaic_widget_layout_height_disables_fill(widget_session) -> None:
    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC, layout=widgets.Layout(height="300px"))

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert res["fill"] is False


def _sent_messages(widget, monkeypatch: pytest.MonkeyPatch) -> list:  # noqa: ANN001, ANN202
    sent: list = []
    monkeypatch.setattr(
        widget, "send", lambda content, buffers=None: sent.append((content, buffers))
    )
    return sent


def _duckdb_settings(con, *names: str) -> dict:  # noqa: ANN001, ANN202
    quoted = ", ".join(f"'{name}'" for name in names)
    rows = con.execute(
        f"SELECT name, value FROM duckdb_settings() WHERE name IN ({quoted})"
    ).fetchall()
    return dict(rows)


def test_render_mosaic_widget_restricts_connection_by_default(
    widget_session, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    secret = tmp_path / "secret.csv"
    secret.write_text("a\n1\n")

    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC)

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None

    widget = r.widget
    sent = _sent_messages(widget, monkeypatch)
    # Without the lockdown, this is exactly the message the browser sends for
    # any Mosaic query -- and it would read the file straight off server disk
    widget._handle_custom_msg(
        {"uuid": "1", "sql": f"SELECT * FROM read_csv('{secret}')", "type": "arrow"},
        [],
    )
    content, _ = sent[0]
    assert "Permission Error" in content["error"]


def test_render_mosaic_widget_allow_unrestricted_connection(
    widget_session, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    pa = pytest.importorskip("pyarrow")

    secret = tmp_path / "secret.csv"
    secret.write_text("a\n1\n")

    r = rw.render_mosaic_widget(allow_unrestricted_connection=True)

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC)

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None

    widget = r.widget
    sent = _sent_messages(widget, monkeypatch)
    widget._handle_custom_msg(
        {"uuid": "1", "sql": f"SELECT * FROM read_csv('{secret}')", "type": "arrow"},
        [],
    )
    content, buffers = sent[0]
    assert "error" not in content
    table = pa.ipc.open_stream(buffers[0]).read_all()
    assert table.column("a").to_pylist() == [1]


def test_render_mosaic_widget_respects_author_locked_connection(
    widget_session,
) -> None:
    import duckdb

    con = duckdb.connect()
    # An author that locks the configuration themselves (here, deliberately
    # leaving external access on) keeps their configuration: a locked
    # connection rejects further SET commands
    con.execute("SET lock_configuration = true")

    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC, con=con)

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None

    assert _duckdb_settings(con, "enable_external_access", "lock_configuration") == {
        "enable_external_access": "true",
        "lock_configuration": "true",
    }


def test_render_mosaic_widget_lockdown_is_permanent_on_a_shared_connection(
    widget_session,
) -> None:
    # DuckDB's lockdown can't be undone, and applies to the whole database, not
    # just the cursor it was set on -- so rendering a widget built on a
    # connection the app keeps using elsewhere locks that connection for good
    import duckdb

    shared = duckdb.connect()
    r = rw.render_mosaic_widget()

    @r
    def _() -> MosaicWidget:
        return MosaicWidget(SPEC, con=shared)

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None

    with pytest.raises(duckdb.InvalidInputException, match="locked"):
        shared.execute("SET memory_limit = '1GB'")
