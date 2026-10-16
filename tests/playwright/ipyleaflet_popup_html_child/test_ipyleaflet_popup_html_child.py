from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


# Issue #101: marker popup with a plain-ipywidgets (HTML) child failed to
# render with the ipywidgets-7-era html-manager (`HTMLStyleModel not found in
# @jupyter-widgets/controls@2.0.0`). Fixed by the html-manager 1.0 upgrade.
def test_marker_popup_with_html_child(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.locator(".leaflet-container").wait_for(timeout=30000)
    marker = page.locator(".leaflet-marker-icon")
    expect(marker).to_have_count(1, timeout=15000)
    marker.click()
    popup = page.locator(".leaflet-popup-content")
    expect(popup).to_contain_text("hello popup #101", timeout=10000)
    page.set_viewport_size({"width": 960, "height": 720})
    # Let the manager's queued resize messages run before checking page errors.
    page.evaluate(
        """() => new Promise(resolve =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
        )"""
    )
    expect(popup).to_contain_text("hello popup #101")
    assert not errors, f"Unexpected console errors: {errors}"


def test_session_popup_and_style_survive_map_replacement(
    page: Page, local_app: ShinyAppProc
) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console", lambda msg: errors.append(msg.text) if msg.type == "error" else None
    )
    page.goto(local_app.url)
    page.locator(".leaflet-marker-icon").click()
    expect(page.locator(".leaflet-popup-content")).to_have_text("hello popup #101")
    page.locator(".leaflet-popup-close-button").click()

    # The style originates in the temporary borrower's default factory;
    # its retained popup must protect it when that render ends.
    for n, color in enumerate(["rgb(255, 0, 0)", "rgb(0, 0, 255)"], start=1):
        previous_id = page.locator("#map").get_attribute("data-shinywidgets-model-id")
        page.click("#rerender")
        # Wait for the replacement map (not just any marker) to attach.
        page.wait_for_function(
            """(previous) => {
                const el = document.querySelector('#map');
                return el.dataset.shinywidgetsModelId &&
                    el.dataset.shinywidgetsModelId !== previous;
            }""",
            arg=previous_id,
        )
        page.locator(".leaflet-marker-icon").click()
        expect(page.locator("#style_lifetime")).to_have_text("render")
        expect(page.locator(".leaflet-popup-content")).to_have_text(f"shared popup {n}")
        expect(page.locator(".leaflet-popup-content .widget-html-content")).to_have_css(
            "color", color
        )
        page.locator(".leaflet-popup-close-button").click()
    assert not errors, errors
