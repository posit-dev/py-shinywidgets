import plotly.express as px
from ipycanvas import Canvas
from shiny.express import ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Drawing primitives", fillable=True)

# The 2007 gapminder rows with the 6 highest GDP per capita
top = px.data.gapminder().query("year == 2007").nlargest(6, "gdpPercap")

W, H = 520, 320
BAR_H = 36
MAX_GDP = top["gdpPercap"].max()

with ui.card(full_screen=True):

    @render_ipycanvas
    def chart():
        c = Canvas(width=W, height=H)
        c.font = "14px sans-serif"
        for i, (_, row) in enumerate(top.iterrows()):
            y = 10 + i * (BAR_H + 10)
            width = 260 * row["gdpPercap"] / MAX_GDP
            c.fill_style = "#2c7fb8"
            c.fill_rect(150, y, width, BAR_H)
            c.stroke_style = "#1c4f73"
            c.stroke_rect(150, y, width, BAR_H)
            c.fill_style = "#222"
            c.text_align = "right"
            c.fill_text(row["country"], 140, y + BAR_H / 2 + 5)
            c.text_align = "left"
            c.fill_text(f"${row['gdpPercap']:,.0f}", 150 + width + 8, y + BAR_H / 2 + 5)
        return c
