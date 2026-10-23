from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Heights of an output's container (what the user sized: a card body or an
# explicit height) and of quak's table, plus how many rows are loaded. quak
# renders into a shadow root, which querySelector() alone doesn't reach.
MEASURE_JS = """(id) => {
  const out = document.getElementById(id);
  const quak = out.querySelector('.lm-Widget').children[0].shadowRoot.querySelector('.quak');
  const scroller = quak.querySelector('.table-container');
  const rows = quak.querySelectorAll('tbody tr').length;
  return {
    container: out.getBoundingClientRect().height,
    quak: quak.getBoundingClientRect().height,
    scrollerClient: scroller.clientHeight,
    scrollerScroll: scroller.scrollHeight,
    rows,
  };
}"""

# Counts ResizeObservers that are observing (i.e., not yet disconnected)
COUNT_RESIZE_OBSERVERS_JS = """
(() => {
  const Native = window.ResizeObserver;
  window.liveResizeObservers = 0;
  window.ResizeObserver = class extends Native {
    observing = false;
    observe(...args) {
      if (!this.observing) window.liveResizeObservers++;
      this.observing = true;
      return super.observe(...args);
    }
    disconnect() {
      if (this.observing) window.liveResizeObservers--;
      this.observing = false;
      return super.disconnect();
    }
  };
})();
"""

# Tolerance (px) for sub-pixel rounding and quak's 1px border
TOLERANCE = 2


def measure(page: Page, output_id: str) -> dict[str, float]:
    return page.evaluate(MEASURE_JS, output_id)


def wait_for_rows(page: Page, output_id: str) -> None:
    expect(page.locator(f"#{output_id} .quak tbody tr").first).to_be_visible(
        timeout=30000
    )


def test_quak_renders_table(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_rows(page, "short")
    expect(page.locator("#short .quak th").nth(1)).to_contain_text("id")
    expect(page.locator("#short .quak .status-bar")).to_contain_text("500 rows")

    assert_no_unexpected_errors(errors, failed_requests)


def test_quak_fills_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1200})
    page.goto(local_app.url)

    for output_id in ("short", "tall"):
        wait_for_rows(page, output_id)
        # The tall container needs more rows than quak initially loads, which
        # only happens once the table asks for them
        page.wait_for_function(
            f"""(id) => {{
              const m = ({MEASURE_JS})(id);
              return m.scrollerScroll > m.scrollerClient &&
                Math.abs(m.quak - m.container) <= {TOLERANCE};
            }}""",
            arg=output_id,
            timeout=30000,
        )
        m = measure(page, output_id)
        print(f"fill {output_id}: {m}")
        assert abs(m["quak"] - m["container"]) <= TOLERANCE, m
        # No blank space: loaded rows more than cover the scroll area (a
        # non-strict check would also pass with too few rows)
        assert m["scrollerScroll"] > m["scrollerClient"], m

    assert_no_unexpected_errors(errors, failed_requests)


def test_quak_tall_table_loads_rows_on_scroll(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1200})
    page.goto(local_app.url)
    wait_for_rows(page, "tall")

    initial = measure(page, "tall")
    # quak's own scroll listener only loads rows within ~380px of the bottom,
    # which a scroll area this tall never gets to
    assert initial["scrollerClient"] > 400, initial

    page.locator("#tall .quak .table-container").hover()
    # Scroll past quak's 100-row query batches, where concurrent loads would
    # show up as missing or repeated rows
    rows = initial["rows"]
    while rows < 250:
        page.mouse.wheel(0, 5000)
        page.wait_for_function(
            f"(rows) => ({MEASURE_JS})('tall').rows > rows",
            arg=rows,
            timeout=10000,
        )
        rows = measure(page, "tall")["rows"]

    # The rows loaded so far are the table's first rows, in order
    ids = page.locator("#tall .quak tbody tr td:nth-child(2)").all_inner_texts()
    assert ids == [str(i) for i in range(rows)], ids

    assert_no_unexpected_errors(errors, failed_requests)


def test_quak_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1200})
    page.goto(local_app.url)

    # output_widget(height="300px")
    wait_for_rows(page, "fixed")
    m = measure(page, "fixed")
    print(f"fixed: {m}")
    assert m["container"] == 300
    assert m["quak"] <= 300 + 0.5, m

    # widget.layout.height = "260px"
    wait_for_rows(page, "layout")
    lm = page.locator("#layout > .lm-Widget")
    box = lm.bounding_box()
    assert box is not None
    m = measure(page, "layout")
    print(f"layout: {m}, lm={box}")
    assert box["height"] == 260
    assert m["quak"] <= 260 + 0.5, m

    assert_no_unexpected_errors(errors, failed_requests)


def test_quak_sort_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_rows(page, "short")
    expect(page.locator("#sql")).to_have_text('SELECT "id", "group", "value" FROM "df"')

    # Clicking a column's sort button changes quak's query, which the widget
    # syncs back to Python's `sql` trait
    page.locator("#short .quak .sort-button").nth(2).dispatch_event("mousedown")
    expect(page.locator("#sql")).to_contain_text('ORDER BY "value"', timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_quak_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.add_init_script(COUNT_RESIZE_OBSERVERS_JS)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    wait_for_rows(page, "short")
    expect(page.locator("#render_count")).to_have_text("0")
    initial_observers = page.evaluate("window.liveResizeObservers")

    for i in range(1, 4):
        old_quak = page.locator("#short .quak").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_quak)
        wait_for_rows(page, "short")

    expect(page.locator("#short .quak")).to_have_count(1)
    # The fit observers of retired views must be disconnected
    assert page.evaluate("window.liveResizeObservers") == initial_observers
    # One model per output, each with exactly one view
    quaks = [m for m in client_models(page) if m["name"] == "AnyModel"]
    assert [m["views"] for m in quaks] == [1] * 4, quaks

    assert_no_unexpected_errors(errors, failed_requests)
