from __future__ import annotations


def test_package_exposes_generated_version_module() -> None:
    import shinywidgets

    assert isinstance(shinywidgets.__version__, str)
    assert shinywidgets.__version__


def test_package_version_matches_generated_module() -> None:
    import shinywidgets
    from shinywidgets.__version import __version__

    assert shinywidgets.__version__ == __version__
