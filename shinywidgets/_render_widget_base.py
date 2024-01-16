from __future__ import annotations

from typing import Any, Generic, Optional, Sequence, TypeVar, Union, cast

from htmltools import Tag
from ipywidgets.widgets import Widget  # pyright: ignore[reportMissingTypeStubs]
from shiny import reactive, req
from shiny.reactive import (
    Calc_ as shiny_reactive_calc_class,  # pyright: ignore[reportPrivateImportUsage]
)
from shiny.reactive import value as shiny_reactive_value
from shiny.reactive._core import Context, get_current_context
from shiny.render.renderer import Jsonifiable, Renderer, ValueFn
from traitlets import Unicode

from ._as_widget import as_widget
from ._output_widget import output_widget
from ._shinywidgets import reactive_depend, reactive_read, set_layout_defaults

__all__ = (
    "render_widget_base",
    "WidgetT",
    "ValueT",
)

# --------------------------------------------------------------------------------------------
# Implement @render_widget()
# --------------------------------------------------------------------------------------------

ValueT = TypeVar("ValueT", bound=object)
"""
The type of the value returned by the Shiny app render function
"""
WidgetT = TypeVar("WidgetT", bound=Widget)
"""
The type of the widget created from the renderer's ValueT
"""


class render_widget_base(Renderer[ValueT], Generic[ValueT, WidgetT]):
    """ """

    def default_ui(self, id: str) -> Tag:
        return output_widget(
            id,
            width=self.width,
            height=self.height,
            fill=self.fill,
            fillable=self.fillable,
        )

    def __init__(
        self,
        _fn: Optional[ValueFn[ValueT]] = None,
        *,
        width: Optional[str] = None,
        height: Optional[str] = None,
        fill: Optional[bool] = None,
        fillable: Optional[bool] = None,
    ):
        super().__init__(_fn)
        self.width: Optional[str] = width
        self.height: Optional[str] = height
        self.fill: Optional[bool] = fill
        self.fillable: Optional[bool] = fillable

        # self._value: ValueT | None = None  # TODO-barret; Not right type
        # self._widget: WidgetT | None = None
        self._contexts: set[Context] = set()

        self._value: shiny_reactive_value[ValueT | None] = shiny_reactive_value(None)
        self._widget: shiny_reactive_value[WidgetT | None] = shiny_reactive_value(None)

    async def render(self) -> Jsonifiable | None:
        value = await self.fn()

        # Attach value/widget attributes to user func so they can be accessed (in other reactive contexts)
        self._value.set(value)
        self._widget.set(None)

        if value is None:
            return None

        # Ensure we have a widget & smart layout defaults
        widget = as_widget(value)
        widget, fill = set_layout_defaults(widget)

        self._widget.set(
            # TODO-future; Remove cast call once `as_widget()` returns a WidgetT
            cast(WidgetT, widget)
        )

        return {
            "model_id": str(
                cast(
                    Unicode,
                    widget.model_id,  # pyright: ignore[reportUnknownMemberType]
                )
            ),
            "fill": fill,
        }

    # ########
    # Enhancements
    # ########

    # TODO-barret; Turn these into reactives. We do not have reactive values in `py-shiny`, we shouldn't have them in `py-shinywidgets`
    # TODO-barret; Add `.reactive_read()` and `.reactive_depend()` methods

    def value(self) -> ValueT:
        value = self._value()
        req(value)

        # Can only get here if value is not `None`
        value = cast(ValueT, value)
        return value

    def widget(self) -> WidgetT:
        widget = self._widget()
        req(widget)

        # Can only get here if widget is not `None`
        widget = cast(WidgetT, widget)
        return widget

    # def value_trait(self, name: str) -> Any:
    #     return reactive_read(self.value(), name)
    def widget_trait(self, name: str) -> Any:
        return reactive_read(self.widget(), name)

    # ##########################################################################

    # TODO-future; Should this method be supported? Can we have full typing support for the trait values?
    # Note: Barret,Carson Jan 11-2024;
    # This method is a very Shiny-like approach to making reactive values from
    # ipywidgets. However, it would not support reaching into the widget with full
    # typing. Instead, it is recommended that we keep `reactive_read(widget_like_obj,
    # name)` that upgrades a (nested within widget) value to a resolved value that will
    # invalidate the current context when the widget value is updated (by some other
    # means).
    #
    # Since we know that `@render_altair` is built on `altair.JupyterChart`, we know
    # that `jchart.widget()` will return an `JupyterChart` object. This object has full
    # typing, such as `jchart.widget().selections` which is a JupyterChart `Selections`
    # object. Then using the `reactive_read()` function, we can create a reactive value
    # from the `Selections` object. This allows for users to reach into the widget as
    # much as possible (with full typing) before using `reactive_read()`.
    #
    # Ex:
    # ----------------------
    # ```python
    # @render_altair
    # def jchart():
    #    return some_altair_chart
    #
    # @render.text
    # def selected_point():
    #    # This is a reactive value that will invalidate the current context when the chart's selection changes
    #    selected_point = reactive_read(jchart.widget().selections, "point")
    #    return f"The selected point is: {selected_point()}"
    # ```
    # ----------------------
    #
    # Final realization:
    # The method below (`_reactive_trait()`) does not support reaching into the widget
    # result object. If the method was updated to support a nested key (str), typing
    # would not be supported.
    #
    # Therefore, `reactive_read()` should be used until we can dynamically create
    # classes that wrap a widget. (Barret: I am not hopeful that this will be possible
    # or worth the effort. Ex: `jchart.traits.selections.point()` would be a reactive
    # and fully typed.)
    def _reactive_trait(
        self,
        names: Union[str, Sequence[str]],
    ) -> shiny_reactive_calc_class[Any]:
        """
        Create a reactive value of a widget's top-level value that can be accessed by
        name.

        Ex:

        ```python
        slider_value = slider.reactive_trait("value")

        @render.text
        def slider_val():
            return f"The value of the slider is: {slider_value()}"
        ```
        """

        if in_reactive_context():
            raise RuntimeError(
                "Calling `reactive_trait()` within a reactive context is not supported."
            )

        reactive_trait: shiny_reactive_value[Any] = shiny_reactive_value(None)

        names_was_str = isinstance(names, str)
        if isinstance(names, str):
            names = [names]

        @reactive.effect
        def _():
            # Set the value to None incase the widget doesn't exist / have the trait
            reactive_trait.set(None)

            widget = self.widget()

            for name in names:
                if not widget.has_trait(  # pyright: ignore[reportUnknownMemberType]
                    name
                ):
                    raise ValueError(
                        f"The '{name}' attribute of {widget.__class__.__name__} is not a "
                        "widget trait, and so it's not possible to reactively read it. "
                        "For a list of widget traits, call `.widget().trait_names()`."
                    )

            # # From `Widget.observe()` docs:
            # A callable that is called when a trait changes. Its
            # signature should be ``handler(change)``, where ``change`` is a
            # dictionary. The change dictionary at least holds a 'type' key.
            # * ``type``: the type of notification.
            # Other keys may be passed depending on the value of 'type'. In the
            # case where type is 'change', we also have the following keys:
            # * ``owner`` : the HasTraits instance
            # * ``old`` : the old value of the modified trait attribute
            # * ``new`` : the new value of the modified trait attribute
            # * ``name`` : the name of the modified trait attribute.
            def on_key_update(change: object):
                if names_was_str:
                    val = getattr(widget, names[0])
                else:
                    val = tuple(getattr(widget, name) for name in names)

                reactive_trait.set(val)

            # set value to the init widget value
            on_key_update(None)

            # Setup - onchange
            # When widget attr changes, update the reactive value
            widget.observe(  # pyright: ignore[reportUnknownMemberType]
                on_key_update,
                names,  # pyright: ignore[reportGeneralTypeIssues]
                "change",
            )

            # Teardown - onchange
            # When the widget object is created again, remove the old observer
            def on_ctx_invalidate():
                widget.unobserve(  # pyright: ignore[reportUnknownMemberType]
                    on_key_update,
                    names,  # pyright: ignore[reportGeneralTypeIssues]
                    "change",
                )

            get_current_context().on_invalidate(on_ctx_invalidate)

        # Return a calc object that can only be read from
        @reactive.calc
        def trait_calc():
            return reactive_trait()

        return trait_calc

    # Note: Should be removed once `._reactive_trait()` is removed
    def _reactive_read(self, names: Union[str, Sequence[str]]) -> Any:
        """
        Reactively read a Widget's trait(s)
        """
        self._reactive_depend(names)

        widget = self.widget()

        return reactive_read(widget, names)

    # Note: Should be removed once `._reactive_trait()` is removed
    def _reactive_depend(
        self,
        names: Union[str, Sequence[str]],
        type: str = "change",
    ) -> None:
        """
        Reactively depend upon a Widget's trait(s)
        """
        return reactive_depend(self.widget(), names, type)


def in_reactive_context() -> bool:
    try:
        # Raises a `RuntimeError` if there is no current context
        get_current_context()
        return True
    except RuntimeError:
        return False
