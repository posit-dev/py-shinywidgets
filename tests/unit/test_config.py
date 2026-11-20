from __future__ import annotations

import pytest
from shinywidgets._config import (
    _SETTINGS,
    cdn_only,
    cdn_url,
    config,
    extension_warning,
    native_events_enabled,
)

CDN_DEFAULT = "https://cdn.jsdelivr.net/npm/"

ENV_VARS = (
    "SHINYWIDGETS_NATIVE_EVENTS",
    "SHINYWIDGETS_CDN",
    "SHINYWIDGETS_CDN_ONLY",
    "SHINYWIDGETS_EXTENSION_WARNING",
)


@pytest.fixture(autouse=True)
def reset_settings():
    _SETTINGS.clear()
    yield
    _SETTINGS.clear()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_native_events_default_off() -> None:
    assert native_events_enabled() is False


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


def test_cdn_defaults_from_clean_environment() -> None:
    assert cdn_url() == CDN_DEFAULT
    assert cdn_only() is False
    assert extension_warning() is False


def test_cdn_env_var_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_CDN", "https://npm.example.com/")
    monkeypatch.setenv("SHINYWIDGETS_CDN_ONLY", "true")
    monkeypatch.setenv("SHINYWIDGETS_EXTENSION_WARNING", "true")
    assert cdn_url() == "https://npm.example.com/"
    assert cdn_only() is True
    assert extension_warning() is True
    # Only "true" parses as true, matching the historical env-var parsing
    monkeypatch.setenv("SHINYWIDGETS_CDN_ONLY", "1")
    monkeypatch.setenv("SHINYWIDGETS_EXTENSION_WARNING", "1")
    assert cdn_only() is False
    assert extension_warning() is False


def test_cdn_explicit_set_overrides_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHINYWIDGETS_CDN", "https://npm.example.com/")
    monkeypatch.setenv("SHINYWIDGETS_CDN_ONLY", "true")
    monkeypatch.setenv("SHINYWIDGETS_EXTENSION_WARNING", "true")
    config(cdn="https://other.example.com/", cdn_only=False, extension_warning=False)
    assert cdn_url() == "https://other.example.com/"
    assert cdn_only() is False
    assert extension_warning() is False


def test_env_vars_are_read_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    # Nothing is snapshotted at import time: an env var set later still wins
    assert cdn_url() == CDN_DEFAULT
    assert cdn_only() is False
    assert extension_warning() is False
    monkeypatch.setenv("SHINYWIDGETS_CDN", "https://npm.example.com/")
    monkeypatch.setenv("SHINYWIDGETS_CDN_ONLY", "true")
    monkeypatch.setenv("SHINYWIDGETS_EXTENSION_WARNING", "true")
    assert cdn_url() == "https://npm.example.com/"
    assert cdn_only() is True
    assert extension_warning() is True


def test_config_returns_current_settings() -> None:
    assert config(native_events=True) == {
        "native_events": True,
        "cdn": CDN_DEFAULT,
        "cdn_only": False,
        "extension_warning": False,
    }
    assert config() == {
        "native_events": True,
        "cdn": CDN_DEFAULT,
        "cdn_only": False,
        "extension_warning": False,
    }


def test_unknown_setting_raises() -> None:
    with pytest.raises(TypeError, match="Unknown shinywidgets config setting"):
        config(cdnn=True)  # type: ignore[call-arg]
