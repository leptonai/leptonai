# Security Policy: leptonai (Lepton SDK and `lep` CLI)

## Reporting a Vulnerability

If you discover a potential security vulnerability, please **do not open a public
issue or pull request.**

- Report via: [NVIDIA Vulnerability Disclosure Program](https://www.nvidia.com/en-us/security/report-vulnerability/) (preferred)
- E-Mail: [psirt@nvidia.com](mailto:psirt@nvidia.com)
  - We encourage you to use the following PGP key for secure email communication:
    [NVIDIA public PGP Key](https://www.nvidia.com/en-us/security/pgp-key)
- GitHub: Use the **Security** tab > **Report a vulnerability** to submit a report
  directly on this repository

Please include the following information:

- Product/project name and version (`lep --version` or `pip show leptonai`)
- Type of vulnerability
- Step-by-step reproduction instructions
- Proof-of-concept code (if available)
- Impact assessment

**Detailed reports help NVIDIA evaluate and address issues faster.**

NVIDIA's PSIRT team will acknowledge receipt, validate severity, develop fixes,
and publish security bulletins as appropriate.

Vulnerabilities in the NVIDIA DGX Cloud Lepton service itself (the workspace API
or the web dashboard) should be reported through the same channels.

## Security Architecture & Context

`leptonai` is the Python SDK and command-line interface (`lep`) for NVIDIA DGX
Cloud Lepton. It is a **client**: it authenticates to a Lepton workspace API over
HTTPS and lets users manage deployments, jobs, pods, Ray clusters, Slurm
resources, secrets, node groups, and logs. It does not run a server, open a
listening port, or store workload data itself; the workspace API enforces all
authorization.

This software operates at the **Library / CLI Tool** level. Its primary security
responsibility is to protect the user's **workspace API token** and to avoid
turning data returned by the workspace (resource specs, logs, shell output, SSH
commands) into unintended actions on the user's machine.

**Repository Exposure Classification:** Public.
Basis: origin remote is github.com and the repository visibility is public;
this document is written to public-safe detail.

**Service Exposure Classification:** External / Regulated (high confidence).
Basis: externally distributed on PyPI as `leptonai`; used by customers to manage
their workspaces; handles customer workspace API tokens and workload secrets.

Key interfaces and trust boundaries:

- **Local user input (trusted as the user's intent):** CLI arguments and options
  (`leptonai/cli/`), YAML/JSON spec files passed to `create` commands, and the
  `LEPTON_WORKSPACE_ID`, `LEPTON_WORKSPACE_TOKEN`, `LEPTON_WORKSPACE_URL`, and
  `LEPTON_CACHE_DIR` environment variables.
- **Local credential store:** `lep workspace login` saves workspace IDs, URLs,
  and API tokens in `~/.cache/lepton/workspace_info.yaml` (or under
  `LEPTON_CACHE_DIR`), read and written with `yaml.safe_load` / `yaml.safe_dump`
  (`leptonai/api/v2/workspace_record.py`).
- **Workspace API (authenticated, semi-trusted):** HTTPS requests carry the token
  as an `Authorization: Bearer` header (`leptonai/api/v2/client.py`). Responses
  are parsed into Pydantic models (`leptonai/api/v2/types/`). Error output is
  scrubbed of endpoint API-token values before display
  (`leptonai/api/v2/api_resource.py`).
- **Interactive sessions:** `lep ... shell` commands open a WebSocket to the
  workspace and relay the local terminal to a remote process
  (`leptonai/cli/ws_shell.py`). `ssh` commands start local `ssh` or Teleport
  `tsh` processes with an argument list (`leptonai/cli/pod.py`,
  `leptonai/cli/slurm.py`, `leptonai/cli/teleport.py`); none use a shell.
- **Ray job submission:** `lep raycluster` job commands send requests through the
  workspace's Ray dashboard proxy using the Ray `JobSubmissionClient`
  (`leptonai/cli/raycluster.py`).
- **Release pipeline:** GitHub Actions builds, tests, and publishes wheels to
  PyPI (`.github/workflows/release.yaml`, `.github/scripts/check_release.py`).

### Threat Model

The following scenarios are the primary security concerns for this project,
including auxiliary and support code:

1. **Token leakage to an untrusted workspace URL:** The hidden
   `lep workspace login --workspace-url` option and the `LEPTON_WORKSPACE_URL`
   variable accept any URL, and the token is sent to that URL on every request. A user tricked into logging in to an attacker-controlled URL
   gives the attacker their token.
2. **Terminal escape injection from remote output:** Interactive shells and
   `lep log` print remote process output to the local terminal. Malicious escape
   sequences in workload output could spoof terminal content or trigger features
   of terminals that act on escape sequences.
3. **Credential leakage in logs and diagnostics:** Trace logging, error messages,
   and API error bodies can include workspace URLs, resource specs, and secret
   references. The client masks the token in trace output and scrubs endpoint
   API tokens from errors, but new code paths that print raw requests or
   responses could reintroduce leaks.
4. **Release pipeline compromise:** Publishing uses PyPI credentials stored as
   repository secrets in a manually triggered workflow. Compromise of those
   secrets, a maintainer account, or a third-party GitHub Action could publish a
   malicious `leptonai` release to all users.

### Critical Security Assumptions

- **The workspace API enforces authorization.** The CLI's checks (for example,
  Slurm job ownership before `ssh`) are for usability, not access control; the
  server must reject unauthorized requests.
- **The workspace API is trusted.** The CLI acts on data it returns, such as
  connection details and resource specs.
- **The user's home directory and cache directory are private.** No other local
  user can read `~/.cache/lepton` or the directory set by `LEPTON_CACHE_DIR`.
- **The local `ssh`, `tsh`, and Python environment are trusted.** The CLI runs
  the `ssh` and `tsh` binaries found on `PATH` and does not verify them.
- **Spec files and environment variables come from the user.** YAML/JSON specs
  and `LEPTON_*` variables are treated as the user's intent, not as untrusted
  input.
- **The local terminal emulator handles untrusted escape sequences safely.** The
  CLI does not sanitize remote output before printing it.

## Supported Versions

Security fixes are released in new versions of `leptonai` on PyPI. Use the latest
release (`pip install -U leptonai`).
