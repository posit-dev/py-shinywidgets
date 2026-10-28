from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import Browser, Page, expect
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc
from tests.playwright.conftest import collect_errors

local_app_explicit = create_app_fixture(Path(__file__).parent / "app_explicit.py")

# The app's cube is pure red against a white background
MIN_RED_PIXELS = 50

# output.ts's get_model() waits this long for a model whose comm_open never
# arrives before rejecting with "Timeout waiting for widget model"
GET_MODEL_TIMEOUT_MS = 30_000


def count_red_pixels(page: Page, selector: str) -> int:
    if page.locator(selector).count() == 0:
        return 0
    try:
        png = page.locator(selector).first.screenshot(timeout=2000)
    except Exception:
        return 0
    rgb = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(int)
    red = (rgb[..., 0] > 200) & (rgb[..., 1] < 60) & (rgb[..., 2] < 60)
    return int(red.sum())


def wait_for_red_pixels(page: Page, selector: str, timeout_ms: int = 30000) -> None:
    waited = 0
    while count_red_pixels(page, selector) <= MIN_RED_PIXELS:
        assert waited < timeout_ms, f"no scene pixels drawn in {selector}"
        page.wait_for_timeout(250)
        waited += 250


def wait_for_console_error(
    errors: list[str], substring: str, page: Page, timeout_ms: int
) -> str:
    waited = 0
    while waited < timeout_ms:
        for err in errors:
            if substring in err:
                return err
        page.wait_for_timeout(250)
        waited += 250
    raise AssertionError(f"no console error containing {substring!r}: {errors}")


def test_shared_light_default_target_shadow_breaks_second_session(
    browser: Browser, local_app: ShinyAppProc
) -> None:
    # Regression for the shared_lifetime() known limitation: a shared
    # pythreejs light left at its default target/shadow has those models
    # created by the first browser's JavaScript; a second session references
    # models only the first browser's session has
    session_a = browser.new_page()
    try:
        errors_a, _ = collect_errors(session_a)
        session_a.goto(local_app.url)
        expect(session_a.locator("#default_light canvas")).to_have_count(
            1, timeout=30000
        )
        wait_for_red_pixels(session_a, "#default_light canvas")

        # Wait until browser A's JS-created target/shadow have synced their
        # (session-A-only) model ids back to the shared Python light
        expect(session_a.locator("#light_state")).to_contain_text(
            "target=Object3D:", timeout=30000
        )
        state = session_a.locator("#light_state").inner_text()
        browser_a_model_ids = [
            part.split(":", 1)[1] for part in state.split() if ":" in part
        ]
        assert len(browser_a_model_ids) == 2

        session_b = browser.new_page()
        try:
            errors_b, _ = collect_errors(session_b)
            session_b.goto(local_app.url)

            # Session B waits for one of browser A's models, gives up after
            # get_model()'s 30s timeout ...
            timeout_err = wait_for_console_error(
                errors_b,
                "Timeout waiting for widget model",
                session_b,
                timeout_ms=GET_MODEL_TIMEOUT_MS + 15_000,
            )
            assert any(mid in timeout_err for mid in browser_a_model_ids)

            # ... and the affected output never renders in session B. (With
            # render_pythreejs from #324, the failure was also seen to
            # cascade to unrelated outputs via "Syncing error: no comm
            # channel defined"; that cascade is not asserted here.)
            expect(session_b.locator("#default_light canvas")).to_have_count(0)
        finally:
            session_b.close()

        # Session A's scenes are unaffected
        wait_for_red_pixels(session_a, "#default_light canvas", timeout_ms=10000)
    finally:
        session_a.close()


def test_shared_light_explicit_target_shadow_render_in_both_sessions(
    browser: Browser, local_app_explicit: ShinyAppProc
) -> None:
    # The documented remedy: an explicit target (added to the scene) and
    # shadow, constructed inside shared_lifetime(), so every session has them
    session_a = browser.new_page()
    try:
        session_a.goto(local_app_explicit.url)
        expect(session_a.locator("#explicit_light canvas")).to_have_count(
            1, timeout=30000
        )
        wait_for_red_pixels(session_a, "#explicit_light canvas")

        session_b = browser.new_page()
        try:
            errors_b, failed_b = collect_errors(session_b)
            session_b.goto(local_app_explicit.url)
            expect(session_b.locator("#explicit_light canvas")).to_have_count(
                1, timeout=30000
            )
            wait_for_red_pixels(session_b, "#explicit_light canvas")
            assert not any("Timeout waiting for widget model" in e for e in errors_b)
            assert not failed_b
        finally:
            session_b.close()
    finally:
        session_a.close()
