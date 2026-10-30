from __future__ import annotations

import pytest
from playwright.sync_api import Page


# The rerun viewer asks api.github.com for its latest release from the
# browser. That request is irrelevant to what these tests assert, and on CI it
# intermittently fails with 403 (GitHub's unauthenticated rate limit counts
# the runner's shared egress IP), which assert_no_unexpected_errors() then
# reports. Answer it deterministically with an ancient version so the viewer
# never sees an "update available" prompt either.
@pytest.fixture(autouse=True)
def _stub_rerun_release_check(page: Page) -> None:
    page.route(
        "**/api.github.com/repos/rerun-io/rerun/releases/**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"tag_name": "0.0.0"}',
        ),
    )
