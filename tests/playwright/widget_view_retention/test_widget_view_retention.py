"""
View disposal and cached-model retention under mount ownership.

The six parameterized cases are the mount-era successors of #246's
WeakMap/`_viewList` instrumentation: views are owned by output mounts and
models by the current epoch's registry. Assertions still require real view
disposal/detachment, current content, popup interaction, and exact
cached-model identity -- zero DOM children alone is insufficient.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


@pytest.mark.parametrize("mode", ["cached", "popup"])
def test_replaced_views_are_removed(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    open_lifecycle_page(page, local_app, f"{local_app.url}?mode={mode}")
    expect(page.locator("#render_count")).to_have_text("0")
    expect(page.locator("#widget > .lm-Widget")).to_have_count(1)
    if mode == "popup":
        page.locator(".leaflet-marker-icon").click()
        expect(page.locator(".leaflet-popup-content")).to_have_text("Popup render 0")
        page.locator(".leaflet-popup-close-button").click()

    page.evaluate(
        """() => {
            const el = document.querySelector('#widget');
            window.previousView = window.widgetLifecycle.acceptedViewFor(el);
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
            const el = document.querySelector('#widget');
            const lifecycle = window.widgetLifecycle;
            const previous = window.previousView;
            return {
                hasPresentation: lifecycle.acceptedViewFor(el) !== null,
                previousDisposed: previous.luminoWidget.isDisposed,
                previousAttached: previous.luminoWidget.isAttached,
                previousModelRegistered: lifecycle.epoch.has_model(previous.model.model_id)
            };
        }"""
    )
    if mode == "popup":
        # The temporary model is collected after the browser releases the old
        # display lease (a round trip after the replacement attaches).
        page.wait_for_function(
            """() => !window.widgetLifecycle.epoch.has_model(
                window.previousView.model.model_id
            )"""
        )
        state["previousModelRegistered"] = page.evaluate(
            """() => window.widgetLifecycle.epoch.has_model(
                window.previousView.model.model_id
            )"""
        )
    assert state["hasPresentation"], "No accepted presentation after replacement"
    assert not state["previousAttached"]
    assert state["previousDisposed"]
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
    open_lifecycle_page(page, local_app, local_app.url)
    expect(page.locator("#widget")).to_have_text("Persistent widget")
    page.evaluate(
        """() => {
            const el = document.querySelector('#widget');
            window.previousView = window.widgetLifecycle.acceptedViewFor(el);
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
            const el = document.querySelector('#widget');
            const lifecycle = window.widgetLifecycle;
            const previous = window.previousView;
            return {
                hasPresentation: lifecycle.acceptedViewFor(el) !== null,
                previousDisposed: previous.luminoWidget.isDisposed,
                previousAttached: previous.luminoWidget.isAttached,
                previousModelRegistered: lifecycle.epoch.has_model(previous.model.model_id)
            };
        }"""
    )
    assert state == {
        "hasPresentation": False,
        "previousDisposed": True,
        "previousAttached": False,
        # A session-retained model survives view-only retirement.
        "previousModelRegistered": True,
    }


@pytest.mark.parametrize("mode", ["empty", "error"])
def test_widget_recovers_after_output_is_cleared(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    open_lifecycle_page(page, local_app, local_app.url)
    expect(page.locator("#widget")).to_have_text("Persistent widget")
    page.evaluate(
        """() => {
            const el = document.querySelector('#widget');
            window.cachedModel = window.widgetLifecycle.acceptedViewFor(el).model;
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
            const el = document.querySelector('#widget');
            const lifecycle = window.widgetLifecycle;
            const accepted = lifecycle.acceptedViewFor(el);
            return {
                hasPresentation: accepted !== null,
                cachedModelRegistered: lifecycle.epoch.has_model(window.cachedModel.model_id),
                cachedModelReused: accepted !== null && accepted.model === window.cachedModel
            };
        }"""
    ) == {
        "hasPresentation": True,
        "cachedModelRegistered": True,
        "cachedModelReused": True,
    }
