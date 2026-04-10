from types import SimpleNamespace

import pytest

import shinywidgets._utils as utils


def test_package_dir_returns_directory_for_imported_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        utils.importlib,
        "import_module",
        lambda *args, **kwargs: SimpleNamespace(
            __file__="/tmp/fakepkg/__init__.py",
        ),
    )

    assert utils.package_dir("fakepkg") == "/tmp/fakepkg"


def test_package_dir_raises_when_imported_module_has_no_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        utils.importlib,
        "import_module",
        lambda *args, **kwargs: SimpleNamespace(__file__=None),
    )

    with pytest.raises(ImportError, match="Couldn't load package fakepkg"):
        utils.package_dir("fakepkg")
