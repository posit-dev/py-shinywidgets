from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional, cast
from weakref import WeakSet

from htmltools import HTMLDependency
from ipywidgets.widgets.widget import Widget
from packaging.version import Version
from shiny.session import get_current_session

from ._dependencies import widget_pkg

if TYPE_CHECKING:
    from bokeh.models import LayoutDOM
    from jupyter_bokeh import BokehModel
    from matplotlib.figure import Figure
    from panel.viewable import Viewable

__all__ = ("as_widget",)

MPL_CLEANUP_CANVASES: WeakSet[Widget] = WeakSet()


# Some objects aren't directly renderable as an ipywidget, but in some cases,
# we can coerce them into one
def as_widget(x: object) -> Widget:
    """
    Coerce an object into an `ipywidgets.Widget`.

    If `x` is already a `Widget`, it is returned as-is. Otherwise, the object is
    coerced based on the package it comes from:

    * altair `Chart` -> `altair.JupyterChart`
    * bokeh model (e.g., `bokeh.plotting.figure`) -> `jupyter_bokeh.BokehModel`
    * holoviews/hvplot object -> bokeh model (via panel)
    * lonboard layer -> `lonboard.Map`
    * maplibre `Map` -> `maplibre.ipywidget.MapWidget`
    * matplotlib `Figure` or `Axes` (or a seaborn figure-level grid) ->
      `ipympl.backend_nbagg.Canvas`
    * panel pane/viewable -> bokeh model
    * plotly `Figure` -> `plotly.graph_objects.FigureWidget`
    * pydeck `Deck` -> `pydeck.widget.DeckGLWidget` (pydeck <= 0.8 only; pydeck
      v0.9 removed its widget, so this raises a `TypeError` that points to
      alternatives)

    Parameters
    ----------
    x
        The object to coerce.

    Returns
    -------
    :
        An `ipywidgets.Widget`.

    Raises
    ------
    TypeError
        If `x` can't be coerced into a `Widget` (the error message points to shiny's
        ``@render.ui`` decorator as a fallback for objects with an HTML repr).
    """
    if isinstance(x, Widget):
        # A Canvas may still need its FigureManager and pyplot cleanup
        if is_ipympl_canvas(x):
            return as_widget_mpl(x)
        # A lonboard layer needs a Map to display
        if any(widget_pkg(cls) == "lonboard" for cls in type(x).__mro__):
            return as_widget_lonboard(x)
        return x

    pkg = widget_pkg(x)

    _as_widget = AS_WIDGET_MAP.get(pkg, None)
    if _as_widget is None and any(
        widget_pkg(base) == "matplotlib" for base in type(x).__mro__
    ):
        _as_widget = as_widget_mpl
    # e.g., a pn.viewable.Viewer or pn.custom.JSComponent subclass defined in the app
    if _as_widget is None and any(
        widget_pkg(base) == "panel" for base in type(x).__mro__
    ):
        _as_widget = as_widget_panel
    if _as_widget is None:
        msg = f"Don't know how to coerce {x} into a ipywidget.Widget object."
        if callable(getattr(x, "_repr_html_", None)):
            msg += " Instead of using shinywidgets to render this object, try using shiny's @render.ui decorator "
            msg += " https://shiny.posit.co/py/api/ui.output_ui.html#shiny.ui.output_ui"
        raise TypeError(msg)

    res = _as_widget(x)

    if not isinstance(res, Widget):
        raise TypeError(
            f"Failed to coerce {x} (an object from package {pkg}) into a ipywidget.Widget object."
        )

    return res


def as_widget_altair(x: object) -> Optional[Widget]:
    try:
        from altair import JupyterChart
    except ImportError:
        raise RuntimeError(
            "Failed to import altair.JupyterChart (do you need to pip install -U altair?)"
        )

    return JupyterChart(x)  # type: ignore


def as_widget_bokeh(x: object) -> Optional[Widget]:
    # TODO: ideally we'd do this in set_layout_defaults() but doing
    # `BokehModel(x)._model.sizing_mode = "stretch_both"`
    # there, but that doesn't seem to work??
    from bokeh.plotting import figure

    if isinstance(x, figure):
        x.sizing_mode = "stretch_both"  # type: ignore

    return bokeh_model_class(context="bokeh")(cast("LayoutDOM", x))


def as_widget_panel(x: object) -> Optional[Widget]:
    return panel_to_widget(
        x,
        context="panel",
        missing_panel_message=(
            "Install the panel package to use panel objects with shinywidgets: "
            "pip install panel"
        ),
    )


def as_widget_holoviews(x: object) -> Optional[Widget]:
    return panel_to_widget(
        x,
        context="holoviews/hvplot",
        missing_panel_message=(
            "Rendering holoviews/hvplot objects requires the panel package "
            "(hvplot renders through panel). Install it with: pip install panel"
        ),
    )


def as_widget_lonboard(x: object) -> Widget:
    # lonboard is guaranteed to be installed here since this function is only
    # called when x comes from the lonboard package
    from lonboard import BaseLayer, Map  # pyright: ignore[reportMissingImports]

    if isinstance(x, BaseLayer):
        x = Map(x)

    if not isinstance(x, Widget):
        raise TypeError(f"Don't know how to coerce {x} into a lonboard Map object.")

    return x


def as_widget_maplibre(x: object) -> Widget:
    # maplibre is guaranteed to be installed here since this function is only
    # called when x comes from the maplibre package
    from maplibre.map import Map

    if not isinstance(x, Map):
        raise TypeError(f"Don't know how to coerce {x} into a maplibre Map object.")

    try:
        from maplibre.ipywidget import MapWidget
    except (ImportError, NameError):
        # maplibre.ipywidget requires anywidget, and unfortunately raises a
        # NameError (not ImportError) when it's missing
        raise ImportError(
            "Install maplibre's anywidget extra to use maplibre with shinywidgets (pip install 'maplibre[anywidget]')."
        )

    # MapWidget.__init__() expects MapOptions (not the dict that Map stores), and
    # provides no way to pass queued calls, so transfer the state after
    # construction. Map.to_dict() returns exactly the state the frontend needs
    # (map options plus the queued JS calls that get replayed on render). Copy
    # it, since to_dict() returns x's own containers, and a module-level Map
    # would otherwise collect every session's widget calls.
    state = x.to_dict()
    res = MapWidget()
    res.map_options = dict(state["mapOptions"])
    res._message_queue = list(state["calls"])
    return res


def as_widget_mpl(x: object) -> Widget:
    from matplotlib.figure import Figure, SubFigure

    # The renderer imports this module, so defer this circular import.
    from ._render_widget_base import is_closed_widget

    # Several higher-level APIs return something that holds the figure: an Axes
    # (e.g., pandas.DataFrame.plot()), an ipympl Canvas, or a seaborn grid
    # (e.g., seaborn.relplot())
    if not isinstance(x, Figure):
        x = getattr(x, "figure", x)
        if isinstance(x, SubFigure):
            x = x.figure

    if not isinstance(x, Figure):
        raise TypeError(
            f"Don't know how to coerce {x} into a matplotlib.figure.Figure object."
        )

    try:
        with backend_selection_suppressed():
            from ipympl.backend_nbagg import Canvas, FigureManager
    except ImportError:
        raise ImportError(
            "Install the ipympl package to use matplotlib with shinywidgets (pip install ipympl)."
        )

    # Canvas(figure=x) alone isn't enough -- ipympl's browser message handling
    # goes through canvas.manager (e.g., a resize message calls
    # manager.handle_json()), so the canvas needs a FigureManager (which also
    # wires up the toolbar).
    if isinstance(x.canvas, Canvas) and not is_closed_widget(x.canvas):
        canvas = x.canvas
    else:
        # The previous canvas may have scaled the dpi by its screen's pixel ratio
        # (e.g., pyplot's macosx backend on a HiDPI display); ipympl applies the
        # browser's ratio instead.
        x.set_dpi(x.dpi / x.canvas.device_pixel_ratio)
        canvas = Canvas(x)
    if canvas.manager is None:
        FigureManager(canvas, getattr(x, "number", id(x)))

    close_mpl_figure_with_widget(canvas, x)

    return canvas


def is_ipympl_canvas(x: Widget) -> bool:
    if widget_pkg(x) != "ipympl":
        return False
    with backend_selection_suppressed():
        from ipympl.backend_nbagg import Canvas
    return isinstance(x, Canvas)


@contextmanager
def backend_selection_suppressed() -> Iterator[None]:
    """
    Make matplotlib.use() a no-op for the duration of the block.

    When first imported, ipympl selects itself as pyplot's backend, which
    would make every pyplot figure in the process (e.g., those drawn by
    shiny's @render.plot) an ipympl widget.
    https://github.com/matplotlib/ipympl/issues/623
    """
    import matplotlib

    use = matplotlib.use
    matplotlib.use = lambda *args, **kwargs: None
    try:
        yield
    finally:
        matplotlib.use = use


def close_mpl_figure_with_widget(canvas: Widget, fig: Figure) -> None:
    """
    Deregister a pyplot figure (via plt.close()) when the canvas widget closes.

    Figures created through pyplot (e.g., plt.subplots()) stay registered in
    pyplot's global figure manager, which leaks memory (and triggers "More
    than 20 figures have been opened" warnings) as renders repeat. The widget
    machinery already closes the ipympl canvas at the end of its lifetime, so
    tying the pyplot deregistration to the widget's close means it happens
    exactly when the canvas goes away -- at render retirement, or at session
    end for widgets kept alive via session_lifetime().
    """
    num = getattr(fig, "number", None)
    if num is None or canvas in MPL_CLEANUP_CANVASES:
        return
    MPL_CLEANUP_CANVASES.add(canvas)

    def on_comm_change(change: dict[str, object]) -> None:
        # The comm becomes None exactly once: when the widget closes
        if change["new"] is not None:
            return
        canvas.unobserve(on_comm_change, names="comm")
        import matplotlib.pyplot as plt

        # plt.close(fig) deregisters by figure identity (Gcf.destroy_fig()), so
        # it's safe even if the user already closed it or the number was reused
        plt.close(fig)

    canvas.observe(on_comm_change, names="comm")


def as_widget_plotly(x: object) -> Optional[Widget]:
    # Don't need a try import here since this won't be called unless x is a plotly object
    import plotly.graph_objects as go

    if not isinstance(x, go.Figure):
        raise TypeError(
            f"Don't know how to coerce {x} into a plotly.graph_objects.FigureWidget object."
        )

    # FigureWidget doesn't support frames (i.e., animations), so constructing
    # one from (data, layout) drops them (#156). Plotly itself raises a
    # ValueError for frames in FigureWidget (still true as of plotly 7.1.0),
    # but animation support is an active area of development upstream
    # (https://github.com/plotly/plotly.py/pull/5601), so we warn rather than
    # error in case plotly ever lifts the restriction.
    if x.frames:
        warnings.warn(
            "plotly's FigureWidget does not support frames (i.e., animations), "
            "so the frames in this figure will be dropped. To render the figure "
            "with frames, use shiny's @render.ui decorator instead of shinywidgets, "
            "and return ui.HTML(fig.to_html()) from the render function.",
            stacklevel=2,
        )

    return go.FigureWidget(x.data, x.layout)  # type: ignore


def as_widget_pydeck(x: object) -> Widget:
    # Check before calling show(): on pydeck >= 0.9 it serializes the whole deck
    # into HTML for nothing, and that can fail with a cryptic error of its own
    # (pydeck <= 0.9.1 can't serialize pandas 3 DataFrames).
    if not pydeck_has_widget():
        raise TypeError(PYDECK_NO_WIDGET_MESSAGE)

    if not hasattr(x, "show"):
        raise TypeError(
            f"Don't know how to coerce {type(x)} (a pydeck object) into an ipywidget without a .show() method."
        )

    res = x.show()  # type: ignore

    if not isinstance(res, Widget):
        raise TypeError(
            f"Expected {type(x).__name__}.show() to return an ipywidget, but got {type(res)}."
        )

    return res


PYDECK_NO_WIDGET_MESSAGE = (
    "pydeck v0.9 removed its Jupyter widget (Deck.show() now returns static HTML), "
    "so shinywidgets can't render pydeck maps. To use pydeck layers in a reactive "
    "map, pass pydeck.Layer objects to a maplibre Map's add_deck_layers() and render "
    "it with @render_maplibre (pip install 'maplibre[anywidget]'). For large data, "
    "consider lonboard and @render_lonboard. For a static map, use shiny's @render.ui "
    "decorator and return deck.show() (or, to fill the container, "
    "ui.tags.iframe(srcdoc=deck.to_html(as_string=True), "
    'style="border:0;width:100%;height:100%;flex:1 1 auto")). '
    "For more, see https://github.com/visgl/deck.gl/issues/9064"
)


AS_WIDGET_MAP = {
    "altair": as_widget_altair,
    "bokeh": as_widget_bokeh,
    "holoviews": as_widget_holoviews,
    "hvplot": as_widget_holoviews,
    "lonboard": as_widget_lonboard,
    "maplibre": as_widget_maplibre,
    "matplotlib": as_widget_mpl,
    "panel": as_widget_panel,
    "plotly": as_widget_plotly,
    "pydeck": as_widget_pydeck,
    "seaborn": as_widget_mpl,
}


def bokeh_model_class(*, context: str) -> type["BokehModel"]:
    try:
        from jupyter_bokeh import BokehModel
    except ImportError:
        raise ImportError(
            f"Install the jupyter_bokeh package to use {context} with shinywidgets."
        )

    return BokehModel


def panel_to_widget(x: object, *, context: str, missing_panel_message: str) -> Widget:
    try:
        import panel as pn
    except ImportError:
        raise ImportError(missing_panel_message)

    from bokeh.document import Document

    model_class = bokeh_model_class(context=context)
    pane = cast("Viewable", pn.panel(x))
    document = Document()
    session = get_current_session()
    if session is not None and not session.is_stub_session():
        dependency = HTMLDependency(
            name="panel-assets",
            version=pn.__version__,
            source={"package": "panel", "subdir": "dist"},
            all_files=True,
        )
        href = dependency.source_path_map(lib_prefix=session.app.lib_prefix)["href"]
        # Panel uses this document setting for initial and updated model stylesheets.
        document.template_variables["dist_url"] = href + "/"
        session._process_ui(dependency)
    root = pane.get_root(doc=document)

    def cleanup_root() -> None:
        # Panel may register a wrapper around the pane (e.g., HoloViews).
        view = pn.state._views.get(root.id)
        if view is not None:
            try:
                view[0]._cleanup(root)
            finally:
                pn.state._views.pop(root.id, None)

    try:
        widget = model_class(cast("LayoutDOM", root))
    except Exception:
        cleanup_root()
        raise

    def on_comm_change(change: dict[str, object]) -> None:
        if change["new"] is not None:
            return
        widget.unobserve(on_comm_change, names="comm")
        cleanup_root()

    widget.observe(on_comm_change, names="comm")
    return widget


def pydeck_has_widget() -> bool:
    """
    Does the installed pydeck provide an ipywidget?

    pydeck v0.9 removed it (https://github.com/visgl/deck.gl/pull/8854): `Deck.show()`
    returns static HTML, `Deck.update()` raises, and `DeckGLWidget` survives only
    as an unused class that pydeck still constructs (several per `Deck`).
    """
    import pydeck

    return Version(pydeck.__version__) < Version("0.9")
