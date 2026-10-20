from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from htmltools import HTMLDependency
from ipywidgets.widgets.widget import Widget
from shiny.session import get_current_session

from ._dependencies import widget_pkg

if TYPE_CHECKING:
    from bokeh.models import LayoutDOM
    from jupyter_bokeh import BokehModel
    from matplotlib.figure import Figure
    from panel.viewable import Viewable

__all__ = ("as_widget",)


# Some objects aren't directly renderable as an ipywidget, but in some cases,
# we can coerce them into one
def as_widget(x: object) -> Widget:
    if isinstance(x, Widget):
        return x

    pkg = widget_pkg(x)

    _as_widget = AS_WIDGET_MAP.get(pkg, None)
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


def as_widget_maplibre(x: object) -> Optional[Widget]:
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
    # (map options plus the queued JS calls that get replayed on render).
    state = x.to_dict()  # type: ignore
    res = MapWidget()
    res.map_options = state["mapOptions"]
    res._message_queue = state["calls"]
    return res  # type: ignore


def as_widget_mpl(x: object) -> Optional[Widget]:
    # matplotlib is guaranteed to be installed here since this function is only
    # called when x comes from the matplotlib package
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    # Several higher-level APIs (e.g., pandas.DataFrame.plot()) return an Axes
    # rather than a Figure
    if isinstance(x, Axes):
        x = x.figure  # type: ignore

    if not isinstance(x, Figure):
        raise TypeError(
            f"Don't know how to coerce {x} into a matplotlib.figure.Figure object."
        )

    try:
        from ipympl.backend_nbagg import Canvas, FigureManager
    except ImportError:
        raise ImportError(
            "Install the ipympl package to use matplotlib with shinywidgets (pip install ipympl)."
        )

    # Canvas(figure=x) alone isn't enough -- ipympl's browser message handling
    # goes through canvas.manager (e.g., a resize message calls
    # manager.handle_json()), so the canvas needs a FigureManager (which also
    # wires up the toolbar).
    canvas = Canvas(x)
    FigureManager(canvas, getattr(x, "number", id(x)))

    _close_mpl_figure_with_widget(canvas, x)

    return canvas


def _close_mpl_figure_with_widget(canvas: Widget, fig: Figure) -> None:
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
    if num is None:
        # Not a pyplot-managed figure, so there's nothing to deregister
        return

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

    return go.FigureWidget(x.data, x.layout)  # type: ignore


def as_widget_pydeck(x: object) -> Optional[Widget]:
    if not hasattr(x, "show"):
        raise TypeError(
            f"Don't know how to coerce {type(x)} (a pydeck object) into an ipywidget without a .show() method."
        )

    res = x.show()  # type: ignore

    if not isinstance(res, Widget):
        raise TypeError(
            "pydeck v0.9 removed ipywidgets support, thus it no longer works with "
            "shinywidgets. Consider either downgrading to pydeck v0.8.0 or using shiny's "
            "@render.ui decorator to display the map (and return Deck.to_html() in "
            "that render function). Note that the latter strategy means you won't be "
            "able to programmatically .update() the map or access user events."
            "For more, see https://github.com/visgl/deck.gl/pull/8854"
        )

    return res


AS_WIDGET_MAP = {
    "altair": as_widget_altair,
    "bokeh": as_widget_bokeh,
    "holoviews": as_widget_holoviews,
    "hvplot": as_widget_holoviews,
    "maplibre": as_widget_maplibre,
    "matplotlib": as_widget_mpl,
    "panel": as_widget_panel,
    "plotly": as_widget_plotly,
    "pydeck": as_widget_pydeck,
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
