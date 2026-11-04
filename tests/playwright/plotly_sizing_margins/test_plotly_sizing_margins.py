from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def plot_height(page: Page, output_id: str) -> float:
    return page.locator(f"#{output_id} .js-plotly-plot").evaluate(
        "(el) => el.getBoundingClientRect().height"
    )


def margins(page: Page, output_id: str) -> dict:
    return page.locator(f"#{output_id} .js-plotly-plot").evaluate(
        """(el) => {
            const m = el._fullLayout.margin;
            return { l: m.l, t: m.t, r: m.r, b: m.b };
        }"""
    )


def test_explicit_output_height_sizes_the_plot(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    for output_id in ("fixed", "filling"):
        plot = page.locator(f"#{output_id} .js-plotly-plot")
        expect(plot).to_have_count(1, timeout=30000)
        # plotly first draws at its 360px fallback; the binding resizes
        # before revealing, so poll for the settled height. Check
        # _fullLayout.height (not just the div): the graph div is sized to
        # the output by CSS, so it can be 300px while plotly's contents are
        # still at the fallback
        page.wait_for_function(
            """(id) => {
                const el = document.querySelector(`#${id} .js-plotly-plot`);
                return el && el._fullLayout &&
                    Math.abs(el.getBoundingClientRect().height - 300) < 2 &&
                    Math.abs(el._fullLayout.height - 300) < 2;
            }""",
            arg=output_id,
            timeout=30000,
        )

    assert_no_unexpected_errors(errors, failed_requests)


def test_template_swap_keeps_compact_margins(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    plot = page.locator("#fixed .js-plotly-plot")
    expect(plot).to_have_count(1, timeout=30000)
    expect(page.locator("#dark")).to_be_enabled(timeout=30000)
    page.wait_for_function(
        """() => {
            const el = document.querySelector('#fixed .js-plotly-plot');
            return el && el._fullLayout && el._fullLayout.paper_bgcolor === 'white';
        }""",
        timeout=30000,
    )

    compact = {"l": 16, "t": 32, "r": 16, "b": 16}
    assert margins(page, "fixed") == compact

    # An in-place template swap (e.g. a dark-mode toggle) used to revert the
    # renderer's compact margins to plotly's 80px defaults. After each click,
    # wait for the swap to actually arrive (paper_bgcolor is the plotly /
    # plotly_dark paper color) before checking the margins
    for bgcolor in ("rgb(17,17,17)", "white"):
        page.click("#dark")
        page.wait_for_function(
            """(bg) => {
                const el = document.querySelector('#fixed .js-plotly-plot');
                return el && el._fullLayout && el._fullLayout.paper_bgcolor === bg;
            }""",
            arg=bgcolor,
            timeout=30000,
        )
        assert margins(page, "fixed") == compact

    assert_no_unexpected_errors(errors, failed_requests)
