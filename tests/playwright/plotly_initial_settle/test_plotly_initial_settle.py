from __future__ import annotations

from playwright.sync_api import Page


def test_plotly_visible_height_matches_container_on_first_visible_paint(
    page: Page, local_app
) -> None:
    page.goto(local_app.url)
    page.wait_for_selector("#plot .js-plotly-plot", timeout=30000)

    first_visible = page.evaluate(
        """
        () => {
          const out = document.querySelector("#plot");
          const gd = document.querySelector("#plot .js-plotly-plot");
          const visibility = getComputedStyle(out).visibility;
          const outHeight = out.getBoundingClientRect().height;
          const layoutHeight = gd?._fullLayout?.height ?? null;
          return {
            visibility,
            outHeight,
            layoutHeight,
            diff: layoutHeight === null ? null : Math.abs(outHeight - layoutHeight),
          };
        }
        """
    )

    assert first_visible["visibility"] != "hidden"
    assert first_visible["layoutHeight"] is not None
    assert first_visible["diff"] <= 2, first_visible
