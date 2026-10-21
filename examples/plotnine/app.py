import numpy as np
from plotnine import (
    aes,
    geom_boxplot,
    geom_histogram,
    geom_point,
    geom_smooth,
    ggplot,
    labs,
    theme,
    theme_minimal,
)
from plotnine.data import penguins
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotnine

penguins = penguins.dropna().reset_index(drop=True)

numeric_vars = {
    "bill_length_mm": "Bill length (mm)",
    "bill_depth_mm": "Bill depth (mm)",
    "flipper_length_mm": "Flipper length (mm)",
    "body_mass_g": "Body mass (g)",
}
group_vars = {"species": "Species", "island": "Island", "sex": "Sex"}
labels = {**numeric_vars, **group_vars}


def note(*args):
    return ui.p(*args, class_="text-muted small mb-2")


app_ui = ui.page_navbar(
    ui.nav_panel(
        "1. Explore & click",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_select("x", "X", numeric_vars, selected="flipper_length_mm"),
                ui.input_select("y", "Y", numeric_vars, selected="body_mass_g"),
                ui.input_select("color", "Color", group_vars),
                ui.input_switch("smooth", "Linear fit per group", True),
                note(
                    "Use the toolbar (hover over the plot) to ",
                    ui.tags.b("zoom"),
                    " and ",
                    ui.tags.b("pan"),
                    ". Expand the card to full screen or resize the window: "
                    "plotnine re-lays out the legend and labels at every size.",
                ),
                note(
                    "Click a point (with no toolbar tool active). A matplotlib "
                    "callback finds the nearest penguin in Python, circles it "
                    "in place (keeping your zoom), and fills in the table.",
                ),
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Palmer penguins"),
                    output_widget("scatter"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("Clicked penguin"),
                    ui.output_data_frame("clicked_table"),
                ),
                col_widths=(8, 4),
            ),
        ),
    ),
    ui.nav_panel(
        "2. Compositions",
        note(
            "plotnine plot compositions (e.g., ",
            ui.code("(p1 | p2) / p3"),
            ") render as a single figure that fills its card and is laid out "
            "as a whole.",
        ),
        ui.card(output_widget("composed"), full_screen=True),
    ),
    title="plotnine, interactive",
    fillable=True,
)


def server(input, output, session):
    # ---- 1. Explore & click ---------------------------------------------------
    @render_plotnine
    def scatter():
        x, y, color = input.x(), input.y(), input.color()
        p = (
            ggplot(penguins, aes(x, y, color=color))
            + geom_point(size=2.5, alpha=0.8)
            + labs(x=labels[x], y=labels[y], color=labels[color])
            + theme_minimal()
        )
        if input.smooth():
            p += geom_smooth(method="lm")
        return p

    clicked = reactive.value(penguins.iloc[[]])

    # Runs whenever the plot re-renders (reading .widget waits for, and
    # depends on, the rendered ipympl Canvas)
    @reactive.effect
    def _():
        canvas = scatter.widget
        ax = canvas.figure.axes[0]
        with reactive.isolate():
            x, y = input.x(), input.y()
        clicked.set(penguins.iloc[[]])
        (circle,) = ax.plot(
            [], [], ls="none", marker="o", ms=14, mfc="none", mec="black", mew=2
        )

        def on_click(event):
            if event.inaxes is not ax or canvas.toolbar.mode:
                return
            # Nearest point on screen (in display coordinates)
            xy = ax.transData.transform(penguins[[x, y]].to_numpy())
            i = int(np.hypot(xy[:, 0] - event.x, xy[:, 1] - event.y).argmin())
            circle.set_data([penguins[x][i]], [penguins[y][i]])
            canvas.draw_idle()
            clicked.set(penguins.iloc[[i]])

        canvas.mpl_connect("button_press_event", on_click)

    @render.data_frame
    def clicked_table():
        row = clicked()
        if row.empty:
            return None
        return row.T.reset_index().set_axis(["variable", "value"], axis=1)

    # ---- 2. Compositions ------------------------------------------------------
    @render_plotnine
    def composed():
        no_legend = theme(legend_position="none")
        scatter = (
            ggplot(penguins, aes("bill_length_mm", "bill_depth_mm", color="species"))
            + geom_point()
            + labs(
                x=labels["bill_length_mm"],
                y=labels["bill_depth_mm"],
                color=labels["species"],
            )
        )
        box = (
            ggplot(penguins, aes("species", "body_mass_g", fill="species"))
            + geom_boxplot()
            + labs(x="", y=labels["body_mass_g"])
            + no_legend
        )
        hist = (
            ggplot(penguins, aes("flipper_length_mm", fill="species"))
            + geom_histogram(bins=30, alpha=0.7, position="identity")
            + labs(x=labels["flipper_length_mm"], y="Count")
            + no_legend
        )
        return (scatter | box) / hist


app = App(app_ui, server)
