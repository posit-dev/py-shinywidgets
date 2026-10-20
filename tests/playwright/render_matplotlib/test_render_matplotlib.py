from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
)


def test_matplotlib_actually_draws_pixels(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # ipympl renders its figure onto a <canvas> (it also keeps an offscreen
    # canvas, so there may be more than one). A non-blank canvas proves the
    # figure's PNG buffer survived the base64 comm transport and was drawn.
    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#mpl")

    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    n_canvases = page.locator("#mpl canvas").count()

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of canvases) ...
    expect(page.locator("#mpl canvas")).to_have_count(n_canvases)

    # ... and the new widget still draws
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#mpl")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


@pytest.mark.parametrize("mode", ["new", "cached"])
def test_matplotlib_releases_replaced_views_and_observers(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    errors, failed_requests = collect_errors(page)
    expose_matplotlib_resources(page)
    page.goto(local_app.url)
    select_canvas_mode(page, mode)
    page.evaluate(
        """() => {
            window.cachedCanvasModel = [...window.widgetManager._liveViews]
                .find(v => v.model.get('_model_name') === 'MPLCanvasModel').model;
        }"""
    )

    for n in range(1, 4):
        remember_current_view(page)
        previous_node = page.locator("#mpl > .lm-Widget").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(n))
        page.wait_for_function("(node) => !node.isConnected", arg=previous_node)
        wait_for_canvas(page)

    assert_resources_released(page, active_canvases=1)
    if mode == "cached":
        assert page.evaluate(
            """() => {
                const model = window.cachedCanvasModel;
                return Object.keys(model.views).length === 1
                    && model._events['change:header_visible'].length === 1
                    && [...window.widgetManager._liveViews]
                        .some(v => v.model === model);
            }"""
        )
        page.evaluate("() => window.cachedCanvasModel.set('header_visible', false)")
        expect(page.locator("#mpl .jupyter-matplotlib-header")).to_be_hidden()
        page.evaluate(
            """() => {
                window.cachedCanvasModel.set('_figure_label', 'Updated figure');
                window.cachedCanvasModel.set('header_visible', true);
            }"""
        )
        expect(page.locator("#mpl .jupyter-matplotlib-header")).to_be_visible()
        expect(page.locator("#mpl .jupyter-matplotlib-header")).to_have_text(
            "Updated figure"
        )
    assert_no_unexpected_errors(errors, failed_requests)


@pytest.mark.parametrize("mode", ["empty", "error"])
def test_matplotlib_clear_disposes_the_cached_view(
    page: Page, local_app: ShinyAppProc, mode: str
) -> None:
    errors, failed_requests = collect_errors(page)
    expose_matplotlib_resources(page)
    page.goto(local_app.url)
    select_canvas_mode(page, "cached")
    remember_current_view(page)

    page.select_option("#mode", mode)
    expect(page.locator("#mpl canvas")).to_have_count(0)
    assert_resources_released(page, active_canvases=0)

    page.select_option("#mode", "cached")
    wait_for_canvas(page)
    assert_resources_released(page, active_canvases=1)
    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_dynamic_ui_disposes_and_restores_the_cached_view(
    page: Page, local_app: ShinyAppProc
) -> None:
    errors, failed_requests = collect_errors(page)
    expose_matplotlib_resources(page)
    page.goto(local_app.url)
    select_canvas_mode(page, "cached")
    remember_current_view(page)

    page.click("#remove")
    expect(page.locator("#mpl")).to_have_count(0)
    assert_resources_released(page, active_canvases=0)

    page.click("#restore")
    wait_for_canvas(page)
    assert_resources_released(page, active_canvases=1)
    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_lumino_disposal_runs_cleanup_once(
    page: Page, local_app: ShinyAppProc
) -> None:
    errors, failed_requests = collect_errors(page)
    expose_matplotlib_resources(page)
    page.goto(local_app.url)
    select_canvas_mode(page, "cached")

    state = page.evaluate(
        """() => {
            const manager = window.widgetManager;
            const node = document.querySelector('#mpl > .lm-Widget');
            const view = [...manager._liveViews].find(v => v.el === node);
            let removes = 0;
            view.on('remove', () => removes++);
            view.luminoWidget.dispose();
            view.remove();
            return {
                removes,
                tracked: manager._liveViews.has(view),
                modelViews: Object.keys(view.model.views).length,
                headerListeners: view.model._events['change:header_visible']?.length ?? 0,
                activeObservers: window.mplObserverProbes.filter(p => !p.disconnected).length,
            };
        }"""
    )
    assert state == {
        "removes": 1,
        "tracked": False,
        "modelViews": 0,
        "headerListeners": 0,
        "activeObservers": 0,
    }
    assert_no_unexpected_errors(errors, failed_requests)


def expose_matplotlib_resources(page: Page) -> None:
    page.route("**/output.js", expose_manager)
    page.add_init_script(
        """
        (() => {
            const Native = window.ResizeObserver;
            window.mplObserverProbes = [];
            window.retiredCanvasViews = [];
            window.ResizeObserver = class extends Native {
                observe(el, options) {
                    if (el.id === "mpl") {
                        this.probe = { disconnected: false };
                        window.mplObserverProbes.push(this.probe);
                    }
                    return super.observe(el, options);
                }
                disconnect() {
                    if (this.probe) this.probe.disconnected = true;
                    return super.disconnect();
                }
            };
        })();
        """
    )


def wait_for_canvas(page: Page) -> None:
    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#mpl", timeout=30000)


def select_canvas_mode(page: Page, mode: str) -> None:
    wait_for_canvas(page)
    if page.locator("#mode").input_value() == mode:
        return
    previous_node = page.locator("#mpl > .lm-Widget").element_handle()
    page.select_option("#mode", mode)
    page.wait_for_function("(node) => !node.isConnected", arg=previous_node)
    wait_for_canvas(page)


def remember_current_view(page: Page) -> None:
    page.evaluate(
        """() => {
            const node = document.querySelector('#mpl > .lm-Widget');
            const view = [...window.widgetManager._liveViews].find(v => v.el === node);
            window.retiredCanvasViews.push(view);
        }"""
    )


def assert_resources_released(page: Page, *, active_canvases: int) -> None:
    page.wait_for_function(
        """(expected) => {
            const manager = window.widgetManager;
            const views = [...manager._liveViews];
            return views.filter(v => v.model.get('_model_name') === 'MPLCanvasModel')
                .length === expected
                && views.filter(v => v.model.get('_model_name') === 'ToolbarModel')
                    .length === expected
                && window.mplObserverProbes.filter(p => !p.disconnected).length === expected
                && window.retiredCanvasViews.every(v =>
                    v.luminoWidget.isDisposed && !v.luminoWidget.isAttached
                    && !v.el.isConnected && !manager._liveViews.has(v));
        }""",
        arg=active_canvases,
        timeout=5000,
    )
