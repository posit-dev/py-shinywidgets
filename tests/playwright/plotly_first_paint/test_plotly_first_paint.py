from __future__ import annotations

from playwright.sync_api import Page


def test_plotly_stays_hidden_until_plot_root_exists(page: Page, local_app) -> None:
    page.add_init_script(
        """
        window.__plotlyTimeline = [];
        window.__plotlyHooked = false;
        window.__plotlyFrames = 0;

        const record = (tag) => {
          const output = document.querySelector("#plot");
          const plot = output && output.querySelector(".js-plotly-plot");

          if (!output) {
            return;
          }

          window.__plotlyTimeline.push({
            tag,
            t: performance.now(),
            outputVis: getComputedStyle(output).visibility,
            outputH: output.getBoundingClientRect().height,
            plotH: plot ? plot.getBoundingClientRect().height : null,
            hasPlot: !!plot,
          });
        };

        const tick = () => {
          const output = document.querySelector("#plot");
          const plot = output && output.querySelector(".js-plotly-plot");

          if (output && !window.__plotlyRecordedOutput) {
            window.__plotlyRecordedOutput = true;
            record("output-found");
          }

          if (plot && !window.__plotlyHooked) {
            window.__plotlyHooked = true;
            record("plot-found");

            let frames = 0;
            const tick = () => {
              record(`raf-${frames}`);
              frames += 1;
              if (frames < 10) {
                requestAnimationFrame(tick);
              }
            };
            requestAnimationFrame(tick);
          }

          window.__plotlyFrames += 1;
          if (window.__plotlyFrames < 180) {
            requestAnimationFrame(tick);
          }
        };

        requestAnimationFrame(tick);
        """
    )

    page.goto(local_app.url, wait_until="domcontentloaded")
    page.wait_for_selector("#plot .js-plotly-plot", timeout=30000)
    page.wait_for_timeout(250)

    timeline = page.evaluate("window.__plotlyTimeline")
    plot_found = next(item for item in timeline if item["tag"] == "plot-found")
    first_visible_with_plot = next(
        (
            item
            for item in timeline
            if item["hasPlot"] and item["outputVis"] == "visible"
        ),
        None,
    )
    hidden_plot_frames = [
        item for item in timeline if item["hasPlot"] and item["outputVis"] == "hidden"
    ]
    height_changes = []
    prior_height = None
    for item in timeline:
        height = item["outputH"]
        if prior_height is None or abs(height - prior_height) > 0.5:
            height_changes.append(item)
            prior_height = height
    last_height_change = height_changes[-1]

    assert plot_found["hasPlot"] is True, timeline
    assert plot_found["outputVis"] == "hidden", timeline
    assert hidden_plot_frames, timeline
    assert first_visible_with_plot is not None, timeline
    assert first_visible_with_plot["t"] > plot_found["t"], timeline
    assert plot_found["t"] > last_height_change["t"], {
        "plotFound": plot_found,
        "lastHeightChange": last_height_change,
        "timeline": timeline,
    }
