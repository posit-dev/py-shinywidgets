# Template: build your own anywidget, wired to Shiny
# A minimal click-counter heatmap -- a small grid of cells that light up as
# they're clicked. Adapt this skeleton for any custom widget: keep the
# Python class and the Shiny app in one file while you're developing, split
# them (like this guide's sparkline_widget.py) once the widget stabilizes.
# Run: uv run --no-sync shiny run template_anywidget_starter.py
# Data: synthetic (an 8x8 grid of click counts)
import anywidget
import traitlets
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

N = 8


class ClickHeatmap(anywidget.AnyWidget):
    _esm = """
    function render({ model, el }) {
      const n = model.get("n");
      const grid = document.createElement("div");
      grid.style.cssText = `display:grid;grid-template-columns:repeat(${n},28px);gap:2px;`;
      const cells = [];
      for (let i = 0; i < n * n; i++) {
        const cell = document.createElement("div");
        cell.style.cssText = "width:28px;height:28px;background:#eee;cursor:pointer;border:1px solid #ccc;box-sizing:border-box;";
        cell.addEventListener("click", () => {
          const counts = model.get("counts").slice();
          counts[i] += 1;
          model.set("counts", counts);
          model.set("last_clicked", i);
          model.save_changes();
        });
        grid.appendChild(cell);
        cells.push(cell);
      }
      el.appendChild(grid);

      function paint() {
        const counts = model.get("counts");
        const max = Math.max(1, ...counts);
        counts.forEach((c, i) => {
          const t = c / max;
          cells[i].style.background = `rgba(42, 111, 151, ${t})`;
        });
      }
      model.on("change:counts", paint);
      paint();
    }
    export default { render };
    """
    n = traitlets.Int(N).tag(sync=True)
    counts = traitlets.List(traitlets.Int()).tag(sync=True)
    last_clicked = traitlets.Int(allow_none=True, default_value=None).tag(sync=True)


ui.page_opts(title="Click-counter heatmap", fillable=True)
ui.input_action_button("reset", "Reset")

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card():

        @render_widget
        def heatmap():
            return ClickHeatmap(counts=[0] * (N * N))

        # Python -> JS, in place: a button resets the SAME widget's data
        # instead of re-rendering (re-rendering would also work, but would
        # send the whole JS bundle to the browser again).
        @reactive.effect
        @reactive.event(input.reset)
        def _reset():
            heatmap.widget.counts = [0] * (N * N)

    with ui.card():
        ui.card_header("heatmap.read(...)")

        @render.code
        def total_out():
            counts = heatmap.read("counts")
            last = heatmap.read("last_clicked")
            return f"total clicks: {sum(counts)}\nlast cell: {last}"
