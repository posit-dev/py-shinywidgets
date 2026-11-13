import plotly.express as px
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Toggle legend items to filter the summary", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            return px.scatter(df, x="gdpPercap", y="lifeExp", color="continent", log_x=True)

    with ui.card():
        ui.card_header("Mean life expectancy, visible continents only")

        @render.data_frame
        def summary():
            vis = plot.visible_traces()
            # None until the browser reports the seed just after first draw
            req(vis is not None)
            shown = set(vis.loc[vis["visible"], "name"])
            subset = df[df["continent"].isin(shown)]
            agg = subset.groupby("continent", as_index=False)["lifeExp"].mean().round(1)
            return render.DataGrid(agg)

        "plot.legend_clicked() -- the trace(s) the last click affected"

        @render.code
        def last_click():
            traces = plot.legend_clicked()
            if traces is None:
                return "None (click a legend item)"
            return ";".join(f"{r.trace_index},{r.name}" for r in traces.itertuples())
