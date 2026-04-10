def test_import_and_version_smoke() -> None:
    import shinywidgets

    assert isinstance(shinywidgets.__version__, str)
    assert shinywidgets.__version__
