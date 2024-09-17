from __future__ import annotations

from typing import Optional

from htmltools import Tag, css, head_content, tags
from shiny.module import resolve_id
from shiny.ui.css import as_css_unit
from shiny.ui.fill import as_fill_item, as_fillable_container

from ._cdn import SHINYWIDGETS_CDN, SHINYWIDGETS_CDN_ONLY
from ._dependencies import output_binding_dependency

__all__ = ("output_widget",)


def output_widget(
    id: str,
    *,
    width: Optional[str] = None,
    height: Optional[str] = None,
    fill: Optional[bool] = None,
    fillable: Optional[bool] = None,
) -> Tag:
    id = resolve_id(id)
    res = tags.div(
        output_binding_dependency(),
        head_content(
            tags.script(
                data_jupyter_widgets_cdn=SHINYWIDGETS_CDN,
                data_jupyter_widgets_cdn_only=SHINYWIDGETS_CDN_ONLY,
            )
        ),
        id=id,
        class_="shiny-ipywidget-output shiny-report-size shiny-report-theme",
        style=css(
            width=as_css_unit(width),
            height=as_css_unit(height),
        ),
    )

    if fill is None:
        fill = height is None

    if fill:
        res = as_fill_item(res)

    if fillable is None:
        fillable = height is None

    if fillable:
        res = as_fillable_container(res)

    return res
