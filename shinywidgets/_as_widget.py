from __future__ import annotations

import asyncio
import threading
import time
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Optional, Protocol, cast

from htmltools import HTMLDependency
from ipywidgets.widgets.domwidget import DOMWidget
from ipywidgets.widgets.widget import Widget
from packaging.version import Version
from shiny.reactive import isolate
from shiny.session import get_current_session

from ._comm import ShinyComm
from ._dependencies import widget_pkg

if TYPE_CHECKING:
    from bokeh.models import LayoutDOM
    from ipympl.backend_nbagg import Canvas
    from ipysigma import Sigma
    from jupyter_bokeh import BokehModel
    from matplotlib.figure import Figure
    from panel.viewable import Viewable
    from perspective.widget import PerspectiveWidget

    class PlotnineDrawable(Protocol):
        def draw(self, *, show: bool = False) -> Figure: ...


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
    * holoviews/hvplot/geoviews object -> bokeh model (via panel)
    * ipyvolume `Container` (e.g., the return value of `ipv.quickscatter()`) ->
      its `ipyvolume.Figure`
    * jupyter-scatter `Scatter` -> `jscatter.widget.JupyterScatter`
    * leafmap's folium and deck backends raise a `TypeError` (leafmap's other
      backends are already ipywidgets)
    * lonboard layer -> `lonboard.Map`
    * maplibre `Map` -> `maplibre.ipywidget.MapWidget`
    * matplotlib `Figure` or `Axes` (or a seaborn figure-level grid) ->
      `ipympl.backend_nbagg.Canvas`
    * panel pane/viewable -> bokeh model
    * perspective `Table` -> `perspective.widget.PerspectiveWidget`
    * pyobsplot `Obsplot`/`Plot` creators raise a `TypeError` (they create
      charts when called; the result is already an ipywidget)
    * plotly `Figure` -> `plotly.graph_objects.FigureWidget`
    * plotnine `ggplot` (or plot composition) -> `ipympl.backend_nbagg.Canvas`
    * pydeck `Deck` -> `pydeck.widget.DeckGLWidget` (pydeck <= 0.8 only; pydeck
      v0.9 removed its widget, so this raises a `TypeError` that points to
      alternatives)
    * pyvista `Plotter` -> a self-contained client-side (vtk.js) widget (via
      pyvista's ``jupyter_backend='html'`` export)

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
        # An ipyvolume Container displays its Figure
        if any(widget_pkg(cls) == "ipyvolume" for cls in type(x).__mro__):
            return as_widget_ipyvolume(x)
        return x

    pkg = widget_pkg(x)

    _as_widget = AS_WIDGET_MAP.get(pkg, None)
    # Subclasses defined in another package should route to the coercer for the
    # base class's package: e.g., leafmap's backend Maps (whose instances report
    # __module__ == "leafmap.*" but subclass ipyleaflet/pydeck/etc. classes), a
    # pn.viewable.Viewer or pn.custom.JSComponent subclass defined in an app, or
    # a seaborn figure-level grid.
    if _as_widget is None:
        for base in type(x).__mro__:
            base_pkg = widget_pkg(base)
            _as_widget = AS_WIDGET_MAP.get(base_pkg, None)
            if _as_widget is not None:
                pkg = base_pkg
                break
    if _as_widget is None:
        msg = f"Don't know how to coerce {_short_repr(x)} into an ipywidget.Widget object."
        if callable(getattr(x, "_repr_html_", None)):
            msg += " Instead of using shinywidgets to render this object, try using shiny's @render.ui decorator "
            msg += " https://shiny.posit.co/py/api/ui.output_ui.html#shiny.ui.output_ui"
        raise TypeError(msg)

    res = _as_widget(x)

    if not isinstance(res, Widget):
        raise TypeError(
            f"Failed to coerce {_short_repr(x)} (an object from package {pkg}) into an ipywidget.Widget object."
        )

    return res


def _short_repr(x: object, limit: int = 300) -> str:
    # Some objects repr() to something enormous (e.g., repr(pydeck.Deck) is the
    # deck's entire JSON spec), which makes for a wall of text in error messages.
    try:
        r = repr(x)
    except Exception:
        r = object.__repr__(x)
    return r if len(r) <= limit else r[:limit] + "..."


def as_widget_altair(x: object) -> Optional[Widget]:
    try:
        from altair import JupyterChart
    except ImportError:
        raise RuntimeError(
            "Failed to import altair.JupyterChart (do you need to pip install -U 'shinywidgets[altair]'?)"
        )

    return JupyterChart(x)  # type: ignore


def as_widget_bokeh(x: object) -> Optional[Widget]:
    from bokeh.plotting import figure

    # Make a figure fill its output, unless the user sized it. This has to
    # happen before BokehModel() snapshots the document: changes made after
    # that are only sent as patches over the comm, which isn't open yet.
    if isinstance(x, figure) and not BOKEH_SIZING_PROPS & set(
        x.properties_with_values(include_defaults=False)
    ):
        x.sizing_mode = "stretch_both"

    return bokeh_model_class(context="bokeh")(cast("LayoutDOM", x))


def as_widget_panel(x: object) -> Optional[Widget]:
    return panel_to_widget(
        x,
        context="panel",
        missing_panel_message=(
            "Install the panel package to use panel objects with shinywidgets: "
            "pip install 'shinywidgets[panel]'"
        ),
    )


def as_widget_holoviews(x: object) -> Optional[Widget]:
    return panel_to_widget(
        x,
        context="holoviews/hvplot/geoviews",
        missing_panel_message=(
            "Rendering holoviews/hvplot/geoviews objects requires the panel package "
            "(they render through panel). Install it with: pip install 'shinywidgets[holoviews]'"
        ),
    )


def as_widget_jscatter(x: object) -> Optional[Widget]:
    # jscatter is guaranteed to be installed here since this function is only
    # called when x comes from the jscatter package
    from jscatter import Scatter

    if not isinstance(x, Scatter):
        raise TypeError(f"Don't know how to coerce {x} into a jscatter Scatter object.")

    # Scatter isn't a widget itself, but wraps (and lazily creates) one
    return x.widget


def as_widget_ipyvolume(x: object) -> Widget:
    # ipyvolume is guaranteed to be installed here since this function is only
    # called when x comes from the ipyvolume package
    from ipyvolume.ui import Container

    # quickscatter() and friends return the Container (figure plus control
    # widgets); the Figure is the renderable part
    if isinstance(x, Container):
        return x.figure

    if not isinstance(x, DOMWidget):
        raise TypeError(
            f"Don't know how to render {type(x).__name__} on its own (it draws "
            "onto an ipyvolume figure) -- return the figure instead (e.g., "
            "`ipv.gcf()` after drawing, or `ipv.figure()`)."
        )

    return x


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
            "Install maplibre's anywidget extra to use maplibre with shinywidgets (pip install 'shinywidgets[maplibre]')."
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


def as_widget_perspective(x: object) -> Optional[Widget]:
    # perspective is guaranteed to be installed here since this function is only
    # called when x comes from the perspective package
    from perspective import Table

    if not isinstance(x, Table):
        raise TypeError(
            f"Don't know how to coerce {x} into a perspective.widget.PerspectiveWidget object."
        )

    return perspective_widget(x)


def perspective_widget(data: object) -> "PerspectiveWidget":
    try:
        from perspective.widget import PerspectiveWidget
    except ImportError:
        raise ImportError(
            "Install the perspective-python package to use perspective with shinywidgets (pip install 'shinywidgets[perspective]')."
        )
    from perspective import Server, Table

    if not isinstance(data, Table):
        # PerspectiveWidget(data) would host the table on perspective.GLOBAL_SERVER,
        # and the browser can open any table on its widget's server, so every
        # session's viewer could read and write it. A server per widget keeps
        # sessions' data apart.
        data = Server().new_local_client().table(data)

    return PerspectiveWidget(data)


def networkx_to_sigma(x: object) -> Sigma:
    # Not in AS_WIDGET_MAP: a networkx graph is generic (ipycytoscape accepts one
    # too), so only @render_ipysigma coerces it.
    try:
        from ipysigma import Sigma
    except ImportError:
        raise ImportError(
            "Install the ipysigma package to use render_ipysigma with shinywidgets (pip install 'shinywidgets[ipysigma]')."
        )

    # Sigma validates the graph itself (raising a TypeError for non-graphs)
    return Sigma(x)


def as_widget_mpl(x: object, *, context: str = "matplotlib") -> Widget:
    from matplotlib.figure import Figure, SubFigure

    # The renderer imports this module, so defer these circular imports.
    from ._render_widget_base import is_closed_widget
    from ._shinywidgets import foreign_or_closed_widget, ownership_error

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
            f"Install the ipympl package to use {context} with shinywidgets (pip install 'shinywidgets[{context}]')."
        )

    # A GUI backend's canvas gets destroyed (its window closed) and replaced
    # with ipympl's below. That path relies on platform-specific behavior
    # (e.g., HiDPI dpi scaling) that automated tests can't exercise, so warn
    # and point to the well-tested paths.
    if not isinstance(x.canvas, Canvas) and is_gui_backend_canvas(x.canvas):
        warnings.warn(
            "render_matplotlib is replacing a canvas created by a GUI backend "
            f"({type(x.canvas).__module__}): the figure's window (if any) is "
            "destroyed and ipympl's canvas takes over, a path that relies on "
            "platform-specific behavior that shinywidgets can't test. Prefer "
            "creating figures with matplotlib.figure.Figure(), or selecting "
            'the agg backend (matplotlib.use("agg")) before creating figures.',
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
                raise ownership_error(bad)
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


def is_gui_backend_canvas(x: object) -> bool:
    """
    Whether a matplotlib canvas comes from an interactive GUI framework (Qt,
    Tk, GTK, wx, macOS). Those canvases live in matplotlib's
    ``backend_<gui>[agg]`` modules (e.g., ``backend_qtagg``); the
    non-interactive ones (agg, svg, pdf, ...) and ipympl's do not.
    """
    module = type(x).__module__.lower()
    return module.startswith("matplotlib.backends.backend_") and any(
        marker in module for marker in ("qt", "tk", "gtk", "wx", "macosx")
    )


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


_PYVISTA_TRAME_SERVER_LOCK = threading.Lock()


def ensure_pyvista_trame_server() -> None:
    """
    Start pyvista's shared trame server, avoiding trame_pyvista's launcher.

    pyvista's html jupyter export requires its shared trame server to be
    running. When it isn't, trame_pyvista launches it via `elegantly_launch()`,
    which globally patches asyncio with nest_asyncio2 -- unsafe inside Shiny's
    event loop -- and leaves the server's lifecycle unmanaged. Start the server
    here instead, in a daemon thread with its own event loop: asyncio stays
    untouched, and the server (localhost-only, on an ephemeral port) is shared
    by every html export in the process and dies with the process.
    """
    import pyvista as pv  # pyright: ignore[reportMissingImports]
    from trame.widgets import vtk as vtk_widgets  # pyright: ignore[reportMissingImports]
    from trame_pyvista.widgets import get_server  # pyright: ignore[reportMissingImports]

    server = get_server(pv.global_theme.trame.jupyter_server_name)
    if server is None:
        raise RuntimeError("Failed to resolve pyvista's shared trame server.")
    if server.running:
        return

    with _PYVISTA_TRAME_SERVER_LOCK:
        if server.running:
            return

        # Enable the vtk widget module (which registers the scene-export
        # protocol the html export uses) before the server starts. This is
        # the piece of trame_pyvista.jupyter.launch_server() the export
        # actually needs; the rest (vuetify UI, vtklocal wasm) is for the
        # interactive backends shinywidgets doesn't use.
        vtk_widgets.initialize(server)

        def run_server() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            start = server.start(
                # Return a coroutine to schedule on this thread's loop (rather
                # than blocking it), so the server runs until the process exits
                exec_mode="coroutine",
                # Non-main thread: don't install signal handlers
                thread=True,
                # Localhost-only, on an ephemeral port; the exported widget is
                # self-contained, so nothing ever connects to this server
                host="127.0.0.1",
                port=0,
                open_browser=False,
                show_connection_info=False,
                disable_logging=True,
                # Disable trame's auto-shutdown when no client is connected
                # (nothing ever is)
                timeout=0,
            )
            loop.create_task(cast(Any, start))
            loop.run_forever()

        threading.Thread(
            target=run_server, name="shinywidgets-pyvista-trame", daemon=True
        ).start()

        deadline = time.monotonic() + 30
        while not server.running:
            if time.monotonic() > deadline:
                raise RuntimeError(
                    "Timed out waiting for pyvista's shared trame server to start "
                    "(needed to export the scene for the html jupyter backend)."
                )
            time.sleep(0.01)


def as_widget_pyvista(x: object) -> Widget:
    # pyvista is guaranteed to be installed here since this function is only
    # called when x comes from the pyvista package
    from ipywidgets import DOMWidget, Layout
    from pyvista import Plotter  # pyright: ignore[reportMissingImports]

    if not isinstance(x, Plotter):
        # Name the type rather than interpolating x: a pyvista mesh repr is a
        # multi-line stats dump that would flood the Shiny error box
        raise TypeError(
            f"Don't know how to coerce {type(x).__name__} into an ipywidget (expected a pyvista.Plotter)."
        )

    # On Python 3.15+ the pyvista import above is unresolvable (no vtk
    # wheels) and isinstance() narrows to object, so access attributes through
    # a cast instead of the narrowed type
    plotter = cast(Any, x)

    # Coercion closes the plotter (below), so a cached/reused Plotter would
    # otherwise fail in trame_pyvista with a misleading "Do not call 'show()'"
    # RuntimeError
    if plotter._closed:
        raise ValueError(
            "This pyvista Plotter has already been closed (coercion closes the "
            "plotter after exporting the scene). Construct a fresh Plotter in "
            "the render function instead of caching and reusing one."
        )

    try:
        from trame_pyvista.jupyter import show_trame  # pyright: ignore[reportMissingImports]
    except ImportError as e:
        raise ImportError(
            "Install pyvista's jupyter extra to use pyvista with shinywidgets (pip install 'shinywidgets[pyvista]')."
        ) from e

    try:
        # jupyter_backend='html' exports the scene to a self-contained,
        # client-side vtk.js view. pyvista's other interactive backends ('trame',
        # 'client', 'server') need their own trame websocket server, which
        # shinywidgets can't host.
        #
        # The export still needs pyvista's shared trame server running, so start
        # it ourselves (localhost-only, in a daemon thread) rather than letting
        # trame_pyvista's elegantly_launch() patch asyncio process-wide via
        # nest_asyncio2. This is inside the try so a startup failure (e.g. its
        # timeout) still closes the plotter below.
        ensure_pyvista_trame_server()

        widget = show_trame(x, mode="html", width="100%", height="100%")
        if not isinstance(widget, DOMWidget):
            raise TypeError(
                f"Expected pyvista's html jupyter backend to produce an ipywidget, but got {type(widget)}."
            )

        # Size the iframe (via width/height='100%' above) and the widget itself to
        # the output container; _LAYOUT_DEFAULTS in _render_widget_base.py keeps
        # this from reading as a user-specified height
        widget.layout = Layout(width="100%", height="100%")
    finally:
        # The scene is fully serialized into the widget, so the plotter's
        # (offscreen) GL resources are no longer needed (mirrors Plotter.show()'s
        # auto_close). Close on failure too, so repeated failed renders don't
        # accumulate rendering resources.
        plotter.close()

    return widget


def as_widget_plotnine(x: object) -> Widget:
    # Both ggplot and plot compositions (e.g., `p1 | p2`, plotnine >= 0.15)
    # draw() to a matplotlib Figure
    if not callable(getattr(x, "draw", None)):
        raise TypeError(f"Don't know how to coerce {x} into a plotnine ggplot object.")

    # draw() attaches the figure to the plot (and a later draw() reuses it), so
    # draw a copy, like plotnine's own save() and show() do
    plot = deepcopy(x)
    forget_drawn_figure(plot)
    figure = cast("PlotnineDrawable", plot).draw()
    canvas = cast("Canvas", as_widget_mpl(figure, context="plotnine"))
    # plotnine closes its pyplot figure after drawing, which frees the figure
    # number for reuse, so the header's "Figure <number>" label is meaningless
    canvas.header_visible = False
    # The footer (the cursor-coordinates readout) appears on first hover, after
    # the figure was fitted to its container, so it pushes the bottom of the plot
    # out of view. Its readout is also unhelpful for plotnine: its fixed tick
    # formatter shows scientific notation, in transformed (e.g., log) units.
    canvas.footer_visible = False
    return canvas


def forget_drawn_figure(plot: object) -> None:
    """
    Drop the figure (and its axes) an earlier draw() attached to a plotnine plot.

    ggplot's deepcopy keeps them (e.g., when the user called draw() on the plot
    being copied), and draw() reuses them, so every copy would otherwise draw onto
    (and share a canvas with) that one figure. A composition's figure and axes
    live on the composition and on each of its plots.
    """
    for name in ("figure", "axs"):
        vars(plot).pop(name, None)
    for item in getattr(plot, "items", ()):
        forget_drawn_figure(item)


LEAFMAP_FOLIUM_MESSAGE = (
    "leafmap's folium backend (leafmap.foliumap.Map) isn't an ipywidget, so it "
    "can't be rendered with a shinywidgets render decorator. For a static map, "
    "use shiny's @render.ui decorator and return ui.HTML(m._repr_html_()) — not "
    "m.to_html(), which is a whole HTML document. For a reactive map, use one of "
    "leafmap's widget backends instead: leafmap.Map (ipyleaflet) or "
    "leafmap.maplibregl.Map."
)


def as_widget_leafmap(x: object) -> Widget:
    """
    Coerce a leafmap map into a Widget (see `as_widget()`).

    leafmap's ipyleaflet (`leafmap.Map`), maplibre (`leafmap.maplibregl.Map`), and
    kepler.gl (`leafmap.kepler.Map`) backends are already ipywidgets, so they
    never reach this function (``as_widget()`` returns those as-is). Its folium
    and deck backends aren't widgets, so this raises a `TypeError` that points to
    an alternative.
    """
    # The deck backend subclasses pydeck's Deck, so give it pydeck's advice
    if any(widget_pkg(base) == "pydeck" for base in type(x).__mro__):
        raise TypeError(
            PYDECK_NO_WIDGET_MESSAGE
            + " With leafmap, that's leafmap.maplibregl.Map and its add_deck_layers()."
        )

    raise TypeError(LEAFMAP_FOLIUM_MESSAGE)


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
    "it with @render_maplibre (pip install 'shinywidgets[maplibre]'). For large data, "
    "consider lonboard and @render_lonboard. For a static map, use shiny's @render.ui "
    "decorator and return deck.show() (or, to fill the container, "
    "ui.tags.iframe(srcdoc=deck.to_html(as_string=True), "
    'style="border:0;width:100%;height:100%;flex:1 1 auto")). '
    "For more, see https://github.com/visgl/deck.gl/issues/9064"
)


def as_widget_pyobsplot(x: object) -> Widget:
    """
    pyobsplot's `ObsplotWidget` is already an ipywidget, so only non-widget
    pyobsplot objects reach this function: the `Plot`/`Obsplot` plot creators
    (calling one with a specification returns the chart widget).
    """
    raise TypeError(
        f"Don't know how to coerce {_short_repr(x)} into an ipywidget.Widget object. "
        "A pyobsplot Plot/Obsplot object is a plot creator, not a chart: call it "
        "with a plot specification (e.g., Plot.plot({'marks': [...]})) and return "
        "the result."
    )


AS_WIDGET_MAP = {
    "altair": as_widget_altair,
    "bokeh": as_widget_bokeh,
    "geoviews": as_widget_holoviews,
    "holoviews": as_widget_holoviews,
    "hvplot": as_widget_holoviews,
    "jscatter": as_widget_jscatter,
    "leafmap": as_widget_leafmap,
    "lonboard": as_widget_lonboard,
    "maplibre": as_widget_maplibre,
    "matplotlib": as_widget_mpl,
    "panel": as_widget_panel,
    "perspective": as_widget_perspective,
    "plotly": as_widget_plotly,
    "plotnine": as_widget_plotnine,
    "pydeck": as_widget_pydeck,
    "pyobsplot": as_widget_pyobsplot,
    "pyvista": as_widget_pyvista,
    "seaborn": as_widget_mpl,
}


BOKEH_SIZING_PROPS = {"width", "height", "sizing_mode", "aspect_ratio"}


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
