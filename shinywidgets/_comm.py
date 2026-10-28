import logging
import threading
from base64 import b64encode
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from shiny import Session

from ._serialization import json_packer


class ShinyCommManager:
    """One per Shiny session: routes client messages to that session's comms."""

    def __init__(self) -> None:
        self.comms: Dict[str, "ShinyComm"] = {}
        # Set to False when the session ends, so closing leftover widgets
        # doesn't try to publish on a dead connection.
        self.active = True

    def register_comm(self, comm: "ShinyComm") -> str:
        id = comm.comm_id
        self.comms[id] = comm
        return id

    def unregister_comm(self, comm: "ShinyComm") -> Optional["ShinyComm"]:
        # A newer comm may have since re-registered this id (e.g., a widget
        # re-created with an explicit model_id); only remove the registry
        # entry if it still belongs to this comm.
        if self.comms.get(comm.comm_id) is not comm:
            return None
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

    _msg_callback: Optional[MsgCallback] = None
    _close_callback: Optional[MsgCallback] = None
    _closed: bool = False
    _closed_data: Dict[str, object] = {}
    # The header of the client message being handled, if any. ipywidgets answers
    # a client update with an `echo_update`, and the browser only drops stale
    # echoes if they name the update they answer in `parent_header.msg_id`.
    _parent_header: Optional[object] = None

    def __init__(
        self,
        comm_id: str,
        comm_manager: ShinyCommManager,
        target_name: str,
        session: Session,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
        **keys: object,
    ) -> None:
        self.comm_id = comm_id
        self.comm_manager = comm_manager
        self.target_name = target_name
        self.session = session
        self.open(data=data, metadata=metadata, buffers=buffers, **keys)

    @classmethod
    def from_client(
        cls,
        comm_id: str,
        comm_manager: ShinyCommManager,
        target_name: str,
        session: Session,
    ) -> "ShinyComm":
        """
        A comm the browser opened (its model already exists there), so it's
        registered without publishing a comm_open.
        """
        comm = cls.__new__(cls)
        comm.comm_id = comm_id
        comm.comm_manager = comm_manager
        comm.target_name = target_name
        comm.session = session
        comm._closed = False
        comm_manager.register_comm(comm)
        return comm

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
        if self.comm_manager.active:
            # N.B. the send may be suppressed at send time if a newer comm has
            # re-registered this id by then (see _publish_msg).
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

        # Construct the message payload
        msg: Dict[str, object] = dict(
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
        if self._parent_header is not None:
            msg["parent_header"] = self._parent_header

        session = self.session
        msg_txt = json_packer(msg)

        async def _send():
            if msg_type == "shinywidgets_comm_close":
                # The close is sent on_flushed; by then, a replacement widget
                # may have re-registered this id (e.g., a widget re-created
                # with an explicit model_id). The id would then belong to the
                # newer comm, and a close would tell the browser to tear down
                # the *new* model, so suppress the send when (and only when) a
                # different comm owns the id at send time. (N.B. close()
                # unregisters this comm before the send happens, so an
                # unregistered id must not suppress the send.)
                owner = self.comm_manager.comms.get(self.comm_id)
                if owner is not None and owner is not self:
                    return
            await session.send_custom_message(msg_type, msg_txt)  # type: ignore

        # N.B., if messages are sent immediately, run_coro_sync() could fail with
        # 'async function yielded control; it did not finish in one iteration.'
        # if executed outside of a reactive context.
        if msg_type in ("shinywidgets_comm_close", "shinywidgets_comm_msg"):
            # The primary way widgets are closed are when a new widget is rendered in
            # its place (see render_widget_base). By sending close on_flushed(), we
            # ensure to close the 'old' widget after the new one is created. (avoiding a
            # "flicker" of the old widget being removed before the new one is created)
            #
            # Mutation messages also need to wait until flush is complete so any child
            # widgets introduced by the update have already sent their comm_open
            # messages. Without that ordering, the browser can receive a parent update
            # that references child models it does not know about yet.
            session.on_flushed(_send)
        else:
            session.on_flush(_send)

    # This is the method that ipywidgets.widgets.Widget uses to respond to client-side changes
    def on_msg(self, callback: MsgCallback) -> None:
        self._msg_callback = callback

    def on_close(self, callback: MsgCallback) -> None:
        self._close_callback = callback

    def handle_msg(self, msg: Dict[str, object]) -> None:
        callback = self._msg_callback
        if callback is not None:
            self.dispatch_client_msg(msg, lambda: callback(msg))

    def dispatch_client_msg(
        self, msg: Dict[str, object], fn: Callable[[], None]
    ) -> None:
        """
        Run `fn` as the handling of client message `msg`: ipywidgets' replies
        (e.g. echo_update) name the message in their parent_header, and
        exceptions its callbacks swallow are rerouted to the shinywidgets logger.
        """
        self._parent_header = msg.get("header")
        scope = ClientMsgScope()
        token = handling_client_msg.set(scope)
        traitlets_level_patch.patch()
        try:
            fn()
        finally:
            self._parent_header = None
            traitlets_level_patch.restore()
            scope.active = False
            handling_client_msg.reset(token)

    def handle_close(self, msg: Dict[str, object]) -> None:
        """The browser closed this comm: a later close() has nothing to publish."""
        self._closed = True
        self.comm_manager.unregister_comm(self)
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


logger = logging.getLogger("shinywidgets")

traitlets_logger = logging.getLogger("traitlets")


class ClientMsgScope:
    """
    Tracks whether dispatch of a client message is still in progress.
    `asyncio.create_task()` and `loop.call_soon()` copy the current context,
    so resetting a ContextVar[bool] when dispatch ends would leave deferred
    work rerouting (and dropping) `traitlets` records for the rest of its
    life. Copied contexts share this object, so deactivating it stops
    rerouting in deferred work too.
    """

    active = True


handling_client_msg: ContextVar[Optional[ClientMsgScope]] = ContextVar(
    "shinywidgets_handling_client_msg", default=None
)


def traitlets_is_enabled_for(level: int) -> bool:
    scope = handling_client_msg.get()
    if scope is not None and scope.active and level >= logging.WARNING:
        # Admit the WARNING records ipywidgets logs for callback exceptions
        # even when the configured level would suppress them (e.g. the root
        # logger at ERROR); ClientMsgErrorFilter reroutes them.
        return True
    return logging.Logger.isEnabledFor(traitlets_logger, level)


class TraitletsLevelPatch:
    """
    While a client message is dispatched, patches `traitlets_logger`'s level
    check so ipywidgets' callback-exception records reach ClientMsgErrorFilter
    regardless of the configured level (logger filters only see records that
    pass the level check). Unlike lowering the logger's level, the patched
    check consults the caller's dispatch scope, so records logged outside the
    dispatch -- from other threads, deferred tasks, or descendant loggers
    (whose records bypass this logger's filters) -- keep their configured
    threshold. Counted so overlapping dispatches don't restore the check early.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.count = 0

    def patch(self) -> None:
        with self.lock:
            if self.count == 0:
                # setattr/delattr since pyright forbids method assignment
                setattr(traitlets_logger, "isEnabledFor", traitlets_is_enabled_for)
            self.count += 1

    def restore(self) -> None:
        with self.lock:
            self.count -= 1
            if self.count == 0:
                delattr(traitlets_logger, "isEnabledFor")


traitlets_level_patch = TraitletsLevelPatch()


class ClientMsgErrorFilter(logging.Filter):
    """
    Outside IPython, ipywidgets catches exceptions raised by widget callbacks
    (observers, on_click handlers, ...) and logs them to the `traitlets` logger,
    whose only handler is a NullHandler. That NullHandler also stops Python's
    last-resort stderr handler from running, so under a Shiny server they vanish.
    While handling a browser message, move such records to the `shinywidgets`
    logger (dropping the original, so a configured root handler doesn't show
    them twice). Everywhere else, e.g. in Jupyter, `traitlets` logging is untouched.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        scope = handling_client_msg.get()
        if scope is None or not scope.active or record.levelno < logging.WARNING:
            return True
        logger.error(record.getMessage(), exc_info=record.exc_info)
        return False


traitlets_logger.addFilter(ClientMsgErrorFilter())
