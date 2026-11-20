from __future__ import annotations

import pytest
from shinywidgets._config import _SETTINGS, config, native_events_enabled


@pytest.fixture(autouse=True)
def reset_settings():
    _SETTINGS.clear()
    yield
    _SETTINGS.clear()


def test_native_events_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHINYWIDGETS_NATIVE_EVENTS", raising=False)
    assert native_events_enabled() is False
    assert config() == {"native_events": False}


def test_native_events_env_var_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", "1")
    assert native_events_enabled() is True
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", "true")
    assert native_events_enabled() is True
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", "0")
    assert native_events_enabled() is False


def test_explicit_set_overrides_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", "1")
    config(native_events=False)
    assert native_events_enabled() is False
    config(native_events=True)
    assert native_events_enabled() is True


def test_config_returns_current_settings() -> None:
    assert config(native_events=True) == {"native_events": True}


def test_unknown_setting_raises() -> None:
    with pytest.raises(TypeError, match="Unknown shinywidgets config setting"):
        config(cdnn=True)  # type: ignore[call-arg]
