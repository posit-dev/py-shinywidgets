from __future__ import annotations

from playwright.sync_api import Page


def test_example_plotly_first_visible_afterplot_is_already_resized(
    page: Page, local_app
) -> None:
    page.add_init_script(
        """
        (() => {
          window.__plotlyAfterplotProbe = { firstVisibleAfterplot: null };
          document.addEventListener("plotlywidget-after-render", (evt) => {
            const gd = evt.detail?.element;
            if (!gd?.on) return;

            gd.on("plotly_afterplot", () => {
              if (window.__plotlyAfterplotProbe.firstVisibleAfterplot) return;
              const out = document.querySelector("#scatterplot");
              if (!out) return;
              const visibility = getComputedStyle(out).visibility;
              const layoutHeight = gd?._fullLayout?.height ?? null;
              const outHeight = out.getBoundingClientRect().height;
              if (visibility === "hidden" || layoutHeight === null) return;

              window.__plotlyAfterplotProbe.firstVisibleAfterplot = {
                visibility,
                outHeight,
                layoutHeight,
                diff: Math.abs(outHeight - layoutHeight),
              };
            });
          });
        })();
        """
    )

    page.goto(local_app.url)
    page.wait_for_function(
        "() => window.__plotlyAfterplotProbe.firstVisibleAfterplot !== null",
        timeout=30000,
    )

    first_visible_afterplot = page.evaluate(
        "() => window.__plotlyAfterplotProbe.firstVisibleAfterplot"
    )

    assert first_visible_afterplot["visibility"] != "hidden"
    assert first_visible_afterplot["diff"] <= 2, first_visible_afterplot
