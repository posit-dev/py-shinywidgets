import importlib
import os
import tempfile
from typing import Any

from ipywidgets import Widget


# similar to base::system.file()
def package_dir(package: str) -> str:
    with tempfile.TemporaryDirectory():
        pkg_file = importlib.import_module(".", package=package).__file__
        if pkg_file is None:
            raise ImportError(f"Couldn't load package {package}")
        return os.path.dirname(pkg_file)


def restrict_client_traits(w: Widget, allowed: frozenset[str], flag: str) -> None:
    """
    Drop client-authored state updates to `w`, except the `allowed` traits.

    For a process-global widget whose synced traits the browser must not
    rewrite (any session's browser could send an ordinary `update` comm
    message, and every later session would then load that state), Python is
    the only legitimate author of everything but `allowed` (traits the
    frontend itself sets to report progress). Rejecting the rest here, before
    `set_state()`, also keeps them out of the echo update a shared comm fans
    out to the other sessions. `flag` (a private attribute name) makes the
    patch idempotent.
    """
    if getattr(w, flag, False):
        return
    set_state = w.set_state

    def guarded_set_state(sync_data: dict[str, Any]) -> None:
        set_state({k: v for k, v in sync_data.items() if k in allowed})

    w.set_state = guarded_set_state  # type: ignore[method-assign]
    setattr(w, flag, True)
