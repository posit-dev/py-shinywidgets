from __future__ import annotations

import ast
import asyncio
import json
import sys
from typing import Any

import ipywidgets as widgets
import mols2grid
import pandas as pd
import pytest
import shinywidgets._render_widget as rw
from mols2grid.molgrid import MolGrid
from mols2grid.widget import MolGridWidget
from shiny import Session
from shiny.session import session_context

DF = pd.DataFrame(
    {
        "SMILES": ["CCO", "c1ccccc1", "CCC(C)CC"],
        "ID": ["ethanol", "benzene", "isopentane"],
    }
)


def render(renderer: rw.render_mols2grid, fn: Any, session: Session) -> Any:
    renderer(fn)
    with session_context(session):
        return asyncio.run(renderer._render())


def test_render_mols2grid_coerces_dataframe(widget_session: Session) -> None:
    r = rw.render_mols2grid()
    res = render(r, lambda: DF, widget_session)

    assert isinstance(res, dict)
    assert isinstance(r.widget, widgets.Box)
    molgrid_widget, html = r.widget.children
    assert isinstance(molgrid_widget, MolGridWidget)
    assert isinstance(html, widgets.HTML)
    # The inner width hint keeps the iframe from collapsing to its 300px
    # replaced-element default inside an inline-flex container
    assert html.layout.width == "100%"
    assert r.widget.layout.width == "100%"

    assert isinstance(r.grid, MolGrid)
    assert r.grid.widget is molgrid_widget
    # Sessions get their own grid name (mols2grid's selection registry is
    # process-global), never the collision-prone "default"
    assert molgrid_widget.grid_id.startswith("shiny")
    assert molgrid_widget.grid_id != "default"


def test_iframe_document_is_escaped(widget_session: Session) -> None:
    r = rw.render_mols2grid()
    render(r, lambda: DF, widget_session)

    assert isinstance(r.widget, widgets.Box)
    html = r.widget.children[1]
    assert isinstance(html, widgets.HTML)
    # The grid document is escaped into the iframe's srcdoc attribute (the
    # unescaped <style> before it is IPython's own Jupyter-integration shim)
    assert 'srcdoc="' in html.value
    assert "&lt;html" in html.value
    assert "<script" not in html.value


def test_render_mols2grid_passes_through_molgrid(widget_session: Session) -> None:
    with session_context(widget_session):
        grid = mols2grid.MolGrid(DF, name="my-grid")

    r = rw.render_mols2grid()
    render(r, lambda: grid, widget_session)

    assert r.grid is grid
    assert grid.widget.grid_id == "my-grid"


def test_render_mols2grid_errors_on_default_grid_name(widget_session: Session) -> None:
    with session_context(widget_session):
        grid = mols2grid.MolGrid(DF)

    r = rw.render_mols2grid()
    with pytest.raises(ValueError, match="default grid name"):
        render(r, lambda: grid, widget_session)


def test_render_kwargs_reach_the_grid_document(widget_session: Session) -> None:
    r = rw.render_mols2grid(subset=["ID"], tooltip=["ID"], n_items_per_page=2)
    render(r, lambda: DF, widget_session)

    assert isinstance(r.widget, widgets.Box)
    html = r.widget.children[1]
    assert isinstance(html, widgets.HTML)
    # Escaped for the srcdoc attribute, so look for the unescaped needles
    import html as html_mod

    doc = html_mod.unescape(html.value)
    assert "'data-ID'" in doc
    assert '"data-ID": "ethanol"' in doc


def test_grid_kwargs_reach_the_molgrid_constructor(widget_session: Session) -> None:
    r = rw.render_mols2grid(size=(150, 100), name="my-grid", cache_selection=True)
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    assert r.grid.img_size == (150, 100)
    # A name passed to the decorator overrides the session-unique default
    assert r.grid.widget.grid_id == "my-grid"


def test_draw_options_reach_the_molgrid_constructor(widget_session: Session) -> None:
    # mols2grid.display() hands its leftover kwargs to MolGrid(), whose remaining
    # **kwargs are RDKit draw options; without the same split they'd be forwarded
    # to the renderer instead (and raise a TypeError)
    r = rw.render_mols2grid(addStereoAnnotation=True, subset=["ID"])
    assert r.grid_kwargs == {"addStereoAnnotation": True}
    assert r.render_kwargs == {"subset": ["ID"]}

    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    draw_opts = json.loads(str(getattr(r.grid, "json_draw_opts")))
    assert draw_opts["addStereoAnnotation"] is True
    # A rendering option must not leak into the drawing options
    assert "subset" not in draw_opts


def test_prerender_draw_options_reach_rdkit(widget_session: Session) -> None:
    # With prerender=True, MolGrid() applies its **kwargs to a real MolDrawOptions
    r = rw.render_mols2grid(prerender=True, addAtomIndices=True)
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    opts = getattr(r.grid, "MolDrawOptions")
    assert opts.addAtomIndices is True


def test_rendering_option_wins_when_a_name_is_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # mols2grid pops its rendering options first, so a name that both a MolGrid()
    # option and a rendering option would accept is treated as a rendering option
    monkeypatch.setattr(rw, "_mols2grid_render_kwargs", lambda: frozenset({"size"}))
    r = rw.render_mols2grid(size=(150, 100), subset=["ID"])

    assert r.render_kwargs == {"size": (150, 100)}
    assert r.grid_kwargs == {"subset": ["ID"]}


def test_kwarg_split_follows_mols2grid_signatures() -> None:
    # The split is derived from mols2grid's own signatures, so a mols2grid upgrade
    # can't silently misroute an option (e.g. by adding a MolGrid() constructor
    # option that this package still thinks is a rendering option)
    import inspect

    render_params = rw._mols2grid_render_kwargs()
    assert {"subset", "tooltip", "sort_by", "n_items_per_page"} <= render_params

    ctor_params = set(inspect.signature(MolGrid.__init__).parameters) - {
        "self",
        "df",
        "smiles_col",
        "mol_col",
        "kwargs",
    }
    assert not (ctor_params & render_params)


def test_prerender_still_renders(widget_session: Session) -> None:
    r = rw.render_mols2grid(prerender=True)
    render(r, lambda: DF, widget_session)

    assert isinstance(r.widget, widgets.Box)
    html = r.widget.children[1]
    assert isinstance(html, widgets.HTML)
    # prerender draws the molecules server-side, inlining SVG into the doc
    assert "&lt;?xml" in html.value


def test_custom_smiles_col(widget_session: Session) -> None:
    df = DF.rename(columns={"SMILES": "smiles"})
    r = rw.render_mols2grid(smiles_col="smiles")
    render(r, lambda: df, widget_session)

    assert isinstance(r.grid, MolGrid)
    assert r.grid.smiles_col == "smiles"


def test_mol_col(widget_session: Session) -> None:
    from rdkit import Chem

    df = pd.DataFrame({"mol": [Chem.MolFromSmiles(s) for s in DF["SMILES"]]})
    # smiles_col=None with a mol_col would trip a mols2grid 2.2.0 bug (it
    # creates a column named NaN); the renderer names the generated SMILES
    # column instead
    r = rw.render_mols2grid(smiles_col=None, mol_col="mol")
    render(r, lambda: df, widget_session)

    assert isinstance(r.grid, MolGrid)
    assert "SMILES" in r.grid.dataframe.columns


def test_missing_smiles_column_raises(widget_session: Session) -> None:
    r = rw.render_mols2grid()
    with pytest.raises((KeyError, ValueError)):
        render(r, lambda: pd.DataFrame({"ID": ["a"]}), widget_session)


def test_render_mols2grid_rejects_bad_return_type(widget_session: Session) -> None:
    r = rw.render_mols2grid()

    @r
    def _():  # noqa: ANN202
        # mols2grid.display() returns an IPython HTML object, not a grid
        return mols2grid.display(DF)

    with session_context(widget_session):
        with pytest.raises(TypeError, match="MolGrid or a pandas.DataFrame"):
            asyncio.run(r._render())


def test_render_mols2grid_requires_mols2grid_package(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "mols2grid", None)
    r = rw.render_mols2grid()

    @r
    def _():  # noqa: ANN202
        return DF

    with session_context(widget_session):
        with pytest.raises(
            ImportError, match=r"pip install 'shinywidgets\[mols2grid\]'"
        ):
            asyncio.run(r._render())


def test_use_iframe_false_is_overridden(widget_session: Session) -> None:
    r = rw.render_mols2grid(use_iframe=False)
    with pytest.warns(UserWarning, match="use_iframe"):
        render(r, lambda: DF, widget_session)

    assert isinstance(r.widget, widgets.Box)
    html = r.widget.children[1]
    assert isinstance(html, widgets.HTML)
    assert "srcdoc" in html.value


def test_selection_trait_parses_with_ast_literal_eval(
    widget_session: Session,
) -> None:
    r = rw.render_mols2grid()
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    # The selection trait is a repr string with unquoted keys, not JSON
    r.grid.widget.selection = str({0: "CCO", 2: "CCC(C)CC"})
    assert ast.literal_eval(r.grid.widget.selection) == {0: "CCO", 2: "CCC(C)CC"}
    with pytest.raises(json.JSONDecodeError):
        json.loads(r.grid.widget.selection)


def test_grid_is_read_only() -> None:
    r = rw.render_mols2grid()
    with pytest.raises(RuntimeError, match=r"`grid` attribute .* read only"):
        r.grid = object()  # type: ignore[misc]


def test_grid_is_none_before_render() -> None:
    r = rw.render_mols2grid()
    assert r.grid is None


def test_grid_names_are_unique_per_output_in_a_session(
    widget_session: Session,
) -> None:
    # Two grids in one session share the browser window, so a shared name
    # would cross-wire their selections (mols2grid keys window models by name)
    r1 = rw.render_mols2grid()
    r2 = rw.render_mols2grid()

    def grid_a():  # noqa: ANN202
        return DF

    def grid_b():  # noqa: ANN202
        return DF

    render(r1, grid_a, widget_session)
    render(r2, grid_b, widget_session)

    assert isinstance(r1.grid, MolGrid) and isinstance(r2.grid, MolGrid)
    assert r1.grid.widget.grid_id != r2.grid.widget.grid_id

    # A re-render of the same output keeps its name (so mols2grid's global
    # selection registry doesn't grow per render)
    first = r1.grid.widget.grid_id
    render(r1, grid_a, widget_session)
    assert isinstance(r1.grid, MolGrid)
    assert r1.grid.widget.grid_id == first


def test_session_end_prunes_the_mols2grid_selection_registry(
    widget_session: Session,
) -> None:
    from mols2grid.select import register

    r = rw.render_mols2grid()
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    name = r.grid.widget.grid_id
    # mols2grid records selections in a module-level dict keyed by grid name, and
    # never prunes it; without the renderer's cleanup, one (potentially large)
    # selection dict would survive every session a server has ever served
    r.grid.widget.selection = str({0: "CCO"})
    assert register.SELECTIONS[name] == {0: "CCO"}

    asyncio.run(widget_session.close())

    assert name not in register.SELECTIONS


def test_grid_names_are_namespaced_per_module(widget_session: Session) -> None:
    # Output ids are only unique within their namespace: two module instances in one
    # session can each register an output named "grid", and they share a browser
    # window, so a name built from the bare output id would cross-wire them
    from shiny import module

    renderers: dict[str, rw.render_mols2grid] = {}

    @module.server
    def mod_server(input: Any, output: Any, session: Session) -> None:
        @rw.render_mols2grid()
        def grid():  # noqa: ANN202
            return DF

        renderers[str(session.ns)] = grid

    with session_context(widget_session):
        mod_server("mod_a")
        mod_server("mod_b")

    names: dict[str, str] = {}
    for mod, r in renderers.items():
        # Not the render() helper: re-decorating would recapture the output id
        # from the root session, rather than the module's namespace
        with session_context(widget_session):
            asyncio.run(r._render())
        assert isinstance(r.grid, MolGrid)
        names[mod] = r.grid.widget.grid_id

    assert names["mod_a"] != names["mod_b"]
    assert "mod_a" in names["mod_a"]
    assert "mod_b" in names["mod_b"]


def test_grid_names_follow_explicit_output_ids(widget_session: Session) -> None:
    # @output(id=...) assigns the final output id after the renderer is created,
    # so two functions with the same name (e.g. `_`) registered under different
    # explicit ids must still get distinct grid names
    def _():  # noqa: ANN202
        return DF

    with session_context(widget_session):
        r1 = rw.render_mols2grid()(_)
        r2 = rw.render_mols2grid()(_)
        widget_session.output(id="grid_a")(r1)
        widget_session.output(id="grid_b")(r2)
        asyncio.run(r1._render())
        asyncio.run(r2._render())

    assert isinstance(r1.grid, MolGrid) and isinstance(r2.grid, MolGrid)
    assert "grid_a" in r1.grid.widget.grid_id
    assert "grid_b" in r2.grid.widget.grid_id


def test_grid_names_disambiguate_unicode_output_ids(widget_session: Session) -> None:
    # The name slug replaces non-ASCII with '-', so without a digest distinct
    # ids like café/cafè would collapse to the same name and cross-wire
    # their selections
    def _():  # noqa: ANN202
        return DF

    with session_context(widget_session):
        r1 = rw.render_mols2grid()(_)
        r2 = rw.render_mols2grid()(_)
        widget_session.output(id="café")(r1)
        widget_session.output(id="cafè")(r2)
        asyncio.run(r1._render())
        asyncio.run(r2._render())

    assert isinstance(r1.grid, MolGrid) and isinstance(r2.grid, MolGrid)
    assert r1.grid.widget.grid_id != r2.grid.widget.grid_id


def test_selection_survives_rerender_with_generated_name(
    widget_session: Session,
) -> None:
    # The generated name is stable across re-renders, and the renderer defaults
    # cache_selection=True so mols2grid restores the selection instead of
    # clearing it (its own default) when the grid is reconstructed
    r = rw.render_mols2grid()
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    r.grid.widget.selection = str({0: "CCO"})

    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    assert r.grid.widget.selection == str({0: "CCO"})


def test_cached_selection_cleared_when_rows_change(
    widget_session: Session,
) -> None:
    # A cached selection is positional ({0: "CCO"} refers to a row, not a
    # molecule), so restoring it onto a different row-to-molecule mapping
    # would select the wrong molecules
    r = rw.render_mols2grid()
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    r.grid.widget.selection = str({0: "CCO"})

    # Same rows, same order: preserved
    render(r, lambda: DF.copy(), widget_session)
    assert isinstance(r.grid, MolGrid)
    assert r.grid.widget.selection == str({0: "CCO"})

    # Reordered rows: the cached selection would now point at benzene
    render(r, lambda: DF.iloc[::-1].reset_index(drop=True), widget_session)
    assert isinstance(r.grid, MolGrid)
    assert r.grid.widget.selection == "{}"


def test_redisplay_does_not_accumulate_callback_observers(
    widget_session: Session,
) -> None:
    # mols2grid's display() observes callback_kwargs with a new partial every
    # time and never unobserves, so re-displaying a supplied grid would
    # invoke the callback once per past display
    calls: list[Any] = []

    with session_context(widget_session):
        grid = mols2grid.MolGrid(DF, name="callback-dedupe-grid")

    r = rw.render_mols2grid(callback=calls.append)
    render(r, lambda: grid, widget_session)
    render(r, lambda: grid, widget_session)
    render(r, lambda: grid, widget_session)

    grid.widget.callback_kwargs = str({"idx": 0})

    assert calls == [{"idx": 0}]


def test_cache_selection_explicitly_disabled_clears_on_rerender(
    widget_session: Session,
) -> None:
    r = rw.render_mols2grid(cache_selection=False)
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    r.grid.widget.selection = str({0: "CCO"})

    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    assert r.grid.widget.selection == "{}"


def test_explicit_name_keeps_mols2grid_cache_default(
    widget_session: Session,
) -> None:
    # An explicit name may be deliberately shared across grids, so the
    # renderer must not force cache_selection on it
    r = rw.render_mols2grid(name="no-forced-cache-grid")
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    r.grid.widget.selection = str({0: "CCO"})

    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    assert r.grid.widget.selection == "{}"


def test_session_end_prunes_selection_registry_for_supplied_grid(
    widget_session: Session,
) -> None:
    from mols2grid.select import register

    with session_context(widget_session):
        grid = mols2grid.MolGrid(DF, name="supplied-cleanup-grid")

    r = rw.render_mols2grid()
    render(r, lambda: grid, widget_session)

    grid.widget.selection = str({0: "CCO"})
    assert register.SELECTIONS["supplied-cleanup-grid"] == {0: "CCO"}

    asyncio.run(widget_session.close())

    assert "supplied-cleanup-grid" not in register.SELECTIONS


def test_session_end_prunes_selection_registry_for_explicit_name(
    widget_session: Session,
) -> None:
    from mols2grid.select import register

    # An explicit `name` replaces the generated one, so the session-end cleanup
    # has to be registered under the effective name, not the generated one
    r = rw.render_mols2grid(name="explicit-name-cleanup-grid")
    render(r, lambda: DF, widget_session)

    assert isinstance(r.grid, MolGrid)
    r.grid.widget.selection = str({0: "CCO"})
    assert register.SELECTIONS["explicit-name-cleanup-grid"] == {0: "CCO"}

    asyncio.run(widget_session.close())

    assert "explicit-name-cleanup-grid" not in register.SELECTIONS


def test_grid_name_stable_within_and_unique_across_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        def __init__(self, id: str) -> None:
            self.id = id

    monkeypatch.setattr(rw, "get_current_session", lambda: FakeSession("a b/c"))
    assert rw.grid_name() == "shiny-a-b-c"
    # Stable across re-renders of the same session (so mols2grid's global
    # selection registry doesn't grow per render)
    assert rw.grid_name() == rw.grid_name()

    monkeypatch.setattr(rw, "get_current_session", lambda: FakeSession("d"))
    assert rw.grid_name() != "shiny-a-b-c"

    monkeypatch.setattr(rw, "get_current_session", lambda: None)
    assert rw.grid_name() == "shiny"
