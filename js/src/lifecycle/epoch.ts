/******************************************************************************
 * Document lifecycle controller.
 *
 * Owns the current transport epoch's manager (a fresh owner after every valid
 * new hello; old owners retire permanently), the root mounts of every bound
 * output element, the display-claim/release event ledger, and one document
 * resize handler. Test instrumentation inspects it through read-only
 * snapshots; there is no production global.
 ******************************************************************************/

import { EpochManager } from "./manager";
import type { ModuleLoader } from "./manager";
import { MountScope, RootMount } from "./mount";
import type { WidgetView } from "@jupyter-widgets/base";
import { protocolError } from "./protocol";
import type {
  DisplayCancelClaim,
  DisplayClaim,
  DisplayEvents,
  DisplayLeaseId,
  DisplayRelease,
  DisplayResult,
  EpochIdentity,
  EventId,
  LifecycleSnapshot,
  MountId,
} from "./types";
import { EpochRetiredError } from "./types";

let eventCounter = 0;

export function newEventId(): EventId {
  eventCounter += 1;
  return `event-${Date.now().toString(36)}-${eventCounter}` as EventId;
}

type DisplayEvent = DisplayClaim | DisplayRelease | DisplayCancelClaim;

interface PendingEvent {
  readonly event: DisplayEvent;
  readonly resolve?: (result: DisplayResult) => void;
  readonly reject?: (error: Error) => void;
}

export class WidgetLifecycle {
  private readonly _loader: ModuleLoader;
  private readonly _sendEvents: (packet: DisplayEvents) => void;
  private _epoch: EpochManager | null = null;
  private _epochWaiter: Promise<EpochManager> | null = null;
  private _resolveEpochWaiter: ((manager: EpochManager) => void) | null = null;
  private readonly _mounts = new Map<HTMLElement, RootMount>();
  private readonly _claimSeqByOutput = new Map<string, number>();
  private readonly _pendingEvents = new Map<EventId, PendingEvent>();

  constructor(options: {
    loader: ModuleLoader;
    sendEvents: (packet: DisplayEvents) => void;
  }) {
    this._loader = options.loader;
    this._sendEvents = options.sendEvents;
  }

  get epoch(): EpochManager | null {
    return this._epoch;
  }

  /**
   * The browser learns its epoch only from a server hello (never by reading
   * an output's generation). A valid new hello mints a fresh owner; the old
   * owner's retirement is its own cached task that fresh work never awaits.
   */
  handleEpochHello(identity: EpochIdentity): EpochManager {
    if (
      this._epoch !== null &&
      this._epoch.identity.session_id === identity.session_id &&
      this._epoch.identity.model_namespace === identity.model_namespace &&
      this._epoch.identity.epoch_id === identity.epoch_id
    ) {
      return this._epoch;
    }
    const old = this._epoch;
    const manager = new EpochManager({
      identity,
      loader: this._loader,
    });
    this._epoch = manager;
    if (this._resolveEpochWaiter !== null) {
      this._resolveEpochWaiter(manager);
      this._resolveEpochWaiter = null;
      this._epochWaiter = null;
    }
    if (old !== null) {
      this._rejectPendingEvents(
        new EpochRetiredError("widget transport epoch retired")
      );
      void old.retire();
    }
    return manager;
  }

  handleDisconnected(): void {
    const old = this._epoch;
    this._epoch = null;
    this._claimSeqByOutput.clear();
    this._rejectPendingEvents(
      new EpochRetiredError("widget transport disconnected")
    );
    // Mounts and their identity markers are invalidated synchronously, before
    // any async disposal. No lifecycle inputs are sent after disconnect;
    // server-side session cleanup releases leases independently.
    for (const [el, mount] of this._mounts) {
      delete el.dataset.shinywidgetsModelId;
      void mount.dispose();
    }
    this._mounts.clear();
    if (old !== null) {
      // Synchronous admission retirement; the cleanup task is cached and
      // tracked separately (never awaited from a jQuery callback, and server
      // session cleanup never depends on a browser acknowledgement).
      old.disconnect();
    }
  }

  currentEpoch(): EpochManager {
    if (this._epoch === null) {
      throw protocolError(
        "received widget traffic before the session's epoch hello"
      );
    }
    return this._epoch;
  }

  /**
   * Wait for the session's epoch hello. A render value can legitimately
   * arrive before the hello (the hello is published just before the first
   * comm_open); the candidate task waits outside Shiny's dispatch queue.
   */
  waitForEpoch(): Promise<EpochManager> {
    if (this._epoch !== null) {
      return Promise.resolve(this._epoch);
    }
    if (this._epochWaiter !== null) {
      return this._epochWaiter;
    }
    this._epochWaiter = new Promise<EpochManager>((resolve, reject) => {
      const timer = setTimeout(() => {
        this._epochWaiter = null;
        reject(
          protocolError("timed out waiting for the session's epoch hello")
        );
      }, 30000);
      this._resolveEpochWaiter = (manager) => {
        clearTimeout(timer);
        resolve(manager);
      };
    });
    return this._epochWaiter;
  }

  /**
   * The root mount for an output element. One mount per element/epoch;
   * claim sequences increase strictly per output/epoch (surviving DOM
   * rebind of the same output).
   */
  mountFor(el: HTMLElement, outputId?: string): RootMount {
    let mount = this._mounts.get(el);
    if (mount !== undefined && mount.accepting) {
      return mount;
    }
    if (mount !== undefined) {
      void mount.dispose();
      this._mounts.delete(el);
    }
    const epoch = this._epoch;
    if (epoch === null) {
      throw protocolError(
        "received widget traffic before the session's epoch hello"
      );
    }
    mount = new RootMount(epoch, () => {
      const key = outputId ?? mount!.outputId;
      const next = (this._claimSeqByOutput.get(key) ?? 0) + 1;
      this._claimSeqByOutput.set(key, next);
      return next;
    });
    this._mounts.set(el, mount);
    return mount;
  }

  existingMountFor(el: HTMLElement): RootMount | null {
    return this._mounts.get(el) ?? null;
  }

  /** Read-only access to the accepted presentation view (test assertions). */
  acceptedViewFor(el: HTMLElement): WidgetView | null {
    return this._mounts.get(el)?.acceptedView ?? null;
  }

  forgetMount(el: HTMLElement): void {
    this._mounts.delete(el);
  }

  /**
   * The currently tracked views across every mount (for the single document
   * resize handler).
   */
  *activeViews(): Iterable<WidgetView> {
    for (const mount of this._mounts.values()) {
      yield* mount.walkViews();
    }
  }

  /**
   * Send display events through the pending-event ledger: every send carries
   * all still-pending events, so a transport that coalesces to the newest
   * input value still delivers every operation.
   */
  sendDisplayEvent(event: DisplayEvent, waitForResult: boolean): Promise<DisplayResult> | null {
    const epoch = this._epoch;
    if (epoch === null) {
      return null;
    }
    let promise: Promise<DisplayResult> | null = null;
    let entry: PendingEvent = { event };
    if (waitForResult) {
      promise = new Promise<DisplayResult>((resolve, reject) => {
        entry = { event, resolve, reject };
        this._pendingEvents.set(event.event_id, entry);
      });
    } else {
      this._pendingEvents.set(event.event_id, entry);
    }
    const packet: DisplayEvents = {
      sw: 1,
      ...epoch.identity,
      version: 1,
      events: [...this._pendingEvents.values()].map((pending) => pending.event),
    };
    this._sendEvents(packet);
    return promise;
  }

  /**
   * Handle the server's display-result message: resolve claim waiters and
   * remove acknowledged events from the ledger.
   */
  handleDisplayResult(message: unknown): void {
    const epoch = this._epoch;
    if (epoch === null) {
      return;
    }
    const results = parseDisplayResults(message, epoch.identity);
    for (const result of results) {
      const pending = this._pendingEvents.get(result.event_id);
      if (pending === undefined) {
        continue;
      }
      this._pendingEvents.delete(result.event_id);
      pending.resolve?.(result);
    }
  }

  private _rejectPendingEvents(error: Error): void {
    for (const pending of this._pendingEvents.values()) {
      pending.reject?.(error);
    }
    this._pendingEvents.clear();
  }

  snapshot(): LifecycleSnapshot {
    const epoch = this._epoch;
    const base = epoch?.snapshot() ?? {
      models: 0,
      waiters: 0,
      mounts: 0,
      views: 0,
      tasks: 0,
    };
    return {
      ...base,
      tasks: base.tasks + this._pendingEvents.size,
    };
  }

  /**
   * Read-only mount inspection for test instrumentation.
   */
  mountSnapshot(el: HTMLElement): {
    mounts: number;
    views: number;
    tasks: number;
  } {
    const mount = this._mounts.get(el);
    if (mount === undefined) {
      return { mounts: 0, views: 0, tasks: 0 };
    }
    return mount.snapshot();
  }

  mountIdentity(el: HTMLElement): {
    mount_id: MountId;
    claim_seq: number;
    accepted_lease: DisplayLeaseId | null;
  } | null {
    const mount = this._mounts.get(el);
    if (mount === undefined) {
      return null;
    }
    return {
      mount_id: mount.mountId,
      claim_seq: mount.claimSeq,
      accepted_lease: mount.acceptedLease,
    };
  }
}

function parseDisplayResults(
  message: unknown,
  identity: EpochIdentity
): DisplayResult[] {
  const packet = message as Record<string, unknown>;
  if (
    typeof packet !== "object" ||
    packet === null ||
    packet["sw"] !== 1 ||
    packet["session_id"] !== identity.session_id ||
    packet["model_namespace"] !== identity.model_namespace ||
    packet["epoch_id"] !== identity.epoch_id
  ) {
    throw protocolError("display result for a different session/epoch");
  }
  const results = packet["results"];
  if (!Array.isArray(results)) {
    throw protocolError("display result packet has no results array");
  }
  return results as DisplayResult[];
}
