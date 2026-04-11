from __future__ import annotations


def find_ipy_model_refs(state: dict[str, object]) -> set[str]:
    """Walk serialized widget state and return all referenced model IDs.

    ipywidgets serializes cross-model references as strings with the
    ``IPY_MODEL_`` prefix (see ``unpack_models`` in ``@jupyter-widgets/base``).
    """
    refs: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, str) and obj.startswith("IPY_MODEL_"):
            refs.add(obj[10:])
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(state)
    return refs
