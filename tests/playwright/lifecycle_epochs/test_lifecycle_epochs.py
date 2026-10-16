"""
Epoch-bound manager contract tests (plan 3).

Each test mints epoch owners through the lifecycle controller's real hello
path (route-instrumented exposure only) and asserts registry/model identity
and actual view attachment, never just DOM text. These are the epoch-based
successors of the `model_waiter_cleanup` clearing-counter cases; the shared
clearing implementation they replaced is gone (retirement is permanent).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


@pytest.fixture
def lifecycle_page(page: Page, local_app: ShinyAppProc) -> Page:
    page = open_lifecycle_page(page, local_app)
    # This app renders a widget, so the server's epoch hello always arrives;
    # wait for it so a late hello can't retire test-minted epoch owners.
    page.wait_for_function("!!window.widgetLifecycle.epoch")
    return page


def test_retirement_cancels_pending_deserialization_lookup(
    lifecycle_page: Page,
) -> None:
    """
    Retirement cancels a child lookup reached by already-pending parent
    deserialization: it rejects promptly (no 30s timeout), never resolves
    into a successful ErrorWidget, and the retired parent can't remain
    registered.
    """
    result = lifecycle_page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const manager = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e1'
            });
            const parent = manager.new_model({
                model_id: 'parent',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            }, {layout: 'IPY_MODEL_missing-layout'});
            // Retire the epoch while the parent's child lookup is pending.
            lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e2'
            });
            const outcome = await Promise.race([
                parent.then(
                    () => 'resolved',
                    (error) => error.name
                ),
                new Promise(resolve => setTimeout(() => resolve('timeout'), 5000))
            ]);
            await manager.retire();
            return {
                outcome,
                managerRetired: manager.retired,
                parentRegistered: manager.has_model('parent'),
            };
        }"""
    )

    assert result == {
        "outcome": "EpochRetiredError",
        "managerRetired": True,
        "parentRegistered": False,
    }


def test_fresh_owner_resolves_late_child_during_old_retirement(
    lifecycle_page: Page,
) -> None:
    """
    An old owner's existing waits reject promptly; a fresh owner waits for
    and resolves its actual late child while the old owner's cleanup is
    still pending.
    """
    result = lifecycle_page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const old = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e1'
            });
            const staleWait = old.get_model('missing').then(
                () => 'resolved',
                (error) => error.name
            );
            // Hold the old owner's cleanup: its model's close never settles
            // until we release it.
            await old.new_model({
                model_id: 'held',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            const heldModel = await old.get_model('held');
            let releaseClose;
            heldModel.close = () => new Promise(resolve => { releaseClose = resolve; });

            const fresh = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e2'
            });
            const childWait = fresh.get_model('child');
            const cancelled = await staleWait;
            const child = await fresh.new_model({
                model_id: 'child',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            const freshResolved = (await childWait) === child;
            releaseClose();
            await old.retire();
            return {
                cancelled,
                freshResolved,
                freshRetired: fresh.retired,
                oldRetired: old.retired,
            };
        }"""
    )

    assert result == {
        "cancelled": "EpochRetiredError",
        "freshResolved": True,
        "freshRetired": False,
        "oldRetired": True,
    }


def test_overlapping_retired_cleanups_cannot_remove_fresh_models(
    lifecycle_page: Page,
) -> None:
    """
    Two retired owners hold pending cleanups and finish in both orders.
    Neither can admit new lookups/registration, same-ID models in the fresh
    epoch can't be removed by old close listeners, and the fresh owner works
    independently throughout.
    """
    result = lifecycle_page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const holdClose = async (manager) => {
                await manager.new_model({
                    model_id: 'shared-suffix',
                    model_name: 'HTMLModel',
                    model_module: '@jupyter-widgets/controls',
                    model_module_version: '2.0.0'
                });
                const held = {};
                held.model = await manager.get_model('shared-suffix');
                held.model.close = () => new Promise(resolve => {
                    held.release = resolve;
                });
                return held;
            };

            const first = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e1'
            });
            const firstHeld = await holdClose(first);
            const second = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e2'
            });
            const secondHeld = await holdClose(second);
            const fresh = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e3'
            });
            // Same full model ID in the fresh epoch.
            const freshModel = await fresh.new_model({
                model_id: 'shared-suffix',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });

            // Old owners reject new lookups and registration while their
            // cleanups are pending.
            const oldLookup = await first.get_model('anything').then(
                () => 'resolved',
                (error) => error.name
            );
            let oldRegister;
            try {
                first.register_model('x', Promise.resolve(freshModel));
                oldRegister = 'registered';
            } catch (error) {
                oldRegister = error.name;
            }

            // Finish the retired cleanups in reverse retirement order.
            secondHeld.release();
            await second.retire();
            const freshAfterSecond = fresh.has_model('shared-suffix');
            firstHeld.release();
            await first.retire();

            return {
                oldLookup,
                oldRegister,
                freshAfterSecond,
                freshRegistered: fresh.has_model('shared-suffix'),
                freshModelIsOurs:
                    (await fresh.get_model('shared-suffix')) === freshModel,
            };
        }"""
    )

    assert result == {
        "oldLookup": "EpochRetiredError",
        "oldRegister": "EpochRetiredError",
        "freshAfterSecond": True,
        "freshRegistered": True,
        "freshModelIsOurs": True,
    }


def test_failed_old_cleanup_reports_and_fresh_epoch_continues(
    lifecycle_page: Page,
) -> None:
    """
    An injected old-close failure is reported by the old owner's close task;
    it can't reopen the retired owner or poison the fresh owner's waiting.
    """
    result = lifecycle_page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const old = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e1'
            });
            const model = await old.new_model({
                model_id: 'throwing',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            model.close = () => { throw new Error('Injected close failure'); };

            const fresh = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e2'
            });
            const error = await old.retire().then(
                () => null,
                (closeError) => closeError.message
            );
            const lookup = fresh.get_model('later').catch(() => null);
            const later = await fresh.new_model({
                model_id: 'later',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            });
            return {
                error,
                resolved: (await lookup) === later,
                oldStillRetired: old.retired,
                freshRetired: fresh.retired,
            };
        }"""
    )

    assert result == {
        "error": "Errors while retiring widget epoch: Error: Injected close failure",
        "resolved": True,
        "oldStillRetired": True,
        "freshRetired": False,
    }


def test_fresh_parent_resolves_its_actual_late_child(lifecycle_page: Page) -> None:
    """
    The regression that motivated epochs: a fresh parent whose child lookup
    is pending resolves to its real view once the child arrives (never an
    ErrorWidget), and the view actually attaches.
    """
    result = lifecycle_page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const manager = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e1'
            });
            const parentPromise = manager.new_model({
                model_id: 'parent-box',
                model_name: 'BoxModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            }, {children: ['IPY_MODEL_late-child']});
            // The child's comm_open arrives late.
            await new Promise(resolve => setTimeout(resolve, 100));
            const child = await manager.new_model({
                model_id: 'late-child',
                model_name: 'HTMLModel',
                model_module: '@jupyter-widgets/controls',
                model_module_version: '2.0.0'
            }, {value: 'late child content'});
            const parent = await parentPromise;
            const el = document.createElement('div');
            document.body.appendChild(el);
            const mount = window.widgetLifecycle.mountFor(el);
            const view = await manager.create_view(parent, {
                lifecycle_scope: mount
            });
            const lumino = view.luminoWidget ?? view.pWidget;
            const { LuminoWidget } = await new Promise((resolve, reject) =>
                require(['shinywidgets-internals'], (...m) => resolve(m[0]), reject)
            );
            LuminoWidget.attach(lumino, el);
            return {
                parentViewName: parent.get('_view_name'),
                attachedContent: el.textContent,
                childRegistered: manager.has_model('late-child'),
            };
        }"""
    )

    assert result["parentViewName"] == "BoxView"
    assert "late child content" in result["attachedContent"]
    assert result["childRegistered"] is True


def test_frontend_controller_model_creation_probe(lifecycle_page: Page) -> None:
    """
    Frontend-initiated model creation has no functioning backend contract
    (measured against the previous manager: the dummy comm never reached
    `new_model`). The epoch manager keeps it an explicit failure.
    """
    result = lifecycle_page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const manager = lifecycle.handleEpochHello({
                session_id: 's', model_namespace: 'n', epoch_id: 'e1'
            });
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

    expected = {
        "error": "Error: Frontend-initiated widget creation (new_widget "
        "without a comm) is not supported by shinywidgets; construct "
        "widgets on the server."
    }
    assert result["button"] == expected
    assert result["axis"] == expected


def test_served_runtime_module_identity_and_assets(lifecycle_page: Page) -> None:
    """
    The served runtime (libembed-amd.js + runtime-register.js) resolves the
    official AMD modules and "shinywidgets-internals" through RequireJS with
    shared constructor identity, and serves font/module assets without 404s.
    """
    failures: list[str] = []
    lifecycle_page.on(
        "response",
        lambda response: (
            failures.append(response.url) if response.status >= 400 else None
        ),
    )
    lifecycle_page.wait_for_selector("#button button")

    result = lifecycle_page.evaluate(
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
            const manager = window.widgetLifecycle.epoch;
            const modelId = document.querySelector('#button').dataset
                .shinywidgetsModelId;
            const model = await manager.get_model(modelId);
            const el = document.querySelector('#button');
            const mount = window.widgetLifecycle.mountFor(el);
            const scope = mount.childScope();
            return {
                modelIsBaseWidget: model instanceof base.WidgetModel,
                managerIsManagerBase: manager instanceof internals.ManagerBase,
                serializeState: typeof internals.serialize_state,
                luminoWidget: typeof internals.LuminoWidget,
                viewLuminoShared: await (async () => {
                    const view = await manager.create_view(model, {
                        lifecycle_scope: scope
                    });
                    const lumino = view.luminoWidget ?? view.pWidget;
                    return lumino instanceof internals.LuminoWidget;
                })(),
            };
        }"""
    )

    assert result == {
        "modelIsBaseWidget": True,
        "managerIsManagerBase": True,
        "serializeState": "function",
        "luminoWidget": "function",
        "viewLuminoShared": True,
    }
    assert failures == []
