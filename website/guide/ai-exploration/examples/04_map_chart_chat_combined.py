# A realistic combination: pan/zoom the map, read a plotly bar chart of
# what's visible, or just ask the chat -- "summarize_view" reads the SAME
# map.bounds() accessor the chart uses (read on demand, from inside a tool
# call, with no warm-up read needed), so the chat's answer and the chart
# always agree. "fly_to" is a second tool, validated against a fixed
# allow-list, that moves the map. Real data: 249 car2go pod locations
# around Montreal (plotly's carshare dataset).
import chatlas
import ipyleaflet as L
import pandas as pd
import plotly.express as px
from shiny import reactive
from shiny.express import ui
from shinychat.express import Chat

from shinywidgets import render_ipyleaflet, render_plotly

pods = px.data.carshare()
pods["period"] = pd.cut(
    pods["peak_hour"], bins=[-1, 5, 11, 17, 23],
    labels=["night", "morning", "afternoon", "evening"],
)
PERIODS = ["night", "morning", "afternoon", "evening"]

PLACES = {
    "downtown": (45.5017, -73.5673, 13),
    "old port": (45.5075, -73.5540, 15),
    "plateau": (45.5234, -73.5825, 14),
    "west island": (45.4443, -73.8275, 12),
    "overview": (45.52, -73.59, 11),
}

ui.page_opts(title="Map + chart + chat", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Pan or zoom; fly_to() moves this map in place")

        @render_ipyleaflet
        def map():
            m = L.Map(center=(45.52, -73.59), zoom=11)
            markers = [L.Marker(location=(r.centroid_lat, r.centroid_lon)) for r in pods.itertuples()]
            m.add(L.MarkerCluster(markers=markers))
            return m

    with ui.div(class_="d-flex flex-column gap-3", style="height: 100%;"):
        with ui.card(full_screen=True):
            ui.card_header("Visible pods, by time of day")

            @render_plotly
            def chart():
                (south, west), (north, east) = map.bounds()
                visible = pods[pods.centroid_lat.between(south, north) & pods.centroid_lon.between(west, east)]
                counts = visible["period"].value_counts().reindex(PERIODS).reset_index()
                counts.columns = ["period", "count"]
                return px.bar(counts, x="period", y="count")

        with ui.card(full_screen=True):
            ui.card_header("Ask about the map")

            def summarize_view() -> str:
                """Summarize the car-share pods currently visible on the map, by time of day."""
                with reactive.isolate():
                    (south, west), (north, east) = map.bounds()
                visible = pods[pods.centroid_lat.between(south, north) & pods.centroid_lon.between(west, east)]
                counts = visible["period"].value_counts().reindex(PERIODS, fill_value=0)
                parts = ", ".join(f"{p}: {n}" for p, n in counts.items())
                return f"{len(visible)} pods visible ({parts})."

            def fly_to(place: str) -> str:
                """
                Move the map to a named place.

                Parameters
                ----------
                place : str
                    One of: downtown, old port, plateau, west island, overview.
                """
                key = place.strip().lower()
                if key not in PLACES:
                    return f"Unknown place {place!r}. Valid places: {', '.join(PLACES)}."
                lat, lng, zoom = PLACES[key]
                map.widget.center = (lat, lng)
                map.widget.zoom = zoom
                return f"Map moved to {place} (zoom {zoom})."

            chat_client = chatlas.ChatAnthropic(
                model="claude-haiku-5-5",
                system_prompt="You help explore a map of Montreal car-share pods. "
                "Use summarize_view to describe what's currently visible, and "
                "fly_to to move the map to one of its supported places.",
            )
            chat_client.register_tool(summarize_view)
            chat_client.register_tool(fly_to)

            chat = Chat(
                "chat",
                client=chat_client,
                greeting="Pan the map, or ask what's visible. "
                "I can also fly to downtown, old port, plateau, or west island.",
            )
            chat.ui()
