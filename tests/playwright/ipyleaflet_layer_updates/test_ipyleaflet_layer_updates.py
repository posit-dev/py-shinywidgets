from playwright.sync_api import Page, expect


# Issue #212 symptoms: (1) after a city change, layers vanished from the
# layers control and the control swapped position with the search control;
# (2) clicking "Sample point" added no marker and made the layers button
# disappear. Verified fixed as of v0.8.2 (most likely by #225's child-model
# ordering fix in v0.8.0).
def test_layers_control_and_markers_survive_updates(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    expect(page.locator(".leaflet-container")).to_be_visible(timeout=30000)

    layers_ctrl = page.locator(".leaflet-control-layers")
    markers = page.locator(".leaflet-marker-icon")

    # Startup: loc1 + loc2 markers and the layers control
    expect(markers).to_have_count(2, timeout=20000)
    expect(layers_ctrl).to_have_count(1)

    # Click "Sample point": a 3rd marker appears, layers button stays
    page.click("#sample")
    expect(markers).to_have_count(3, timeout=15000)
    expect(layers_ctrl).to_have_count(1)

    # Click again: marker count stays at 3 (point re-added), control stays
    page.click("#sample")
    page.wait_for_timeout(1500)
    expect(markers).to_have_count(3, timeout=15000)
    expect(layers_ctrl).to_have_count(1)

    # Change a city via selectize: layers control keeps working
    page.evaluate(
        """() => {
            const el = $('#loc1');
            const s = el[0].selectize;
            s.setValue('Paris', true);
        }"""
    )
    page.wait_for_timeout(2000)
    expect(markers).to_have_count(3, timeout=15000)
    expect(layers_ctrl).to_have_count(1)

    # Layers control should still list all the overlay layers
    layers_ctrl.hover()
    labels = page.locator(".leaflet-control-layers-list label")
    expect(labels.first).to_be_visible(timeout=5000)
    texts = [labels.nth(i).inner_text() for i in range(labels.count())]
    joined = " ".join(texts)
    for layer_name in ["loc1", "loc2", "point", "line"]:
        assert layer_name in joined, f"layer {layer_name!r} missing from {texts}"

    # Controls shouldn't have swapped position: layers control stays topleft
    expect(
        page.locator(".leaflet-top.leaflet-left .leaflet-control-layers")
    ).to_have_count(1)

    assert not errors, f"Unexpected console errors: {errors}"
