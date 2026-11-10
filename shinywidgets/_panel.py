"""
The `param(name)` accessor for `render_panel`: reads a parameter of the
rendered object reactively, via `param.watch` on the server (Panel parameters
aren't widget traits, so there's no JavaScript bridge involved).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from jupyter_bokeh import BokehModel

    from ._render_widget import render_panel

# Accessor slot names are prefixed so a parameter named like a declared
# accessor (or "value", which AccessorSpec reserves) can't collide with one
PARAM_PREFIX = "param:"


def dynamic_accessor_spec(renderer: render_panel, name: str) -> Optional[AccessorSpec]:
    """The spec behind `renderer.param(name)`, or None for other names."""
    if not name.startswith(PARAM_PREFIX):
        return None
    param_name = name[len(PARAM_PREFIX) :]

    def attach(widget: BokehModel, emit: Emit) -> Callable[[], None]:
        return watch_param(renderer, param_name, emit)

    return AccessorSpec(name=name, kind="state", attach=attach)


def watch_param(renderer: render_panel, name: str, emit: Emit) -> Callable[[], None]:
    """
    Watch `name` on the renderer's current `.value`, emitting its current
    value right away (the seed) and each later change; the returned function
    un-watches.
    """
    import param

    value = renderer._value
    call = f"`{renderer.output_id}.param({name!r})`"
    if not isinstance(value, param.Parameterized):
        raise TypeError(
            f"{call} needs the rendered object to be a param.Parameterized "
            f"(e.g., a panel widget, pane, or Viewer), but "
            f"`{renderer.output_id}.value` is a {type(value).__name__}. Return "
            "a panel object explicitly -- a raw value like a string or "
            "DataFrame has no parameters to read."
        )
    if name not in value.param:
        raise ValueError(
            f"{call}: {type(value).__name__} has no parameter {name!r} "
            f"(its parameters are: {', '.join(value.param)})."
        )

    def on_change(event: param.parameterized.Event) -> None:
        emit(event.new)

    watcher = value.param.watch(on_change, name)
    # Seed with the current value (after watching, so a change in between
    # isn't missed)
    emit(getattr(value, name))
    return lambda: value.param.unwatch(watcher)
