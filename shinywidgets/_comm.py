from base64 import b64encode
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from shiny._utils import run_coro_hybrid
from shiny.session import get_current_session

from ._serialization import json_packer


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
        **keys: object
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
        **keys: object
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
                **keys
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
        **keys: object
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

        session = get_current_session()
        if session is None:
            raise RuntimeError(
                "Cannot send an ipywidget messages to the client outside of a Shiny session context."
            )

        msg_txt = json_packer(msg)

        # In theory, it seems that this send could maybe be async (that we then asyncio.create_task() with),
        # but that might mean that messages are sent out of order, which is not what we want.
        def _send():
            run_coro_hybrid(session.send_custom_message(msg_type, msg_txt))  # type: ignore

        # N.B., if messages are sent immediately, run_coro_sync() could fail with
        # 'async function yielded control; it did not finish in one iteration.'
        # if executed outside of a reactive context.
        if msg_type == "shinywidgets_comm_close":
            # The primary way widgets are closed are when a new widget is rendered in
            # its place (see render_widget_base). By sending close on_flushed(), we
            # ensure to close the 'old' widget after the new one is created. (avoiding a
            # "flicker" of the old widget being removed before the new one is created)
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
