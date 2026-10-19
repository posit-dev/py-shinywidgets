from __future__ import annotations

from playwright.sync_api import Page
from tests.playwright.conftest import expose_manager


# A child view whose create_view() promise is still pending when its parent
# view is removed (e.g., dynamic UI removes the output while a container is
# still instantiating a child view) must be torn down once it resolves, not
# tracked (and retained) forever. removeViewTree() only sweeps views that are
# live at sweep time, so the manager marks removed views and lets
# late-resolving descendants tear themselves down.
def test_late_resolving_child_view_is_torn_down(page: Page, local_app) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_selector("#box .widget-label", timeout=15000)

    result = page.evaluate(
        """async () => {
            const mgr = window.widgetManager;
            const models = await Promise.all(
                Object.values(mgr._models).map((p) => p.catch(() => null))
            );
            const boxModel = models.find((m) => m && m.get('_model_name') === 'VBoxModel');
            const labelModel = models.find((m) => m && m.get('_model_name') === 'LabelModel');
            const rootView = await Object.values(boxModel.views)[0];

            // Start creating a second view of the label (parented to the
            // box's view), then remove the box's whole view tree before the
            // child view's creation promise resolves.
            const viewPromise = mgr.create_view(labelModel, { parent: rootView });
            mgr.removeViewTree(rootView);
            const lateView = await viewPromise;

            return {
                tracked: mgr._liveViews.has(lateView),
                disposed: lateView.luminoWidget ? lateView.luminoWidget.isDisposed : null,
            };
        }"""
    )

    assert result["tracked"] is False, "late-resolving child view should not be tracked as live"
    assert result["disposed"] is True, "late-resolving child view should have been removed"
