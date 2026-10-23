from __future__ import annotations

import asyncio
import json
import warnings

import pydeck as pdk
import pytest
from packaging.version import Version
from pydeck.widget import DeckGLWidget
from shiny import Session, reactive
from shiny.reactive import Context
from shiny.session import session_context
from shiny.session._session import AppSession
from shinywidgets import as_widget, render_pydeck
from shinywidgets._render_widget_base import WidgetRenderContext
from shinywidgets._widget_registry import WIDGET_INSTANCE_MAP

pytestmark = pytest.mark.skipif(
    Version(pdk.__version__) < Version("0.9"),
    reason="These tests cover pydeck >= 0.9, which has no ipywidget",
)


@pytest.fixture
def comm_opens(widget_session: Session, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The model names of widgets whose comms were opened."""
    opens: list[str] = []

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            opens.append(json.loads(message)["content"]["data"]["state"]["_model_name"])

    monkeypatch.setattr(widget_session, "send_custom_message", send_custom_message)
    return opens


def flush(session: Session) -> None:
    assert isinstance(session, AppSession)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(reactive.flush())
    loop.run_until_complete(session._flush_callbacks.invoke())


def scatter_deck() -> pdk.Deck:
    layer = pdk.Layer(
        "ScatterplotLayer", [{"lng": 0.0, "lat": 0.0}], get_position=["lng", "lat"]
    )
    return pdk.Deck(layers=[layer])


def deprecated_render_pydeck() -> render_pydeck[object]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return render_pydeck()


def test_deck_outside_session() -> None:
    # pydeck constructs DeckGLWidgets it never displays (e.g., to probe for
    # Jupyter support), which used to hit shinywidgets' "construct widgets in a
    # session" error, so a module-level Deck crashed the app
    deck = scatter_deck()
    assert "ScatterplotLayer" in deck.to_html(as_string=True)


def test_deck_inside_session_opens_no_comms(
    widget_session: Session, comm_opens: list[str]
) -> None:
    n_instances = len(WIDGET_INSTANCE_MAP)
    with session_context(widget_session):
        with Context()(), WidgetRenderContext():
            scatter_deck()
        flush(widget_session)
    assert comm_opens == []
    assert len(WIDGET_INSTANCE_MAP) == n_instances


def test_deck_widget_settings_still_apply() -> None:
    # pydeck still sets traits on its (inert) deck_widget
    deck = pdk.Deck(height=321, tooltip=False)
    assert deck.deck_widget.height == 321
    assert deck.deck_widget.tooltip is False


def test_render_pydeck_is_deprecated() -> None:
    with pytest.warns(DeprecationWarning, match="render_pydeck.*render_maplibre"):
        render_pydeck()


def test_as_widget_deck_explains_without_serializing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Serializing can fail on its own (pydeck <= 0.9.1 can't serialize pandas 3
    # DataFrames), hiding the explanation behind a cryptic error
    def show(self: pdk.Deck) -> object:
        raise AssertionError("Deck.show() shouldn't be called")

    monkeypatch.setattr(pdk.Deck, "show", show)
    with pytest.raises(TypeError) as excinfo:
        as_widget(scatter_deck())

    msg = str(excinfo.value)
    assert "pydeck v0.9 removed its Jupyter widget" in msg
    assert "render_maplibre" in msg
    assert "return deck.show()" in msg
    assert "srcdoc=deck.to_html(as_string=True)" in msg
    assert "downgrad" not in msg
    assert ".For" not in msg


@pytest.mark.parametrize("value", [scatter_deck, DeckGLWidget])
def test_render_pydeck_explains(widget_session: Session, value: type) -> None:
    r = deprecated_render_pydeck()

    @r
    def _():  # noqa: ANN202
        return value()

    with session_context(widget_session):
        with pytest.raises(TypeError, match="pydeck v0.9 removed its Jupyter widget"):
            asyncio.run(r._render())
