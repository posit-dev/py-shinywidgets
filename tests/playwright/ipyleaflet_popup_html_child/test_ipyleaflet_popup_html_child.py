from playwright.sync_api import Page, expect


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
    assert not errors, f"Unexpected console errors: {errors}"
