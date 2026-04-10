from __future__ import annotations

from typing import Any

from playwright.sync_api import Page


def _sample_transient_swap_state(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """
        async () => {
          const root = document.querySelector("#plot");
          const button = document.querySelector("#rerender");
          if (!root || !button) {
            throw new Error("Missing #plot or #rerender");
          }

          const childCount = () => root.querySelectorAll(":scope > .lm-Widget").length;
          const directChildren = () => root.children.length;
          const height = () => root.getBoundingClientRect().height;

          let maxChildren = childCount();
          let maxDirectChildren = directChildren();
          let minHeight = height();
          const startHeight = minHeight;

          const sample = () => {
            const nChildren = childCount();
            const nDirectChildren = directChildren();
            const h = height();
            if (nChildren > maxChildren) maxChildren = nChildren;
            if (nDirectChildren > maxDirectChildren) {
              maxDirectChildren = nDirectChildren;
            }
            if (h < minHeight) minHeight = h;
          };

          const observer = new MutationObserver(sample);
          observer.observe(root, { childList: true });

          sample();
          button.click();

          const start = performance.now();
          await new Promise((resolve) => {
            const tick = () => {
              sample();
              if (performance.now() - start > 1200) {
                resolve(null);
                return;
              }
              requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
          });

          sample();
          observer.disconnect();
          return {
            maxChildren,
            maxDirectChildren,
            minHeight,
            startHeight,
            endHeight: height(),
          };
        }
        """
    )


def test_plotly_rerender_does_not_log_cleanup_errors(
    page: Page, local_app
) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector("#plot .js-plotly-plot", timeout=30000)

    transient_samples: list[dict[str, Any]] = []
    for rerender_id in range(1, 4):
        transient_samples.append(_sample_transient_swap_state(page))
        page.wait_for_selector(f"text=render {rerender_id}", timeout=30000)

    max_lm_widget_children = max(sample["maxChildren"] for sample in transient_samples)
    max_direct_children = max(sample["maxDirectChildren"] for sample in transient_samples)
    min_height_ratio = min(
        sample["minHeight"] / sample["startHeight"]
        for sample in transient_samples
        if sample["startHeight"] > 0
    )
    assert max_lm_widget_children <= 1, {
        "samples": transient_samples,
        "maxDirectChildren": max_direct_children,
    }
    assert min_height_ratio >= 0.9, transient_samples

    assert page.locator("#plot > .lm-Widget").count() == 1
    assert page.locator("#plot .js-plotly-plot").count() == 1
    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel defined" in err.lower() for err in errors)
