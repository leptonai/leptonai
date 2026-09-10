# Plan: Dynamo Graph Deployment support in `lep`

Status: implemented (2026-09-08). Phases 1-4 landed in `leptonai/api/v2/{dynamo,dynamo_spec,dynamo_patch}.py`,
`leptonai/api/v2/types/dynamo.py`, `leptonai/cli/dynamo.py`, plus `lep log get --dynamo`.
Deviations from the plan are listed in section 7 at the end.

Source material used to derive the scope:

- GUI interaction specs in `lep-fe/interaction-specs/apps/dashboard/specs/`:
  12 pages (`deployment-dynamo-*.md`, `deployment-create-dynamo.md`,
  `deployment-edit-dynamo.md`) and 6 components (`dynamo-*.md`,
  `llm-engine-selector.md`).
- Dashboard form logic that the specs delegate to:
  `apps/dashboard/src/generated/forms/dynamo/{helpers,submit,contract}.ts`
  (default images/commands/workdirs, submit payload shape, edit merge-patch rules).
- Backend contract: `lep-fe/docs/api-server/httpapi/dynamo/{spec,contract,design}.md`,
  `lep-fe/api-server/httpapi/dynamo/handler.go`, `.../metrics/handler_metrics.go`,
  `.../log/handler_log.go`, and the CRD types in
  `deployment-operator/api/v1alpha1/leptondynamographdeployment_types.go`.
- Existing CLI patterns to mirror: `leptonai/cli/raycluster.py` (multi-group
  create, `-f` spec file, `get -p`), `leptonai/cli/deployment.py` (`status`,
  `log`), `leptonai/api/v2/raycluster.py` (API layer), `leptonai/api/v2/types/*`.

## 1. What the GUI can do that the CLI cannot

| GUI surface (spec) | Backend call | Proposed CLI command |
|---|---|---|
| Dynamo list, search / status / creator filter (`deployment-dynamo-list.md`) | `GET /dynamographdeployments` (no server-side filters; client-side) | `lep dynamo list [-n SUBSTR]... [--state S]... [--created-by U]...` |
| Create form (`deployment-create-dynamo.md`, `dynamo-config.md`, `dynamo-service.md`) | `POST /dynamographdeployments` | `lep dynamo create` |
| Edit overlay, JSON Merge Patch (`deployment-edit-dynamo.md`) | `PATCH /dynamographdeployments/:id[?dryrun=true]` | `lep dynamo update` |
| Detail summary card (`deployment-dynamo-detail.md`, `dynamo-deployment-card.md`) | `GET /:id`, `GET /:id/services`, `GET /:id/monitoring/status` | `lep dynamo status -n X`, `lep dynamo get -n X [-p PATH]` |
| Delete with confirm | `DELETE /:id` | `lep dynamo remove -n X` |
| Services tab, per-service card + run command (`deployment-dynamo-detail-services.md`, `dynamo-service-item.md`) | `GET /:id/services`, `GET /:id/services/:svc` | `lep dynamo service list -n X` (table), `lep dynamo service get -n X -s SVC` (detail) |
| Restart service with confirm | `PUT /:id/services/:svc/restart` | `lep dynamo service restart -n X -s SVC` |
| Replicas tab, status filter, node column (`deployment-dynamo-detail-replicas.md`) | `GET /:id/services/:svc/replicas`, `GET /:id/replicas[?service=]` | `lep dynamo replica list -n X [-s SVC] [--state R]...` |
| Delete replica | `DELETE /:id/replicas/:rid` (or service-scoped) | `lep dynamo replica remove -n X -r RID` |
| Logs overlay, per-replica logs (`deployment-dynamo-detail-logs.md`, `...-replicas-detail-logs.md`) | `GET /:id/replicas/:rid/log?tail=&timestamps=`; shared `GET /logs?dynamo_graph_deployment=&dynamo_service=&replica=` | `lep dynamo replica log -n X [-s SVC] [-r RID] [--tail N] [--timestamps]`; `lep log get --dynamo X` for historical windows |
| Deployment metrics (`deployment-dynamo-detail-metrics.md`) | `GET /:id/monitoring/{GPUUtilAvg,...}?window=H` | `lep dynamo metrics -n X [--window H]` (phase 4, optional) |
| Replica metrics (`...-replicas-detail-metrics*.md`) | `GET /:id/replicas/:rid/monitoring/{metric}` | `lep dynamo replica metrics -n X -r RID` (phase 4, optional) |
| Not in GUI, cheap | `GET /:id/history` | `lep dynamo history -n X` (phase 4, optional) |

Explicitly out of scope: the LLM-engine switcher, node-group preference
storage, permission-based button disabling, and every layout/skeleton rule.
Those are browser concerns. The server remains the authority for RBAC; the CLI
just surfaces 403 via the existing `click_group` error handler.

## 2. Backend facts that shape the CLI design

These were verified against the handler source, not only the docs.

- Resource path is `/dynamographdeployments` with ID `dgdid`; the CLI can
  address a deployment by `metadata.id` (same as name for user-created ones).
- List has no query params; `q` / `status` / `created_by` filtering is
  client-side. Response is a bare array.
- `spec.services` is a map keyed by service name. Service names the GUI uses:
  `frontend`, `worker`, `prefill-worker`, `decode-worker`. `component_type`
  is only `frontend` or `worker`.
- Server static validation on create: name rules, at least one frontend,
  `min_replicas >= 1` (`max_replicas` is forced equal to `min_replicas`),
  `multinode.node_count >= 2` and worker only, `backend_framework` in
  `vllm|sglang|trtllm`, image must be
  `nvcr.io/nvidia/ai-dynamo/{vllm|sglang|tensorrtllm}-runtime:<version>` with
  the version in `SupportedDynamoVersions` (today only `1.3.1`),
  `ingress_timeout_seconds` in 300..3600.
- `dynamo_namespace` must be empty. `validation.go` rejects any non-empty
  value for Dynamo 1.3.1. The `spec.md` sentence about name rules is stale.
  The CLI must not expose this field.
- `ingress_enabled` is a plain Go bool with `omitempty`; the server does not
  default it to true. The GUI always sends `true` by default. The CLI should
  too.
- Update is RFC 7396 merge patch against the user spec. Removing a service is
  `{"spec":{"services":{"<name>":null}}}`. Multinode presence is immutable per
  service; `node_count` inside an existing multinode block may change.
  `?dryrun=true` validates without persisting.
- Replica log endpoints are one-shot JSON (`{"logs": "...", ...}`), default
  `tail=100`, optional `timestamps=true`. They do not stream. The handler
  reads `tail`; the OpenAPI yaml documents the parameter as `lines`, which is
  wrong, so do not generate the client from the yaml. The shared
  `/logs` route accepts `dynamo_graph_deployment=<id>` plus `dynamo_service=`
  and `replica=` for historical windows.
- States: deployment `Ready | Starting | Updating | Not Ready | Deleting`;
  service `Ready | Starting | Updating | Scaling | Restarting | Not Ready`;
  monitoring `overall_health` is `healthy | degraded | unhealthy`.
- Replica objects are `httpapi.Replica` with `status.readiness_issue.reason`,
  `status.node{name,id,node_group_id}`, `status.container_status`,
  `status.last_termination`. The readiness reason set is wider than the CLI's
  current `ReplicaReadinessReason` enum (adds `WaitingForCapacity`,
  `Migrating`, `UserCodeError`, `DeploymentConfigError`, `Failed`,
  `Preempting`, `Completed`, `Terminated`, `NodeNotReady`).
- Metrics routes exist at deployment level (`window` in hours: 1,2,3,6,12,24)
  and replica level (no window). Response is a list of
  `{metric:{name,device?}, values:[[ts_seconds, "value"|null], ...]}`.

## 3. Defaults registry to port from the dashboard

`forms/dynamo/helpers.ts` is the single source of the GUI defaults. Port it
verbatim into `leptonai/api/v2/types/dynamo.py` (or a sibling
`dynamo_defaults.py`) so `lep dynamo create` can fill in what the GUI computes:

- `DYNAMO_VERSION = "1.3.1"`, `WORKER_ROLE_LABEL_KEY = "lepton.ai/dynamo-worker-role"`.
- Images per framework: `nvcr.io/nvidia/ai-dynamo/{vllm,sglang,tensorrtllm}-runtime:<version>`.
- Working dir: frontend `/workspace`; workers `/workspace/examples/backends/vllm`,
  `/workspace/examples/backends/sglang`, `/workspace/` (trtllm).
- Default commands per `(version, serving_mode, service_name, framework)`
  exactly as in `SERVICE_COMMAND["1.3.1"]`, including the multinode rewrite
  for SGLang (`--tp 1` becomes `--tp <gpu*nodes>`; disaggregated also swaps the
  bootstrap port and appends `--mem-fraction-static 0.82`).
- Rules: vLLM only supports aggregated; multinode only for SGLang non-frontend
  services; prefill/decode workers get the role label automatically; workers
  inherit the frontend node group; command strings are sent as
  `["/bin/sh", "-c", "<string>"]` (the dashboard's `toShellCommandArgv`).

Keep the registry data-only and unit-tested so a version bump is a one-line change.

## 4. Deliverables by layer

### 4.1 Types: `leptonai/api/v2/types/dynamo.py` (new)

Pydantic models mirroring the CRD and handler response types. Field names must
match JSON exactly; follow `types/raycluster.py` conventions (`Optional`
everywhere, `_missing_` on enums, `Field(alias=...)` for `id`/`from`).

- `DynamoBackendFramework` enum (`vllm`, `sglang`, `trtllm`).
- `DynamoComponentType` enum (`frontend`, `worker`).
- `DynamoMultinodeSpec { node_count }`.
- `DynamoMainContainerSpec { image, working_dir, command: List[str] }`.
- `DynamoExtraPodSpec { main_container, image_pull_secrets, node_selector, termination_grace_period_seconds }`.
- `DynamoExtraPodMetadata { annotations, labels }`.
- `LeptonDynamoServiceSpec`: `component_type`, `envs`, `env_from_secret`,
  `mounts`, `multinode`, `extra_pod_metadata`, `extra_pod_spec`, plus the
  inlined resource requirement fields (`resource_shape`, `cpu`, `memory`,
  `ephemeral_storage_in_gb`, `accelerator_*`, `shared_memory_size`,
  `affinity`, `min_replicas`, `max_replicas`, `host_network`, `is_adaptive`).
  Reuse `EnvVar`, `Mount`, `LeptonResourceAffinity` from existing modules.
- `LeptonDynamoGraphDeploymentUserSpec`: `display_name`, `dynamo_version`,
  `backend_framework`, `ingress_enabled`, `envs`, `services: Dict[str, LeptonDynamoServiceSpec]`,
  `load_balance_config`, `routing_policy`, `auth_config`,
  `ingress_timeout_seconds`. Include `dynamo_namespace` for round-tripping
  server responses but never set it from the CLI.
- `LeptonDynamoGraphDeploymentState`, `LeptonDynamoServiceState` enums.
- `LeptonDynamoServiceStatus { state, ready_replicas, desired_replicas, last_ready_replicas }`.
- `LeptonDynamoGraphDeploymentStatus { state, conditions, observed_generation, services, endpoint: DeploymentEndpoint, default_lepton_ingress }`.
- `LeptonDynamoGraphDeployment { metadata: Metadata, spec, status }`.
- Response models: `DynamoServiceInfo`, `DynamoServicesResponse`,
  `DynamoServiceResponse` (+ `DynamoServiceStatus`, `DynamoServiceCondition`,
  `DynamoServiceReplicaStatus`), `DynamoReplica` (+ `DynamoReplicaStatus`,
  `DynamoReplicaNode`, `DynamoReplicaReadinessIssue`),
  `DynamoServiceReplicasResponse`, `DynamoReplicaLogResponse`,
  `DynamoReplicaDeleteResponse`, `DynamoServiceRestartResponse`,
  `DynamoMonitoringStatusResponse`, `DynamoHistoryItem`.
- Extend `types/readiness.py::ReplicaReadinessReason` with the missing
  members listed in section 2. This also fixes endpoint replicas showing
  `Unknown` for those reasons.
- Register the module in `types/__init__.py`.

Decision: define a dedicated `DynamoReplica` rather than reusing
`types/replica.py::Replica`, because the Dynamo `Node` carries
`node_group_id` and the status carries readiness and container info the flat
type lacks. If we later enrich `Replica`, the two can converge.

### 4.2 API layer: `leptonai/api/v2/dynamo.py` (new) and client wiring

`class DynamoGraphDeploymentAPI(APIResourse)` with one method per route:

```text
list_all() -> List[LeptonDynamoGraphDeployment]
get(name_or_obj) -> LeptonDynamoGraphDeployment
create(spec) -> LeptonDynamoGraphDeployment            # returns created object (201 body)
update(name_or_obj, patch: dict, dryrun=False) -> LeptonDynamoGraphDeployment
delete(name_or_obj) -> bool
list_services(name) -> DynamoServicesResponse
get_service(name, service) -> DynamoServiceResponse
restart_service(name, service) -> DynamoServiceRestartResponse
list_replicas(name, service=None) -> List[DynamoReplica]         # flat route, ?service=
list_service_replicas(name, service) -> DynamoServiceReplicasResponse
get_replica_log(name, replica, service=None, tail=None, timestamps=False) -> DynamoReplicaLogResponse
delete_replica(name, replica, service=None) -> DynamoReplicaDeleteResponse
get_monitoring_status(name) -> DynamoMonitoringStatusResponse
get_history(name) -> List[DynamoHistoryItem]
get_metric(name, metric, window=None) -> list                     # phase 4
get_replica_metric(name, replica, metric) -> list                 # phase 4
```

Notes:

- `update` takes a raw merge-patch `dict`, not a full model, because the
  patch semantics (nulls remove keys) do not survive `safe_json`, which drops
  `None`. Provide a helper `build_merge_patch(original_spec, desired_spec)`
  in a pure module (`leptonai/api/v2/dynamo_patch.py`) that diffs two dicts
  and emits `null` for removed keys, mirroring the dashboard's edit transform.
- Register in `client.py` as `self.dynamo = DynamoGraphDeploymentAPI(self)`.
  Dynamo is a separate resource and is not affected by the
  `enable_new_deployment_api` switch, so no property indirection is needed.
- Extend `LogAPI.get_log` / `get_log_time_series` with `name_or_dynamo` and
  `dynamo_service` so `lep log get` can target Dynamo deployments via the
  shared `/logs` route (`dynamo_graph_deployment=` query key).
- Add `client.dynamo` to the module docstring in `api/v2/__init__.py`.

### 4.3 CLI: `leptonai/cli/dynamo.py` (new), registered in `cli.py`

Top-level group `lep dynamo` created with `click_group()` so abbreviations and
the shared error handler apply. Note that `lep dyn` is ambiguous: the
subsequence matcher in `click_group` also matches the hidden `deployment`
alias (d-y-n appear in order in "deployment"). `lep dyna` is the shortest
unambiguous form; document `lep dynamo` in examples.

Commands, in the order to implement:

1. `list` — table: Name/ID (`make_name_id_cell`), State (`colorize_state`),
   Framework, Serving mode (derived: any `prefill-worker`/`decode-worker`
   means disaggregated), Ingress, Services as one line per service
   `name: replicas x shape (ready/desired)`, Node groups (union of service
   affinities), Created at, Created by. Filters `-n` (substring, repeatable),
   `--state` (repeatable, matches `status.state`), `--created-by`
   (repeatable). Sorted by `created_at` descending like the GUI.
2. `get -n X [-d] [-p PATH]` — print sanitized JSON; `-p` saves `spec` only
   as `dynamo-spec-<name>.json`, reusable by `create -f`. Same shape as
   `raycluster get`.
3. `status -n X [-d]` — the summary card plus detail tabs in text: state,
   framework, version, ingress and external endpoint (only when `Ready`, as
   the GUI does), node groups, global env names (values hidden, secrets marked),
   a service table from `/services` (component type, ready/desired, total
   pods, multinode node_count, shape, min_replicas), the monitoring
   `overall_health` line, and a replica table from `/replicas` (id, service,
   readiness reason colored, node, created at). `-d` dumps the full object.
4. `service list -n X` and `service get -n X -s SVC` — table and single-service
   detail (spec, status phase/health/state/uptime, conditions, last replica
   error events, and the run command rendered as a shell line).
5. `replica list -n X [-s SVC] [--state REASON]...` — per-service or flat list.
   Status filter uses the GUI's readiness-reason groups verbatim.
6. `replica log -n X [-s SVC] [-r RID] [--tail N] [--timestamps] [-p PATH]` — one-shot
   pod log. Selection rule mirrors `lep endpoint log`: if `-r` is missing,
   choose the first replica of `-s` (default service `frontend`), print which
   one was chosen. Print a hint that this endpoint does not stream and that
   `lep log get --dynamo X` covers historical windows.
7. `service restart -n X -s SVC [-y]` — confirm prompt like the GUI dialog unless
   `-y`; print `deleted_pods`. Refuse client-side when the service is
   deleting or `min_replicas <= 0` (same disable rule as the GUI).
8. `remove -n X [-y]` and `replica remove -n X -r RID [-s SVC] [-y]` —
   confirm prompts; surface the 400 "already being deleted" message plainly.
9. `create` — see 4.4.
10. `update` — see 4.5.
11. Phase 4: deployment-level `metrics`, `replica metrics`, `history`, and
    `lep log get --dynamo`.

Every command takes `--name/-n` as the deployment identifier, matching the
rest of the CLI. Destructive commands accept `-y/--yes` so the agent skill and
scripts can run them non-interactively.

### 4.4 `lep dynamo create` design

Two input paths that can be combined, exactly like `raycluster create`:

- `-f/--file spec.json`: a `LeptonDynamoGraphDeploymentUserSpec` JSON (the
  file `get -p` writes). CLI flags override or add on top.
- Flags only.

Global flags:

```text
-n/--name                    required, validated locally (<=36 chars, lowercase
                             alnum/'-', starts with a letter, ends alnum,
                             not ending in "by-lepton")
--framework                  vllm|sglang|trtllm, default vllm
--serving-mode               aggregated|disaggregated, default aggregated
--dynamo-version             default 1.3.1 (drives image tags and command registry)
--ingress-enabled/--no-ingress   default enabled
--ingress-timeout            300..3600 seconds, optional
--display-name               optional
-e/--env NAME=VALUE, -s/--secret NAME[=SECRET]   global envs (reuse make_env_vars_from_strings)
--image-pull-secrets         repeatable, applied to each service's extra_pod_spec
--visibility                 public|private (metadata.visibility, as raycluster does)
```

Per-service blocks using a repeatable marker, parsed by a generalized copy of
`WorkerGroupCommand` (extract the block parser into `cli/util.py` so both
raycluster and dynamo share it):

```text
-svc/--service TYPE   TYPE in frontend|worker|prefill-worker|decode-worker
  --resource-shape S           required for every new service
  --node-group NG              only meaningful on frontend; workers inherit it
  --replicas N                 default 1, >= 1
  --node-count N               >= 2, sglang workers only; emits multinode
  --image IMG                  default derived from framework+version
  --working-dir DIR            default derived
  --command "..."              default derived; sent as /bin/sh -c argv
  -e/--env, -s/--secret        per-service envs
  --mount FROM:MOUNT:VOLUME    reuse make_mounts_from_strings
  --annotation K=V, --label K=V
  --shared-memory-size MiB
  --termination-grace-period SECONDS
```

Behavior rules copied from the GUI page and `helpers.ts`:

- If no `frontend` block is given, one is synthesized with defaults. It still
  needs `--resource-shape` and `--node-group`, so the CLI errors with a clear
  message telling the user to add `-svc frontend --resource-shape ... --node-group ...`.
- `worker` is only valid in aggregated mode; `prefill-worker` and
  `decode-worker` only in disaggregated mode. Error, do not silently switch.
- `--framework vllm --serving-mode disaggregated` is an error (GUI
  auto-switches; a CLI should not change what the user typed).
- `--node-count` on a frontend, or on any service when framework is not
  sglang, is an error.
- Worker `--node-group` that differs from the frontend's is an error; absent
  means inherit.
- `lepton.ai/dynamo-worker-role: prefill|decode` is added to prefill/decode
  worker labels automatically.
- Image: if `--image` is given, warn that the server only accepts the
  official runtime image with a supported tag, then send it as typed.
- Node group names are resolved to IDs with the existing
  `_get_valid_nodegroup_ids`.
- Optional pre-flight: validate `--resource-shape` against
  `client.shapes.list_shapes(node_group)` and print the available shapes on
  mismatch. Make this best-effort so a shapes API failure does not block
  create (the GUI treats catalog failures the same way).
- On success print the name and `lep dynamo status -n X` hint, mirroring the
  GUI's "Endpoint created" dialog.

Spec assembly lives in pure functions (`build_dynamo_spec(...)`,
`build_service_spec(...)`) in `leptonai/api/v2/dynamo_spec.py` so they are unit
testable without click.

### 4.5 `lep dynamo update` design

Merge-patch builder with three input styles, any combination allowed:

- Global fields: `--display-name`, `--ingress-enabled/--no-ingress`,
  `--ingress-timeout`, `-e/-s` (replaces the global env list, as the GUI
  edit form does; document this).
- Service blocks `-svc NAME` with `--replicas`, `--resource-shape`,
  `--command`, `--working-dir`, `-e/-s`, `--mount`, `--annotation`,
  `--label`, `--node-count` (only if the service already has multinode),
  and `--remove` to delete the service (`null` in the patch). A block naming
  a service that does not exist adds it and therefore requires
  `--resource-shape` (node group inherited from the frontend).
- `-f patch.json`: a raw merge patch applied as-is for anything the flags do
  not cover.
- `--dryrun`: sends `?dryrun=true` and prints the server-validated result.
- Empty patch prints "No changes detected" and exits 0 without a request,
  same as the GUI.
- Client-side guard: adding or removing `multinode` on an existing service is
  rejected before the request with the server's wording.

Clearing rules from the edit spec: clearing a worker `--working-dir ""` is
rejected by the global empty-string guard, so expose `--clear-working-dir`
instead, which emits `working_dir: null` for workers and `/workspace` for the
frontend.

### 4.6 Tests

Follow the existing layout and fixtures.

- `leptonai/tests/test_dynamo_spec.py`: pure-function tests for the defaults
  registry, `build_dynamo_spec`, worker-role labels, node-group inheritance,
  every error rule in 4.4, and `build_merge_patch` (removed keys become
  `null`, unchanged paths omitted, service removal).
- `leptonai/api/v2/tests/test_dynamo_api.py`: `responses`-based tests that
  each method hits the right path, query string (`?service=`, `?tail=`,
  `?timestamps=true`, `?dryrun=true`), and parses the documented response
  shapes, including the bare-array list and the `{"services": {...}}` map.
- `leptonai/cli/tests/test_dynamo_cli.py`: `CliRunner` with a patched
  `APIClient` (the `_FakeAPIClient` pattern in `test_deployment_cli.py`).
  Cover: list rendering and filters, `create` payload assertions for the
  three GUI user stories (single frontend, aggregated worker, disaggregated
  prefill/decode), each create rejection, `update` patch assertions and
  no-op exit, `replica log` auto-selection, confirm prompts and `-y`.
- Run with `pytest -x leptonai` as CI does.

### 4.7 Docs and agent skill

- README: add `lep dynamo` to the getting-started list and the CLI feature
  bullet.
- `plugins/lepton-cli/skills/lepton-cli/references/workloads.md` already
  describes Dynamo endpoints conceptually; add the command mapping and the
  confirm-before-destroy note for `remove`, `replica remove`, `service restart`.
- `example_usage.md`: one aggregated and one disaggregated create example.
- The external e2e script (`lepton/sdk/release_scripts/e2e_sdk_cli_test.sh`)
  needs a Dynamo create/status/remove case; track it as a follow-up in that
  repo.

## 5. Phasing and PR split

Each phase is one reviewable PR in the style of the recent `feat(cli):` commits.

| Phase | Content | Depends on |
|---|---|---|
| 1 | Types, defaults registry, API layer, client wiring, readiness enum extension, API and spec unit tests | none |
| 2 | Read and lifecycle commands: `list`, `get`, `status`, `service list/get/restart`, `replica list/log/remove`, `remove`; CLI tests | 1 |
| 3 | `create` and `update`, shared block parser extracted from raycluster, spec-file round trip, CLI tests | 1, 2 |
| 4 | `metrics`, `history`, `lep log get --dynamo`, README and skill docs, e2e follow-up | 2 |

Phase 1 plus 2 already gives operators everything the GUI detail pages offer.
Phase 3 is the largest and is where the GUI rules matter most. Phase 4 is
optional polish; the CLI has no metrics commands for endpoints today either,
so `metrics` can be dropped if it does not earn its keep.

## 6. Decisions taken and open questions

Decisions made in this plan:

- Top-level `lep dynamo` group rather than nesting under `lep endpoint`. The
  API resource, spec shape, and lifecycle differ enough that sharing option
  parsers with `endpoint create` would be forced. This also matches the
  `raycluster` precedent.
- No `dynamo_namespace` flag. The server rejects non-empty values.
- `ingress_enabled` defaults to true to match the GUI.
- Service names are restricted to the four GUI names in `create`. The API
  accepts arbitrary keys, but the default command registry only knows these
  four. An `--allow-custom-service-name` escape hatch can be added later.

Questions to confirm before phase 3:

1. Should `create` allow `--image` at all, given the server only accepts the
   official runtime image for the chosen framework and version? Proposed:
   allow with a warning, so future versions do not need a CLI release.
2. Is the shared `/logs` route for Dynamo gated to enterprise workspaces the
   way the GUI's Logs tab is? If yes, `lep dynamo replica log` (one-shot pod log)
   stays the default and `lep log get --dynamo` documents the tier
   requirement.
3. Does `update` need to support `load_balance_config`, `routing_policy`, or
   `auth_config`? The GUI edit form does not expose them. Proposed: reachable
   only through `-f patch.json` in v1.
4. Should `list` also appear as a tab-like hint in `lep endpoint list` output
   ("N Dynamo endpoints exist, see `lep dynamo list`")? Cheap, but touches an
   unrelated command. Proposed: skip.

Answer to the open questions from user:

1. Yes, allow `--image` with a warning, so future versions do not need a CLI release.
2. Yes, the external e2e script needs a Dynamo create/status/remove case; track it as a follow-up in that repo.
3. No, `update` does not need to support `load_balance_config`, `routing_policy`, or `auth_config`.
4. No, `list` does not need to appear as a tab-like hint in `lep endpoint list` output. Skip.

## 7. Implementation notes (post-plan)

- The repeatable `-svc` block parser is a new generic factory,
  `make_block_option_command` in `leptonai/cli/util.py`, instead of a refactor
  of raycluster's `WorkerGroupCommand`. Raycluster is untouched; the two can be
  unified later.
- `lep dynamo get` prints JSON only (no `-d`), because the raycluster-style
  double print was redundant. `status -d` and `service get -d` dump the full
  object.
- `lep dynamo create` gained `--dry-run` (prints the payload without a request)
  and `--visibility`. Node groups are accepted by name or id.
- `lep dynamo update` re-syncs worker node groups to the frontend after
  applying blocks, and rejects `--node-group` on workers, matching the
  dashboard's "workers inherit the frontend node group" rule.
- Per the review answers: `--image` is allowed with a warning;
  `load_balance_config` / `routing_policy` / `auth_config` are reachable only via
  `update -f patch.json`; no hint was added to `lep endpoint list`; the e2e
  script case is tracked in the `lepton` repo.
- The shared `/logs` route tier gating was not confirmed; `lep dynamo replica
  log` uses the one-shot pod-log endpoint by default and `lep log get --dynamo`
  documents that historical logs may need an enterprise tier.
