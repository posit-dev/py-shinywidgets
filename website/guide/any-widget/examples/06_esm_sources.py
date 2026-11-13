from pathlib import Path

import anywidget
import traitlets
from shiny.express import ui
from shinywidgets import render_widget

ui.page_opts(title="Three ways to load an anywidget's JS", fillable=True)


class InlineBox(anywidget.AnyWidget):
    # `_esm` as a plain string: the simplest option, and what every other
    # example in this guide uses. The whole string is sent to the browser as
    # part of the widget's synced state.
    _esm = """
    function render({ model, el }) {
      const box = document.createElement("div");
      box.textContent = "click me";
      box.style.cssText =
        "display:flex;align-items:center;justify-content:center;" +
        "width:160px;height:90px;border-radius:8px;cursor:pointer;" +
        "background:#2a6f97;color:white;font:14px sans-serif;";
      let n = 0;
      box.addEventListener("click", () => {
        n += 1;
        box.textContent = `clicked ${n}x`;
        model.set("clicks", n);
        model.save_changes();
      });
      el.appendChild(box);
    }
    export default { render };
    """
    clicks = traitlets.Int(0).tag(sync=True)


class FileBox(anywidget.AnyWidget):
    # `_esm` as a Path: anywidget reads the file at render time, and
    # (outside headless testing) watches it for hot reload -- edit
    # box_widget.js and re-render to see the change without restarting
    # Python. Byte-for-byte the same widget as InlineBox above.
    _esm = Path(__file__).parent / "box_widget.js"
    clicks = traitlets.Int(0).tag(sync=True)


class CdnBarChart(anywidget.AnyWidget):
    # `_esm` can import straight from a CDN. No local JS dependency, no
    # bundler -- but the browser needs network access to esm.sh (or
    # whichever CDN), and that import is on the critical path of every
    # render.
    _esm = """
    import * as d3 from "https://esm.sh/d3@7";

    function render({ model, el }) {
      const data = model.get("data");
      const width = 220, height = 90;
      const svg = d3.create("svg").attr("width", width).attr("height", height);
      const x = d3.scaleBand().domain(data.map((_, i) => i)).range([0, width]).padding(0.2);
      const y = d3.scaleLinear().domain([0, d3.max(data)]).range([height, 0]);
      svg.selectAll("rect").data(data).join("rect")
        .attr("x", (_, i) => x(i))
        .attr("y", (d) => y(d))
        .attr("width", x.bandwidth())
        .attr("height", (d) => height - y(d))
        .attr("fill", "#9d4edd");
      el.appendChild(svg.node());
    }
    export default { render };
    """
    data = traitlets.List(traitlets.Float()).tag(sync=True)


with ui.layout_columns():
    with ui.card():
        ui.card_header("Inline string")

        @render_widget
        def inline_box():
            return InlineBox()

    with ui.card():
        ui.card_header("Sibling file (box_widget.js)")

        @render_widget
        def file_box():
            return FileBox()

    with ui.card():
        ui.card_header("CDN import (d3, via esm.sh)")

        @render_widget
        def bars():
            return CdnBarChart(data=[4, 8, 15, 16, 23, 42])
