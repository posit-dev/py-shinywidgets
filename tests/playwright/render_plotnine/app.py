from __future__ import annotations

from matplotlib.text import Text
from plotnine import aes, geom_point, ggplot, labs, theme
from plotnine.data import mpg
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotnine

app_ui = ui.page_fillable(
    ui.div(
        ui.input_action_button("rerender", "Rerender"),
        ui.input_action_button("check_layout", "Check layout"),
        ui.output_text("render_count", inline=True),
        ui.output_text("layout", inline=True),
        ui.output_text("clicked", inline=True),
    ),
    ui.layout_columns(
        ui.card(output_widget("plot"), full_screen=True),
        ui.div(output_widget("fixed", height="250px")),
        col_widths=(8, 4),
    ),
)


def server(input, output, session):
    @render.text
    def render_count():
        return str(input.rerender())

    @render_plotnine
    def plot():
        input.rerender()
        return (
            ggplot(mpg, aes("displ", "hwy", color="class"))
            + geom_point()
            + labs(title="Fuel economy", x="Displacement (L)", y="Highway MPG")
        )

    @render_plotnine
    def fixed():
        return (
            ggplot(mpg, aes("displ", "hwy")) + geom_point() + theme(figure_size=(4, 2))
        )

    # Reports the figure's size (in CSS px) and whether every text artist
    # (titles, axis labels, tick labels, legend) lies within the figure, as
    # laid out at the size the browser resized it to. plotnine only re-lays out
    # the plot when it's redrawn, which happens after the resize, so also report
    # whether the figure is stale (resized but not yet redrawn)
    @render.text
    @reactive.event(input.check_layout)
    def layout():
        canvas = plot.widget
        assert canvas is not None
        fig = canvas.figure
        renderer = fig.canvas.get_renderer()
        bounds = fig.bbox.padded(1)
        texts = [
            t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()
        ]
        clipped = [
            t.get_text()
            for t in texts
            if not bounds.contains(*t.get_window_extent(renderer).p0)
            or not bounds.contains(*t.get_window_extent(renderer).p1)
        ]
        ratio = canvas.device_pixel_ratio
        w, h = fig.bbox.width / ratio, fig.bbox.height / ratio
        return (
            f"n={input.check_layout()} size={w:.0f}x{h:.0f} stale={fig.stale} "
            f"texts={len(texts)} clipped={clipped}"
        )

    clicks = reactive.value(0)

    @reactive.effect
    def _():
        canvas = plot.widget
        canvas.mpl_connect(
            "button_press_event",
            lambda event: clicks.set(clicks.get() + 1) if event.inaxes else None,
        )

    @render.text
    def clicked():
        return f"clicks={clicks()}"


app = App(app_ui, server)
