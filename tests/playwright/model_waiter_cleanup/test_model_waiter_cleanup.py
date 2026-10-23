import pytest
from playwright.sync_api import Page, Route
from shiny.run import ShinyAppProc


def test_clear_cancels_wait_created_by_pending_model(manager_page: Page) -> None:
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const parent = manager.new_model({
                model_id: 'parent',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            }, {layout: 'IPY_MODEL_missing-layout'});
            const cleared = await Promise.race([
                manager.clear_state().then(() => true),
                new Promise(resolve => setTimeout(() => resolve(false), 1000))
            ]);
            if (!cleared) {
                return {cleared};
            }
            await parent;
            return {cleared, parentRegistered: manager.has_model('parent')};
        }"""
    )

    assert result["cleared"], "Cleanup stalled on a child lookup started after clearing"
    assert not result["parentRegistered"]


def test_clear_cancels_existing_waits_and_restores_waiting(manager_page: Page) -> None:
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const existing = manager.get_model('missing').then(
                () => 'resolved', error => error.message
            );
            await manager.clear_state();
            const cancelled = await Promise.race([
                existing,
                new Promise(resolve => setTimeout(() => resolve('pending'), 1000))
            ]);
            const lookup = manager.get_model('later');
            const model = await manager.new_model({
                model_id: 'later',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            return {cancelled, resumed: await lookup === model};
        }"""
    )

    assert result == {
        "cancelled": "Widget state cleared while waiting for model missing",
        "resumed": True,
    }


def test_missing_lookup_rejects_until_all_clears_finish(manager_page: Page) -> None:
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const Model = await manager.loadModelClass(
                'HTMLModel', '@jupyter-widgets/controls', '2.0.0'
            );
            const firstModel = new Model({}, {widget_manager: manager, model_id: 'first'});
            const secondModel = new Model({}, {widget_manager: manager, model_id: 'second'});
            let releaseFirst;
            let releaseSecond;
            manager.register_model('first', new Promise(resolve => { releaseFirst = resolve; }));
            const firstClear = manager.clear_state();
            manager.register_model('second', new Promise(resolve => { releaseSecond = resolve; }));
            let secondFinished = false;
            const secondClear = manager.clear_state().then(() => { secondFinished = true; });
            const registeredLookup = manager.get_model('second');
            releaseFirst(firstModel);
            await firstClear;
            const secondStillPending = !secondFinished;
            const missingLookup = manager.get_model('missing').then(
                () => 'resolved', error => error.message
            );
            const duringClear = await Promise.race([
                missingLookup,
                new Promise(resolve => setTimeout(() => resolve('pending'), 1000))
            ]);
            releaseSecond(secondModel);
            await secondClear;
            const registeredResolved = await registeredLookup === secondModel;
            const laterLookup = manager.get_model('later');
            const laterModel = new Model({}, {widget_manager: manager, model_id: 'later'});
            manager.register_model('later', Promise.resolve(laterModel));
            return {
                secondStillPending,
                duringClear,
                registeredResolved,
                resumed: await laterLookup === laterModel
            };
        }"""
    )

    assert result == {
        "secondStillPending": True,
        "duringClear": "Widget state cleared while waiting for model missing",
        "registeredResolved": True,
        "resumed": True,
    }


def test_model_waiting_resumes_after_clear_failure(manager_page: Page) -> None:
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const model = await manager.new_model({
                model_id: 'throwing',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            model.close = () => { throw new Error('Injected close failure'); };
            const error = await manager.clear_state().then(
                () => null, error => error.message
            );
            const lookup = manager.get_model('later').catch(() => null);
            const laterModel = await manager.new_model({
                model_id: 'later',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            return {error, resumed: await lookup === laterModel};
        }"""
    )

    assert result == {"error": "Injected close failure", "resumed": True}


@pytest.fixture
def manager_page(page: Page, local_app: ShinyAppProc) -> Page:
    def expose_manager(route: Route) -> None:
        response = route.fetch()
        original = "const manager = new OutputManager({ loader: shinyRequireLoader });"
        text = response.text()
        assert original in text
        # Keep the manager's test access out of the shipped bundle.
        route.fulfill(
            response=response,
            body=text.replace(
                original,
                "const manager = window.widgetManager = new OutputManager({ loader: shinyRequireLoader });",
            ),
        )

    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_function("!!window.widgetManager")
    return page


def test_comm_open_waits_for_assets_without_waiting_for_child_models(
    manager_page: Page,
) -> None:
    requests: list[Route] = []
    manager_page.route(
        "**/delayed-widget-assets.js", lambda route: requests.append(route)
    )
    with manager_page.expect_request("**/delayed-widget-assets.js"):
        manager_page.evaluate(
            """() => {
                window.openFinished = false;
                window.openDispatch = Shiny.shinyapp.dispatchMessage(JSON.stringify({
                    custom: {shinywidgets_comm_open: JSON.stringify({
                        content: {
                            comm_id: 'asset-parent',
                            data: {state: {
                                _model_name: 'HTMLModel',
                                _model_module: '@jupyter-widgets/controls',
                                _model_module_version: '2.0.0',
                                layout: 'IPY_MODEL_asset-child'
                            }, buffer_paths: []},
                            html_deps: [{
                                name: 'delayed-widget-assets',
                                version: '1.0',
                                script: [{src: '/delayed-widget-assets.js'}]
                            }]
                        },
                        metadata: {version: '2.1.0'},
                        buffers: []
                    })}
                })).then(() => { window.openFinished = true; });
            }"""
        )

    finished_before_release = manager_page.evaluate(
        """async () => {
            await new Promise(requestAnimationFrame);
            return window.openFinished;
        }"""
    )
    requests[0].fulfill(body="", content_type="application/javascript")
    result = manager_page.evaluate(
        """async () => {
            await window.openDispatch;
            await Shiny.shinyapp.dispatchMessage(JSON.stringify({
                custom: {shinywidgets_comm_open: JSON.stringify({
                    content: {
                        comm_id: 'asset-child',
                        data: {state: {
                            _model_name: 'LayoutModel',
                            _model_module: '@jupyter-widgets/base',
                            _model_module_version: '2.0.0'
                        }, buffer_paths: []},
                        html_deps: []
                    },
                    metadata: {version: '2.1.0'},
                    buffers: []
                })}
            }));
            const parent = await window.widgetManager.get_model('asset-parent');
            const child = await window.widgetManager.get_model('asset-child');
            return parent.get('layout') === child;
        }"""
    )

    assert not finished_before_release
    assert result, "Opening the parent must permit its child to arrive afterward"
