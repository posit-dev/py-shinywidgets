from __future__ import annotations


def test_find_ipy_model_refs_empty_state():
    from shinywidgets._bulk_state import find_ipy_model_refs

    assert find_ipy_model_refs({}) == set()


def test_find_ipy_model_refs_flat():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"layout": "IPY_MODEL_abc123", "style": "IPY_MODEL_def456"}
    assert find_ipy_model_refs(state) == {"abc123", "def456"}


def test_find_ipy_model_refs_nested_dicts():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"outer": {"inner": "IPY_MODEL_nested1"}}
    assert find_ipy_model_refs(state) == {"nested1"}


def test_find_ipy_model_refs_lists():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"layers": ["IPY_MODEL_l1", "IPY_MODEL_l2", "not_a_ref"]}
    assert find_ipy_model_refs(state) == {"l1", "l2"}


def test_find_ipy_model_refs_mixed_nesting():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {
        "controls": [
            {"widget": "IPY_MODEL_ctrl1"},
            "IPY_MODEL_ctrl2",
        ],
        "name": "Map",
        "count": 42,
        "layout": "IPY_MODEL_lay1",
    }
    assert find_ipy_model_refs(state) == {"ctrl1", "ctrl2", "lay1"}


def test_find_ipy_model_refs_deduplicates():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"a": "IPY_MODEL_x", "b": "IPY_MODEL_x"}
    assert find_ipy_model_refs(state) == {"x"}


def test_find_ipy_model_refs_ignores_non_model_strings():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"label": "IPY_MODEL_looks_like_ref", "title": "not IPY_MODEL_nope", "prefix": "IPY_MODE"}
    # "IPY_MODEL_looks_like_ref" IS a ref (starts with IPY_MODEL_)
    # "not IPY_MODEL_nope" is NOT (doesn't start with prefix)
    # "IPY_MODE" is NOT (too short)
    assert find_ipy_model_refs(state) == {"looks_like_ref"}
