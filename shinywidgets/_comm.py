from base64 import b64encode
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from shiny.session import get_current_session

from ._serialization import json_packer

_PENDING_UPDATES_ATTR = "__shinywidgets_pending_comm_updates"


class ShinyCommManager:
    comms: Dict[str, "ShinyComm"] = {}

    def register_comm(self, comm: "ShinyComm") -> str:
        id = comm.comm_id
        self.comms[id] = comm
        return id

    def unregister_comm(self, comm: "ShinyComm") -> "ShinyComm":
        return self.comms.pop(comm.comm_id)


MsgCallback = Callable[[Dict[str, object]], None]
DataType = Optional[Dict[str, object]]
MetadataType = Optional[Dict[str, object]]
BufferType = Optional[List[bytes]]


# Compare to `ipykernel.comm.Comm` (uses the Shiny session instead of a Kernel to send/receive messages).
# Also note that `ipywidgets.widgets.Widget` is responsible to calling these methods when need be.
class ShinyComm:
    # `ipywidgets.widgets.Widget` does some checks for `if self.comm.kernel is not None` but
    # we don't have a kernel here, so give it a meaningless value.
    kernel = "Shiny"

    _msg_callback: Optional[MsgCallback]
    _close_callback: Optional[MsgCallback]
    _closed: bool = False
    _closed_data: Dict[str, object] = {}

    def __init__(
        self,
        comm_id: str,
        comm_manager: ShinyCommManager,
        target_name: str,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
        **keys: object,
    ) -> None:
        self.comm_id = comm_id
        self.comm_manager = comm_manager
        self.target_name = target_name
        self.open(data=data, metadata=metadata, buffers=buffers, **keys)

    def open(
        self,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
        **keys: object,
    ) -> None:
        self.comm_manager.register_comm(self)
        try:
            self._publish_msg(
                "shinywidgets_comm_open",
                data=data,
                metadata=metadata,
                buffers=buffers,
                target_name=self.target_name,
                target_module=None,
                **keys,
            )
            self._closed = False
        except Exception:
            self.comm_manager.unregister_comm(self)
            raise

    # Inform client of any mutation(s) to the model (e.g., add a marker to a map, without a full redraw)
    def send(
        self,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
    ) -> None:
        self._publish_msg(
            "shinywidgets_comm_msg", data=data, metadata=metadata, buffers=buffers
        )

    def close(
        self,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
        deleting: bool = False,
    ) -> None:
        if self._closed:
            return
        self._closed = True
        data = self._closed_data if data is None else data
        if get_current_session():
            self._publish_msg(
                "shinywidgets_comm_close", data=data, metadata=metadata, buffers=buffers
            )
        if not deleting:
            # If deleting, the comm can't be unregistered
            self.comm_manager.unregister_comm(self)

    # trigger close on gc
    def __del__(self):
        self.close(deleting=True)

    # Compare to `ipykernel.comm.Comm._publish_msg`, but...
    # https://github.com/jupyter/jupyter_client/blob/c5c0b80/jupyter_client/session.py#L749
    # ...the real meat of the implement is in `jupyter_client.session.Session.send`
    # https://github.com/jupyter/jupyter_client/blob/c5c0b8/jupyter_client/session.py#L749-L862
    def _publish_msg(
        self,
        msg_type: str,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
        **keys: object,
    ) -> None:
        data = {} if data is None else data
        metadata = {} if metadata is None else metadata

        # Add buffers, if any. Note that this is just here for validation of the buffers
        # and the buffer paths should be embedded inside data.
        buffers = [] if buffers is None else buffers
        for idx, buf in enumerate(buffers):
            if not isinstance(buf, memoryview):
                try:
                    view = memoryview(buf)
                    if not view.contiguous:
                        # zmq requires memoryviews to be contiguous
                        raise ValueError(
                            "Buffer %i (%r) is not contiguous" % (idx, buf)
                        )
                except TypeError as e:
                    raise TypeError(
                        "Buffer objects must support the buffer protocol."
                    ) from e

        session = get_current_session()
        if session is None:
            raise RuntimeError(
                "Cannot send an ipywidget messages to the client outside of a Shiny session context."
            )

        # Coalesce state-update comm_msg messages for the same widget within a
        # flush cycle. When multiple reactive effects modify the same widget
        # (e.g., map.remove(old_layer) then map.add(new_layer)), each trait
        # change sends a separate comm_msg. Intermediate states can cause race
        # conditions in widget JS views (e.g., ipyleaflet's LayersControl losing
        # track of layers). Coalescing sends only the final state per trait,
        # similar to ipywidgets' hold_sync().
        if msg_type == "shinywidgets_comm_msg" and data.get("method") == "update":
            pending = _get_pending_updates(session)
            if self.comm_id in pending:
                _merge_pending_update(pending[self.comm_id], data, buffers)
                return

            state = data.get("state") or {}
            buffer_paths = data.get("buffer_paths") or []
            entry: Dict[str, Any] = {
                "comm_id": self.comm_id,
                "data": {
                    "method": "update",
                    "state": dict(state),  # type: ignore[arg-type]
                    "buffer_paths": list(buffer_paths),  # type: ignore[arg-type]
                },
                "metadata": metadata,
                "buffers": list(buffers),
            }
            pending[self.comm_id] = entry

            async def _send_merged(cid: str = self.comm_id) -> None:
                e = pending.pop(cid, None)
                if e is None:
                    return
                msg = dict(
                    content=dict(data=e["data"], comm_id=e["comm_id"]),
                    metadata=e["metadata"],
                    buffers=[b64encode(b).decode("ascii") for b in e["buffers"]],
                    ident="comm-" + e["comm_id"],
                    parent={},
                )
                await session.send_custom_message(
                    "shinywidgets_comm_msg",
                    json_packer(msg),  # type: ignore[arg-type]
                )

            session.on_flushed(_send_merged)
            return

        # Construct the message payload
        msg = dict(
            content=dict(data=data, comm_id=self.comm_id, **keys),
            metadata=metadata,
            # Since Shiny doesn't currently have support for sending binary data, we base64 encode
            # it (and decode whenever it's received).
            buffers=[b64encode(b).decode("ascii") for b in buffers],
            # I don't think this value matters unless we decide we want to sign
            # the message in a similar way to the kernel (since we don't
            # necessarily execute code from the client, it doesn't seem necessary)
            # https://github.com/ipython/ipykernel/blob/378af4b/ipykernel/comm/comm.py#L36-L40
            ident="comm-" + self.comm_id,
            # I don't think we need this info, but I could be wrong
            parent={},  # self.kernel.get_parent("shell")
        )

        msg_txt = json_packer(msg)

        async def _send():
            await session.send_custom_message(msg_type, msg_txt)  # type: ignore

        # N.B., if messages are sent immediately, run_coro_sync() could fail with
        # 'async function yielded control; it did not finish in one iteration.'
        # if executed outside of a reactive context.
        if msg_type == "shinywidgets_comm_close":
            # The primary way widgets are closed are when a new widget is rendered in
            # its place (see render_widget_base). By sending close on_flushed(), we
            # ensure to close the 'old' widget after the new one is created. (avoiding a
            # "flicker" of the old widget being removed before the new one is created)
            session.on_flushed(_send)
        elif msg_type == "shinywidgets_comm_msg":
            # Non-update comm_msg (e.g., method="custom") still needs on_flushed
            # so child widget comm_open messages are sent first.
            session.on_flushed(_send)
        else:
            session.on_flush(_send)

    # This is the method that ipywidgets.widgets.Widget uses to respond to client-side changes
    def on_msg(self, callback: MsgCallback) -> None:
        self._msg_callback = callback

    def on_close(self, callback: MsgCallback) -> None:
        self._close_callback = callback

    def handle_msg(self, msg: Dict[str, object]) -> None:
        if self._msg_callback is not None:
            self._msg_callback(msg)

    def handle_close(self, msg: Dict[str, object]) -> None:
        if self._close_callback is not None:
            self._close_callback(msg)


def _get_pending_updates(session: object) -> Dict[str, Dict[str, Any]]:
    """Get the per-session dict of pending coalesced comm_msg updates."""
    pending = vars(session).get(_PENDING_UPDATES_ATTR)
    if pending is None:
        pending = {}
        vars(session)[_PENDING_UPDATES_ATTR] = pending
    return pending


def _merge_pending_update(
    pending: Dict[str, Any],
    new_data: Dict[str, object],
    new_buffers: List[Any],
) -> None:
    """Merge a new state update into an existing pending entry.

    For each trait key in the new update, the new value replaces the old one.
    Buffer paths belonging to overridden keys are replaced as well.
    """
    new_state: Dict[str, Any] = new_data.get("state", {})  # type: ignore[assignment]
    new_bpaths: List[List[str]] = new_data.get("buffer_paths", [])  # type: ignore[assignment]
    overridden_keys = set(new_state.keys())

    old_bpaths: List[List[str]] = pending["data"]["buffer_paths"]
    old_buffers: List[Any] = pending["buffers"]

    # Keep old buffer entries only for keys NOT being overridden
    filtered_bpaths: List[List[str]] = []
    filtered_buffers: List[Any] = []
    for path, buf in zip(old_bpaths, old_buffers):
        if path[0] not in overridden_keys:
            filtered_bpaths.append(path)
            filtered_buffers.append(buf)

    # Merge state (new values win)
    pending["data"]["state"].update(new_state)
    pending["data"]["buffer_paths"] = filtered_bpaths + new_bpaths
    pending["buffers"] = filtered_buffers + new_buffers


@dataclass
class OrphanedShinyComm:
    """
    A 'mock' `ShinyComm`. It's only purpose is to allow one to get
    the `model_id` (i.e., `comm_id`) of a widget after closing it.
    """

    comm_id: str

    def send(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        pass

    def close(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        pass

    def on_msg(self, callback: MsgCallback) -> None:
        pass
