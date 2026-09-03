---
name: lepton-cli
description: "Operate NVIDIA DGX Cloud Lepton through the globally installed `lep` CLI. Use when the user asks to inspect or manage Lepton workspaces, endpoints/deployments, dev pods, batch jobs, fine-tuning jobs, Ray clusters, Slurm clusters, Dynamo endpoints, storage, secrets, nodes, ingress, templates, logs, authentication, or workspace status — or any task that needs safe command-line access to Lepton resources. Skip when the user is operating a different cloud or a different `lep`/`lepton` tool that isn't NVIDIA DGX Cloud Lepton."
---

# Lepton CLI

Use the globally installed `lep` command to operate NVIDIA DGX Cloud Lepton resources from the terminal.

## Runner

Run commands directly:

```bash
lep <command> [args...]
```

Before doing real work, verify the CLI is available:

```bash
lep --help
```

If `lep` is missing, tell the user the global Lepton CLI is not available in the current environment and ask them to install or expose it on `PATH`. Do not attempt to download or install it yourself.

## Source Of Truth

- Use `lep --help` and `lep <group> --help` before any unfamiliar command.
- Use `lep <group> <subcommand> --help` for exact flags and required arguments.
- Read [references/workloads.md](references/workloads.md) for the workload types Lepton exposes (endpoints, dev pods, batch jobs, Ray clusters, Slurm, fine-tuning) and when each one applies. Consult it before recommending a resource shape to the user.
- Treat the installed `lep` help output as authoritative for command behavior — command availability and flags vary by version.

## Auth And Context

Lepton authentication is scoped to a single workspace. A logged-in `lep` CLI may have a default workspace, but that default must not be assumed when the user has not named a workspace.

The CLI may read local configuration and these environment variables:

- `LEP_API_URL` — workspace URL used by `lep`.
- `LEP_TOKEN` — workspace auth token.
- `LEP_WORKSPACE` — default workspace name/display name.
- `LEP_ENV` — optional environment label.

Rules:

- Before running a series of operations, identify the target workspace. If the user did not specify one, ask whether they intend to use the CLI's default logged-in workspace.
- Start read-only with `lep workspace auth-status`, `lep workspace status`, `lep workspace list`, `lep workspace url`, or `lep workspace id`.
- If the CLI is not logged in for the target workspace, fall back to provided `LEP_*` environment variables when available.
- Prefer the exact `LEP_*` variables above when using environment credentials. Do not substitute `LEPTON_WORKSPACE_*` names unless the installed `lep` help or local configuration proves this CLI version reads them.
- Do not run `lep workspace token`, print config files, echo tokens, or include tokens in final answers unless the user explicitly asks.
- Prefer existing config/env credentials. Only run `lep workspace login -i <id> -t <token>` when the user explicitly provides credentials and accepts that the token may be persisted by the CLI.
- If a read-only `lep` command fails with `FailedToOpenSocket`, DNS, or other connection errors that look like a sandboxed network, surface the error to the user and ask whether to retry with broader network permission rather than silently retrying.

## Operating Workflow

1. Identify the target workspace and resource; confirm default-workspace intent when the user has not specified a workspace.
2. Verify current context with a read-only workspace command.
3. Discover exact syntax with `--help`.
4. For reads, run the narrowest command that answers the request.
5. For mutations, inspect current state first when possible.
6. For destructive operations, require explicit user intent or ask before proceeding.
7. Summarize the result with resource names, status, and any next action; redact secrets.

Destructive or high-impact commands include `remove`, `delete`, `stop`, `stop-all`, `remove-all`, `rm`, `rmdir`, `update`, `restart`, `create`, uploads/downloads to user-sensitive paths, and interactive `pod ssh`.

## Modifying Or Deleting Existing Workloads

Workloads are endpoints/deployments, dev pods, batch jobs, fine-tuning jobs, Ray clusters, Slurm clusters, and Dynamo endpoints (see [references/workloads.md](references/workloads.md)). Any command that modifies or deletes an existing workload requires explicit confirmation before it runs — even when auto mode is active or the user has previously approved similar actions in the session. Authorization does not carry over between resources or invocations.

Before running the mutation, read the workload's current state with a narrow read-only command, then show the user: the exact `lep` command to be run, the target workload name, the workspace, and the current state. State what will change in one sentence (e.g., "About to delete endpoint `foo` in workspace `bar` — this is irreversible") and ask the user to confirm. Only execute the mutating command after an explicit yes. A waiver applies only to the single named workload — do not generalize it to other workloads or to a later command.

## Output Handling

- Prefer table output for human inspection.
- Use JSON/YAML only when a command advertises `--output` or when the command naturally emits structured JSON.
- For logs or streaming commands, scope the request with available flags such as replica/name/time/tail when the command supports them.
- If a command writes files through options like `--path`, `download`, or `upload`, verify the source and destination before running.

## Known Gotchas

- `deployment` may be available as an alias for `endpoint`.
- Some command groups may be hidden from top-level help but still invokable. If the user asks for a known Lepton resource, try `lep <group> --help` before concluding it is unsupported.
- Slurm clusters are not self-serve — they are provisioned on request by the Lepton team. See [references/workloads.md](references/workloads.md).
- Slurm is exposed as nested commands with flag-based selectors (no positional resource arguments). Start with `lep slurm cluster list` and `lep slurm job list`; both lists accept repeatable `--status` filters, while cluster list also accepts repeatable `--name` substring filters. Use `lep slurm cluster get --name <name>` (or `--id <namespace/name>`), `lep slurm job get --id <job-id>` (or `--name <job-name>`), `lep slurm job attempts ...`, and `lep slurm job logs ...` for detail. Add `--output json` where advertised when structured output is needed.
- Slurm job submission and cancellation still happen through native Slurm tools (`sbatch`, `squeue`, `scancel`) after connecting to the cluster. The CLI's Slurm job API is intentionally read-only. `lep slurm cluster shell --name <name>` opens an interactive login-node shell through the workspace API; treat it as high-impact under the confirmation rules above.
- A Slurm Dev Pod belongs to the current user and can be listed, inspected, created, removed, or connected to under `lep slurm devpod`. `create` takes `--cluster <name-or-namespace/name>`. For `get`, `remove`, `shell`, and `ssh`, `--name` and `--id` are mutually exclusive while `--cluster` is an optional scope that can also select the cluster's Dev Pod by itself. `get` displays configuration, identity, connection details, and a web link by default (`--output json` preserves the API record). `ssh` executes the platform-reported bastion command; `shell` uses the workspace API. Treat `create`, `remove`, and interactive connection commands as high-impact operations under the confirmation rules above.
- Help output is authoritative for the installed CLI version; command availability and flags can vary by version.
