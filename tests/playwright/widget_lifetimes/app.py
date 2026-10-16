import ipywidgets as W
from ipywidgets.widgets.widget import _instances
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_select("key", "Cached key", ["A", "B"]),
    ui.input_action_button("recolor", "Recolor cached A"),
    ui.output_text("server_widgets"),
    output_widget("fresh"),
    output_widget("cached"),
)


def server(input, output, session):
    @render_widget
    def fresh():
        n = input.rerender()
        # Each child lazily creates a Layout and a Style model while serializing.
        return W.VBox([W.Button(description=f"btn {n}"), W.IntSlider(value=n)])

    cache: dict[str, W.Button] = {}

    @render_widget
    def cached():
        key = input.key()
        if key not in cache:
            with session_lifetime():
                cache[key] = W.Button(description=f"cached {key}")
            # Materialized under the render, but owned by the cached widget.
            cache[key].style.button_color = "rgb(200, 200, 200)"
        return cache[key]

    @reactive.effect
    @reactive.event(input.recolor)
    def _():
        cache["A"].style.button_color = "rgb(0, 128, 0)"

    @render.text
    def server_widgets():
        reactive.invalidate_later(0.25)
        return str(len(_instances))


app = App(app_ui, server)
