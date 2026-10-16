/******************************************************************************
 * Wire protocol validation.
 *
 * Every transport envelope (comm open/msg/close, frontend send, epoch hello)
 * carries the session ID, model namespace, and transport epoch. Values are
 * parsed as `unknown` and strictly validated before routing; legacy packets
 * (no envelope) are rejected explicitly -- a mixed package/bundle is a
 * useful protocol error, not guessed state.
 ******************************************************************************/

import type {
  DisplayLeaseId,
  DisplayOfferId,
  EpochId,
  EpochIdentity,
  GenerationId,
  ModelId,
  ModelNamespace,
  SessionId,
  WidgetValue,
} from "./types";

export interface CommEnvelope extends EpochIdentity {
  readonly sw: 1;
  readonly msg: Record<string, unknown>;
}

export function parseEpochIdentity(value: unknown): EpochIdentity {
  const packet = asRecord(value, "epoch identity");
  return {
    session_id: asString(packet["session_id"], "session_id") as SessionId,
    model_namespace: asString(
      packet["model_namespace"],
      "model_namespace"
    ) as ModelNamespace,
    epoch_id: asString(packet["epoch_id"], "epoch_id") as EpochId,
  };
}

export function parseEpochHello(value: unknown): EpochIdentity {
  const packet = asRecord(value, "epoch hello");
  if (packet["sw"] !== 1) {
    throw protocolError("epoch hello without version marker");
  }
  return parseEpochIdentity(packet);
}

export function packComm(identity: EpochIdentity, msg: unknown): string {
  return JSON.stringify({
    sw: 1,
    session_id: identity.session_id,
    model_namespace: identity.model_namespace,
    epoch_id: identity.epoch_id,
    msg,
  });
}

export function unpackComm(
  current: EpochIdentity,
  packet: unknown
): Record<string, unknown> {
  const envelope = asRecord(packet, "comm packet");
  if (envelope["sw"] !== 1) {
    throw protocolError(
      "legacy shinywidgets packet (missing the versioned envelope); " +
        "the Python package and its JavaScript bundle are out of sync"
    );
  }
  const identity = parseEpochIdentity(envelope);
  requireCurrentEpoch(current, identity);
  return asRecord(envelope["msg"], "comm packet 'msg'");
}

export function parseWidgetValue(value: unknown): WidgetValue {
  const packet = asRecord(value, "widget value");
  if (packet["version"] !== 1 || packet["kind"] !== "widget") {
    throw protocolError("legacy widget value (missing the versioned envelope)");
  }
  const identity = parseEpochIdentity(packet);
  return {
    ...identity,
    version: 1,
    kind: "widget",
    output_id: asString(packet["output_id"], "output_id"),
    generation_id: asString(packet["generation_id"], "generation_id") as GenerationId,
    offer_id: asString(packet["offer_id"], "offer_id") as DisplayOfferId,
    candidate_lease_id: asString(
      packet["candidate_lease_id"],
      "candidate_lease_id"
    ) as DisplayLeaseId,
    model_id: asString(packet["model_id"], "model_id") as ModelId,
    fill: packet["fill"] === true,
    widget_pkg: asString(packet["widget_pkg"], "widget_pkg"),
  };
}

export function requireCurrentEpoch(
  current: EpochIdentity,
  identity: EpochIdentity
): void {
  if (
    identity.session_id !== current.session_id ||
    identity.model_namespace !== current.model_namespace ||
    identity.epoch_id !== current.epoch_id
  ) {
    throw protocolError(
      "shinywidgets packet for a different session/epoch; " +
        "it can't mutate this connection's widgets"
    );
  }
}

export function protocolError(message: string): Error {
  return new Error(`shinywidgets protocol error: ${message}`);
}

function asRecord(value: unknown, what: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw protocolError(`expected an object for ${what}`);
  }
  return value as Record<string, unknown>;
}

function asString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw protocolError(`expected a non-empty string for '${field}'`);
  }
  return value;
}
