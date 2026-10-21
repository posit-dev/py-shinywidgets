import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.widgets import RectangleSelector
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_matplotlib

rng = np.random.default_rng(1)

# Three years of noisy daily readings with a few short-lived spikes: detail
# that's invisible at full scale but obvious once you zoom in
days = pd.date_range("2023-01-01", periods=3 * 365, freq="D")
seasonal = 15 + 10 * np.sin(2 * np.pi * np.arange(len(days)) / 365)
readings = seasonal + rng.normal(0, 1.5, len(days))
for i in rng.choice(len(days), 6, replace=False):
    readings[i : i + 3] += rng.uniform(8, 14)

cars = pd.DataFrame(
    {
        "model": [f"Car {i + 1}" for i in range(150)],
        "weight": rng.uniform(1.5, 5.0, 150).round(2),
    }
)
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, 150)).round(1)
cars["hp"] = (40 * cars["weight"] + rng.normal(0, 25, 150)).round()


def timeseries_figure():
    fig, ax = plt.subplots()
    ax.plot(days, readings, lw=0.8)
    ax.set_ylabel("Reading")
    fig.autofmt_xdate()
    return fig


def note(*args):
    return ui.p(*args, class_="text-muted small mb-2")


app_ui = ui.page_navbar(
    ui.nav_panel(
        "1. Zoom & pan",
        note(
            "Same figure, rendered two ways. There are six short spikes hidden in "
            "this data. On the right, pick the ",
            ui.tags.b("zoom-to-rectangle"),
            " tool (the square icon in the toolbar) and drag a box around a "
            "bump to inspect it, use the ",
            ui.tags.b("pan"),
            " tool to move along, and ",
            ui.tags.b("home"),
            " to reset. The cursor's data coordinates show below the figure. "
            "None of that is possible with the static image on the left.",
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("@render.plot (static image)"),
                ui.output_plot("static_plot"),
            ),
            ui.card(
                ui.card_header("@render_matplotlib (interactive ipympl widget)"),
                output_widget("interactive_plot"),
            ),
        ),
    ),
    ui.nav_panel(
        "2. Select points → Python",
        note(
            "Drag a box on the scatter plot (with no toolbar tool active). The "
            "selection is handled by a regular matplotlib callback, in Python, "
            "which updates a reactive value, so the table and summary update. "
            "Any matplotlib event (clicks, key presses, selectors) works this way.",
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Cars: weight vs. mpg"),
                output_widget("scatter"),
            ),
            ui.card(
                ui.card_header(ui.output_text("selection_summary")),
                ui.output_data_frame("selected_table"),
            ),
            col_widths=(7, 5),
        ),
    ),
    ui.nav_panel(
        "3. Update in place",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_slider("freq", "Frequency", 1, 20, 5),
                ui.input_slider("noise", "Noise", 0.0, 1.0, 0.1, step=0.05),
                note(
                    "Zoom into part of the plot first, then move the sliders. "
                    "The line is updated in place (line.set_ydata() + "
                    "draw_idle()), so your zoom is kept. With @render.plot, "
                    "every change redraws the whole figure from scratch."
                ),
            ),
            ui.card(output_widget("live")),
        ),
    ),
    title="matplotlib, interactive",
    fillable=True,
)


def server(input, output, session):
    # ---- 1. Zoom & pan --------------------------------------------------------
    @render.plot
    def static_plot():
        return timeseries_figure()

    @render_matplotlib
    def interactive_plot():
        return timeseries_figure()

    # ---- 2. Select points -----------------------------------------------------
    selected = reactive.value(np.zeros(len(cars), dtype=bool))

    @render_matplotlib
    def scatter():
        fig, ax = plt.subplots()
        points = ax.scatter(cars["weight"], cars["mpg"], c="tab:blue", alpha=0.7)
        ax.set_xlabel("Weight (1000 lbs)")
        ax.set_ylabel("Miles per gallon")

        def on_select(press, release):
            x0, x1 = sorted([press.xdata, release.xdata])
            y0, y1 = sorted([press.ydata, release.ydata])
            mask = cars["weight"].between(x0, x1) & cars["mpg"].between(y0, y1)
            points.set_facecolors(np.where(mask, "tab:orange", "tab:blue"))
            fig.canvas.draw_idle()
            selected.set(mask.to_numpy())

        # Keep a reference: matplotlib selectors stop working once garbage
        # collected
        fig._selector = RectangleSelector(ax, on_select, interactive=True)
        return fig

    @render.text
    def selection_summary():
        sel = cars[selected()]
        if sel.empty:
            return "Nothing selected"
        return f"{len(sel)} cars selected · mean mpg {sel['mpg'].mean():.1f}"

    @render.data_frame
    def selected_table():
        return cars[selected()]

    # ---- 3. Update in place ---------------------------------------------------
    x = np.linspace(0, 1, 500)

    @render_matplotlib
    def live():
        # Deliberately doesn't depend on the sliders: the figure is built once
        fig, ax = plt.subplots()
        ax.plot(x, np.sin(2 * np.pi * 5 * x))
        ax.set_ylim(-2.2, 2.2)
        return fig

    @reactive.effect
    def _():
        # The rendered ipympl Canvas (reading it waits until it has rendered)
        canvas = live.widget
        if canvas is None:
            return
        noise = rng.normal(0, input.noise(), len(x))
        line = canvas.figure.axes[0].lines[0]
        line.set_ydata(np.sin(2 * np.pi * input.freq() * x) + noise)
        canvas.draw_idle()


app = App(app_ui, server)
