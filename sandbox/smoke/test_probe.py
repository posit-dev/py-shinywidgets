from __future__ import annotations

from playwright.sync_api import Page


def test_probe_dom(page: Page, local_app) -> None:
    page.goto(local_app.url)
    page.wait_for_selector("#fig canvas", timeout=30000)
    page.wait_for_timeout(1000)
    print(page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('#fig canvas').forEach((c, i) => {
        out.push({
          i,
          cls: c.className,
          parentCls: c.parentElement.className,
          w: c.clientWidth, h: c.clientHeight,
          style: c.style.cssText,
        });
      });
      return JSON.stringify(out, null, 1);
    }"""))
