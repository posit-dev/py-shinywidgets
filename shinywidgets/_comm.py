import asyncio
import traceback
from base64 import b64encode
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

from shiny import Session, reactive

from ._serialization import json_packer


class ShinyCommManager:
    """One per Shiny session: routes client messages to that session's comms."""

    def __init__(self) -> None:
        self.comms: Dict[str, "ShinyComm"] = {}
        # Set to False when the session ends, so closing leftover widgets
        # doesn't try to publish on a dead connection.
        self.active = True
        # Queued messages are only sent when Shiny flushes, which it does on its
        # own only after client input, invalidate_later(), or an ExtendedTask.
        # Messages published at any other time (from an asyncio task, a timer,
        # a thread) must request a flush themselves, on the session's loop.
        self.loop = running_loop()
        self.undelivered = 0
        self.flush_requested = False
        # asyncio only keeps weak references to tasks
        self.flush_tasks: Set[asyncio.Task[None]] = set()

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

    def publish(self, queue: Callable[[], None]) -> None:
        """Queue a message (via `queue`) and make sure a flush will send it."""
        if self.loop is None:
            # The session's first widget was constructed off the loop's thread.
            self.loop = running_loop()
        loop = self.loop
        if loop is None or not loop.is_running():
            queue()
            return

        def queue_and_request_flush() -> None:
            queue()
            if self.active and not self.flush_requested:
                self.flush_requested = True
                task = loop.create_task(self.flush_undelivered())
                self.flush_tasks.add(task)
                task.add_done_callback(self.flush_done)

        if running_loop() is loop:
            queue_and_request_flush()
            return
        # Session callbacks and the reactive lock belong to the loop's thread.
        try:
            loop.call_soon_threadsafe(queue_and_request_flush)
        except RuntimeError:
            # The loop closed (app shutdown) since the is_running() check.
            queue()

    async def flush_undelivered(self) -> None:
        # Same pattern Shiny uses for invalidate_later() and ExtendedTask. If
        # the lock is held, a flush is underway (Shiny holds it while handling
        # input, through the flush that follows), which usually sends our
        # messages too, in which case there's nothing left to do.
        try:
            async with reactive.lock():
                # Reset first: a message published during this flush may miss it
                # (e.g. once the session has started its on_flushed callbacks), so
                # it must be able to request another one.
                self.flush_requested = False
                if self.undelivered > 0:
                    await reactive.flush()
        except Exception:
            traceback.print_exc()
            raise

    def flush_done(self, task: asyncio.Task[None]) -> None:
        self.flush_tasks.discard(task)
        # A request that never got to reset the flag (e.g., cancelled before
        # acquiring the lock) mustn't block future ones.
        if task.cancelled() or task.exception() is not None:
            self.flush_requested = False


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

        session = self.session
        manager = self.comm_manager
        msg_txt = json_packer(msg)

        async def _send():
            # Session flushes run on the session's loop, so this corrects any
            # loop captured from the wrong thread.
            manager.loop = running_loop()
            try:
                if msg_type == "shinywidgets_comm_close":
                    # The close is sent on_flushed; by then, a replacement widget
                    # may have re-registered this id (e.g., a widget re-created
                    # with an explicit model_id). The id would then belong to the
                    # newer comm, and a close would tell the browser to tear down
                    # the *new* model, so suppress the send when (and only when) a
                    # different comm owns the id at send time. (N.B. close()
                    # unregisters this comm before the send happens, so an
                    # unregistered id must not suppress the send.)
                    owner = manager.comms.get(self.comm_id)
                    if owner is not None and owner is not self:
                        return
                await session.send_custom_message(msg_type, msg_txt)  # type: ignore
            finally:
                manager.undelivered -= 1

        # N.B., if messages are sent immediately, run_coro_sync() could fail with
        # 'async function yielded control; it did not finish in one iteration.'
        # if executed outside of a reactive context.
        def queue() -> None:
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
                # (One gap remains: a child opened partway through a session's
                # flush -- after it started its on_flush callbacks, before its
                # on_flushed ones -- misses that flush, so its comm_open trails
                # the parent's update by one flush. Since publish() requests that
                # next flush right away, that's milliseconds rather than until the
                # next client input.)
                session.on_flushed(_send)
            else:
                session.on_flush(_send)
            manager.undelivered += 1

        manager.publish(queue)

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


def running_loop() -> Optional[asyncio.AbstractEventLoop]:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None
