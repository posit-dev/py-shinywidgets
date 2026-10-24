"""Regression test for #212: LayersControl must stay consistent after remove+add."""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_layers_control_consistent_after_update(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    map_loc = page.locator(".leaflet-container")
    map_loc.wait_for(timeout=30000)

    # Wait for the map to be fully interactive
    page.wait_for_function(
        """() =>
        document
            .querySelector(".leaflet-container")
            ?.classList.contains("leaflet-touch-zoom")
        """,
        timeout=30000,
    )

    # Initial load: marker + line should both be in the layers control
    expect(page.locator(".leaflet-marker-icon")).to_have_count(1, timeout=5000)

    layers_control = page.locator(".leaflet-control-layers")
    expect(layers_control).to_have_count(1)
    layers_control.hover()

    overlay_labels = page.locator(".leaflet-control-layers-overlays label")
    expect(overlay_labels).to_have_count(2)

    # Change location — triggers remove+add for both marker and line
    page.locator("#loc-selectized").click()
    page.locator("#loc-selectized").fill("B")
    page.locator('.option[data-value="B"]').click()

    # Wait for the update to propagate
    page.wait_for_timeout(2000)

    # Marker should still be visible
    expect(page.locator(".leaflet-marker-icon")).to_have_count(1, timeout=5000)

    # Layers control should still list both overlays after remove+add
    layers_control.hover()
    expect(overlay_labels).to_have_count(2, timeout=5000)

    # Change again to verify stability
    page.locator("#loc-selectized").click()
    page.locator("#loc-selectized").fill("C")
    page.locator('.option[data-value="C"]').click()

    page.wait_for_timeout(2000)
    expect(page.locator(".leaflet-marker-icon")).to_have_count(1, timeout=5000)

    layers_control.hover()
    expect(overlay_labels).to_have_count(2, timeout=5000)

    assert not errors, f"Unexpected JS errors: {errors}"
