"""
Output widget MIME presentations (plan 3, task 7).

Nested widget MIME renderings own child mount scopes: clear/replace retires
the old child scope before the next rendering, root removal retires nested
admission synchronously, and a session-retained model can appear in a normal
root view and a nested MIME view at once.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


def test_nested_output_clear_and_replace(page: Page, local_app: ShinyAppProc) -> None:
    open_lifecycle_page(page, local_app)
    out = page.locator("#out_widget")
    expect(out).to_contain_text("nested content 0")
    expect(out).to_contain_text("deep nested 0")

    page.click("#clear")
    expect(out).not_to_contain_text("nested content 0")
    expect(out).not_to_contain_text("deep nested 0")

    # Replacement MIME: the old child scope is retired before the next render.
    page.click("#replace")
    expect(out).to_contain_text("nested content 1")
    expect(out).to_contain_text("deep nested 1")
    page.click("#replace")
    expect(out).to_contain_text("nested content 2")
    expect(out).to_contain_text("deep nested 2")
    expect(out).not_to_contain_text("nested content 1")

    # The MIME mount tree doesn't accumulate views/tasks across cycles.
    snapshot = page.evaluate(
        """() => {
            const el = document.querySelector('#out_widget');
            return window.widgetLifecycle.mountSnapshot(el);
        }"""
    )
    assert snapshot["tasks"] == 0


def test_same_model_in_root_view_and_nested_mime_view(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#shared")).to_have_text("shared root and mime")
    expect(page.locator("#out_widget")).to_contain_text("shared root and mime")
    model_id = page.locator("#shared").get_attribute("data-shinywidgets-model-id")
    assert model_id is not None

    # Dropping the root view leaves the nested MIME view (and the shared
    # model) fully functional.
    page.click("#drop")
    page.wait_for_function("() => !document.querySelector('#slot-holder #shared')")
    expect(page.locator("#out_widget")).to_contain_text("shared root and mime")
    registered = page.evaluate(
        """(modelId) => window.widgetLifecycle.epoch.has_model(modelId)""",
        model_id,
    )
    assert registered is True


def test_root_removal_while_nested_model_loading_is_held(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    result = page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const manager = await lifecycle.waitForEpoch();
            const [internals] = await new Promise((resolve, reject) =>
                require(['shinywidgets-internals'], (...m) => resolve(m), reject)
            );

            // A real Output model whose MIME payload references a model that
            // will never arrive (its lookup is held by the 30s waiter).
            const output = await manager.new_model({
                model_id: 'held-output',
                model_name: 'OutputModel',
                model_module: '@jupyter-widgets/output',
                model_module_version: '1.0.0'
            }, {
                outputs: [{
                    output_type: 'display_data',
                    data: {
                        'application/vnd.jupyter.widget-view+json': {
                            model_id: manager.normalizeModelId('never-arrives'),
                            version_major: 2,
                            version_minor: 0
                        },
                        'text/plain': 'held widget'
                    },
                    metadata: {}
                }]
            });

            const el = document.createElement('div');
            document.body.appendChild(el);
            const mount = window.widgetLifecycle.mountFor(el);
            const view = await manager.create_view(output, {
                lifecycle_scope: mount
            });
            internals.LuminoWidget.attach(view.luminoWidget, el);
            // The nested MIME renderer's child lookup is now pending.
            await new Promise(resolve => setTimeout(resolve, 100));
            const duringLoad = mount.snapshot();
            // Root removal while the nested model lookup is held: admission
            // is invalidated synchronously and no stale attachment happens.
            await mount.dispose();
            const afterDispose = mount.snapshot();
            return {
                duringLoad,
                afterDispose,
                attached: el.textContent.includes('held widget'),
            };
        }"""
    )

    assert result["duringLoad"]["tasks"] >= 1
    assert result["afterDispose"] == {"mounts": 1, "views": 0, "tasks": 0}
    assert result["attached"] is False
