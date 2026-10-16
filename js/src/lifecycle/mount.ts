/******************************************************************************
 * Presentation ownership.
 *
 * A MountScope owns the views, observers, timers, and in-flight tasks of one
 * presentation (a root output binding or a nested MIME rendering). Disposal
 * invalidates admission synchronously and joins one cached disposal promise;
 * disposing a mount never closes a session-retained shared *model*.
 ******************************************************************************/

import type { WidgetView } from "@jupyter-widgets/base";
import type { EpochManager } from "./manager";
import type {
  DisplayLeaseId,
  DisplayOfferId,
  GenerationId,
  ModelId,
  MountId,
} from "./types";
import { EpochRetiredError } from "./types";

let mountCounter = 0;

function newMountId(): MountId {
  mountCounter += 1;
  return `mount-${Date.now().toString(36)}-${mountCounter}` as MountId;
}

export interface MountSnapshot {
  mounts: number;
  views: number;
  tasks: number;
}

export class MountScope {
  readonly mountId: MountId;
  readonly epoch: EpochManager;
  private readonly _parent: MountScope | null = null;
  private readonly _children = new Set<MountScope>();
  private readonly _views = new Set<WidgetView>();
  private readonly _cleanups = new Set<() => void | Promise<void>>();
  private readonly _tasks = new Set<Promise<unknown>>();
  private _accepting = true;
  private _disposal: Promise<void> | null = null;

  constructor(epoch: EpochManager, parent: MountScope | null = null) {
    this.mountId = newMountId();
    this.epoch = epoch;
    this._parent = parent;
    if (parent !== null) {
      parent._children.add(this);
    }
  }

  get accepting(): boolean {
    return this._accepting && !this.epoch.retired;
  }

  checkAdmission(operation: string): void {
    if (!this.accepting) {
      throw new EpochRetiredError(
        `Widget presentation mount is retired; ${operation} is no longer allowed`
      );
    }
  }

  childScope(): MountScope {
    this.checkAdmission("childScope");
    return new MountScope(this.epoch, this);
  }

  trackView(view: WidgetView): void {
    this._views.add(view);
  }

  untrackView(view: WidgetView): void {
    this._views.delete(view);
  }

  get views(): ReadonlySet<WidgetView> {
    return this._views;
  }

  *walkViews(): Iterable<WidgetView> {
    yield* this._views;
    for (const child of this._children) {
      yield* child.walkViews();
    }
  }

  /**
   * Track an admitted task. The task's continuations must check mount/epoch
   * admission before mutating any presentation state.
   */
  trackTask<T>(task: Promise<T>): Promise<T> {
    this._tasks.add(task);
    const done = () => {
      this._tasks.delete(task);
    };
    task.then(done, done);
    return task;
  }

  /**
   * Register owned cleanup (observers, timers, listeners, package-specific
   * teardown adapters) to run at disposal.
   */
  onDispose(cleanup: () => void | Promise<void>): void {
    if (this._disposal !== null || !this._accepting) {
      // A late registration to a retired mount runs immediately.
      void cleanup();
      return;
    }
    this._cleanups.add(cleanup);
  }

  /**
   * Invalidate admission synchronously, then run owned cleanup and dispose
   * tracked views through their public lifecycle methods. Repeated disposal
   * joins the same promise.
   */
  dispose(): Promise<void> {
    if (this._disposal !== null) {
      return this._disposal;
    }
    this._accepting = false;
    this._disposal = this._doDispose();
    return this._disposal;
  }

  private async _doDispose(): Promise<void> {
    this._parent?._children.delete(this);
    const children = [...this._children];
    this._children.clear();
    const errors: unknown[] = [];
    // Owned cleanup (observers/timers/adapters) runs before view disposal so
    // late callbacks can't touch views that are going away.
    for (const cleanup of this._cleanups) {
      try {
        await cleanup();
      } catch (error) {
        errors.push(error);
      }
    }
    this._cleanups.clear();
    // Dispose child views before their parents (reverse tracking order): a
    // parent's teardown can remove a whole DOM subtree (e.g., ipyleaflet
    // destroys the map container), which would otherwise break later
    // detaches. An already-removed presentation satisfies the disposal goal.
    for (const view of [...this._views].reverse()) {
      try {
        view.remove();
      } catch (error) {
        if (error instanceof Error && error.message === "Widget is not attached.") {
          continue;
        }
        errors.push(error);
      }
    }
    this._views.clear();
    await Promise.all(children.map((child) => child.dispose()));
    if (errors.length > 0) {
      throw new Error(
        `Errors while disposing widget presentation: ${errors
          .map((e) => String(e))
          .join("; ")}`
      );
    }
  }

  snapshot(): MountSnapshot {
    let snapshot: MountSnapshot = {
      mounts: 1,
      views: this._views.size,
      tasks: this._tasks.size,
    };
    for (const child of this._children) {
      const nested = child.snapshot();
      snapshot = {
        mounts: snapshot.mounts + nested.mounts,
        views: snapshot.views + nested.views,
        tasks: snapshot.tasks + nested.tasks,
      };
    }
    return snapshot;
  }
}

/**
 * A root output mount: owns the accepted presentation and the in-flight
 * candidate for one output element, and allocates strictly increasing claim
 * sequences per output/epoch (surviving DOM rebind).
 */
export class RootMount extends MountScope {
  outputId: string = "";
  private readonly _nextSeq: () => number;
  private _claimSeq = 0;
  private _candidate: MountScope | null = null;
  private _acceptedScope: MountScope | null = null;

  constructor(epoch: EpochManager, nextSeq: () => number) {
    super(epoch);
    this._nextSeq = nextSeq;
  }
  acceptedOffer: DisplayOfferId | null = null;
  acceptedLease: DisplayLeaseId | null = null;
  acceptedGeneration: GenerationId | null = null;
  acceptedRoot: ModelId | null = null;
  acceptedView: WidgetView | null = null;

  nextClaimSeq(): number {
    // Allocated by the document controller per output/epoch, so sequences
    // increase strictly even across DOM rebind of the same output.
    this._claimSeq = this._nextSeq();
    return this._claimSeq;
  }

  get claimSeq(): number {
    return this._claimSeq;
  }

  /**
   * The current candidate presentation (an in-flight replacement). Starting
   * a new candidate retires the previous candidate's admission, but never
   * touches the accepted presentation.
   */
  startCandidate(): MountScope {
    if (this._candidate !== null) {
      void this._candidate.dispose();
    }
    this.checkAdmission("startCandidate");
    this._candidate = this.childScope();
    return this._candidate;
  }

  get candidate(): MountScope | null {
    return this._candidate;
  }

  retireCandidate(candidate: MountScope): void {
    if (this._candidate === candidate) {
      this._candidate = null;
    }
    void candidate.dispose();
  }

  /**
   * The candidate became the accepted presentation. The caller has attached
   * its view and records the new offer/lease identity here.
   */
  acceptCandidate(
    candidate: MountScope,
    value: {
      offer_id: DisplayOfferId;
      generation_id: GenerationId;
      model_id: ModelId;
    },
    leaseId: DisplayLeaseId,
    view: WidgetView
  ): void {
    if (this._candidate === candidate) {
      this._candidate = null;
    }
    this._acceptedScope = candidate;
    this.acceptedOffer = value.offer_id;
    this.acceptedGeneration = value.generation_id;
    this.acceptedRoot = value.model_id;
    this.acceptedLease = leaseId;
    this.acceptedView = view;
  }

  /**
   * Dispose the accepted presentation's views (through their mount) without
   * touching any in-flight candidate.
   */
  async retireAccepted(): Promise<void> {
    const scope = this._acceptedScope;
    this._acceptedScope = null;
    this.acceptedOffer = null;
    this.acceptedGeneration = null;
    this.acceptedRoot = null;
    this.acceptedLease = null;
    this.acceptedView = null;
    if (scope !== null) {
      await scope.dispose();
    }
  }

  /**
   * Retire the candidate and the accepted presentation (null/error/unbind
   * paths). Returns the accepted lease, which the caller releases only after
   * this presentation removal has completed.
   */
  async retirePresentation(): Promise<DisplayLeaseId | null> {
    const candidate = this._candidate;
    this._candidate = null;
    if (candidate !== null) {
      void candidate.dispose();
    }
    const lease = this.acceptedLease;
    await this.retireAccepted();
    return lease;
  }
}
