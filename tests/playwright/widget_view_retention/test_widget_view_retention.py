import pytest
from playwright.sync_api import Page, Route, expect
from shiny.run import ShinyAppProc


@pytest.mark.parametrize("mode", ["cached", "popup"])
def test_replaced_views_are_removed(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(f"{local_app.url}?mode={mode}")
    expect(page.locator("#render_count")).to_have_text("0")
    expect(page.locator("#widget > .lm-Widget")).to_have_count(1)
    if mode == "popup":
        page.locator(".leaflet-marker-icon").click()
        expect(page.locator(".leaflet-popup-content")).to_have_text("Popup render 0")
        page.locator(".leaflet-popup-close-button").click()

    page.evaluate(
        """() => {
            window.previousView = [...window.widgetManager._viewList][0];
        }"""
    )
    for n in range(1, 4):
        old_node = page.locator("#widget > .lm-Widget").element_handle()
        page.click("#redraw")
        expect(page.locator("#render_count")).to_have_text(str(n))
        page.wait_for_function("(node) => !node.isConnected", arg=old_node)
        expect(page.locator("#widget > .lm-Widget")).to_have_count(1)
        if mode == "popup":
            page.locator(".leaflet-marker-icon").click()
            expect(page.locator(".leaflet-popup-content")).to_have_text(
                f"Popup render {n}"
            )
            page.locator(".leaflet-popup-close-button").click()

    state = page.evaluate(
        """() => {
            const manager = window.widgetManager;
            const previous = window.previousView;
            return {
                trackedViews: manager._viewList.size,
                previousTracked: manager._viewList.has(previous),
                previousDisposed: previous.luminoWidget.isDisposed,
                previousAttached: previous.luminoWidget.isAttached,
                previousModelRegistered: manager.has_model(previous.model.model_id)
            };
        }"""
    )
    assert state["trackedViews"] == 1, "The old view remains tracked after replacement"
    assert not state["previousTracked"]
    assert state["previousDisposed"]
    assert not state["previousAttached"]
    assert state["previousModelRegistered"] == (mode == "cached")

    if mode == "popup":
        page.locator(".leaflet-marker-icon").click()
        expect(page.locator(".leaflet-popup-content")).to_have_text("Popup render 3")
    else:
        expect(page.locator("#widget")).to_have_text("Persistent widget")


@pytest.mark.parametrize("mode", ["empty", "error"])
def test_cleared_outputs_remove_the_previous_view(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#widget")).to_have_text("Persistent widget")
    page.evaluate(
        """() => {
            window.previousView = [...window.widgetManager._viewList][0];
        }"""
    )

    page.select_option("#mode", mode)
    if mode == "empty":
        page.wait_for_function(
            "() => document.querySelector('#widget').style.visibility === 'hidden'"
        )
    else:
        expect(page.locator("#widget")).to_have_text("Requested widget failure")
    expect(page.locator("#widget > .lm-Widget")).to_have_count(0)
    state = page.evaluate(
        """() => {
            const manager = window.widgetManager;
            const previous = window.previousView;
            return {
                trackedViews: manager._viewList.size,
                previousDisposed: previous.luminoWidget.isDisposed,
                previousAttached: previous.luminoWidget.isAttached,
                previousModelRegistered: manager.has_model(previous.model.model_id)
            };
        }"""
    )
    assert state == {
        "trackedViews": 0,
        "previousDisposed": True,
        "previousAttached": False,
        "previousModelRegistered": True,
    }


@pytest.mark.parametrize("mode", ["empty", "error"])
def test_widget_recovers_after_output_is_cleared(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#widget")).to_have_text("Persistent widget")
    page.evaluate(
        """() => {
            window.cachedModel = [...window.widgetManager._viewList][0].model;
        }"""
    )
    page.select_option("#mode", mode)
    if mode == "empty":
        page.wait_for_function(
            "() => document.querySelector('#widget').style.visibility === 'hidden'"
        )
    else:
        expect(page.locator("#widget")).to_have_text("Requested widget failure")

    page.select_option("#mode", "cached")

    expect(page.locator("#widget")).to_have_text("Persistent widget")
    expect(page.locator("#widget > .lm-Widget")).to_have_count(1)
    assert page.evaluate(
        """() => {
            const manager = window.widgetManager;
            return {
                trackedViews: manager._viewList.size,
                cachedModelRegistered: manager.has_model(window.cachedModel.model_id),
                cachedModelReused: [...manager._viewList][0].model === window.cachedModel
            };
        }"""
    ) == {
        "trackedViews": 1,
        "cachedModelRegistered": True,
        "cachedModelReused": True,
    }


def expose_manager(route: Route) -> None:
    response = route.fetch()
    text = response.text()
    original = "const manager = new OutputManager({ loader: shinyRequireLoader });"
    assert original in text
    route.fulfill(
        response=response,
        body=text.replace(
            original,
            "const manager = window.widgetManager = new OutputManager({ loader: shinyRequireLoader });",
        ),
    )
