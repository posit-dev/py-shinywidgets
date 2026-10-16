"""
Reproduction evidence for the connection-clearing failure modes that motivate
epoch-bound managers (plan 3, task 1).

These tests run against the *current* shared OutputManager (exposed through the
same route interception as `model_waiter_cleanup`) and document what actually
happens today when a pending `clear_state()` overlaps fresh work. They are
replaced by epoch-based contract tests in the same directory once the
epoch-bound controller ships (plan 3, task 11).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, Route
from shiny.run import ShinyAppProc


@pytest.fixture
def manager_page(page: Page, local_app: ShinyAppProc) -> Page:
    def expose_manager(route: Route) -> None:
        response = route.fetch()
        original = "const manager = new OutputManager({ loader: _lifecycle_loader__WEBPACK_IMPORTED_MODULE_2__.shinyRequireLoader });"
        text = response.text()
        assert original in text
        route.fulfill(
            response=response,
            body=text.replace(
                original,
                "const manager = window.widgetManager = new OutputManager({ loader: _lifecycle_loader__WEBPACK_IMPORTED_MODULE_2__.shinyRequireLoader });",
            ),
        )

    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_function("!!window.widgetManager")
    return page


def test_pending_clear_removes_newly_registered_model(manager_page: Page) -> None:
    """
    A model registered while an older clear is still pending is removed by
    that clear, even though it was created after the clear began.
    """
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const Model = await manager.loadModelClass(
                'HTMLModel', '@jupyter-widgets/controls', '2.0.0'
            );
            // Hold the old model's registration promise pending: clear_state()
            // snapshots the registry and waits for the snapshot to resolve
            // before replacing the whole registry.
            let releaseOld;
            manager.register_model('old', new Promise(resolve => { releaseOld = resolve; }));
            const clearing = manager.clear_state();

            // Fresh work registers a new model while the old clear's snapshot
            // is still pending.
            const freshModel = new Model({}, {widget_manager: manager, model_id: 'fresh'});
            manager.register_model('fresh', Promise.resolve(freshModel));

            // Releasing the old snapshot lets the clear replace the registry.
            releaseOld(new Model({}, {widget_manager: manager, model_id: 'old'}));
            await clearing;

            const freshRegistered = manager.has_model('fresh');
            return {
                freshRegistered,
                freshModel: freshRegistered
                    ? (await manager.get_model('fresh')).model_id
                    : null,
            };
        }"""
    )

    # The failure mode: the fresh model is gone after the old clear finishes.
    assert result == {"freshRegistered": False, "freshModel": None}


def test_fresh_parent_late_child_becomes_error_widget(manager_page: Page) -> None:
    """
    A parent whose child lookup is pending when an older clear runs has its
    wait cancelled; the parent resolves to an ErrorWidget instead of its real
    view, even though the child's registration arrives right after.
    """
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const parentPromise = manager.new_model({
                model_id: 'parent',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            }, {layout: 'IPY_MODEL_late-layout'});
            await manager.clear_state();
            const parent = await parentPromise;
            // The child's comm_open arrives just after the clear.
            const child = await manager.new_model({
                model_id: 'late-layout',
                model_name: 'LayoutModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            return {
                parentName: parent.get('_view_name'),
                isErrorWidget: parent.get('_view_name') === 'ErrorWidgetView',
                childRegistered: manager.has_model('late-layout'),
            };
        }"""
    )

    # The failure mode: the fresh parent is an ErrorWidget even though its
    # child legitimately arrived late.
    assert result["isErrorWidget"], result


def test_frontend_controller_model_creation_probe(manager_page: Page) -> None:
    """
    Boundary evidence for frontend-initiated model creation: core
    ControllerModel creates button/axis models via `new_widget()` without a
    model ID; the installed manager answers `_create_comm()` with a dummy comm
    that has no comm_id and no backend channel. This is not a functioning
    contract, so the epoch manager rejects new backend comm creation
    explicitly instead of pretending the dummy establishes one.
    """
    result = manager_page.evaluate(
        """async () => {
            const manager = window.widgetManager;
            const ControllerModel = await manager.loadModelClass(
                'ControllerModel', '@jupyter-widgets/controls', '2.0.0'
            );
            const controller = new ControllerModel(
                {}, {widget_manager: manager, model_id: 'controller'}
            );
            // Avoid any gamepad polling/scheduling; invoke the creation
            // methods directly and capture the precise outcome.
            const attempt = async (create) => {
                try {
                    const model = await create();
                    return {created: model.get('_model_name')};
                } catch (error) {
                    return {error: String(error)};
                }
            };
            return {
                button: await attempt(() => controller._create_button_model(0)),
                axis: await attempt(() => controller._create_axis_model(0)),
            };
        }"""
    )

    # Frontend-initiated creation has no functioning contract today: the
    # dummy comm never reaches new_model, which rejects. The epoch manager
    # keeps this an explicit failure (via _create_comm) rather than pretending
    # a dummy comm establishes a backend channel.
    assert result["button"] == {
        "error": "Error: Neither comm nor model_id provided in options object. "
        "At least one must exist."
    }
    assert result["axis"] == result["button"]


def test_served_runtime_module_identity_and_assets(manager_page: Page) -> None:
    """
    The served runtime (libembed-amd.js + runtime-register.js) resolves the
    official AMD modules and "shinywidgets-internals" through RequireJS with
    shared constructor identity, and serves font/module assets without 404s.
    """
    failures: list[str] = []
    manager_page.on(
        "response",
        lambda response: failures.append(response.url)
        if response.status >= 400
        else None,
    )
    manager_page.wait_for_selector("#button button")

    result = manager_page.evaluate(
        """async () => {
            const [base, controls, html, internals] = await new Promise(
                (resolve, reject) => require(
                    [
                        '@jupyter-widgets/base',
                        '@jupyter-widgets/controls',
                        '@jupyter-widgets/html-manager',
                        'shinywidgets-internals',
                    ],
                    (...modules) => resolve(modules),
                    reject,
                )
            );
            const manager = window.widgetManager;
            const models = await Promise.all(
                Object.keys(manager._models).map((id) => manager.get_model(id))
            );
            const model = models.find(
                (m) => m.get('_model_name') === 'ButtonModel'
            );
            if (!model) throw new Error('ButtonModel not registered');
            return {
                modelIsBaseWidget: model instanceof base.WidgetModel,
                managerIsManagerBase: manager instanceof internals.ManagerBase,
                htmlManagerShared: manager instanceof html.HTMLManager,
                serializeState: typeof internals.serialize_state,
                luminoWidget: typeof internals.LuminoWidget,
                viewLuminoShared: await (async () => {
                    const view = await manager.create_view(model);
                    return view.luminoWidget instanceof internals.LuminoWidget;
                })(),
            };
        }"""
    )

    assert result == {
        "modelIsBaseWidget": True,
        "managerIsManagerBase": True,
        "htmlManagerShared": True,
        "serializeState": "function",
        "luminoWidget": "function",
        "viewLuminoShared": True,
    }
    assert failures == []
