from __future__ import annotations

import pytest

from shinywidgets._shinywidgets import ws_max_size


def test_default_matches_uvicorn() -> None:
    assert ws_max_size() == 16 * 1024 * 1024


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_WS_MAX_SIZE", "33554432")
    assert ws_max_size() == 33554432


def test_invalid_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_WS_MAX_SIZE", "huge")
    with pytest.warns(UserWarning, match="SHINYWIDGETS_WS_MAX_SIZE"):
        assert ws_max_size() == 16 * 1024 * 1024
