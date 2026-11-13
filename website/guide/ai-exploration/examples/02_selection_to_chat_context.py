# Lasso some points, THEN ask the chat about "the points I selected" -- the
# question is augmented with a small SUMMARY of plot.selected_rows(df) (not
# the raw rows) before it goes to the model, keeping the prompt small no
# matter how big the selection is.
#
# Nothing here reads plot.selected_rows() until chat.on_user_submit runs,
# which only happens after the user's first message -- the textbook "read on
# demand" case. That's safe because the accessor attaches the moment `plot`
# renders and records the lasso whether or not anything has read it yet; see
# ../../reacting-to-widgets/article.md#read-on-demand.
import chatlas
import plotly.express as px
from shiny.express import ui
from shinychat.express import Chat

from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)
chat_client = chatlas.ChatAnthropic(
    model="claude-haiku-5-5",
    system_prompt="You analyze a lasso selection from a gapminder scatter plot "
    "(gdp per capita vs. life expectancy, 2007). Answer in 2-3 sentences.",
)

ui.page_opts(title="Selection as chat context", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Lasso some countries")

        @render_plotly
        def plot():
            fig = px.scatter(
                df, x="gdpPercap", y="lifeExp", color="continent",
                custom_data=[df.index],
            )
            return fig.update_layout(dragmode="lasso")

    with ui.card(full_screen=True):
        ui.card_header("Ask about your selection")
        chat = Chat("chat", greeting="Lasso some points, then ask me about them.")
        chat.ui()

        @chat.on_user_submit
        async def _respond(user_input: str):
            rows = plot.selected_rows(df)
            if rows.empty:
                summary = "Nothing is currently selected on the plot."
            else:
                top_continents = rows["continent"].value_counts().head(3).to_dict()
                summary = (
                    f"{len(rows)} countries selected. "
                    f"Mean life expectancy {rows['lifeExp'].mean():.1f}, "
                    f"mean gdp per capita {rows['gdpPercap'].mean():.0f}. "
                    f"Continents: {top_continents}."
                )
            prompt = f"Selection summary: {summary}\n\nQuestion: {user_input}"
            response = await chat_client.stream_async(prompt)
            await chat.append_message_stream(response)
