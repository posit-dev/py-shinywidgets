/******************************************************************************
 * Lifecycle identity types.
 *
 * A render generation, a model namespace, a transport epoch, a mount, and a
 * lease are distinct identities; never conflate them. Model/comm IDs include
 * the session namespace and stay stable for the widget's life; every
 * transport and display envelope carries the current epoch.
 ******************************************************************************/

declare const identity: unique symbol;
export type Identity<Name extends string> = string & { readonly [identity]: Name };
export type SessionId = Identity<"session">;
export type ModelNamespace = Identity<"model-namespace">;
export type EpochId = Identity<"transport-epoch">;
export type GenerationId = Identity<"render-generation">;
export type ModelId = Identity<"model">;
export type DisplayOfferId = Identity<"display-offer">;
export type DisplayLeaseId = Identity<"display-lease">;
export type MountId = Identity<"mount">;
export type EventId = Identity<"event">;

export interface EpochIdentity {
  readonly session_id: SessionId;
  readonly model_namespace: ModelNamespace;
  readonly epoch_id: EpochId;
}

export interface WidgetValue extends EpochIdentity {
  readonly version: 1;
  readonly kind: "widget";
  readonly output_id: string;
  readonly generation_id: GenerationId;
  readonly offer_id: DisplayOfferId;
  readonly candidate_lease_id: DisplayLeaseId;
  readonly model_id: ModelId;
  readonly fill: boolean;
  readonly widget_pkg: string;
}

export interface LifecycleSnapshot {
  readonly models: number;
  readonly waiters: number;
  readonly mounts: number;
  readonly views: number;
  readonly tasks: number;
}

export interface DisplayClaim {
  readonly action: "claim";
  readonly event_id: EventId;
  readonly output_id: string;
  readonly offer_id: DisplayOfferId;
  readonly candidate_lease_id: DisplayLeaseId;
  readonly generation_id: GenerationId;
  readonly root_id: ModelId;
  readonly mount_id: MountId;
  readonly claim_seq: number;
}

export interface DisplayRelease {
  readonly action: "release";
  readonly event_id: EventId;
  readonly output_id: string;
  readonly lease_id: DisplayLeaseId;
  readonly mount_id: MountId;
  readonly presentation_removed: true;
  readonly reason: "replaced" | "null" | "error" | "unbound" | "stale";
  readonly cleanup: "complete" | "failed";
}

export interface DisplayCancelClaim {
  readonly action: "cancel-claim";
  readonly event_id: EventId;
  readonly output_id: string;
  readonly mount_id: MountId;
  readonly claim_seq: number;
}

export interface DisplayEvents extends EpochIdentity {
  readonly version: 1;
  readonly events: readonly (DisplayClaim | DisplayRelease | DisplayCancelClaim)[];
}

export interface DisplayResult extends EpochIdentity {
  readonly version: 1;
  readonly event_id: EventId;
  readonly output_id: string;
  readonly mount_id: MountId;
  readonly claim_seq: number;
  readonly outcome:
    | { readonly claimed: DisplayLeaseId }
    | {
        readonly refused:
          | "stale-offer"
          | "stale-generation"
          | "root-closed"
          | "foreign-owner"
          | "superseded"
          | "cancelled"
          | "epoch-retired";
      };
}
