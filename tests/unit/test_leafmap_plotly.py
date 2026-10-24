import asyncio
from typing import cast

import pytest
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_leafmap

pytest.importorskip("plotly")
from plotly.graph_objects import FigureWidget, Layout


@pytest.mark.parametrize("height", [None, 600, 250])
def test_render_leafmap_plotly_preserves_widget_and_height_intent(
    widget_session: Session, height: int | None
) -> None:
    with session_context(widget_session):
        figure = LeafmapPlotlyMap(layout={"height": height})
        renderer = render_leafmap()

        @renderer
        def render_map() -> FigureWidget:
            return figure

        result = asyncio.run(renderer._render())

    assert isinstance(result, dict)
    assert renderer.value is figure
    assert renderer.widget is figure
    assert result["widget_pkg"] == "leafmap"
    assert result["fill"] is (height in (None, 600))
    layout = cast(Layout, figure.layout)
    assert layout.height == (None if height in (None, 600) else height)
    if result["fill"]:
        assert figure._config["responsive"] is True


class LeafmapPlotlyMap(FigureWidget):
    __module__ = "leafmap.plotlymap"
