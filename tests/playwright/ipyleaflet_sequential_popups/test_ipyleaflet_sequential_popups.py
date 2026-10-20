from playwright.sync_api import Page, expect


# Issue #194: sequential map clicks each produce a popup with a rendered
# plotly FigureWidget child. On the ipywidgets-7-era html-manager (<= 0.8.2)
# only the last popup ever displayed; fixed by the html-manager 1.0 upgrade.
def test_sequential_popups_render_plotly(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    map_el = page.locator(".leaflet-container")
    expect(map_el).to_be_visible(timeout=30000)

    box = map_el.bounding_box()
    assert box is not None
    points = [
        (box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.5),
        (box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.6),
    ]

    for x, y in points:
        page.mouse.click(x, y)
        popup = page.locator(".leaflet-popup")
        expect(popup).to_have_count(1, timeout=15000)
        plotly = popup.locator(".js-plotly-plot")
        expect(plotly).to_have_count(1, timeout=20000)

    assert not errors, f"Unexpected console errors: {errors}"
