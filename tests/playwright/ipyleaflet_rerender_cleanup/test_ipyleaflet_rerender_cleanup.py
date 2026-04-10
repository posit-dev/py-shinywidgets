from __future__ import annotations

from playwright.sync_api import Page, expect


def test_ipyleaflet_rerender_stays_usable_with_many_layers(
    page: Page, local_app
) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    expect(page.locator("#render_count")).to_have_text("0")
    expect(page.locator("#plot .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#plot .leaflet-control-container")).to_have_count(
        1, timeout=30000
    )
    page.wait_for_function(
        """() =>
        document.querySelectorAll("#plot path.leaflet-interactive").length > 0
        """,
        timeout=30000,
    )

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i), timeout=30000)
        expect(page.locator("#plot .leaflet-container")).to_have_count(1, timeout=30000)
        expect(page.locator("#plot .leaflet-control-container")).to_have_count(
            1, timeout=30000
        )
        page.wait_for_function(
            """() =>
            document.querySelectorAll("#plot path.leaflet-interactive").length > 0
            """,
            timeout=30000,
        )

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("state_change" in err.lower() for err in errors)
    assert not any("t is undefined" in err.lower() for err in errors)
    assert not any(
        "cannot read properties of undefined" in err.lower() for err in errors
    )
