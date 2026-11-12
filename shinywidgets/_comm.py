import logging
import threading
from base64 import b64encode
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from shiny import Session, ui

if TYPE_CHECKING:
    from ipywidgets import Widget

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
    # True for a comm the browser opened (see from_client()), until a browser
    # message names its widget and so settles what its lifetime follows (see
    # claim_browser_created() in _shinywidgets.py).
    awaiting_owner: bool = False

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
        # Error messages already shown to the user (see notify_client_msg_error)
        self._notified_errors: set[str] = set()
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
        comm._notified_errors = set()
        comm._closed = False
        comm.awaiting_owner = True
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
        self.publish_packed(
            msg_type,
            pack_comm_msg(
                self.comm_id,
                data=data,
                metadata=metadata,
                buffers=buffers,
                parent_header=self._parent_header,
                **keys,
            ),
        )

    def publish_packed(self, msg_type: str, msg_txt: str) -> None:
        """Schedule an already serialized message (see pack_comm_msg())."""
        session = self.session

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
        scope.comm = self
        token = handling_client_msg.set(scope)
        traitlets_level_patch.patch()
        try:
            fn()
        finally:
            self._parent_header = None
            traitlets_level_patch.restore()
            scope.active = False
            # Deferred work shares this scope via its copied context (see
            # ClientMsgScope); release the comm so that work can't pin it
            # (and its widget callbacks and session) after dispatch ends.
            scope.comm = None
            handling_client_msg.reset(token)

    def handle_close(self, msg: Dict[str, object]) -> None:
        """The browser closed this comm: a later close() has nothing to publish."""
        self._closed = True
        self.comm_manager.unregister_comm(self)
        if self._close_callback is not None:
            self._close_callback(msg)


def flush_queued_sends(placeholder: object, comm: "ShinyComm") -> None:
    """
    Deliver, in order, the sends queued on a pre-open placeholder through the
    real comm that replaced it (see OrphanedShinyComm).
    """
    if not isinstance(placeholder, OrphanedShinyComm):
        return
    for msg_txt in placeholder.take_queued_sends():
        comm.publish_packed("shinywidgets_comm_msg", msg_txt)


@dataclass
class OrphanedShinyComm:
    """
    A placeholder `ShinyComm`, standing in for a widget's real comm in one of
    two states:

    * Pre-open (`pending_open=True`): the widget was constructed in a session,
      but its real comm only opens on a later reactive flush (see
      `init_shiny_widget()`). `send()` calls made in the meantime queue up and
      replay, in FIFO order, through the real comm when it opens (see
      `flush_queued_sends()`), so widget methods that send custom messages
      (e.g., k3d's `start_auto_play()`) work even when called while their
      output is still rendering. `widget.send()` reaches the queue too (see
      `queue_sends_until_comm_open()`). A send is serialized right away, by
      the serializer an open comm uses (see `pack_comm_msg()`), so what
      reaches the browser doesn't depend on whether the comm had opened yet.
    * Post-close (`pending_open=False`): the widget was closed (or was never
      meant to open); the placeholder only keeps `model_id` working, and
      sends are no-ops, as they've always been for a closed widget.
    """

    comm_id: str
    # No default: a placeholder left at a close site in the pre-open state
    # would queue every later send for as long as the widget lives
    pending_open: bool
    _queue: List[str] = field(default_factory=lambda: [], repr=False)

    # Cross-library contract: ipywidgets treats a comm with `kernel = None`
    # like a `DummyComm`, and ipyvue >= 3 skips caching templates whose comm
    # was never sent to the frontend.
    kernel = None

    def send(
        self,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
    ) -> None:
        if self.pending_open:
            self._queue.append(
                pack_comm_msg(
                    self.comm_id, data=data, metadata=metadata, buffers=buffers
                )
            )

    def close(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        # Closed before it opened: nothing left to wait for or flush
        self.pending_open = False
        self._queue.clear()

    def on_msg(self, callback: MsgCallback) -> None:
        pass

    def take_queued_sends(self) -> List[str]:
        """
        The (serialized) sends queued while pre-open, in FIFO order. Drains the queue and
        ends the pre-open state (the real comm is taking over), so a later
        `send()` is a no-op here and goes through the real comm instead.
        """
        self.pending_open = False
        queue, self._queue = self._queue, []
        return queue


class SharedShinyComm:
    """
    The comm of a widget that is open in several sessions at once. `send()`
    fans out to the `ShinyComm` of every active session; incoming client
    messages still arrive through each session's own `ShinyComm`, which runs
    the callbacks registered here. A shared widget is never closed.

    Before fanning out, `send()` guards against updates that reference a model
    some session doesn't have (a browser without it waits forever for it): a
    process-global one is opened in the sessions missing it, and any other is
    warned about once per referenced model (see guard_shared_send).
    """

    kernel = "Shiny"

    def __init__(self, comm_id: str) -> None:
        self.comm_id = comm_id
        # Keyed by root session id
        self.comms: Dict[str, ShinyComm] = {}
        # Referenced models a dangling-reference warning was already issued for
        self._dangling_warned: set[str] = set()
        self._msg_callback: Optional[MsgCallback] = None
        self._close_callback: Optional[MsgCallback] = None

    def add(self, comm: ShinyComm) -> None:
        self.comms[comm.session.id] = comm
        if self._msg_callback is not None:
            comm.on_msg(self._msg_callback)
        if self._close_callback is not None:
            comm.on_close(self._close_callback)

    def has_session(self, session_id: str) -> bool:
        return session_id in self.comms

    def drop_session(self, session_id: str) -> None:
        self.comms.pop(session_id, None)

    def sessions_missing(self, model_id: str) -> List[str]:
        """The active fan-out sessions whose browser has no `model_id` model."""
        return [
            session_id
            for session_id, comm in self.comms.items()
            if comm.comm_manager.active and model_id not in comm.comm_manager.comms
        ]

    def dangling_warning_due(self, model_id: str) -> bool:
        """True the first time a dangling reference to `model_id` is reported."""
        if model_id in self._dangling_warned:
            return False
        self._dangling_warned.add(model_id)
        return True

    def send(
        self,
        data: DataType = None,
        metadata: MetadataType = None,
        buffers: BufferType = None,
    ) -> None:
        # _shinywidgets imports this module at module scope, so keep the
        # guard's import function-local (the same trick _render_widget_base
        # uses to import _shinywidgets in the other direction)
        from ._shinywidgets import guard_shared_send

        guard_shared_send(self, data)
        for comm in list(self.comms.values()):
            if comm.comm_manager.active:
                comm.send(data=data, metadata=metadata, buffers=buffers)

    def close(self, *args: object, **kwargs: object) -> None:
        pass

    def on_msg(self, callback: MsgCallback) -> None:
        self._msg_callback = callback
        for comm in self.comms.values():
            comm.on_msg(callback)

    def on_close(self, callback: MsgCallback) -> None:
        self._close_callback = callback
        for comm in self.comms.values():
            comm.on_close(callback)


def pack_comm_msg(
    comm_id: str,
    data: DataType = None,
    metadata: MetadataType = None,
    buffers: BufferType = None,
    parent_header: Optional[object] = None,
    **keys: object,
) -> str:
    """
    Serialize a comm message for the wire.

    The one serializer for every comm message, whether it's published right
    away (ShinyComm) or queued until the comm opens (OrphanedShinyComm).
    """
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
                    raise ValueError("Buffer %i (%r) is not contiguous" % (idx, buf))
            except TypeError as e:
                raise TypeError(
                    "Buffer objects must support the buffer protocol."
                ) from e

    # Construct the message payload
    msg: Dict[str, object] = dict(
        content=dict(data=data, comm_id=comm_id, **keys),
        metadata=metadata,
        # Since Shiny doesn't currently have support for sending binary data, we base64 encode
        # it (and decode whenever it's received).
        buffers=[b64encode(b).decode("ascii") for b in buffers],
        # I don't think this value matters unless we decide we want to sign
        # the message in a similar way to the kernel (since we don't
        # necessarily execute code from the client, it doesn't seem necessary)
        # https://github.com/ipython/ipykernel/blob/378af4b/ipykernel/comm/comm.py#L36-L40
        ident="comm-" + comm_id,
        # I don't think we need this info, but I could be wrong
        parent={},  # self.kernel.get_parent("shell")
    )
    if parent_header is not None:
        msg["parent_header"] = parent_header

    return json_packer(msg)


logger = logging.getLogger("shinywidgets")

traitlets_logger = logging.getLogger("traitlets")


def is_sessionless(w: "Widget") -> bool:
    """
    Is `w` open, but with a comm that isn't one of ours (e.g. the DummyComm of a
    widget constructed outside any session)?
    """
    comm = w.comm
    return comm is not None and not isinstance(
        comm, (ShinyComm, SharedShinyComm, OrphanedShinyComm)
    )


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
    # The comm whose message is being dispatched: how a rerouted callback
    # error finds the session (and per-widget dedup set) for its user-facing
    # notification (see notify_client_msg_error).
    comm: Optional["ShinyComm"] = None


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


# Cap per comm so a callback that fails with ever-changing messages can't
# grow the dedup set (or flood the user with notifications) without bound.
MAX_ERROR_NOTIFICATIONS_PER_COMM = 50


def notify_client_msg_error(comm: ShinyComm, record: logging.LogRecord) -> None:
    """
    Show a sticky browser notification for a widget-callback error that
    ipywidgets swallowed (see ClientMsgErrorFilter): the error already
    reached the server log, but if the failing callback is part of how the
    widget renders, the user's output is otherwise blank with no
    explanation. Each unique message is shown once per widget; repeats only
    go to the server log.
    """
    if record.exc_info is not None and record.exc_info[1] is not None:
        msg = str(record.exc_info[1])
    else:
        msg = record.getMessage()
    notified = comm._notified_errors
    if msg in notified or len(notified) >= MAX_ERROR_NOTIFICATIONS_PER_COMM:
        return
    notified.add(msg)
    session = comm.session
    try:
        if session.app.sanitize_errors:
            msg = session.app.sanitize_error_msg
        ui.notification_show(msg, type="error", duration=None, session=session)
    except Exception:
        logger.exception("Failed to show widget callback error in the browser")


class ClientMsgErrorFilter(logging.Filter):
    """
    Outside IPython, ipywidgets catches exceptions raised by widget callbacks
    (observers, on_click handlers, ...) and logs them to the `traitlets` logger,
    whose only handler is a NullHandler. That NullHandler also stops Python's
    last-resort stderr handler from running, so under a Shiny server they vanish.
    While handling a browser message, move such records to the `shinywidgets`
    logger (dropping the original, so a configured root handler doesn't show
    them twice). Everywhere else, e.g. in Jupyter, `traitlets` logging is untouched.

    A rerouted record is also shown to the user as a sticky error
    notification (deduplicated per widget, see notify_client_msg_error): the
    failing callback often leaves their output blank with no explanation.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        scope = handling_client_msg.get()
        if scope is None or not scope.active or record.levelno < logging.WARNING:
            return True
        logger.error(record.getMessage(), exc_info=record.exc_info)
        if scope.comm is not None:
            notify_client_msg_error(scope.comm, record)
        return False


traitlets_logger.addFilter(ClientMsgErrorFilter())
