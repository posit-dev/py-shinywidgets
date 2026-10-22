from __future__ import annotations

import threading

from ipywidgets import Widget


def stop_nglview_threads(w: Widget) -> None:
    """
    Stop the background threads an nglview widget sends its remote calls from.

    Every `NGLWidget` starts threads (`RemoteCallThread`s; two, since its
    constructor runs `_initialize_threads()` twice) that poll forever, holding a
    reference to the widget, and `close()` doesn't stop them. A notebook leaks a
    pair per displayed viewer; Shiny constructs a new viewer per render, so the
    leak would grow for the life of the process.
    """
    # nglview is optional, and this only runs for nglview widgets
    from nglview.remote_thread import RemoteCallThread

    for t in threading.enumerate():
        if isinstance(t, RemoteCallThread) and t.view is w:
            # The thread runs queued callbacks in order, so it exits (silently:
            # threads swallow SystemExit) once it has sent anything pending
            t.q.append(exit_thread)


def exit_thread(view: Widget) -> None:
    raise SystemExit
