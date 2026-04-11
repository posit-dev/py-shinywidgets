from __future__ import annotations

from base64 import b64encode
from typing import Any, Callable


def build_manager_state(
    root_widget: Any,
    widget_instance_map: dict[str, Any],
    remove_buffers: Callable[[dict[str, Any]], tuple[dict[str, Any], list[list[str]], list[bytes]]],
    collect_deps: Callable[[Any], list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build a bulk manager-state payload for the full widget dependency closure.

    Parameters
    ----------
    root_widget
        The root widget to start traversal from.
    widget_instance_map
        Map of model_id -> widget instance (typically ``Widget.widgets``).
    remove_buffers
        Callable that strips binary buffers from serialized state, returning
        ``(state, buffer_paths, buffers)``. Typically ``ipywidgets._remove_buffers``.
    collect_deps
        Callable that returns HTML dependency dicts for a given widget.
    """
    visited: dict[str, dict[str, Any]] = {}
    html_deps: list[dict[str, Any]] = []
    seen_dep_keys: set[tuple[str, str]] = set()
    queue = [root_widget]

    while queue:
        w = queue.pop()
        wid = w.model_id
        if wid in visited:
            continue

        if hasattr(w, "_repr_mimebundle_") and callable(w._repr_mimebundle_):
            w._repr_mimebundle_()

        state, buffer_paths, buffers = remove_buffers(w.get_state())

        encoded_buffers = []
        for path, buf in zip(buffer_paths, buffers):
            encoded_buffers.append({
                "path": path,
                "encoding": "base64",
                "data": b64encode(buf).decode("ascii"),
            })

        visited[wid] = {
            "model_name": w._model_name,
            "model_module": w._model_module,
            "model_module_version": w._model_module_version,
            "state": state,
            "buffers": encoded_buffers,
        }

        for dep in collect_deps(w):
            key = (dep.get("name", ""), dep.get("version", ""))
            if key not in seen_dep_keys:
                seen_dep_keys.add(key)
                html_deps.append(dep)

        for ref_id in find_ipy_model_refs(state):
            if ref_id not in visited and ref_id in widget_instance_map:
                queue.append(widget_instance_map[ref_id])

    return {
        "root_model_id": root_widget.model_id,
        "state": visited,
        "html_deps": html_deps,
    }


def materialize_bulk_comms(
    state_entries: dict[str, dict[str, Any]],
    widget_instance_map: dict[str, Any],
    comm_manager: Any,
    comm_class: type[Any],
    widget_comm_patch: Callable[[], Any],
) -> None:
    """Create ``comm_class(emit_open=False)`` for each widget in the bulk closure
    and set the ``_shinywidgets_bulk_owned`` flag so the legacy per-widget open
    effect skips them."""
    for wid in state_entries:
        w = widget_instance_map.get(wid)
        if w is None:
            continue
        with widget_comm_patch():
            w.comm = comm_class(
                comm_id=wid,
                comm_manager=comm_manager,
                target_name="jupyter.widget",
                emit_open=False,
            )
        w._shinywidgets_bulk_owned = True


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
