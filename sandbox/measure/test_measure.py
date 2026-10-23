from __future__ import annotations

from playwright.sync_api import Page
from tests.playwright.conftest import client_models, expose_manager


def test_measure(page: Page, local_app) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_selector("#sized_layout canvas", timeout=30000)
    page.wait_for_timeout(2000)
    models = client_models(page)
    figs = [m for m in models if m["name"] == "FigureModel"]
    print("FigureModels:", figs)
    print(page.evaluate("""async () => {
      const models = await Promise.all(Object.values(window.widgetManager._models).map(p => p.catch(() => null)));
      const figs = models.filter(m => m && m.get('_model_name') === 'FigureModel');
      return figs.map(f => ({w: f.get('width'), h: f.get('height'), views: Object.keys(f.views).length}));
    }"""))
