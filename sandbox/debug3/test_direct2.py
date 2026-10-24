from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import expose_manager, client_models


def test_direct2(page: Page, local_app) -> None:
    msgs: list[str] = []
    page.on("console", lambda msg: msgs.append(f"{msg.type}: {msg.text[:200]}"))
    page.on("pageerror", lambda err: msgs.append(f"pageerror: {err}"))
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    page.wait_for_timeout(5000)
    box = page.locator("#plot canvas").first.bounding_box()
    print("canvas box:", box)
    print("models:", sorted(m["name"] for m in client_models(page)))
    cam = page.evaluate("""async () => {
      const models = await Promise.all(Object.values(window.widgetManager._models).map(p => p.catch(() => null)));
      const fig = models.find(m => m && m.get('_model_name') === 'FigureModel');
      const scatters = fig.get('scatters');
      const sc = await Promise.all(scatters.map(r => r instanceof Promise ? r : Promise.resolve(r)));
      return {w: fig.get('width'), h: fig.get('height'), nsc: scatters.length};
    }""")
    print("fig:", cam)
    print("MSGS:", [m for m in msgs if not m.startswith(("info", "log", "warning: DEPRECATED"))][:20])
