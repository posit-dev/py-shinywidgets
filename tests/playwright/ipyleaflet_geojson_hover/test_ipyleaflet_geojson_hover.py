from __future__ import annotations

from playwright.sync_api import Page, expect


def test_geojson_hover_updates_widget_control(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    map_locator = page.locator(".leaflet-container")
    map_locator.wait_for(timeout=30000)
    page.wait_for_function(
        """() =>
        document
            .querySelector(".leaflet-container")
            ?.classList.contains("leaflet-touch-zoom")
        """,
        timeout=30000,
    )

    # WidgetControl with HTML should be rendered
    html_control = page.locator(".leaflet-control .widget-html-content")
    expect(html_control).to_have_count(1, timeout=5000)
    expect(html_control).to_contain_text("Hover over a region")

    # Hover over the GeoJSON polygon to trigger on_hover callback
    geojson_path = page.locator(".leaflet-interactive")
    expect(geojson_path).to_have_count(1, timeout=5000)
    geojson_path.hover()

    # The on_hover callback should update the HTML widget text
    expect(html_control).to_contain_text("TestRegion", timeout=5000)

    assert not errors, f"Unexpected console errors: {errors}"
