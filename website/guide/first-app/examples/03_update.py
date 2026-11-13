import plotly.express as px
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Gapminder 2007", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Lasso a few countries")

        @render_plotly
        def plot():
            fig = px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                size="pop",
                color="continent",
                size_max=48,
                hover_name="country",
                custom_data=[df.index],
                log_x=True,
                template="plotly_white",
            )
            fig.update_traces(marker=dict(opacity=0.85, line=dict(width=0)))
            fig.update_layout(dragmode="lasso", legend_title_text="")
            return fig

    with ui.card(full_screen=True):
        ui.card_header("Selected countries")

        @render.data_frame
        def selected_countries():
            rows = plot.selected_rows(df)
            req(not rows.empty)
            return rows[["country", "continent", "gdpPercap", "lifeExp", "pop"]]


# Summarize the lassoed countries directly on the existing figure, as an
# annotation, without rebuilding the plot: a re-render would clear the lasso
# itself and reset any zoom the user made first. No `reactive.isolate()`
# around the write below: restyling `plot.widget` doesn't feed back into
# `selected_rows()`, which only updates from the browser's own selection
# events. See "Writing back" in the Updating in place guide for the pattern
# where isolate() IS required (an effect that reads and writes the SAME reactive
# state).
@reactive.effect
def _summarize():
    rows = plot.selected_rows(df)
    note = (
        f"<b>{len(rows)} countries</b><br>"
        f"avg life expectancy {rows.lifeExp.mean():.1f} yrs<br>"
        f"{rows['pop'].sum() / 1e9:.1f}B people"
        if len(rows)
        else ""
    )
    plot.widget.layout.annotations = [
        dict(
            text=note,
            xref="paper", yref="paper", x=0.02, y=0.98,
            xanchor="left", yanchor="top", align="left",
            showarrow=False, font=dict(size=15, color="#111"),
            bgcolor="rgba(255,255,255,0.92)", bordercolor="#111",
            borderwidth=1.5, borderpad=10,
        )
    ] if note else []
