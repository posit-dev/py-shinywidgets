# Register a tool the model can call to move the map. The tool validates
# `city` against a fixed allow-list before touching the widget -- the model's
# argument is untrusted text, so never pass it straight into widget state
# (or, worse, a file path, a URL, or a SQL string) without checking it first.
import chatlas
from ipyleaflet import Map
from shiny.express import ui
from shinychat.express import Chat

from shinywidgets import render_ipyleaflet

CITIES = {
    "paris": (48.8566, 2.3522, 11),
    "tokyo": (35.6762, 139.6503, 10),
    "nairobi": (-1.2921, 36.8219, 11),
    "san francisco": (37.7749, -122.4194, 11),
}

ui.page_opts(title="A tool that moves the map", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("fly_to() moves this map in place")

        @render_ipyleaflet
        def map():
            return Map(center=(20, 0), zoom=2)

    with ui.card(full_screen=True):
        ui.card_header("Ask it to fly somewhere")

        def fly_to(city: str) -> str:
            """
            Move the map to a named city.

            Parameters
            ----------
            city : str
                One of: paris, tokyo, nairobi, san francisco.
            """
            key = city.strip().lower()
            if key not in CITIES:
                return f"Unknown city {city!r}. Valid cities: {', '.join(CITIES)}."
            lat, lng, zoom = CITIES[key]
            map.widget.center = (lat, lng)
            map.widget.zoom = zoom
            return f"Map moved to {city} (zoom {zoom})."

        chat_client = chatlas.ChatAnthropic(
            model="claude-haiku-5-5",
            system_prompt="You control a map via the fly_to tool. "
            "Only call it with one of its supported cities.",
        )
        chat_client.register_tool(fly_to)

        chat = Chat(
            "chat",
            client=chat_client,
            greeting="Ask me to fly to paris, tokyo, nairobi, or san francisco.",
        )
        chat.ui()
