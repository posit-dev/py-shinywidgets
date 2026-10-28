from __future__ import annotations

import asyncio
import sys
from typing import Any

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

# The autouse `_locked_duckdb` fixture below replaces `rw.duckdb_settings`, so keep the
# real one for the test that exercises the settings query itself
real_duckdb_settings = rw.duckdb_settings

pytest.importorskip("pygwalker")

import pandas as pd  # noqa: E402

try:
    # pygwalker >= 0.6
    from pygwalker.services.anywidget_widget import (  # pyright: ignore[reportMissingImports]  # noqa: E402
        WalkerAnyWidget as _WalkerWidget,
    )
except ImportError:
    # pygwalker <= 0.5
    from pygwalker.api.anywidget import _WalkerWidget  # noqa: E402


@pytest.fixture(autouse=True)
def _offline_pygwalker(monkeypatch: pytest.MonkeyPatch):
    # pygwalker phones home (update check, usage events) when it builds a walker
    from pygwalker import GlobalVarManager

    monkeypatch.setattr(GlobalVarManager, "privacy", "offline")


@pytest.fixture(autouse=True)
def _locked_duckdb(monkeypatch: pytest.MonkeyPatch):
    # Rendering requires a locked-down DuckDB connection, and locking is permanent for
    # the process, so stand in for a locked connection instead of locking this one
    # (test_duckdb_settings* exercise the real settings query on a throwaway database)
    monkeypatch.setattr(rw, "duckdb_settings", lambda con=None: (False, True))


def render(value: object, widget_session) -> rw.render_pygwalker:
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return value

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    return r


def test_render_pygwalker_is_exported() -> None:
    assert shinywidgets.render_pygwalker is rw.render_pygwalker
    assert "render_pygwalker" in shinywidgets.__all__
    assert "render_pygwalker" in rw.__all__


def test_dataframe_is_coerced_to_walker_widget(widget_session) -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    r = render(df, widget_session)
    assert isinstance(r.widget, _WalkerWidget)
    assert r.value is df
    # getattr: r.widget is typed by pygwalker's public base (see WalkerWidget in
    # _render_widget.py), which doesn't declare the pygwalker-specific props trait
    props: Any = getattr(r.widget, "props")
    assert '"a"' in props


def test_dataframe_subclass_is_coerced_to_walker_widget(widget_session) -> None:
    class MyFrame(pd.DataFrame):
        pass

    r = render(MyFrame({"a": [1, 2, 3]}), widget_session)
    assert isinstance(r.widget, _WalkerWidget)


def test_polars_dataframe_gets_pandas_hint(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    # When the installed pygwalker can't read polars (its parser still uses dtype
    # groups that polars 1.0 removed; the fix, Kanaries/pygwalker@5055d702, is due
    # in 0.6), a polars frame is rejected with a pandas hint. Force the unsupported
    # case so the test holds on pygwalker versions that have the fix too.
    monkeypatch.setattr(rw, "polars_supported", lambda: False)
    # (A stand-in is enough: only the type's package and name are inspected.)
    DataFrame = type("DataFrame", (), {"__module__": "polars.dataframe.frame"})
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return DataFrame()

    with session_context(widget_session):
        with pytest.raises(TypeError, match=r"to_pandas\(\)"):
            asyncio.run(r._render())


def test_polars_supported_follows_installed_packages() -> None:
    import polars as pl
    from pygwalker.data_parsers import polars_parser

    # What's installed today: modern polars, unfixed pygwalker
    installed = hasattr(pl, "NUMERIC_DTYPES") or hasattr(
        polars_parser, "_is_numeric_dtype"
    )
    assert rw.polars_supported() is installed


def test_polars_supported_with_old_polars(monkeypatch: pytest.MonkeyPatch) -> None:
    import polars as pl

    # polars < 1.0 still has the dtype groups, so every pygwalker release works
    monkeypatch.setattr(pl, "NUMERIC_DTYPES", (), raising=False)
    assert rw.polars_supported() is True


def test_polars_supported_with_pygwalker_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    from pygwalker.data_parsers import polars_parser

    # Upstream's fix (Kanaries/pygwalker@5055d702) is merged and staged for pygwalker
    # 0.6, but no published release has it yet
    monkeypatch.setattr(
        polars_parser, "_is_numeric_dtype", lambda dtype: True, raising=False
    )
    assert rw.polars_supported() is True


def test_polars_dataframe_is_rendered_once_supported(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    from pygwalker.api.anywidget import walk

    # Stand in for a pygwalker release that can read polars: capability says yes and
    # pygwalker accepts the frame
    monkeypatch.setattr(rw, "polars_supported", lambda: True)
    with session_context(widget_session):
        accepted = walk(pd.DataFrame({"a": [1, 2, 3]}))
    monkeypatch.setattr(
        "pygwalker.api.anywidget.walk", lambda _df: accepted, raising=True
    )

    polars_frame = type("DataFrame", (), {"__module__": "polars.dataframe.frame"})()
    r = render(polars_frame, widget_session)
    assert r.widget is accepted
    # ... and it's hardened like any other walker widget
    comm = rw.walker_comm(accepted)
    assert comm is not None
    with pytest.raises(RuntimeError, match="'open_in_desktop' action"):
        comm._endpoint_map["open_in_desktop"]({})


def test_prebuilt_walker_widget_is_passed_through(widget_session) -> None:
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}), theme_key="vega")
    r = render(w, widget_session)
    assert r.widget is w


def test_is_walker_widget_recognizes_old_and_new_class_names() -> None:
    # pygwalker <= 0.5: pygwalker.api.anywidget._WalkerWidget; pygwalker >= 0.6:
    # pygwalker.services.anywidget_widget.WalkerAnyWidget. Stand-ins are enough:
    # only each class's package and name are inspected.
    old = type("_WalkerWidget", (), {"__module__": "pygwalker.api.anywidget"})()
    new = type(
        "WalkerAnyWidget", (), {"__module__": "pygwalker.services.anywidget_widget"}
    )()
    assert rw.is_walker_widget(old)
    assert rw.is_walker_widget(new)
    assert not rw.is_walker_widget(object())
    assert not rw.is_walker_widget(type("_WalkerWidget", (), {})())  # wrong package


def test_unsupported_value_raises_type_error(widget_session) -> None:
    class NotAFrame:
        pass

    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return NotAFrame()

    with session_context(widget_session):
        with pytest.raises(TypeError, match="coerce"):
            asyncio.run(r._render())


def test_missing_pygwalker_gives_install_hint(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    monkeypatch.setitem(sys.modules, "pygwalker.api.anywidget", None)
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return pd.DataFrame({"a": [1]})

    with session_context(widget_session):
        with pytest.raises(
            ImportError, match=r"pip install 'shinywidgets\[pygwalker\]'"
        ):
            asyncio.run(r._render())


def layout_defaults(widget_session, **layout: str) -> tuple[_WalkerWidget, bool]:
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}))
        for k, v in layout.items():
            setattr(w.layout, k, v)
        _, fill = rwb.set_layout_defaults(w)
    return w, fill


def test_layout_defaults_scroll_within_container(widget_session) -> None:
    # PyGWalker's UI has a minimum height, so it must scroll (not be clipped)
    # when the container, or an explicit height, is shorter than that
    w, fill = layout_defaults(widget_session)
    assert fill is True
    assert w.layout.overflow == "auto"
    assert w.layout.height == "100%"


def test_layout_defaults_respect_explicit_height(widget_session) -> None:
    w, fill = layout_defaults(widget_session, height="300px")
    assert fill is False
    assert w.layout.height == "300px"
    assert w.layout.overflow == "auto"


def test_layout_defaults_respect_explicit_overflow(widget_session) -> None:
    w, _ = layout_defaults(widget_session, overflow="visible")
    assert w.layout.overflow == "visible"


def test_layout_defaults_are_idempotent_across_renders(widget_session) -> None:
    # A widget that's rendered again (e.g., reused via session_lifetime()) must
    # keep filling, even though the first pass wrote layout.height
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}))
        fills = [rwb.set_layout_defaults(w)[1] for _ in range(3)]
    assert fills == [True, True, True]
    assert w.layout.height == "100%"


def test_duckdb_settings_reports_lockdown() -> None:
    import duckdb

    # A throwaway database, so locking its configuration doesn't outlive the test
    con = duckdb.connect(":memory:")
    try:
        assert real_duckdb_settings(con) == (True, False)
        con.execute("SET enable_external_access = false")
        assert real_duckdb_settings(con) == (False, False)
        con.execute("SET lock_configuration = true")
        assert real_duckdb_settings(con) == (False, True)
    finally:
        con.close()


def test_unlocked_duckdb_refuses_to_render(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    monkeypatch.setattr(rw, "duckdb_settings", lambda con=None: (True, False))
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return pd.DataFrame({"a": [1]})

    with session_context(widget_session):
        with pytest.raises(RuntimeError, match="lock_configuration"):
            asyncio.run(r._render())


def test_unlocked_duckdb_refuses_prebuilt_walker(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    from pygwalker.api.anywidget import walk

    # The browser's SQL runs on the same connection whichever way the widget is made
    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1]}))
    monkeypatch.setattr(rw, "duckdb_settings", lambda con=None: (True, False))
    with session_context(widget_session):
        with pytest.raises(RuntimeError, match="enable_external_access"):
            rw.render_pygwalker()._as_widget(w)


def test_non_walker_widget_needs_no_lockdown(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    from ipywidgets import IntSlider

    # Only a PyGWalker widget runs the browser's SQL, so don't demand a lockdown
    monkeypatch.setattr(rw, "duckdb_settings", lambda con=None: (True, False))
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return IntSlider()

    with session_context(widget_session):
        asyncio.run(r._render())
    assert isinstance(r.widget, IntSlider)


def walker_handlers(widget_session) -> tuple[_WalkerWidget, dict[str, Any]]:
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}))
    render(w, widget_session)
    comm = rw.walker_comm(w)
    assert comm is not None
    return w, comm._endpoint_map


def test_harden_walker_widget_needs_a_walker(widget_session) -> None:
    from ipywidgets import IntSlider

    # Fail closed if pygwalker's handlers can't be found: silently rendering an
    # unhardened widget would let a visitor at the server's credentials
    with session_context(widget_session):
        slider = IntSlider()
    with pytest.raises(RuntimeError, match="can't find its request handlers"):
        rw.harden_walker_widget(slider)


def _patch_across_versions(
    monkeypatch: pytest.MonkeyPatch,
    module_names: tuple[str, ...],
    attr: str,
    value: Any,
) -> None:
    """Patch `attr` on every importable module in `module_names`.

    pygwalker 0.6 moved internals between modules; safety-net patches should land
    wherever the target lives in the installed version (and be a no-op elsewhere).
    """
    import importlib

    for name in module_names:
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        monkeypatch.setattr(module, attr, value, raising=False)


def test_upload_spec_to_cloud_rejects_visitor_token(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    from pygwalker import GlobalVarManager

    def unexpected_set_config(_config: dict) -> None:
        raise AssertionError("a visitor's token reached set_config")

    # pygwalker writes the token to its config file; never let a test reach it.
    # It imports set_config into pygwalker.api.pygwalker on 0.5 and into
    # pygwalker.services.cloud_communication on 0.6; patch whichever exists.
    _patch_across_versions(
        monkeypatch,
        ("pygwalker.api.pygwalker", "pygwalker.services.cloud_communication"),
        "set_config",
        unexpected_set_config,
    )
    monkeypatch.setattr(GlobalVarManager, "kanaries_api_key", "")
    _, handlers = walker_handlers(widget_session)

    with pytest.raises(RuntimeError, match="Visitors can't set the server's"):
        handlers["upload_spec_to_cloud"]({"newToken": "visitor", "fileName": "f"})
    assert GlobalVarManager.kanaries_api_key == ""


def test_upload_spec_to_cloud_delegates_when_no_token(widget_session) -> None:
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1]}))
    comm = rw.walker_comm(w)
    assert comm is not None
    sent: list[dict] = []
    comm.register("upload_spec_to_cloud", lambda data: sent.append(data) or {})
    render(w, widget_session)

    # Saving with the app's own token still works; only the token is refused
    comm._endpoint_map["upload_spec_to_cloud"]({"newToken": "", "fileName": "f"})
    assert sent == [{"newToken": "", "fileName": "f"}]


def test_open_in_desktop_is_rejected(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    opened: list[object] = []
    fake_subprocess = type("S", (), {"call": lambda *a: opened.append(a)})
    # open_in_desktop's shell-out lives in pygwalker.api.pygwalker on 0.5 and in
    # pygwalker.services.desktop_import on 0.6; patch whichever exists.
    _patch_across_versions(
        monkeypatch,
        ("pygwalker.api.pygwalker", "pygwalker.services.desktop_import"),
        "subprocess",
        fake_subprocess,
    )
    _, handlers = walker_handlers(widget_session)

    with pytest.raises(RuntimeError, match="'open_in_desktop' action"):
        handlers["open_in_desktop"]({"spec": {}, "fields": {}})
    assert opened == []


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT a, COUNT(*) FROM pygwalker_mid_table GROUP BY a",
        "WITH x AS (SELECT a FROM pygwalker_mid_table) SELECT * FROM x",
        "(SELECT a FROM pygwalker_mid_table)",
        "SELECT a FROM pygwalker_mid_table UNION ALL SELECT a FROM pygwalker_mid_table",
        "SELECT * FROM main.pygwalker_mid_table",
    ],
)
def test_validate_visitor_sql_allows_reads_of_own_data(sql: str) -> None:
    rw.validate_visitor_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        # DDL persists in the shared in-memory database for every visitor to read
        "CREATE TABLE stash AS SELECT * FROM pygwalker_mid_table",
        "DROP TABLE pygwalker_mid_table",
        # Other statement kinds (SHOW would enumerate the shared namespace)
        "SHOW TABLES",
        "SET TimeZone = 'UTC'",
        # Multiple statements
        "SELECT 1 FROM pygwalker_mid_table; SELECT 2 FROM pygwalker_mid_table",
        # Tables other than the widget's own (another visitor's data, app views)
        "SELECT * FROM other_table",
        # Table-valued functions (empty table name in the parse tree)
        "SELECT * FROM read_csv_auto('/etc/passwd')",
        "SELECT * FROM duckdb_tables()",
        # Not SQL at all
        "not a query",
        "",
    ],
)
def test_validate_visitor_sql_rejects_everything_else(sql: str) -> None:
    with pytest.raises(RuntimeError, match="isn't a single"):
        rw.validate_visitor_sql(sql)


def test_get_datas_validates_visitor_sql(widget_session) -> None:
    _, handlers = walker_handlers(widget_session)

    with pytest.raises(RuntimeError, match="isn't a single"):
        handlers["get_datas"]({"sql": "CREATE TABLE stash AS SELECT 1"})
    with pytest.raises(RuntimeError, match="isn't a single"):
        handlers["get_datas"]({"sql": "SELECT * FROM pg_catalog.pg_tables"})
    # A legitimate read of the widget's own data still goes through
    out = handlers["get_datas"]({"sql": "SELECT a FROM pygwalker_mid_table ORDER BY a"})
    assert "1" in str(out) and "3" in str(out)


def test_batch_get_datas_validates_every_query(widget_session) -> None:
    _, handlers = walker_handlers(widget_session)

    with pytest.raises(RuntimeError, match="isn't a single"):
        handlers["batch_get_datas_by_sql"](
            {
                "queryList": [
                    "SELECT a FROM pygwalker_mid_table",
                    "CREATE TABLE stash AS SELECT 1",
                ]
            }
        )

    # ... and the expected request shape still reaches duckdb
    out = handlers["batch_get_datas_by_sql"](
        {"queryList": ["SELECT a FROM pygwalker_mid_table ORDER BY a"]}
    )
    assert "1" in str(out) and "3" in str(out)


def test_export_dataframe_by_sql_validates_visitor_sql(widget_session) -> None:
    _, handlers = walker_handlers(widget_session)

    with pytest.raises(RuntimeError, match="isn't a single"):
        handlers["export_dataframe_by_sql"]({"sql": "ATTACH 'evil.db'"})


def test_pygwalker_internal_contracts_hold(widget_session) -> None:
    """Check the pygwalker internals shinywidgets relies on against the installed
    version, so a release that changes them fails loudly here.

    At render time these drift silently: a renamed endpoint is skipped (leaving
    visitor SQL unvalidated), a renamed view makes the validator reject every
    query, and a renamed token field would let visitor credentials through.
    """
    from pathlib import Path

    import pygwalker
    from pygwalker.data_parsers.pandas_parser import PandasDataFrameDataParser

    # The view validate_visitor_sql allow-lists must be the one pygwalker
    # registers each widget's data under
    parser = PandasDataFrameDataParser(
        pd.DataFrame({"a": [1]}),
        field_specs=[],
        infer_string_to_date=False,
        infer_number_to_dimension=False,
        other_params={},
    )
    assert parser.placeholder_table_name == rw._WALKER_TABLE_NAME

    # Every handler shinywidgets rejects, validates, or relies on must be
    # registered by the installed pygwalker
    _, handlers = walker_handlers(widget_session)
    for action in (
        *rw._WALKER_SQL_ACTIONS,
        *rw._WALKER_BLOCKED_ACTIONS,
        "upload_spec_to_cloud",
        "get_datas_by_payload",
    ):
        assert action in handlers, (
            f"pygwalker no longer registers a {action!r} handler, "
            "so shinywidgets' hardening silently doesn't apply to it"
        )

    # The token field the rejection wrapper looks for must be one pygwalker
    # actually reads (a rename would let a visitor set the server's credentials)
    package = Path(pygwalker.__file__).parent
    assert any(
        "newToken" in path.read_text(encoding="utf-8", errors="ignore")
        for path in package.rglob("*.py")
    ), "pygwalker no longer reads 'newToken'; check the rejection wrapper"


def test_hardening_a_widget_twice_still_rejects(widget_session) -> None:
    w, handlers = walker_handlers(widget_session)
    rw.harden_walker_widget(w)

    with pytest.raises(RuntimeError, match="'open_in_desktop' action"):
        handlers["open_in_desktop"]({})
    with pytest.raises(RuntimeError, match="Visitors can't set the server's"):
        handlers["upload_spec_to_cloud"]({"newToken": "visitor"})
