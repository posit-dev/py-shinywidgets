## pydeck layers app

<a href='https://connect.posit.cloud/publish?framework=shiny&sourceRepositoryURL=https%3A%2F%2Fgithub.com%2Fposit-dev%2Fpy-shinywidgets&sourceRef=main&sourceRefType=branch&primaryFile=examples%2Fpydeck%2Fapp.py&pythonVersion=3.11'><img src='https://cdn.connect.posit.cloud/assets/deploy-to-connect-blue.svg' align="right" /></a>

pydeck v0.9 removed its Jupyter widget (`Deck.show()` now returns static HTML), so `@render_pydeck` can no longer render a `pydeck.Deck`. pydeck's `pdk.Layer` API still works in Shiny, though: a [maplibre](https://eoda-dev.github.io/py-maplibregl/) map accepts `pdk.Layer` objects directly (`Map.add_deck_layers()`), and `@render_maplibre` turns it into a two-way Shiny output. This app bins 140,000 points into 3D hexagons in the browser, restyles them in place with `deck.widget.set_deck_layers()` when a slider moves (the camera stays put), and uses `reactive_read()` on the map's `view_state` and `clicked` traits to count what's on screen and near a click.

If your data is large, or you want selection tools, consider lonboard and `@render_lonboard` instead (see `examples/lonboard`).

If you only need a static map, skip shinywidgets and use shiny's `@render.ui`:

```python
@render.ui
def deck():
    return deck_object.show()  # a 500px-tall iframe
    # or, to fill the container:
    # return ui.tags.iframe(
    #     srcdoc=deck_object.to_html(as_string=True),
    #     style="border:0;width:100%;height:100%;flex:1 1 auto",
    # )
```

Every change re-sends the whole page (and resets the camera), and there are no events back to Python. Don't return `deck_object.to_html()`: without a filename, it returns `None`.
