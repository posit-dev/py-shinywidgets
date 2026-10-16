from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ipywidgets.widgets.widget import Widget

from ._dependencies import widget_pkg

if TYPE_CHECKING:
    from matplotlib.figure import Figure

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
    try:
        from jupyter_bokeh import BokehModel
    except ImportError:
        raise ImportError(
            "Install the jupyter_bokeh package to use bokeh with shinywidgets."
        )

    # TODO: ideally we'd do this in set_layout_defaults() but doing
    # `BokehModel(x)._model.sizing_mode = "stretch_both"`
    # there, but that doesn't seem to work??
    from bokeh.plotting import figure

    if isinstance(x, figure):
        x.sizing_mode = "stretch_both"  # type: ignore

    return BokehModel(x)  # type: ignore


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

    _close_mpl_figure_with_lifetime(x)

    return canvas


def _close_mpl_figure_with_lifetime(fig: Figure) -> None:
    """
    Deregister a pyplot figure (via plt.close()) when the current widget
    lifetime ends.

    Figures created through pyplot (e.g., plt.subplots()) stay registered in
    pyplot's global figure manager, which leaks memory (and triggers "More
    than 20 figures have been opened" warnings) as renders repeat. The widget
    lifecycle already closes the ipympl canvas; this takes care of the pyplot
    registration.
    """
    num = getattr(fig, "number", None)
    if num is None:
        # Not a pyplot-managed figure, so there's nothing to deregister
        return

    import matplotlib.pyplot as plt

    if num not in plt.get_fignums():
        return

    from shiny.session import get_current_session

    session = get_current_session()
    if session is None or session.is_stub_session():
        return

    # Imported here to avoid a circular import at module load time
    from ._lifecycle import get_lifecycle
    from ._shinywidgets import current_lifetime

    lifecycle = get_lifecycle(session)
    # plt.close(fig) deregisters by figure identity (Gcf.destroy_fig()), so
    # it's safe even if the user already closed it or the number was reused
    lifecycle.add_disposer(current_lifetime(lifecycle), lambda: plt.close(fig))


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
    "matplotlib": as_widget_mpl,
    "plotly": as_widget_plotly,
    "pydeck": as_widget_pydeck,
}
