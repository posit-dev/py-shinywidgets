from typing import Callable, Optional, cast

from ipywidgets import IntSlider
from shiny import reactive
from shiny.express import render
from shinywidgets import reactive_read, render_widget
from shinywidgets._accessors import AccessorSpec


def observe_value(
    widget: IntSlider, emit: Callable[[object], None]
) -> Callable[[], None]:
    def handler(change: dict) -> None:
        emit(change["new"])

    widget.observe(handler, "value")
    return lambda: widget.unobserve(handler, "value")


class render_slider(render_widget[IntSlider]):
    _accessor_specs = (
        AccessorSpec(
            name="value_state",
            kind="state",
            attach=observe_value,
            rate_policy="debounce",
        ),
    )

    def value_state(self) -> Optional[int]:
        return cast(Optional[int], self._read_accessor("value_state"))


counts = {name: reactive.value(0) for name in ("fast", "slow", "raw", "policy")}


def bump(name: str) -> None:
    with reactive.isolate():
        counts[name].set(counts[name]() + 1)


@render_slider(rate_delay=0)
def fast():
    return IntSlider(value=0, max=100)


@render_slider()
def slow():
    return IntSlider(value=0, max=100)


@render_widget(rate_policy="debounce")
def policy():
    return IntSlider(value=0, max=100)


@render.text
def fast_model():
    return fast.widget.model_id


@render.text
def slow_model():
    return slow.widget.model_id


@render.text
def policy_model():
    return policy.widget.model_id


@render.text
def fast_value():
    bump("fast")
    return str(fast.value_state())


@render.text
def slow_value():
    bump("slow")
    return str(slow.value_state())


@render.text
def raw_slow():
    bump("raw")
    return str(reactive_read(slow.widget, "value"))


@render.text
def policy_value():
    bump("policy")
    return str(reactive_read(policy.widget, "value"))


@render.text
def fast_count():
    return str(counts["fast"]())


@render.text
def slow_count():
    return str(counts["slow"]())


@render.text
def raw_count():
    return str(counts["raw"]())


@render.text
def policy_count():
    return str(counts["policy"]())
