import numpy as np
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, DataTable, Select, TableColumn
from bokeh.plotting import figure
from shiny.express import ui
from shinywidgets import render_bokeh

ui.page_opts(title="Bokeh's own widgets", fillable=True)

rng = np.random.default_rng(1)
data = {
    "temp": rng.normal(20, 4, 90),
    "humidity": rng.normal(55, 10, 90),
    "site": rng.choice(["A", "B", "C"], size=90),
}


@render_bokeh
def dashboard():
    src = ColumnDataSource(data)
    view = ColumnDataSource(data)

    p = figure(title="temperature vs. humidity", sizing_mode="stretch_both")
    p.scatter("temp", "humidity", source=view, size=10, alpha=0.7)

    table = DataTable(
        source=view,
        columns=[TableColumn(field=c) for c in ("site", "temp", "humidity")],
        height=200,
    )

    picker = Select(title="Site", value="All", options=["All", "A", "B", "C"])

    def filter_site(attr, old, new):
        if new == "All":
            view.data = dict(src.data)
        else:
            mask = src.data["site"] == new
            view.data = {k: np.asarray(v)[mask] for k, v in src.data.items()}

    picker.on_change("value", filter_site)

    return column(picker, row(p, table, sizing_mode="stretch_both"), sizing_mode="stretch_both")
