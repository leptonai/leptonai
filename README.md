<img src="https://raw.githubusercontent.com/leptonai/leptonai/main/assets/logo.svg" height=100>

# Lepton AI

**The Python library and `lep` CLI for NVIDIA DGX Cloud Lepton**

<a href="https://docs.nvidia.com/dgx-cloud/lepton">Homepage</a> •
<a href="https://github.com/leptonai/examples">Examples</a> •
<a href="https://docs.nvidia.com/dgx-cloud/lepton">Documentation</a> •
<a href="https://docs.nvidia.com/dgx-cloud/lepton/reference/cli/get-started/">CLI References</a>

The LeptonAI Python library lets you operate the [NVIDIA DGX Cloud Lepton](https://docs.nvidia.com/dgx-cloud/lepton) platform from Python and the command line. Key features include:

- A `lep` command-line tool to create and manage endpoints, batch jobs, dev pods, Ray and Slurm clusters, fine-tuning jobs, storage, secrets, and more.
- A `Client` to call your deployed endpoints like native Python functions.
- Building blocks — `KV`, `Queue`, and object storage — to back your services with managed state.
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

Batch jobs and dev pods work the same way:

```shell
# Run a batch job
lep job create -n my-job --container-image my-registry/my-trainer:latest --command "python train.py"

# Launch an interactive dev pod
lep pod create -n my-pod --resource-shape gpu.a10
```

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

Contributions and collaborations are welcome and highly appreciated. Please check out the [contributor guide](https://github.com/leptonai/leptonai/blob/main/CONTRIBUTING.md) for how to get involved.

## License

The Lepton AI Python library is released under the Apache 2.0 license.

Developer Note: early development of LeptonAI was in a separate mono-repo, which is why you may see commits from the `leptonai/lepton` repo. We intend to use this open source repo as the source of truth going forward.
