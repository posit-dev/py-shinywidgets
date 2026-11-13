import plotly.express as px
from keplergl import KeplerGl
from shiny.express import ui
from shinywidgets import render_keplergl

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

# A hand-written kepler.gl config: one 3D hexbin layer, colored and sized by
# average car-share hours per hexagon. Writing config upfront, rather than
# setting `.widget.config` after render, avoids a duplicate auto-created
# layer (see Gotchas & limitations).
CONFIG = {
    "version": "v1",
    "config": {
        "visState": {
            "layers": [
                {
                    "id": "carshare-hex",
                    "type": "hexagon",
                    "config": {
                        "dataId": "data",
                        "label": "Car-share activity",
                        "columns": {"lat": "lat", "lng": "lon"},
                        "isVisible": True,
                        "visConfig": {
                            "worldUnitSize": 0.5,
                            "resolution": 8,
                            "colorRange": {
                                "name": "Global Warming",
                                "type": "sequential",
                                "category": "Uber",
                                "colors": [
                                    "#4C0035",
                                    "#880030",
                                    "#B72F15",
                                    "#D6610A",
                                    "#EF9100",
                                    "#FFC300",
                                ],
                            },
                            "coverage": 0.9,
                            "elevationScale": 15,
                            "enable3d": True,
                        },
                    },
                    "visualChannels": {
                        "colorField": {"name": "car_hours", "type": "real"},
                        "colorScale": "quantile",
                        "sizeField": {"name": "car_hours", "type": "real"},
                        "sizeScale": "linear",
                    },
                }
            ],
        },
        "mapState": {
            "latitude": 45.53,
            "longitude": -73.626,
            "zoom": 11.2,
            "pitch": 50,
            "bearing": -15,
        },
    },
}

ui.page_opts(title="3D hexbin via config", fillable=True)


@render_keplergl
def map():
    return KeplerGl(data={"data": carshare}, config=CONFIG)
