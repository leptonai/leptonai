# LEP-6218 Test Strategy and Results

## Authority and traceability

The acceptance criteria in NVIDIA Jira issue LEP-6218 are the authoritative
behavioral specification for these tests. The issue does not define formal
`REQ-*` or `SCN-*` identifiers, so the tests use comments beginning with
`LEP-6218:` and the acceptance-criterion prose. No requirement identifiers are
invented.

The server-side contracts in MR !8876 are supporting wire-format context:

- `spec.api_tokens` remains the API-token field.
- `spec.allow_unauthenticated_access` records explicit opt-out.
- normal create/get/update responses may contain literal API tokens.
- the compatibility `create()` method remains a boolean status operation.
- `create_with_response()` is strict by default; explicit rollout tolerance
  accepts only a blank/whitespace or `{}` legacy response as boolean success.

## Strategy

The suite verifies behavior at three independent public boundaries:

1. Click command scenarios invoke `lep endpoint ...` and the hidden
   `lep deployment ...` compatibility group through `CliRunner`. A fake public
   `APIClient` records submitted models and supplies controlled workspace info
   and full create/update responses.
2. SDK contract tests use `responses` around the real public `APIClient`, then
   inspect HTTP requests, boolean `create()` results, and token-bearing
   `create_with_response()` models for both legacy `/deployments` and new
   `/endpoints` routing.
3. Translation/model tests operate on public conversion functions and Pydantic
   serialization to verify `true`, `false`, and absent values, including
   GET/export/file round trips.

No live workspace or external mutation is used. Every test sets a temporary
Lepton cache directory before importing the client.

## Mocking and fixtures

- CLI: `CliRunner`, a feature-aware fake `APIClient`, and `Mock` deployment API
  methods (`list_all`, `validate_create`, `create`, `create_with_response`,
  `get`, `update`, and status readiness/termination methods).
- HTTP: `responses` intercepts `/workspace`, `/deployments`, and `/endpoints`.
- API families: `features.enable_new_deployment_api` selects the route; the
  independent `features.enable_secure_endpoint_defaults` field is included in
  workspace responses.
- Secrets: unique sentinel literals make accidental disclosure assertions
  unambiguous.
- Logging: a temporary Loguru sink at `TRACE` captures request/response trace
  output. The SDK/CLI has no separate direct telemetry sink in this path; HTTP
  request bodies are asserted separately as the intended transport channel.

## Acceptance coverage

| LEP-6218 acceptance behavior | Automated coverage |
|---|---|
| Feature-enabled default defers token generation and has no misleading warning | `TestSecureEndpointCreateCLI.test_default_create_prints_generated_token_without_logging_it`; `TestSecureEndpointCreateContract.test_create_with_response_returns_token_model_for_both_api_families` |
| Generated token is clearly labelled/copyable and absent from logs, traces, and errors | CLI generated-token and update TRACE-redaction tests; status detail redacts unless `--show-tokens` is explicit; malformed-success, marked-error, and markerless downstream-error contract tests |
| Repeatable `--tokens` preserves caller values without requesting generation | CLI supplied-token matrix covers secure flag true/false/absent and verifies create omits the opt-out field; create contract matrix covers explicit SDK fields |
| Explicit opt-out sends `true` plus `[]`, warns, and conflicts with tokens | CLI create/update opt-out and conflict tests; contract create/update matrices |
| `--public` changes only network reachability | CLI create/update public-independence tests; status scenarios independently report public reachability and token authentication |
| Unrelated updates preserve authentication state | CLI sparse-update test; cross-family HTTP omission test |
| Protected/unauthenticated transitions are atomic | CLI and cross-family HTTP transition matrices |
| File and API translations retain explicit mode | CLI file precedence tests; translation true/false/absent tests; GET/export/reload contract test |
| Feature-disabled or absent secure-default flag retains legacy behavior | CLI disabled/missing matrix sends the legacy payload and calls response-preserving create with narrow legacy tolerance |
| Failed workspace discovery never guesses an auth default | Undecided create aborts before mutation with a generic token-free error; explicit CLI auth modes proceed without calling workspace info |
| Discovery/server rollout mismatch cannot lose a credential | A stale false discovery still surfaces a token-bearing server response; a secure true discovery with no returned token exits with an explicit post-create recovery command |
| Both visible endpoint commands and hidden deployment aliases | Every core CLI scenario iterates both command groups |
| Both legacy and new API families | Every SDK contract scenario iterates `/deployments` and `/endpoints` |
| Hidden `--remove-tokens` cannot silently opt out | CLI rejection/directive test and help visibility test |
| Endpoint opt-out is never applied to DevPods | Pod-shaped files with explicit true/false and CLI opt-out reject before API access without printing the opt-out warning |
| Existing SDK create compatibility is preserved | `create()` returns literal `True` for successful empty/malformed bodies; strict `create_with_response()` returns a token-bearing model or generic error; explicit tolerance returns `True` only for blank/whitespace or `{}` and still rejects arbitrary/token-bearing malformed bodies |
| Workspace feature model is strict | `TestWorkspaceFlagSchema.test_secure_endpoint_defaults_flag_accepts_only_strict_booleans` |

## Security and adversarial coverage

| Category | Coverage |
|---|---|
| Boundary | secure flag true/false/absent; auth mode true/false/absent; empty/one/multiple tokens; public/restricted reachability |
| Invalid input | conflicting CLI modes; invalid file with tokens plus opt-out; endpoint-only auth on pod-shaped files; hidden token removal |
| Failure injection | workspace-info exception with undecided and decisive auth; rollout discovery/server mismatch; narrow empty-response tolerance; arbitrary/token-bearing malformed 2xx responses; 4xx/5xx create responses |
| Security | literal only in designated create stdout; Loguru trace redaction; body-free decode errors; marker-bearing and markerless `ClientError`/`ServerError` response redaction |

Thread-level races and resource-exhaustion cases are not applicable to this
stateless CLI/model translation change. The relevant rollout-time
feature-discovery/create mismatch is covered explicitly. Authentication
authorization itself is enforced by the server/data plane and remains outside
this repository's test boundary.

## Files

| File | Purpose |
|---|---|
| `leptonai/cli/tests/test_secure_endpoint_auth_cli.py` | User-level CLI scenarios and secret-output assertions |
| `leptonai/api/v2/tests/test_secure_endpoint_auth_contract.py` | Public SDK/wire contracts for both API families |
| `leptonai/api/v2/tests/test_new_api_translation_regressions.py` | Translation/model/export round trips |
| `leptonai/api/v2/tests/test_new_api_flag_cache.py` | Strict workspace feature schema |
| `leptonai/cli/tests/test_new_api_cli_regressions.py` | Existing rerun dispatch updated to preserve the create response and explicit legacy tolerance |

## Verification results

The final regression selection covers every v2 API test plus the existing and
new endpoint/deployment CLI suites:

```text
/Users/kennethd/leptonai/activate/bin/python -m pytest --no-cov -q leptonai/api/v2/tests leptonai/cli/tests/test_deployment_cli.py leptonai/cli/tests/test_new_api_cli_regressions.py leptonai/cli/tests/test_secure_endpoint_auth_cli.py
```

Result: **200 passed, 120 warnings in 16.19s**. The warnings are pre-existing
Pydantic/deprecation notices plus the expected `RuntimeWarning` exercised by
the boolean-create compatibility tests. No test is skipped.

An independent full-package check with `pytest --no-cov -q leptonai` reported
**298 passed and one unrelated environment-dependent failure** in
`leptonai/util/tests/test_s3cache.py`: this workstation has an
`~/.aws/credentials` file but does not have `boto3` installed, leading to a
`NameError`. AWS credentials were not accessed and no AWS dependency was
installed; the impacted 200-test selection above is fully green.

Changed-line coverage was generated from that run and enforced against
`origin/main`:

```text
/Users/kennethd/leptonai/activate/bin/python -m pytest -q -o addopts= --cov=leptonai --cov-report=xml:/tmp/lep6218-coverage.xml leptonai/api/v2/tests leptonai/cli/tests/test_deployment_cli.py leptonai/cli/tests/test_new_api_cli_regressions.py leptonai/cli/tests/test_secure_endpoint_auth_cli.py
uv run --no-project --with diff-cover diff-cover /tmp/lep6218-coverage.xml --compare-branch=origin/main --fail-under=80
```

Result: **87% diff coverage** (510 changed executable lines, 62 uncovered),
above the required 80% threshold.

The two dedicated LEP-6218 suites were also executed in ten fresh Python
processes with this command per run:

```text
/Users/kennethd/leptonai/activate/bin/python -m pytest -q --disable-warnings -o addopts= leptonai/cli/tests/test_secure_endpoint_auth_cli.py leptonai/api/v2/tests/test_secure_endpoint_auth_contract.py
```

Result: all ten runs passed; each run reported **74 passed and 245 subtests
passed**. A Go-style race detector is not applicable to this Python CLI/SDK
change.

Formatting and lint checks:

```text
git diff --name-only -z origin/main -- '*.py' | xargs -0 /Users/kennethd/leptonai/activate/bin/python -m black --check
git diff --name-only -z origin/main -- '*.py' | xargs -0 uvx ruff==0.5.7 check
git diff --check
```

Result: all checks passed.
