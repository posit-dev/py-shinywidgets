from __future__ import annotations

import sys
import threading
from typing import Any, Dict

from ipywidgets import Widget

from ._dependencies import widget_pkg


def is_nglview_widget(w: object) -> bool:
    """
    Is `w` an `nglview.NGLWidget` (or a subclass defined by an application)?

    An app-defined subclass reports the app's own module as its `widget_pkg()`,
    so recognize NGLWidget through the MRO (same as `set_layout_defaults()`)
    rather than by module. Restricted to actual NGLWidget instances: non-viewer
    nglview widgets (e.g. the global `_ColormakerRegistry`, or a
    `RepresentationControl`) also match a package-wide MRO check, but have no
    background threads to stop.
    """
    return any(
        cls.__name__ == "NGLWidget" and widget_pkg(cls) == "nglview"
        for cls in type(w).__mro__
    )


def stop_threads_on_close(w: Widget) -> None:
    """
    Stop an NGLWidget's background threads when the widget is closed.

    Hooking the widget's own `close()` (rather than only the cleanup paths in
    `close_widget()`) covers a user calling `widget.close()` directly: render
    cleanup skips already-closed widgets, and session cleanup only sees widgets
    still in the registry, so a directly-closed viewer would otherwise keep its
    (idle, polling) threads -- and itself -- alive for the rest of the process.
    """
    close = w.close

    def close_and_stop_threads() -> None:
        try:
            stop_nglview_threads(w)
        finally:
            close()

    w.close = close_and_stop_threads  # type: ignore[method-assign]

    # The close above can run before nglview starts its threads: a widget
    # constructed in an already-invalidated render context is closed inside
    # Widget.__init__ (Context.on_invalidate() fires its callback
    # immediately), and nglview's own __init__ starts its second batch of
    # threads only after super().__init__() returns. Stop threads started
    # after a shutdown, too.
    initialize_threads = getattr(w, "_initialize_threads", None)
    if initialize_threads is not None:

        def initialize_threads_stopped() -> None:
            initialize_threads()
            if getattr(w, "_shinywidgets_threads_stopped", False):
                stop_nglview_threads(w)

        w._initialize_threads = initialize_threads_stopped  # type: ignore[attr-defined]


def stop_nglview_threads(w: Widget) -> None:
    """
    Stop the background threads an nglview widget sends its remote calls from.

    Every `NGLWidget` starts threads (`RemoteCallThread`s; two, since its
    constructor runs `_initialize_threads()` twice) that poll forever, holding a
    reference to the widget, and `close()` doesn't stop them. A notebook leaks a
    pair per displayed viewer; Shiny constructs a new viewer per render, so the
    leak would grow for the life of the process.

    This is safe to call more than once (e.g. an explicit `close()` followed by
    cleanup of the same widget, or a close inside `Widget.__init__` followed
    by nglview's second `_initialize_threads()` -- see stop_threads_on_close).
    """
    # nglview is optional, and this only runs for nglview widgets
    from nglview.remote_thread import RemoteCallThread

    # Record the shutdown so threads started *after* this call (nglview's
    # second _initialize_threads() runs after the close in some lifecycles)
    # are stopped as they start
    w._shinywidgets_threads_stopped = True  # type: ignore[attr-defined]

    # Release any wait on a browser acknowledgement that can no longer arrive
    # (the widget's comm is closed): a thread blocked in
    # `_wait_until_finished()` (e.g. mid-`loadFile` after a structure was
    # loaded/replaced, or an image exported) would otherwise never reach the
    # queued exit_thread. nglview's `_wait_until_finished()` clears `_event`
    # *before* waiting, so setting the event only releases a wait already in
    # progress; overriding the method on the instance also makes waits that
    # start afterwards return immediately.
    w._wait_until_finished = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    w._event.set()  # type: ignore[attr-defined]

    for t in threading.enumerate():
        if isinstance(t, RemoteCallThread) and t.view is w:
            # Drop work that hasn't started (its messages would only go to a
            # closed comm) and let the thread exit once it next reaches its
            # queue. The thread runs queued callbacks in order, so it exits
            # (silently: threads swallow SystemExit) on reaching exit_thread.
            t.q.clear()
            t.q.append(exit_thread)


def importing_nglview() -> bool:
    """
    Is nglview constructing its global `ColormakerRegistry` widget (i.e., is
    nglview mid-import)?

    That widget is constructed outside any session, and it can't belong to one
    anyway: it's shared process-wide, and only a notebook ever displays it.
    """
    color = sys.modules.get("nglview.color")
    # The module binds ColormakerRegistry once the widget's construction returns
    return color is not None and not hasattr(color, "ColormakerRegistry")


def exit_thread(view: Widget) -> None:
    raise SystemExit


def is_nglview_registry(w: Widget) -> bool:
    """
    Is `w` nglview's process-global `_ColormakerRegistry`?

    Singled out because the hidden-view replay (js/src/nglview.ts) executes
    this widget's archived `_call()` messages as JS in every session.
    """
    return (
        type(w).__name__ == "_ColormakerRegistry" and widget_pkg(type(w)) == "nglview"
    )


# The one trait the registry's view legitimately writes: it flips `_ready`
# once its render() completes, releasing Python's queue of pending `_call()`s
_REGISTRY_CLIENT_TRAITS = frozenset({"_ready"})


def guard_registry_state(w: Widget) -> None:
    """
    Drop client-authored state updates to the shared registry, except `_ready`.

    `_msg_ar` (the archive of `_call()` messages) is a synced trait, so any
    session could write it through the usual `update` comm message -- and the
    hidden-view replay executes archived `executeCode` messages as JS in
    every later session. Python is the only legitimate author of everything
    but `_ready` (which the view sets when it finishes rendering), so reject
    the rest at the point they'd be applied. Filtering here, before
    `set_state()`, also keeps rejected writes out of the echo update the
    shared comm would fan out to the other sessions.
    """
    if getattr(w, "_shinywidgets_registry_guarded", False):
        return
    set_state = w.set_state

    def guarded_set_state(sync_data: Dict[str, Any]) -> None:
        set_state({k: v for k, v in sync_data.items() if k in _REGISTRY_CLIENT_TRAITS})

    w.set_state = guarded_set_state  # type: ignore[method-assign]
    w._shinywidgets_registry_guarded = True  # type: ignore[attr-defined]
