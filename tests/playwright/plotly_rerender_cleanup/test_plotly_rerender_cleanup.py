from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_rerender_cleanup


def test_plotly_rerender_does_not_log_cleanup_errors(page: Page, local_app) -> None:
    assert_rerender_cleanup(page, local_app, "#plot .js-plotly-plot")


def test_plotly_resize_failure_does_not_leave_output_hidden(
    page: Page, local_app
) -> None:
    page.add_init_script(
        """
        (() => {
          const patchResize = () => {
            const plots = window.Plotly?.Plots;
            const resize = plots?.resize;
            if (!plots || !resize || plots.__pyShinywidgetsPatchedResize) {
              return false;
            }

            const originalResize = resize.bind(plots);
            plots.__pyShinywidgetsPatchedResize = true;
            plots.resize = (...args) => {
              if (window.__pyShinywidgetsInjectResizeFailure) {
                window.__pyShinywidgetsInjectResizeFailure = false;
                throw new Error("Injected Plotly resize failure");
              }
              return originalResize(...args);
            };
            return true;
          };

          if (patchResize()) {
            return;
          }

          const intervalId = window.setInterval(() => {
            if (patchResize()) {
              window.clearInterval(intervalId);
            }
          }, 0);
        })();
        """
    )

    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_have_count(1)
    page.wait_for_function(
        """
        () => {
          const out = document.querySelector("#plot");
          return out && getComputedStyle(out).visibility !== "hidden";
        }
        """,
        timeout=30000,
    )
    page.evaluate("() => { window.__pyShinywidgetsInjectResizeFailure = true; }")
    page.click("#rerender")
    expect(page.locator("#render_count")).to_have_text("1")
    page.wait_for_function(
        """
        () => {
          const out = document.querySelector("#plot");
          return out && getComputedStyle(out).visibility !== "hidden";
        }
        """,
        timeout=30000,
    )
