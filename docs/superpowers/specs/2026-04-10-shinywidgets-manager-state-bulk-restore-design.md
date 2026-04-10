# Shinywidgets Manager-State Bulk Restore Design

## Summary

Replace the current per-widget initial `comm_open` flow with a manager-state-first restore path modeled after `ipywidgets` bulk state restoration. The new path should materialize an entire widget dependency graph in the browser before rendering the root view, while preserving the existing live `comm_msg` and `comm_close` behavior for the restored models. The existing per-model `comm_open` path should remain part of live widget semantics for models introduced after initial restore. In v1, the old "everything initializes through per-model open" path should remain available only as an explicit opt-out and as a server-side escape hatch when bulk payload generation fails. Version 1 should also stay conservative about model ownership: bulk restore is for creating a fresh browser-side graph for the current output render, not for generically merging into already-live model ids.

## Problem

`shinywidgets` currently initializes frontend widget models by sending one custom message per widget model. That works for small graphs, but it is a poor fit for widget trees with many cross-model references.

In `ipyleaflet`, a `Map` may refer to a `LayerGroup`, which may refer to hundreds or thousands of `CircleMarker` models. Frontend deserialization uses `unpack_models`, which assumes that the widget manager can already resolve every referenced model id. With the current Shiny protocol, those models arrive incrementally, so parent models can be deserialized before all referenced child models have been registered. That creates missing-model races and scales poorly because large graphs produce large numbers of independent open messages.

The short-term recursive Python fix works by forcing child-before-parent ordering, but it encodes the invariant manually. The longer-term design should instead use the same conceptual model that `ipywidgets` uses for bulk restoration: register the whole graph with the widget manager, then render views from that registered graph.

## Goals

- Align initial widget graph materialization more closely with `ipywidgets` manager-state restoration.
- Eliminate parent-before-child model registration races during initial render and rerender.
- Reduce message count for large widget graphs.
- Preserve live comm semantics for models created through the bulk restore path.
- Give `renderValue()` a deterministic way to wait for the correct restore to finish.
- Bound failure impact so one failed output restore does not leave unrelated outputs in a bad state.
- Preserve the existing live mutation and teardown behavior unless there is a clear need to change it.
- Provide an explicit opt-out and a server-side escape hatch to the current per-model open path while the bulk path matures.

## Non-Goals

- Replacing the existing `comm_msg` mutation path.
- Replacing the existing `comm_close` teardown path.
- Replacing live per-model `comm_open` for models created after the initial graph materialization.
- Designing chunked bulk restore in the first iteration.
- Designing a multi-output transactional restore in the first iteration.
- Designing cross-output graph deduplication in the first iteration.
- Designing automatic size-based fallback in the first iteration.
- Designing generic browser-side model-id reuse during bulk restore in the first iteration.
- Optimizing every widget workload immediately; correctness and architectural alignment come first.

## Background Reference

`ipywidgets` uses two relevant patterns:

1. Normal live widget creation still uses one `comm_open` per model.
2. Bulk restoration and embedding use manager state plus `manager.set_state(...)`.

The important property of the manager-state path is not just batching. It is that `new_model(...)` registers model promises synchronously before deserialization completes, so references between models are safe during restore. That is the core behavior this design wants to reuse.

## Hard Evidence From `ipywidgets` And `ipyleaflet`

This design is not based on a generic intuition that “batching sounds cleaner”. It is based on specific behavior in upstream `ipywidgets` and `ipyleaflet`.

### Evidence 1: `ipywidgets` still supports live per-model `comm_open`

Kernel-side widget construction in `ipywidgets` still opens one comm per model. See [widget.py](../ipywidgets/python/ipywidgets/ipywidgets/widgets/widget.py) around the `open()` implementation at lines 522-535 and the frontend-side `handle_comm_open(...)` path in [manager-base.ts](../ipywidgets/packages/base-manager/src/manager-base.ts) at lines 238-260.

That means a per-model protocol is normal in live Jupyter.

### Evidence 2: `ipywidgets` also has a first-class bulk restore path

`ipywidgets` exposes full manager state from Python in [widget.py](../ipywidgets/python/ipywidgets/ipywidgets/widgets/widget.py) at lines 433-461, and exposes a control-comm `request_states` / `update_states` path in the same file at lines 381-407.

On the frontend, `ipywidgets` restores bulk state by calling `manager.set_state(...)` in [libembed.ts](../ipywidgets/packages/html-manager/src/libembed.ts) at lines 74-80.

This is the closest upstream analog to what `shinywidgets` needs when it has to materialize a large widget graph all at once.

### Evidence 3: `ipywidgets` explicitly relies on synchronous model registration during restore

In [manager-base.ts](../ipywidgets/packages/base-manager/src/manager-base.ts), `new_model(...)` registers the model promise before its first `await`; see lines 355-372.

`set_state(...)` then documents the key invariant directly at lines 671-680:

- any `new_model` call with state registers the model promise synchronously
- deserialization and state application happen asynchronously afterward
- without those assumptions, references could be resolved before the target model exists

This is the strongest upstream evidence that the real problem is model-registration semantics, not just view timing.

### Evidence 4: `ipywidgets` bulk restore already has its own fallback story

`ipywidgets` first tries the control-comm `request_states` path in [manager-base.ts](../ipywidgets/packages/base-manager/src/manager-base.ts) at lines 386-431, and falls back to per-model state retrieval in `_loadFromKernelModels()` at lines 500-565.

This is directly relevant to the proposed `shinywidgets` design, because it shows that upstream already treats bulk restore as the preferred path and a more incremental model-loading path as fallback. However, `ipywidgets` is talking to a kernel over comm channels that support a richer request/reply recovery story than `shinywidgets` currently has.

The upstream schema also explicitly warns that `update_states` messages may be large enough to be dropped and recommends fallback behavior; see [messages.md](../ipywidgets/packages/schema/messages.md) at lines 374-406, especially line 406.

For `shinywidgets`, that warning is useful as future-proofing, but it should not by itself force a v1 size-based fallback requirement. Local Shiny defaults are already materially larger than the measured heavy repro payload, and the main architectural problem here is registration semantics, not transport size.

### Evidence 5: `ipyleaflet` depends on `unpack_models`

`ipywidgets` resolves serialized `IPY_MODEL_*` references through `unpack_models(...)` in [widget.ts](../ipywidgets/packages/base/src/widget.ts) at lines 40-58.

`ipyleaflet` uses that exact mechanism in its model serializers:

- `Map.layers`, `controls`, and style traits in [Map.ts](../ipyleaflet/python/jupyter_leaflet/src/Map.ts) at lines 177-183
- `LayerGroup.layers` in [LayerGroup.ts](../ipyleaflet/python/jupyter_leaflet/src/layers/LayerGroup.ts) at lines 20-22

So when `ipyleaflet` restores a map or layer group, it is depending on the manager already being able to resolve every referenced child model id.

### Evidence 6: `shinywidgets` currently diverges at exactly that point

Today, `shinywidgets` still schedules per-widget initial opens during `init_shiny_widget(...)` in [shinywidgets/_shinywidgets.py](/Users/cpsievert/github/py-shinywidgets/shinywidgets/_shinywidgets.py) at lines 117-130, and transport still sends one `shinywidgets_comm_open` custom message at a time in [shinywidgets/_comm.py](/Users/cpsievert/github/py-shinywidgets/shinywidgets/_comm.py) at lines 55-71 and 144-169.

The current recursive workaround in [shinywidgets/_shinywidgets.py](/Users/cpsievert/github/py-shinywidgets/shinywidgets/_shinywidgets.py) at lines 201-223 is effectively compensating for the fact that `shinywidgets` has the per-model open path but not the upstream-style bulk graph registration path.

### Evidence 7: the `ipyleaflet` scale issue is concrete

Local measurement on 2026-04-10 for the heavy repro shape:

```bash
/Users/cpsievert/github/py-shinywidgets/.venv/bin/python - <<'PY'
import json
import ipyleaflet as L
from ipywidgets.embed import dependency_state
from ipywidgets import Widget
from ipywidgets.widgets.widget import _remove_buffers

POINTS = [(63.1016, -151.5129)] * 1000
markers = [L.CircleMarker(location=point, radius=8) for point in POINTS]
group = L.LayerGroup(layers=markers)
m = L.Map(center=(POINTS[0][0], POINTS[0][1]), zoom=2)
m.add(group)

state = {'version_major': 2, 'version_minor': 0, 'state': dependency_state(m, drop_defaults=False)}
blob = json.dumps(state)
widgets = list(Widget.widgets.values())
total = 0
for w in widgets:
    s, bp, bufs = _remove_buffers(w.get_state())
    total += len(json.dumps({'state': s, 'buffer_paths': bp}).encode())

print('models', len(state['state']))
print('manager_state_json_bytes', len(blob.encode()))
print('sum_per_widget_state_payload_bytes', total)
print('group_layers_refs', len(_remove_buffers(group.get_state())[0]['layers']))
PY
```

Observed output:

- `models 1009`
- `manager_state_json_bytes 1078566`
- `sum_per_widget_state_payload_bytes 949391`
- `group_layers_refs 1000`

Implications:

- the 1,000-marker case really does create a graph with 1,009 widget models
- `LayerGroup` alone references 1,000 child models
- a bulk manager-state payload is only modestly larger than the summed per-widget state payloads
- the main likely gain from bulk restore is lower message count and stronger registration semantics, not a dramatic byte reduction

## Current State Versus Upstream Pattern

| Concern | `ipywidgets` upstream | `shinywidgets` current state | Gap |
|---|---|---|---|
| Live model creation | One `comm_open` per model | One `shinywidgets_comm_open` per model | Similar |
| Bulk graph restore | `request_states` / `update_states` / `manager.set_state(...)` | No equivalent first-class path | Missing |
| Cross-model restore invariant | Synchronous `register_model(...)` before async deserialization | Manual child-before-parent recursion | Divergent |
| Large graph fallback | Bulk path falls back to incremental loading when upstream transport supports it | No bulk path yet; only incremental path exists | Missing, but not required as an automatic size policy in v1 |
| `ipyleaflet` compatibility model | `unpack_models` expects manager to resolve refs during restore | Incremental open path can lag referenced children | Problem source |

## Proposed Architecture

Split widget traffic into two phases:

### 1. Graph Materialization

When Shiny needs to introduce a root widget tree to the browser, the server will:

- compute the dependency closure for the root widget or widgets
- serialize that closure in a manager-state-like payload
- send one bulk custom message per Shiny output
- let the browser restore all models through a Shiny-specific manager-state restore helper that preserves live comm wiring
- render the requested root view only after restore succeeds

This replaces the current behavior where every widget independently schedules a `comm_open`.

### 2. Live Synchronization

After the graph is registered in the frontend manager:

- models introduced later through normal live widget behavior continue to use per-model `comm_open`
- incremental state changes continue to use `comm_msg`
- widget teardown continues to use `comm_close`

This keeps the protocol change focused on the initial graph creation problem instead of trying to redesign the entire live comm lifecycle.

## Protocol Design

Introduce a new Shiny custom message for bulk graph restore. The exact name can be decided during implementation, but it should be conceptually similar to:

- `shinywidgets_manager_state`

The payload should follow the `ipywidgets` manager-state shape closely:

```json
{
  "version_major": 2,
  "version_minor": 0,
  "state": {
    "<model-id>": {
      "model_name": "...",
      "model_module": "...",
      "model_module_version": "...",
      "state": { "...": "..." },
      "buffers": [
        {
          "path": ["..."],
          "encoding": "base64",
          "data": "..."
        }
      ]
    }
  },
  "output_id": "<shiny-output-id>",
  "restore_id": "<opaque-restore-token>",
  "root_model_id": "<root-model-id>",
  "html_deps": ["..."]
}
```

Notes:

- `state` should be manager-state compatible enough to drive the same model-registration and deserialization flow as `ipywidgets` bulk restore.
- `output_id` identifies the Shiny output instance that owns this restore.
- `restore_id` lets the frontend coordinate `renderValue()` with the correct in-flight restore.
- `root_model_id` identifies the widget model that should be rendered for the output after restore.
- `html_deps` remains Shiny-specific and should be rendered before restore.
- Buffers should use the same base64 transport approach already used by `shinywidgets`.
- Version 1 should send one payload per output, not one payload shared across multiple outputs.

The corresponding Shiny render payload delivered to `renderValue()` should also be extended explicitly. Instead of only sending `model_id` plus layout metadata, Version 1 should send:

```json
{
  "model_id": "<root-model-id>",
  "root_model_id": "<root-model-id>",
  "output_id": "<shiny-output-id>",
  "restore_id": "<opaque-restore-token>",
  "fill": true
}
```

Notes:

- `model_id` may remain for backward compatibility and should equal `root_model_id` in the bulk path
- `renderValue()` should consume `output_id`, `restore_id`, and `root_model_id` from this payload rather than discovering them indirectly
- Version 1 should prefer explicit render payload fields over hidden global bookkeeping

## Server-Side Design

### Dependency Closure

The server should build the full graph for a root widget tree by traversing serialized state references, not live Python object attributes alone.

Rationale:

- frontend deserialization resolves `IPY_MODEL_*` references from serialized state
- serialized state is the truth for what the frontend must be able to resolve
- this matches the actual problem better than Python-only trait introspection

The closure builder should:

- start from one or more root widgets
- call any required pre-serialization hooks such as `_repr_mimebundle_()` before `get_state()`
- serialize each widget state
- collect any `IPY_MODEL_*` references recursively
- deduplicate shared models
- preserve buffer paths and buffers in manager-state format
- collect Shiny-side `html_deps` from every widget instance included in the final closure, not just from the root widget

Version 1 should not use `ipywidgets.embed.dependency_state(...)` as the primary closure builder. Upstream documents that helper as incomplete for nested structures, which is too risky for a correctness-driven restore path.

This means the current `_find_widget_model_refs(...)` style traversal is closer to the desired long-term design than the simpler `ipywidgets.embed.dependency_state(...)` helper.

The dependency-closure algorithm therefore has two related outputs:

- manager-state entries for every widget model id that frontend deserialization may resolve
- the union of Shiny-rendered HTML dependencies needed to load those models' frontend classes

Those two outputs come from related but not identical sources. Serialized widget state is the source of truth for model-id reachability, while live widget instances remain the source of truth for Shiny-specific dependency objects such as the `require.config(...)` wrappers currently attached during per-model open.

### Flush Integration

Instead of each widget independently opening a comm during initialization, server-side widget initialization should:

- register widgets as pending members of a graph that needs initial materialization
- defer actual transport until the appropriate Shiny flush boundary
- emit one bulk manager-state message for the graph instead of many per-widget open messages

The output-rendering path should be the main owner of graph materialization, because that is where Shiny already knows which root widget belongs to which output slot.

Version 1 should keep ownership narrow and explicit:

- the render output path owns graph collection for its current root widget
- the render output path owns `restore_id` generation for that output render
- the render output path decides whether bulk restore or the legacy escape hatch is used before any initial transport is emitted
- the widget construction hook remains responsible for ordinary live widget setup outside that initial bulk-owned path

The design does not need to freeze exact helper names yet, but it should preserve that separation of responsibilities so graph materialization is driven by output lifecycle, not by incidental widget construction order.

To keep the escape hatch viable, ownership transfer from "legacy per-model open pending" to "bulk-owned initial materialization" must happen only after the server has successfully built the complete bulk payload for that render. A safe v1 sequencing rule is:

1. widgets are constructed in their existing legacy-open-pending state
2. the output render path attempts full bulk payload generation before any initial transport is emitted
3. only after payload generation succeeds does the output render path mark that closure as bulk-owned and suppress the legacy scheduled opens for those widgets
4. if payload generation fails before that transfer, the server leaves the original per-model open scheduling intact and uses the legacy path

This avoids a correctness hole where the design suppresses legacy initial opens but then has no authoritative owner left to emit the fallback transport.

### Initial Restore Versus Later Live Creation

Version 1 needs a hard boundary between:

- initial graph materialization for the current output root
- later live model creation after that restore has completed

The bulk restore path replaces only the initial materialization of the output's dependency closure. It does not replace normal live per-model creation for widgets introduced later by post-restore behavior.

Examples of cases that should still use per-model `comm_open` after the initial restore:

- a user interaction causes Python to create a brand-new child widget model
- a later `comm_msg` update introduces references to newly created child models
- a widget library lazily creates additional models after the root view already exists

This rule is required for correctness because upstream `ipywidgets` still uses one `comm_open` per model for live creation, and the existing `shinywidgets` update path already depends on child models being opened before parent updates that reference them.

### Same Python Widget Instance Across Rerenders

The design should also be explicit about an important boundary case: a later output rerender may return the exact same Python widget instance that was returned earlier, rather than constructing a fresh widget tree.

Version 1 should not treat that case as a normal bulk-restore reuse path. Re-rendering the same Python widget instance can imply that the browser may still hold old manager state, old deferred closes, or other lifecycle bookkeeping tied to the prior render. Until the implementation defines generation-aware close suppression or equivalent stale-close protection, v1 should treat this shape conservatively:

- if the rerender produces a fresh widget graph with fresh browser-side model ids, bulk restore may proceed
- if the rerender would require reusing already-registered browser model ids from a prior render of that same Python widget instance, the implementation should use the legacy escape hatch or raise the explicitly documented restore error

This keeps the v1 contract aligned with the rest of the spec: bulk restore creates the browser graph for the current output render; it does not yet define full reuse semantics for still-live or ambiguously-live model ids.

### Suppressing Legacy Initial Auto-Open

The current `init_shiny_widget(...)` hook schedules a per-widget initial open automatically. Version 1 must define how that path is suppressed for widgets that belong to a bulk-restored output, otherwise the system risks double initialization of the same model ids.

The design requirement is:

- widgets participating in bulk initial materialization must be marked before the legacy scheduled open fires
- the legacy scheduled open effect must no-op for widgets whose initial graph ownership has been transferred to the bulk restore path
- widgets created outside a bulk-restored output, or created later after initial restore, must continue to use the existing per-model open flow

The exact mechanism can be decided during implementation, but the design should treat this suppression rule as mandatory, not incidental.

Version 1 should additionally make the fallback transition explicit:

- bulk ownership is transferred only after successful bulk payload generation
- if payload generation fails before ownership transfer, the already-scheduled legacy per-model opens remain active
- if the implementation ever needs to suppress first and decide later, it must also define an explicit server-side helper that can emit the legacy per-model graph materialization for those suppressed widgets before the flush completes

Version 1 should restore one output at a time:

- each render output computes and emits its own graph payload
- each payload carries exactly one `output_id`, one `restore_id`, and one `root_model_id`
- the implementation should not try to batch multiple outputs into one restore transaction

This keeps failure handling and render synchronization tractable in the first iteration.

### Output Ownership Versus Global Manager State

The browser still has one global widget manager, even though bulk restore in v1 is scoped to one output at a time.

That means the implementation should treat these as separate concerns:

- restore ownership and stale-render coordination are per-output
- model registration, lookup, and live comm routing are global

The spec should not assume that a model id belongs exclusively to one output forever. However, v1 should remain conservative about what it will actually support during bulk restore:

- models newly created during a restore are attributed to that restore for rollback purposes
- the output only owns rendering of `root_model_id`
- shared or pre-existing models remain global manager state and should not be aggressively deleted just because one output rerendered

For version 1, bulk restore should only create model ids that are not already registered in the browser manager for that render. Generic "existing model id already live in the manager, now merge or reuse it during bulk restore" semantics should be treated as out of scope until the implementation also defines how to prevent stale deferred closes from tearing down the reused model.

This is important because the highest-risk correctness bugs in this design are stale-output rendering, accidental recreation of already-registered models, over-eager cleanup of global state, and silent state divergence between server and browser after a failed restore.

### Backward-Compatible Escape Hatch

Keep the existing "initial materialization through per-model open" path available as an escape hatch, not as a co-equal design.

Version 1 should support these fallback cases:

- an explicit development flag disables bulk restore
- server-side bulk payload generation fails before any bulk message is sent
- the implementation detects an initial-render shape that would require underspecified browser-side model reuse instead of creating a fresh graph

Version 1 should not include an automatic size-based fallback heuristic. The measured `ipyleaflet` many-marker case is already about 1.08 MB of manager-state JSON, which is well below Shiny's default local websocket size setting, and a conservative heuristic would route exactly the workloads that need this design back through the legacy path.

Version 1 also should not claim automatic fallback after a frontend restore failure unless the implementation adds an explicit client->server recovery protocol. Without such a protocol, the frontend can surface the error and reject the restore, but it cannot silently re-request a server-side per-model open path.

Instead of automatic size fallback, v1 should record payload size telemetry and benchmark data so a later chunking or recovery design can be based on real workloads.

## Frontend Design

Add a new handler for the bulk manager-state message. It should:

1. parse the message
2. render `html_deps`
3. create a restore promise keyed by `restore_id`
4. restore all models through a Shiny-specific helper that mirrors the important ordering guarantees of `manager.set_state(...)` while attaching real `ShinyComm` instances to restored models
5. resolve or reject the restore promise
6. make the restored root model available for normal Shiny output rendering

`renderValue()` should not assume that the restore is already complete just because the custom message has been delivered. The implementation should first verify whether Shiny's existing websocket/task-queue ordering is already sufficient to serialize "bulk restore custom message, then output value" for the common case. The current `shinywidgets` transport already relies on Shiny flush ordering: initial opens are sent on `on_flush`, output values are delivered in the flush payload, and later live `comm_msg` / `comm_close` traffic waits until `on_flushed`. Version 1 should therefore treat Shiny's existing ordering as the base sequencing mechanism and use explicit restore tokens primarily to reject stale rerender completions, not as a second parallel ordering system for the normal case. If the implementation keeps explicit restore tokens, `renderValue()` should:

1. read `output_id`, `restore_id`, and `root_model_id` from the render payload
2. await the restore promise for that specific `restore_id`
3. verify that the resolved restore still matches the most recent restore requested for that output
4. only then call `manager.get_model(root_model_id)` and create the view

The browser should not try to partially render a root widget view before graph restore completes. Correct full-graph registration is more important than earlier but incomplete paint.

### Frontend Restore Helper

Do not call `HTMLManager.set_state(...)` directly and assume the existing live protocol will keep working. In `html-manager`, restored models are built against placeholder comms. `shinywidgets` needs restored models to keep using live `comm_msg`, `comm_close`, and later live per-model `comm_open`.

Add a Shiny-specific restore helper on the frontend manager, conceptually similar to:

- `restoreManagerState(state, { outputId, restoreId, rootModelId })`

This helper should:

- iterate through the manager-state entries in any order, relying on the same synchronous `register_model(...)` before async deserialization invariant that upstream `set_state(...)` relies on
- branch on whether the model already exists in the global manager
- for a new model id:
  - create a `ShinyComm`
  - register that comm in the browser-side lookup used by the existing `shinywidgets_comm_msg` and `shinywidgets_comm_close` handlers
  - pass the serialized model state into `new_model(...)` so that cross-model references resolve through already-registered model promises
- for an existing model id:
  - do not silently merge, recreate, or overwrite comm routing in v1
  - treat the restore as unsupported for the bulk path unless the implementation can prove it is the same still-live model and can also prevent stale deferred close semantics from invalidating it
- treat "existing model id appears during a v1 bulk restore" as a fail-fast condition by default, not as an automatic overwrite or reuse case
- track which model ids were newly created by this restore versus merely updated by this restore
- track restore-local comm registrations separately from pre-existing ones so rollback can distinguish owned state from shared global state

The goal is to reuse the upstream restore semantics, not necessarily the exact `set_state(...)` API surface.

Version 1 should prefer a conservative ownership rule:

- if a model id is absent, bulk restore may create it
- if a model id is already present, the implementation should prefer the legacy escape hatch or an explicit restore error rather than a merge path that v1 does not define
- a future iteration may design explicit model reuse only together with generation-aware close suppression or an equivalent stale-close safety mechanism

This keeps the v1 behavior biased toward fail-fast correctness instead of optimistic but underspecified reuse.

### HTML Dependency Handling

`html_deps` remains a Shiny-specific concern and should be handled deliberately rather than treated as an opaque extra field.

Version 1 should:

- render dependencies before model restore begins
- await dependency rendering before any `new_model(...)`, class loading, or manager-state deserialization work begins
- rely on Shiny's existing dependency deduplication behavior rather than inventing a separate widget-specific deduper
- treat dependency-render failure as a restore failure for that output
- define `html_deps` as the deduplicated union of dependencies for every widget instance in the dependency closure, not merely the root widget's dependencies

This ordering matters because widget model class loading may depend on dependency scripts or module path configuration being in place before `new_model(...)` begins loading classes.

### Rerender And Teardown Ordering

Bulk restore changes initial materialization, but it should not weaken the existing rerender cleanup guarantees.

Version 1 should preserve this ordering for output replacement:

1. start restore for the new output value
2. wait until the new restore is complete and the new root view is ready to render
3. render the new root view
4. only then allow teardown of the previous output view and any associated `comm_close` traffic

The design should remain compatible with the current flush-delayed close behavior used to avoid flicker and parent-before-child races during replacement.

## Error Handling

### Server-Side

- If bulk payload generation fails before any bulk message is sent, log a structured error and use the per-model escape hatch.
- If dependency collection encounters a missing referenced widget id, log enough detail to identify the root widget and the missing reference.
- If the server detects that a render would require unsupported v1 model-id reuse semantics, log that fact explicitly and use the escape hatch or fail fast according to the configured policy.
- Record bulk-restore telemetry so real deployment data can inform future chunking or transport work. At minimum:
  - payload bytes
  - model count
  - output id
  - root model id
  - bulk payload generation duration
  - whether the per-model escape hatch was used

### Frontend

- If the restore helper fails, log the restore error and reject the restore promise for that `restore_id`.
- If restore fails for one output, attempt best-effort cleanup of any models and comm registrations created by that restore before surfacing the failure.
- Failure isolation should be scoped to "best effort for one-output restore". It should not claim full transactional isolation across the entire global manager unless the implementation actually provides rollback for every created model and comm and preserves server/browser consistency.
- The frontend should not silently continue to partial rendering after a failed restore.
- Version 1 should not claim automatic downgrade to per-model open after a frontend restore failure unless a dedicated recovery protocol is added.
- The v1 user-visible behavior for a frontend restore failure should be explicit:
  - reject the restore for that output
  - surface a clear output error
  - do not automatically retry with the per-model path
- leave unrelated outputs functional
- acknowledge that the server may still believe the failed models exist until a later rerender, close, or session end reconciles them

### Version 1 Failure Policy

The v1 implementation should not leave failure handling as an open-ended runtime choice. At minimum, it should follow a documented policy like this:

| Condition | When detected | Required v1 behavior |
|---|---|---|
| Bulk payload generation fails | Server, before ownership transfer and before any bulk message is sent | Keep legacy per-model open scheduling intact and use the server-side escape hatch |
| Dependency closure includes unsupported v1 pre-existing browser model ids | Server if discoverable, otherwise frontend at restore start | Prefer the legacy escape hatch if the server can still choose it; otherwise reject the restore explicitly |
| `html_deps` fail to render | Frontend, before model restore begins | Reject the restore for that output and do not partially create models |
| Frontend restore fails after some models have been registered | Frontend, during restore | Attempt best-effort rollback, reject the restore, and surface a clear output error; do not silently retry with per-model open |
| Output rerender returns the same Python widget instance and would require browser-side model reuse | Server if discoverable from current ownership state, otherwise frontend | Treat as unsupported for v1 bulk restore and route to the escape hatch or explicit error according to the same rule as other pre-existing model-id cases |

The important property is not which side detects every case first. It is that v1 behavior stays deterministic: either the server intentionally falls back before ownership transfer, or the client fails explicitly without pretending that browser/server state has been fully reconciled.

### Rollback Semantics

Rollback is one of the most failure-prone parts of this design and should be specified directly.

Version 1 rollback is a browser-local cleanup attempt, not a distributed transaction. Without a dedicated client->server recovery protocol, rollback can reduce frontend contamination but cannot guarantee that Python and the browser remain perfectly synchronized after a partial restore failure.

For a failed restore, v1 should attempt to clean up, in this order:

1. any restore-local comm routing entries that were registered before model creation completed
2. any model ids whose manager entries were newly registered by this restore
3. any fully constructed models newly created by this restore, using normal close semantics where possible

Rollback should not delete or close:

- models that existed before the restore began
- comm registrations that predated the restore
- models that were only updated by the restore

Because model promises may be registered before deserialization finishes, the implementation should explicitly handle both:

- fully resolved newly created models
- newly registered model ids whose creation later rejected

The design should not assume that every rollback target has a fully constructed model instance.

Accordingly, the design should make only these v1 guarantees:

- unrelated outputs should remain usable if cleanup succeeds well enough
- the failed output should surface an explicit error instead of partially rendering
- cleanup should minimize leaked frontend manager state

It should not guarantee:

- exact transactional rollback of the global manager
- automatic reconciliation of server-side model state after a frontend-only failure

## Performance Design

Performance validation should be an explicit part of this work.

Measure at least:

- initial graph materialization time
- rerender time for heavy widget graphs
- message count
- total payload bytes
- console/page errors under load
- dependency render failures
- restore rollback failures

Benchmark three cases:

1. current per-model open path
2. new manager-state bulk restore path
3. explicit opt-out path

Use at least:

- a medium graph
- a heavy graph such as the `ipyleaflet` many-marker case

The main performance hypothesis is:

- bulk restore may not reduce total bytes dramatically
- but it should reduce message count and remove ordering races
- this should improve stability and likely improve heavy-graph performance
- the measured heavy repro is comfortably below Shiny's default local websocket size setting, so transport size alone should not drive v1 design decisions
- one-output-at-a-time restore may leave some batching gains on the table compared to a hypothetical multi-output transaction, but it should materially reduce complexity and rollback risk in v1

## Testing Strategy

### Correctness

- Heavy `ipyleaflet` rerender regression remains green.
- `ipyleaflet_marker_click` remains green.
- Add focused coverage for nested widget trees that require cross-model resolution during initial restore.
- Add focused coverage that live post-restore `comm_msg` traffic still reaches restored models.
- Add focused coverage that models introduced after initial restore still use the live per-model `comm_open` path and remain usable.
- Add focused coverage that the render payload includes the expected `output_id`, `restore_id`, and `root_model_id` values for the current output render.
- Add coverage that `renderValue()` waits for the matching restore and ignores stale restore completions after rerender.

### Regression Coverage

- Existing rerender cleanup tests for `plotly`, `altair`, and `bokeh` remain green.
- Teardown behavior remains green with unchanged `comm_close` semantics.
- Output replacement preserves the required ordering of "new restore completes before old teardown closes".

### Fallback Coverage

- Add a test hook to force the legacy per-model open path.
- Verify the explicit opt-out path still renders and updates correctly.
- Add coverage that server-side bulk payload generation failure uses the per-model escape hatch.
- Add coverage that payload-generation failure happens before ownership transfer, so the already-scheduled legacy per-model opens still materialize the graph correctly.
- Add coverage that a render shape requiring unsupported v1 pre-existing model-id reuse chooses the documented escape hatch or raises the documented explicit error.

### Failure-Isolation Coverage

- Add a test hook that forces a frontend restore failure after some models have been created.
- Verify the failed output shows a clear error.
- Verify a different output on the same page continues to render and update correctly.
- Verify partially created models from the failed restore are rolled back.
- Verify the implementation does not claim automatic server/browser reconciliation after that failure unless an explicit recovery protocol exists.
- Add coverage that `html_deps` render failure aborts the restore before any model creation work begins.

### Lifecycle Boundary Coverage

- Add coverage for rerendering the same Python widget instance across output invalidations.
- Verify that if this shape would require browser-side model reuse, v1 does not silently merge manager state and instead follows the documented escape-hatch-or-error policy.
- Add coverage that the old output's deferred close cannot tear down a newly restored graph in the supported fresh-model-id path.

### Performance Coverage

- Add a repeatable benchmarking harness or scripted measurement flow for medium and heavy graphs.
- Record baseline numbers before implementation.
- Re-run after implementation and compare:
  - render/rerender latency
  - message count
  - payload bytes
  - browser-side error rate

### Telemetry And Diagnostics

In addition to benchmark runs, production-oriented telemetry should be part of the implementation plan.

Minimum browser-side diagnostics:

- restore duration
- rerender duration
- dependency render failures
- restore failures
- rollback failures
- missing-model errors observed in `comm_msg` or `comm_close` handling after restore
- whether a restore encountered pre-existing model ids and used the escape hatch or failed fast

Minimum server-side diagnostics:

- payload bytes
- model count
- payload generation duration
- whether bulk restore was disabled explicitly
- whether server-side payload generation fell back to per-model open

## Rollout Plan

Implement in stages:

1. Add server-side manager-state payload generation for a root widget tree.
2. Add frontend restore bookkeeping keyed by `output_id` and `restore_id`.
3. Add frontend bulk restore handling via a Shiny-specific restore helper that creates live comms for restored models.
4. Wire initial output materialization to use the bulk path.
5. Add the ownership-transfer and suppression rule that prevents the legacy scheduled initial per-model open from firing only after bulk payload generation has succeeded for those widgets.
6. Preserve existing live `comm_msg`, `comm_close`, and post-restore live per-model `comm_open`.
7. Keep the legacy initial per-model materialization path only as an explicit opt-out and server-side escape hatch, including cases where v1 detects unsupported model-id reuse shapes.
8. Benchmark before and after.
9. Remove the current recursive child-open workaround for initial materialization only after the bulk path is proven and the fallback remains healthy.

## Tradeoffs

### Advantages

- Closer to `ipywidgets` bulk restore design.
- Solves child-model registration races structurally.
- Reduces message count for large graphs.
- Keeps live update and teardown scope small.

### Costs

- Adds a new protocol path.
- Requires a clean boundary between graph materialization and live sync.
- Requires Shiny-specific restore bookkeeping instead of a trivial `manager.set_state(...)` call.
- Large manager-state payloads may still require future chunking or a richer recovery protocol for truly extreme graphs or stricter hosted environments.

## Open Decisions For Implementation

- Exact custom message name.
- Whether a future chunking or client-driven recovery protocol is needed after v1 benchmarking and telemetry.
- Where benchmarking artifacts should live in the repository.

## Recommendation

Adopt a manager-state-first protocol for initial widget graph materialization, keep `comm_msg` and `comm_close` unchanged, preserve live per-model `comm_open` for models created after initial restore, and keep the legacy initial per-model materialization path in v1 only as an explicit opt-out and server-side escape hatch. Do not make automatic size-based fallback part of the first iteration. Instead, implement one-output-at-a-time restore with explicit stale-render guards, a Shiny-specific frontend restore helper that preserves live comm behavior, an ownership-transfer rule that suppresses legacy initial opens only after successful bulk payload generation, closure-wide `html_deps` aggregation, and a conservative v1 policy that bulk restore creates fresh model ids instead of attempting underspecified browser-side model reuse. This is the best long-term direction because it addresses the real architectural gap: `shinywidgets` currently imitates live per-model widget creation but lacks the bulk graph registration path that `ipywidgets` already uses for complex state restoration.
