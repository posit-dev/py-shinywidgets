from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional, cast

from htmltools import HTMLDependency
from ipywidgets.widgets.widget import Widget
from shiny.reactive import isolate
from shiny.session import get_current_session

from ._comm import ShinyComm
from ._dependencies import widget_pkg

if TYPE_CHECKING:
    from bokeh.models import LayoutDOM
    from ipympl.backend_nbagg import Canvas
    from jupyter_bokeh import BokehModel
    from matplotlib.figure import Figure
    from panel.viewable import Viewable

__all__ = ("as_widget",)


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
    * pydeck `Deck` -> `pydeck.widget.DeckGLWidget`

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
        # A Canvas may still need its FigureManager and to leave pyplot
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

    # The renderer imports this module, so defer these circular imports.
    from ._render_widget_base import is_closed_widget
    from ._shinywidgets import foreign_or_closed_widget

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

    # Before the ipympl canvas is attached: leaving pyplot may replace the
    # figure's canvas. Isolated since destroying a GUI-backend manager fires
    # close_event, running the user's callbacks (see the draw below).
    with isolate():
        leave_pyplot(x, keep_canvas=isinstance(x.canvas, Canvas))

    # Canvas(figure=x) alone isn't enough -- ipympl's browser message handling
    # goes through canvas.manager (e.g., a resize message calls
    # manager.handle_json()), so the canvas needs a FigureManager (which also
    # wires up the toolbar).
    if isinstance(x.canvas, Canvas) and not is_closed_widget(x.canvas):
        canvas = x.canvas
    else:
        # The previous canvas may have scaled the dpi by its screen's pixel ratio
        # (e.g., a GUI backend on a HiDPI display); ipympl applies the browser's
        # ratio instead.
        x.set_dpi(x.dpi / x.canvas.device_pixel_ratio)
        canvas = Canvas(x)
    if canvas.manager is None:
        FigureManager(canvas, getattr(x, "number", id(x)))

    # A cached image describes the figure only if it hasn't changed since the
    # image was drawn.
    if not canvas._data_url or x.stale:
        # Drawing updates state synced to the browser (and a failure may close
        # the canvas), so a reused canvas that's live in another session must
        # be rejected before the draw, not after it by the renderer.
        session = get_current_session()
        if session is not None and not session.is_stub_session():
            bad = foreign_or_closed_widget(canvas, session.root_scope())
            if bad is not None:
                raise RuntimeError(
                    f"{type(bad).__name__} belongs to another Shiny session, so it "
                    "can't be displayed here. Construct widgets per session."
                )
        draw_initial_image(canvas)

    return canvas


def draw_initial_image(canvas: "Canvas") -> None:
    """
    Draw the image the frontend first paints now, rather than when the comm
    opens (see init_shiny_widget()), so that a draw-time error (e.g., invalid
    mathtext) fails the render instead of the comm-open effect, which would
    end the whole session.
    """
    # The renderer imports this module, so defer this circular import.
    from ._shinywidgets import close_widget

    try:
        # Isolated since drawing fires the user's callbacks (e.g., draw_event,
        # or xlim_changed from autoscaling), and what they read shouldn't
        # become dependencies of the render.
        with isolate():
            canvas._repr_mimebundle_()
    except Exception:
        # Close only a canvas whose comm hasn't opened yet (opening it would
        # fail the same way, inside an effect, ending the session). A live
        # canvas may be displayed by other outputs in this session, so just
        # propagate the error to this render.
        if not isinstance(canvas.comm, ShinyComm):
            close_widget(canvas)
        raise


def refresh_stale_mpl_canvases(widget: Widget) -> None:
    """
    Redraw ipympl canvases anywhere in `widget`'s tree whose image is stale.

    as_widget() draws the canvas it coerces, but a canvas coerced earlier and
    then returned nested in a container (e.g., VBox([canvas])) isn't coerced
    again, so a change made to its figure after the coercion (or a canvas never
    coerced at all) would otherwise reach the browser with an out-of-date (or
    missing) initial image: the deferred comm open reuses the cached one.
    Drawing here, during the render, also keeps a draw-time error this output's
    error rather than a failure in the comm-open effect.

    Must run after the renderer's ownership validation, since drawing updates
    state synced to the browser.
    """
    from ._shinywidgets import walk_widget_tree

    for w in walk_widget_tree([widget]):
        if not is_ipympl_canvas(w):
            continue
        canvas = cast("Canvas", w)
        if not canvas._data_url or canvas.figure.stale:
            draw_initial_image(canvas)


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


def leave_pyplot(fig: Figure, *, keep_canvas: bool) -> None:
    """
    Remove a figure from pyplot's global figure registry, like @render.plot does.

    pyplot's registry (and its "current figure") is shared by every output and
    session in the process, so leaving a live figure there lets a later
    plt.gca(), plt.figure(num), or seaborn call (from any session) draw into it.
    The ipympl canvas doesn't need the registry to keep working.

    Parameters
    ----------
    fig
        The figure.
    keep_canvas
        Whether the figure's current canvas must survive (it's the ipympl canvas
        that gets displayed).
    """
    from matplotlib._pylab_helpers import Gcf

    found = next(
        (item for item in Gcf.figs.items() if item[1].canvas.figure is fig), None
    )
    if found is None:
        return
    num, manager = found
    if not keep_canvas:
        # What plt.close(fig) does. Destroying a manager also resets the figure
        # to a plain canvas, which undoes a GUI backend's HiDPI dpi scaling
        # without firing resize_event.
        Gcf.destroy(manager)
        # Matplotlib 3.10 leaves the figure on the destroyed manager's canvas, so
        # resizing the figure (e.g., undoing the dpi scaling) would resize the
        # destroyed window and fire resize_event.
        if fig.canvas.manager is manager:
            fig.canvas.manager = None
        return
    # The canvas comes from pyplot itself (ipympl is pyplot's backend) or from
    # the user. Destroying the manager would close or detach it, so only
    # deregister it, like ipympl's own non-interactive show() does.
    del Gcf.figs[num]
    cid = getattr(manager, "_cidgcf", None)
    if cid is not None:
        manager.canvas.mpl_disconnect(cid)


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
