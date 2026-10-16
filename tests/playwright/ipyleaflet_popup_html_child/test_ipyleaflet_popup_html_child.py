import pytest
from conftest import open_lifecycle_page
from playwright.sync_api import ConsoleMessage, JSHandle, Page, expect
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
    errors = record_errors(page)
    open_lifecycle_page(page, local_app)
    page.locator(".leaflet-marker-icon").click()
    expect(page.locator(".leaflet-popup-content")).to_have_text("hello popup #101")
    page.locator(".leaflet-popup-close-button").click()

    # The style originates in the temporary borrower's default factory;
    # its retained popup must protect it when that render ends.
    popup_model: JSHandle | None = None
    for n, color in enumerate(["rgb(255, 0, 0)", "rgb(0, 0, 255)"], start=1):
        native_map = page.evaluate_handle(
            """() => Array.from(window.widgetLifecycle.activeViews()).find(view =>
                view.model.get('_view_name') === 'LeafletMapView'
            ).obj"""
        )
        assert native_map.evaluate(
            "map => typeof map.getContainer()._leaflet_id === 'number'"
        )
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
        if popup_model is None:
            popup_model = page.evaluate_handle(
                """() => Array.from(window.widgetLifecycle.activeViews()).find(view =>
                    view.model.get('value') === 'shared popup 1'
                ).model"""
            )
        assert popup_model.evaluate("model => Object.keys(model.views).length") == 1
        # Native remove() releases container ownership; widget DOM detachment
        # alone leaves Leaflet's ownership marker set.
        assert native_map.evaluate(
            "map => map.getContainer()._leaflet_id === undefined"
        )
        native_map.dispose()
    page.locator(".leaflet-popup-close-button").click()
    assert popup_model is not None
    popup_model.dispose()
    assert not errors, errors


@pytest.mark.parametrize("fail_child", [False, True])
def test_explicit_close_and_late_moveend_release_retained_child_views(
    page: Page, local_app: ShinyAppProc, fail_child: bool
) -> None:
    errors = record_errors(page)
    open_lifecycle_page(page, local_app)
    expect(page.locator(".leaflet-control .widget-html-content")).to_have_text(
        "retained control"
    )
    native_map = page.evaluate_handle(
        """() => Array.from(window.widgetLifecycle.activeViews()).find(view =>
            view.model.get('_view_name') === 'LeafletMapView'
        ).obj"""
    )
    map_model = page.evaluate_handle(
        """() => Array.from(window.widgetLifecycle.activeViews()).find(view =>
            view.model.get('_view_name') === 'LeafletMapView'
        ).model"""
    )
    retained_model = page.evaluate_handle(
        """() => Array.from(window.widgetLifecycle.activeViews()).find(view =>
            view.model.get('value') === 'retained control'
        ).model"""
    )
    assert retained_model.evaluate("model => Object.keys(model.views).length") == 1
    if fail_child:
        page.evaluate(
            """() => {
                const views = Array.from(window.widgetLifecycle.activeViews());
                const retained = views.find(view =>
                    view.model.get('value') === 'retained control'
                );
                const child = views.slice(views.indexOf(retained) + 1).find(view =>
                    view.options.parent === retained
                );
                const remove = child.remove.bind(child);
                child.remove = () => {
                    child.remove = remove;
                    throw new Error('controlled child teardown failure');
                };
            }"""
        )
    model_id = page.locator("#map").get_attribute("data-shinywidgets-model-id")
    assert model_id is not None

    page.locator("#close_map").click()
    expect(page.locator("#closed_map")).to_have_text(model_id)
    page.wait_for_function("model => model.views === undefined", arg=map_model)
    assert retained_model.evaluate("model => Object.keys(model.views).length") == 0
    assert native_map.evaluate("map => map.getContainer()._leaflet_id === undefined")

    native_map.evaluate(
        """map => {
            map.fire('moveend');
            return new Promise(resolve => setTimeout(resolve, 0));
        }"""
    )
    page.locator("#rerender").click()
    page.wait_for_function(
        """previous => {
            const id = document.querySelector('#map').dataset.shinywidgetsModelId;
            return id && id !== previous;
        }""",
        arg=model_id,
    )
    expect(page.locator(".leaflet-control .widget-html-content")).to_have_text(
        "retained control"
    )
    assert retained_model.evaluate("model => Object.keys(model.views).length") == 1
    if fail_child:
        assert errors == [
            "Error cleaning up view: Error: Errors while removing widget view tree: "
            "Error: controlled child teardown failure"
        ]
    else:
        assert not errors, errors
    native_map.dispose()
    map_model.dispose()
    retained_model.dispose()


def record_errors(page: Page) -> list[str]:
    errors: list[str] = []

    def console_error(message: ConsoleMessage) -> None:
        if message.type != "error":
            return
        text = " ".join(
            argument.evaluate("value => String(value)") for argument in message.args
        )
        errors.append(text or message.text)

    page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
    page.on("console", console_error)
    return errors
