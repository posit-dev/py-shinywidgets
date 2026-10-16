"""
Model-waiter mechanics on the epoch-owned registry.

The #237 clearing-counter cases these replace have epoch-based successors in
`tests/playwright/lifecycle_epochs/` (retirement is permanent now, so "clear
then resume on the same manager" no longer exists). What remains here are the
waiter mechanics themselves: late-child resolution, prompt retirement
rejection, and waiter accounting in the lifecycle snapshot.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, Route
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page

HELLO = "{session_id: 's', model_namespace: 'n', epoch_id: 'e1'}"
NEW_MODEL = """{
    model_name: 'HTMLModel',
    model_module: '@jupyter-widgets/controls',
    model_module_version: '2.0.0'
}"""


@pytest.fixture
def lifecycle_page(page: Page, local_app: ShinyAppProc) -> Page:
    # This app renders no widgets, so no server hello can interfere with the
    # epochs minted by the tests.
    return open_lifecycle_page(page, local_app)


def test_waiter_resolves_with_registered_promise_identity(
    lifecycle_page: Page,
) -> None:
    result = lifecycle_page.evaluate(
        f"""async () => {{
            const manager = window.widgetLifecycle.handleEpochHello({HELLO});
            const waiting = manager.get_model('late');
            let resolveRegistration;
            manager.register_model(
                'late', new Promise(resolve => {{ resolveRegistration = resolve; }})
            );
            const Model = await manager.loadModelClass(
                'HTMLModel', '@jupyter-widgets/controls', '2.0.0'
            );
            const model = new Model({{}}, {{widget_manager: manager, model_id: 'late'}});
            resolveRegistration(model);
            const resolved = await waiting;
            return {{
                sameModel: resolved === model,
                waiters: window.widgetLifecycle.snapshot().waiters,
            }};
        }}"""
    )

    assert result == {"sameModel": True, "waiters": 0}


def test_retirement_rejects_existing_waiters_promptly(lifecycle_page: Page) -> None:
    result = lifecycle_page.evaluate(
        f"""async () => {{
            const lifecycle = window.widgetLifecycle;
            const manager = lifecycle.handleEpochHello({HELLO});
            const first = manager.get_model('missing-a').then(
                () => 'resolved', (error) => error.name
            );
            const second = manager.get_model('missing-b').then(
                () => 'resolved', (error) => error.name
            );
            await manager.retire();
            const outcomes = await Promise.race([
                Promise.all([first, second]),
                new Promise(resolve => setTimeout(() => resolve('timeout'), 5000)),
            ]);
            return {{
                outcomes,
                waiters: lifecycle.snapshot().waiters,
                retired: manager.retired,
            }};
        }}"""
    )

    assert result == {
        "outcomes": ["EpochRetiredError", "EpochRetiredError"],
        "waiters": 0,
        "retired": True,
    }


def test_waiter_timeout_removes_only_that_waiter(lifecycle_page: Page) -> None:
    result = lifecycle_page.evaluate(
        f"""async () => {{
            const manager = window.widgetLifecycle.handleEpochHello({HELLO});
            // Patch the timeout down for this test only: expiry must remove
            // just the expired waiter (other waiters keep waiting).
            const realSetTimeout = window.setTimeout;
            window.setTimeout = (fn, ms, ...args) => realSetTimeout(fn, 50, ...args);
            try {{
                const expired = manager.get_model('never-arrives').then(
                    () => 'resolved', (error) => error.message
                );
                const stillWaiting = manager.get_model('arrives-later');
                const expiredMessage = await expired;
                // new_model registers synchronously and resolves the waiter.
                await manager.new_model(
                    Object.assign({{model_id: 'arrives-later'}}, {NEW_MODEL})
                );
                const resolved = await stillWaiting;
                return {{
                    expiredMessage,
                    resolvedIsModel: !!resolved && resolved.get('_model_name') === 'HTMLModel',
                    waiters: window.widgetLifecycle.snapshot().waiters,
                }};
            }} finally {{
                window.setTimeout = realSetTimeout;
            }}
        }}"""
    )

    assert result["expiredMessage"].startswith("Timeout waiting for widget model")
    assert result["resolvedIsModel"] is True
    assert result["waiters"] == 0


def test_comm_open_waits_for_assets_without_waiting_for_child_models(
    lifecycle_page: Page,
) -> None:
    requests: list[Route] = []
    lifecycle_page.route(
        "**/delayed-widget-assets.js", lambda route: requests.append(route)
    )
    with lifecycle_page.expect_request("**/delayed-widget-assets.js"):
        lifecycle_page.evaluate(
            """() => {
                const identity = {session_id: 's', model_namespace: 'n', epoch_id: 'e1'};
                window.widgetLifecycle.handleEpochHello(identity);
                window.openFinished = false;
                window.openDispatch = Shiny.shinyapp.dispatchMessage(JSON.stringify({
                    custom: {shinywidgets_comm_open: JSON.stringify({
                        sw: 1, ...window.widgetLifecycle.epoch.identity, msg: {
                        content: {
                            comm_id: 'sw-n-asset-parent',
                            data: {state: {
                                _model_name: 'HTMLModel',
                                _model_module: '@jupyter-widgets/controls',
                                _model_module_version: '2.0.0',
                                layout: 'IPY_MODEL_sw-n-asset-child'
                            }, buffer_paths: []},
                            html_deps: [{
                                name: 'delayed-widget-assets',
                                version: '1.0',
                                script: [{src: '/delayed-widget-assets.js'}]
                            }]
                        },
                        metadata: {version: '2.1.0'},
                        buffers: []
                    }})}
                })).then(() => { window.openFinished = true; });
            }"""
        )

    finished_before_release = lifecycle_page.evaluate(
        """async () => {
            await new Promise(requestAnimationFrame);
            return window.openFinished;
        }"""
    )
    requests[0].fulfill(body="", content_type="application/javascript")
    result = lifecycle_page.evaluate(
        """async () => {
            await window.openDispatch;
            await Shiny.shinyapp.dispatchMessage(JSON.stringify({
                custom: {shinywidgets_comm_open: JSON.stringify({
                    sw: 1, ...window.widgetLifecycle.epoch.identity, msg: {
                    content: {
                        comm_id: 'sw-n-asset-child',
                        data: {state: {
                            _model_name: 'LayoutModel',
                            _model_module: '@jupyter-widgets/base',
                            _model_module_version: '2.0.0'
                        }, buffer_paths: []},
                        html_deps: []
                    },
                    metadata: {version: '2.1.0'},
                    buffers: []
                }})}
            }));
            const parent = await window.widgetLifecycle.epoch.get_model('sw-n-asset-parent');
            const child = await window.widgetLifecycle.epoch.get_model('sw-n-asset-child');
            return parent.get('layout') === child;
        }"""
    )

    assert not finished_before_release
    assert result, "Opening the parent must permit its child to arrive afterward"
