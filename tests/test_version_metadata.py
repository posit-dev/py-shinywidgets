from __future__ import annotations

from importlib.metadata import version as package_version


def test_package_exposes_generated_version_module() -> None:
    import shinywidgets

    assert isinstance(shinywidgets.__version__, str)
    assert shinywidgets.__version__


def test_package_version_matches_installed_metadata() -> None:
    import shinywidgets

    assert shinywidgets.__version__ == package_version("shinywidgets")
