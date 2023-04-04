from typing import Optional

from ipywidgets.widgets.widget import Widget

from ._dependencies import widget_pkg

__all__ = ("as_widget",)


# Some objects aren't directly renderable as an ipywidget, but in some cases,
# we can coerce them into one
def as_widget(x: object) -> Widget:
    if isinstance(x, Widget):
        return x

    pkg = widget_pkg(x)

    _as_widget = AS_WIDGET_MAP.get(pkg, None)
    if _as_widget is None:
        raise TypeError(f"Don't know how to coerce {x} into a ipywidget.Widget object.")

    res = _as_widget(x)

    if not isinstance(res, Widget):
        raise TypeError(
            f"Failed to coerce {x} (an object from package {pkg}) into a ipywidget.Widget object."
        )

    return res


def as_widget_altair(x: object) -> Optional[Widget]:
    try:
        from vega.widget import VegaWidget
    except ImportError:
        raise ImportError("Install the vega package to use altair with shinywidgets.")

    if not hasattr(x, "to_dict"):
        raise TypeError(
            f"Don't know how to coerce {x} (an altair object) into an ipywidget without a .to_dict() method."
        )

    try:
        return VegaWidget(x.to_dict())  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Failed to coerce {x} into a VegaWidget: {e}")


def as_widget_bokeh(x: object) -> Optional[Widget]:
    try:
        from jupyter_bokeh import BokehModel
    except ImportError:
        raise ImportError(
            "Install the jupyter_bokeh package to use bokeh with shinywidgets."
        )

    return BokehModel(x)  # type: ignore


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
            f"Don't know how to coerce {x} (a pydeck object) into an ipywidget without a .show() method."
        )

    return x.show()  # type: ignore


AS_WIDGET_MAP = {
    "altair": as_widget_altair,
    "bokeh": as_widget_bokeh,
    "plotly": as_widget_plotly,
    "pydeck": as_widget_pydeck,
}
