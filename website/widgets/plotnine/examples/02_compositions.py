from plotnine import aes, geom_boxplot, geom_histogram, geom_point, ggplot, labs, theme
from plotnine.data import penguins
from shiny.express import ui
from shinywidgets import render_plotnine

penguins = penguins.dropna().reset_index(drop=True)

ui.page_opts(title="plotnine compositions", fillable=True)

no_legend = theme(legend_position="none")

with ui.card(full_screen=True):
    ui.card_header("Bill shape, species, and flipper length")

    @render_plotnine
    def composed():
        scatter = (
            ggplot(penguins, aes("bill_length_mm", "bill_depth_mm", color="species"))
            + geom_point()
            + labs(x="Bill length (mm)", y="Bill depth (mm)", color="Species")
        )
        box = (
            ggplot(penguins, aes("species", "body_mass_g", fill="species"))
            + geom_boxplot()
            + labs(x="", y="Body mass (g)")
            + no_legend
        )
        hist = (
            ggplot(penguins, aes("flipper_length_mm", fill="species"))
            + geom_histogram(bins=30, alpha=0.7, position="identity")
            + labs(x="Flipper length (mm)", y="Count")
            + no_legend
        )
        return (scatter | box) / hist
