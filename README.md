<img src="https://raw.githubusercontent.com/leptonai/leptonai/main/assets/logo.svg" height=100>

# Lepton AI

**The Python library and `lep` CLI for NVIDIA DGX Cloud Lepton**

<a href="https://docs.nvidia.com/dgx-cloud/lepton">Homepage</a> •
<a href="https://github.com/leptonai/examples">Examples</a> •
<a href="https://docs.nvidia.com/dgx-cloud/lepton">Documentation</a> •
<a href="https://docs.nvidia.com/dgx-cloud/lepton/reference/cli/get-started/">CLI References</a>

The LeptonAI Python library lets you operate the [NVIDIA DGX Cloud Lepton](https://docs.nvidia.com/dgx-cloud/lepton) platform from Python and the command line. Key features include:

- A `lep` command-line tool to create and manage endpoints, Dynamo graph deployments, batch jobs, dev pods, Ray clusters, fine-tuning jobs, storage, secrets, and more, plus inspect managed Slurm clusters and jobs.
- A `Client` to call your deployed endpoints like native Python functions.
- Pythonic configuration specs that are readily shipped to the cloud.
- Skills that let agents operate the Lepton platform for you.

## Getting started

Install the library, which also installs the `lep` command-line tool:

```shell
pip install -U leptonai
```

Log in to your workspace (this opens a browser to fetch credentials if you don't pass them in):

```shell
lep login
```

Deploy a container image as an endpoint, then inspect it:

```shell
lep endpoint create -n my-endpoint --container-image my-registry/my-app:latest
lep endpoint list
lep endpoint status -n my-endpoint
```

In workspaces with secure endpoint defaults enabled, an endpoint created without
`--tokens` is protected automatically. The create command prints the generated API
token; save that value so clients can authenticate. You can instead provide one or
more repeatable `--tokens` values, or explicitly opt out with
`--allow-unauthenticated-access` (the CLI displays a warning). The `--public` option
only controls IP reachability and does not disable API-token authentication.
`lep endpoint status` reports these dimensions separately as `IP Access` and
`API Token Authentication`.

SDK callers that leave endpoint authentication unspecified should use
`client.deployment.create_with_response(...)` and save the token from the returned
resource. The older `create(...)` method keeps its boolean return contract and cannot
return a server-generated credential, so it emits a `RuntimeWarning` for requests that
may ask the server to generate one. SDK updates may not clear `api_tokens` by sending
an empty list alone: set `allow_unauthenticated_access=true` in the same update, or
replace the list with at least one token.

`lep endpoint get` redacts literal tokens by default. Use `--show-tokens` only when you
need a credential-bearing response or reusable spec export, and handle that output as
a secret. The former hidden `update --remove-tokens` option is rejected; use
`--allow-unauthenticated-access` for an explicit opt-out.

Authentication-mode updates are explicit:

```shell
# Replace tokens and enable token authentication
lep endpoint update -n my-endpoint --tokens MY_TOKEN

# Clear tokens and explicitly allow requests without API-token authentication
lep endpoint update -n my-endpoint --allow-unauthenticated-access
```

You can also launch batch jobs and dev pods:

```shell
# Run a batch job
lep job create -n my-job --container-image my-registry/my-trainer:latest --command "python train.py"

# Launch an interactive dev pod
lep pod create -n my-pod --resource-shape gpu.a10

# Open a shell in the pod through the workspace API (no SSH setup needed)
lep pod shell -n my-pod

# Connect to a pod with Teleport SSH enabled (requires local tsh)
lep pod ssh -n my-pod --transport teleport
```

`lep pod shell`, `lep endpoint shell`, `lep job shell`, and `lep raycluster shell`
open the same interactive shell as the dashboard terminal. The session is
tunnelled through the workspace API over HTTPS, so it needs no SSH key, public
IP, or Teleport client. They follow the dashboard's rules: a pod must be Ready
and opens in its newest replica, an endpoint or job with several running
replicas requires `--replica`, archived jobs and platform-managed tuning jobs
have no shell, and a Ray cluster shell opens on the head node of a cluster that
is not stopped unless `--replica` selects another node. Idle shells send a
keepalive so the workspace ingress does not close them.

Teleport SSH commands require `tsh` v18 or newer in your PATH. The CLI checks
the client version before reading login profiles or starting SSO; missing, older,
or unrecognized clients produce an actionable error. This minimum version check
does not guarantee compatibility with every Teleport cluster version.

Teleport SSH reuses your local Teleport login, or starts SSO login when needed.
As in the dashboard, legacy Pods and Slurm Dev Pods sign in with the `Starfleet`
connector by default, while other targets let Teleport use the cluster's default
connector; use `--teleport-auth <connector>` to choose one. Lepton API
credentials and Teleport login are separate. Your workspace
(`dev_pod_teleport`), node group, and pod must have Teleport enabled, and the
pod must be Ready. Pods on the new DevPod API do not publish their Teleport
proxy, so, as for Jobs below, Teleport SSH uses the active `tsh` profile or
`--teleport-proxy <host>:443` and connects as `root` to the pod's
`<workspace-id>-<pod-name>` node. Without `--transport teleport`, `lep pod ssh`
continues to use direct SSH.

Jobs can also be accessed through Teleport when their workspace has `job_teleport`
enabled and their image/entrypoint starts a Teleport agent:

```shell
lep job replicas --id <job-id>
lep job ssh --id <job-id> --replica <replica-id>
# Or select a uniquely named job (a single ready replica is selected automatically)
lep job ssh --name <job-name>
# Specify the proxy when you have not logged in, or to switch from another proxy
lep job ssh --id <job-id> --replica <replica-id> --teleport-proxy <host>:443
```

Job SSH defaults to the active `tsh` profile because the Job API does not publish
Teleport connection details. It uses the standard Lepton agent's
`<workspace-id>-<replica-id>` hostname and workspace label to find one node, then
connects to its Teleport node ID as `root`. Historical and unready replicas are
excluded; multiple ready replicas require `--replica`. The job must be Running
or Starting. Job SSH does not install the agent or change the workload's startup
command. Use `--teleport-auth` to choose an SSO connector.

Slurm compute nodes also support Teleport SSH:

```shell
lep node list-nodes --node-group <node-group>
lep node ssh --node-group <node-group-name-or-id> --id <node-id>
```

Node SSH discovers the Slurm cluster, Teleport proxy, Machine hostname, and Linux
account automatically. Use a personal API token with workspace user or admin
access; Teleport sign-in must match that token's owner. The compute group must
enable Teleport and use host networking. For clusters using Pod Networking, use
`lep slurm job ssh` on a running Slurm job you own instead.
The session opens in the compute container; Slurm account permissions and job
allocation policies still apply. Use `--teleport-auth` to override the SSO connector.

For a workspace with managed Slurm, inspect clusters and jobs:

```shell
lep slurm cluster list --name prod --status Ready
lep slurm cluster shell -n production
lep slurm job list --cluster production --status Running --include-archived
lep slurm job attempts -i 12345 --steps
lep slurm job logs -n my-training-job --follow
lep slurm devpod get --cluster production
lep slurm devpod ssh --cluster production
```

Login nodes, running jobs, and Dev Pods can also be reached through Teleport:

```shell
lep slurm cluster ssh -n production
lep slurm job ssh -i 12345 --node <allocated-node>
lep slurm devpod ssh --cluster production --transport teleport
```

Like `lep node ssh`, these need a personal API token whose owner matches your
Teleport sign-in. Login-node SSH requires a Ready cluster with Teleport enabled
for its login nodes and connects as your mapped Slurm account; `--node` picks a
login node other than the first. Job SSH requires a running job owned by your
Slurm account; a job on several nodes requires `--node`. Dev Pod SSH uses the
Teleport node and Linux account the Dev Pod reports.

Personal Slurm Dev Pods are available under `lep slurm devpod`; run
`lep slurm --help` for the complete command tree. `devpod get` shows the
effective configuration, identity, connection details, and dashboard link;
`devpod ssh` runs the bastion command reported by the platform unless
`--transport teleport` is given. Slurm job
submission and cancellation remain native Slurm operations (`sbatch`, `squeue`,
`scancel`) on the cluster rather than Lepton API mutations.

Dynamo graph deployments (multi-service LLM inference with a vLLM, SGLang, or
TensorRT-LLM backend) have their own command group. Each `-svc` block configures
one service; the frontend is required and workers inherit its node group:

```shell
lep dynamo create -n my-dynamo --framework vllm \
  -svc frontend --resource-shape cpu.small --node-group my-node-group \
  -svc worker --resource-shape gpu.h100-80gb --replicas 2 -e MODEL=Qwen/Qwen3-0.6B
lep dynamo status -n my-dynamo
lep dynamo replica log -n my-dynamo -s worker --tail 200
lep dynamo update -n my-dynamo -svc worker --replicas 4
```

Dynamo 1.3.1 multi-node workers are configured with `--node-count`; `--replicas`
counts independent worker groups. vLLM, SGLang and TensorRT-LLM accept aggregated
and disaggregated configurations:

```shell
lep dynamo create -n my-multi --framework vllm \
  -svc frontend --resource-shape cpu.small --node-group my-node-group \
  -svc worker --resource-shape gpu.h100-80gb --node-count 2
lep dynamo create -n my-pd --framework vllm --serving-mode disaggregated \
  -svc frontend --resource-shape cpu.small --node-group my-node-group \
  -svc prefill-worker --resource-shape gpu.h100-80gb --node-count 2 \
  -svc decode-worker --resource-shape gpu.h100-80gb --node-count 2
lep dynamo create -n my-trt --framework trtllm \
  -svc frontend --resource-shape cpu.small --node-group my-node-group \
  -svc worker --resource-shape gpu.h100-80gb --node-count 2
lep dynamo update -n my-multi --dry-run -svc worker --node-count 4
```

Choose shapes available in your group. Default commands derive GPU parallelism
from the selected shape; unknown or fractional GPU counts require an explicit
`--command`. Updates synchronize recognized default commands with changed
parallelism and protect custom commands.

Run `lep --help`, or `lep <command> --help` for any subcommand, to explore everything. See the [CLI references](https://docs.nvidia.com/dgx-cloud/lepton/reference/cli/get-started/) for the full guide.

## Calling an endpoint from Python

Once an endpoint is running, call it from Python with the `Client`. It reads the endpoint's OpenAPI schema and exposes each path as a method:

```python
from leptonai.client import Client, local

# Connect to a workspace endpoint...
c = Client("my-workspace", "my-endpoint", token="MY_TOKEN")
# ...or to something running locally:
c = Client(local(port=8080))

# Discover the available paths and their docs
print(c.paths())
print(c.run.__doc__)

# Call the endpoint as if it were a local function
print(c.run(inputs="hello world"))
```

## Checking out more examples

You can find more examples in the [examples repository](https://github.com/leptonai/examples), and full guides in the [documentation](https://docs.nvidia.com/dgx-cloud/lepton).

## Skills: Operating Lepton from Claude Code or Codex

This repo ships an [agent skill](plugins/lepton-cli/skills/lepton-cli/SKILL.md) that lets [Claude Code](https://claude.com/claude-code) (or Codex) drive the `lep` CLI for you — listing endpoints, inspecting jobs and dev pods, checking workspace status, and managing workloads, all from natural language. It uses the same `lep` CLI installed above, so make sure it is authenticated to your workspace.

The plugin lives under [plugins/lepton-cli](plugins/lepton-cli) with per-agent manifests for Claude Code, Codex, and Cursor (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`), all sharing the one skill at [skills/lepton-cli](plugins/lepton-cli/skills/lepton-cli). It is listed in two marketplaces in this repo: [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json) for Claude Code and [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json) for Codex.

**Codex** — add this repo as a marketplace, then install the plugin:

```text
codex plugin marketplace add leptonai/leptonai
codex plugin add lepton-cli@lepton-skills
```

Or browse interactively: run `/plugins` in the Codex CLI (or open **Plugins** in the Codex app), find **Lepton CLI**, and install.

**Claude Code** — install from the Lepton marketplace in one line, nothing to clone:

```text
/plugin marketplace add leptonai/leptonai
/plugin install lepton-cli@lepton-skills
```

Start a new session, then ask something like *"List the endpoints in my Lepton workspace."* The skill asks for explicit confirmation before any command that modifies or deletes a workload.

<details>
<summary><b>Codex, or Claude Code without plugins</b></summary>

Clone this repo, then copy the skill into your agent's skills directory:

```bash
# Codex
cp -R plugins/lepton-cli/skills/lepton-cli "${CODEX_HOME:-$HOME/.codex}/skills/lepton-cli"
# Claude Code (personal skill)
cp -R plugins/lepton-cli/skills/lepton-cli "$HOME/.claude/skills/lepton-cli"
```

Restart the agent afterward.
</details>

## Contributing

This repository uses [uv](https://docs.astral.sh/uv/) to manage its Python environment and dependencies. After installing uv, run these commands from the repository root:

```shell
uv sync --locked
uv run lep --help
```

This installs the local source and development tools into `.venv`, using the Python version in `.python-version` and the dependencies in `uv.lock`. Use `uv run lep` to run the CLI without activating the environment.

Contributions and collaborations are welcome and highly appreciated. Please check out the [contributor guide](https://github.com/leptonai/leptonai/blob/main/CONTRIBUTING.md) for how to get involved.

## License

The Lepton AI Python library is released under the Apache 2.0 license.

Developer Note: early development of LeptonAI was in a separate mono-repo, which is why you may see commits from the `leptonai/lepton` repo. We intend to use this open source repo as the source of truth going forward.
