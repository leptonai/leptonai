r"""Opt-in GPU qualification through the real CLI, API and Lepton ingress.

This module does not construct a client or read credentials unless explicitly
enabled. Run cases sequentially (no pytest-xdist) against a JSON configuration
kept outside the repository:

    LEPTON_DYNAMO_INTEGRATION=1 LEPTON_DYNAMO_TEST_CONFIG=/abs/dynamo-test.json \
      uv run --no-sync python -m pytest -v --no-cov \
      leptonai/cli/tests/integration/test_dynamo_multinode.py

Configuration keys (exact constraints are asserted below):

- workspace_id, workspace_url, node_group: target workspace and node group.
- frontend_shape, worker_shape, gpus_per_node: shapes in that node group; the
  worker shape must report exactly gpus_per_node whole GPUs.
- nodes (default 2) and update_nodes (> nodes): worker nodes per group before
  and after the node-count update. Without update_nodes the case stops after
  the base flow and is skipped as incomplete.
- max_nodes, max_gpus: budgets for peak worker pods plus the frontend, and for
  their GPU requests.
- platform_versions: deployed platform/runtime versions recorded in the report.
- cases: e.g. "vllm-aggregated", "trtllm-disaggregated"; case_overrides maps a
  case to setting overrides. ready_timeout_seconds defaults to 900.

Never put tokens in the configuration: the workspace token comes from
LEPTON_WORKSPACE_TOKEN or the `lep login` record, and ingress uses
LEPTON_DYNAMO_INFERENCE_TOKEN when set. A case is skipped, never passed, when
the node group has too few idle GPU nodes. Redacted reports, CLI output and
inference results go to LEPTON_DYNAMO_ARTIFACT_DIR (default: pytest tmp_path).
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import requests


pytestmark = pytest.mark.skipif(
    os.environ.get("LEPTON_DYNAMO_INTEGRATION") != "1",
    reason="GPU integration is opt-in; set LEPTON_DYNAMO_INTEGRATION=1",
)


@pytest.mark.parametrize("framework", ["vllm", "sglang", "trtllm"])
@pytest.mark.parametrize("mode", ["aggregated", "disaggregated"])
def test_dynamo_1_3_1_multinode_cli(framework, mode, tmp_path):
    from leptonai.api.v2.api_resource import ClientError
    from leptonai.api.v2.client import APIClient

    config_path = os.environ.get("LEPTON_DYNAMO_TEST_CONFIG")
    assert (
        config_path
    ), "Set LEPTON_DYNAMO_TEST_CONFIG to a reviewed JSON configuration."
    config = json.loads(Path(config_path).read_text())
    case = f"{framework}-{mode}"
    if case not in config["cases"]:
        pytest.skip(f"{case} is not selected in the test configuration")
    config = {**config, **config.get("case_overrides", {}).get(case, {})}
    for key in (
        "workspace_id",
        "workspace_url",
        "node_group",
        "frontend_shape",
        "worker_shape",
        "gpus_per_node",
        "max_nodes",
        "max_gpus",
        "platform_versions",
    ):
        assert config.get(key), f"Missing required test setting: {key}"
    nodes = config.get("nodes", 2)
    update_nodes = config.get("update_nodes")
    assert type(nodes) is int and nodes >= 2
    assert type(config["gpus_per_node"]) is int and config["gpus_per_node"] > 0
    assert update_nodes is None or (type(update_nodes) is int and update_nodes > nodes)
    workers = (
        ["worker"] if mode == "aggregated" else ["prefill-worker", "decode-worker"]
    )
    peak_nodes = max(nodes, update_nodes or nodes) * len(workers)
    assert (
        peak_nodes + 1 <= config["max_nodes"]
    ), "Worker pods plus frontend exceed max_nodes"
    assert (
        peak_nodes * config["gpus_per_node"] <= config["max_gpus"]
    ), "GPU budget exceeded"
    timeout = config.get("ready_timeout_seconds", 900)
    assert 30 <= timeout <= 3600
    name = f"cli-dyn-{framework}-{uuid4().hex[:12]}"
    artifacts = Path(os.environ.get("LEPTON_DYNAMO_ARTIFACT_DIR", str(tmp_path))) / name
    artifacts.mkdir(parents=True, mode=0o700)
    client = APIClient(workspace_id=config["workspace_id"], url=config["workspace_url"])
    inference_token = (
        os.environ.get("LEPTON_DYNAMO_INFERENCE_TOKEN") or client.auth_token
    )
    secrets = [token for token in (client.auth_token, inference_token) if token]

    def redact(value):
        if isinstance(value, dict):
            return {
                key: (
                    "[REDACTED]"
                    if any(
                        word in key.lower()
                        for word in ("token", "password", "authorization")
                    )
                    else redact(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, str):
            for secret in secrets:
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", value)
        return value

    def save(filename, value):
        path = artifacts / filename
        path.write_text(json.dumps(redact(value), indent=2, default=str) + "\n")
        path.chmod(0o600)

    env = {
        **os.environ,
        "LEPTON_WORKSPACE_ID": config["workspace_id"],
        "LEPTON_WORKSPACE_URL": config["workspace_url"],
    }
    if client.auth_token:
        env["LEPTON_WORKSPACE_TOKEN"] = client.auth_token
    cli_calls = []

    def cli(*args):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from leptonai.cli import lep; lep()",
                "dynamo",
                *args,
            ],
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
        )
        cli_calls.append({
            "args": args,
            "code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
        save("cli.json", cli_calls)
        assert result.returncode == 0, redact(result.stdout + result.stderr)
        return result.stdout

    report = {"case": case, "name": name, "config": config, "outcome": "started"}
    report["cli_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        cwd=Path(__file__).resolve().parents[4],
    ).strip()
    report["cli_dirty"] = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        ).strip()
    )
    snapshots = []

    def snapshot():
        dep = client.dynamo.get(name)
        replicas = {
            service: client.dynamo.list_service_replicas(name, service).replicas
            for service in ["frontend", *workers]
        }
        snapshots.append({
            "time": time.time(),
            "status": dep.status.model_dump(mode="json") if dep.status else None,
            "replicas": {
                key: [r.model_dump(mode="json", by_alias=True) for r in values]
                for key, values in replicas.items()
            },
        })
        save("snapshots.json", snapshots)
        return dep, replicas

    def wait_ready(count):
        deadline = time.monotonic() + timeout
        stable = 0
        observed = {service: set() for service in ["frontend", *workers]}
        while time.monotonic() < deadline:
            dep, replicas = snapshot()
            ready = bool(dep.status and dep.status.state == "Ready")
            for service, pods in replicas.items():
                expected = 1 if service == "frontend" else count
                observed[service].update(p.metadata.id_ or p.id_ for p in pods)
                ready = (
                    ready
                    and len(pods) == expected
                    and all(
                        p.status
                        and p.status.readiness_issue
                        and p.status.readiness_issue.reason == "Ready"
                        for p in pods
                    )
                )
                if service != "frontend":
                    node_ids = {
                        p.status.node.id_ or p.status.node.name
                        for p in pods
                        if p.status and p.status.node
                    }
                    ready = ready and None not in node_ids and len(node_ids) == expected
            stable = stable + 1 if ready else 0
            if stable >= 3:
                for service, pods in replicas.items():
                    assert len(observed[service]) == len(
                        pods
                    ), f"{service} pods were replaced during startup; inspect snapshots"
                    assert all(
                        not (p.status.container_status or {}).get("restart_count", 0)
                        for p in pods
                    ), f"{service} restarted during startup"
                return dep, replicas
            time.sleep(10)
        pytest.fail(
            f"Not stably Ready on {count} distinct physical nodes per worker within"
            f" {timeout}s; artifacts: {artifacts}"
        )

    def infer(dep, phase):
        endpoint = (
            dep.status.endpoint.external_endpoint
            if dep.status and dep.status.endpoint
            else None
        )
        assert endpoint and endpoint.startswith(
            "https://"
        ), "Expected the normal HTTPS Lepton ingress"
        base_url = endpoint.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
        headers = (
            {"Authorization": f"Bearer {inference_token}"} if inference_token else {}
        )
        response = requests.get(
            base_url + "/models", headers=headers, timeout=120, allow_redirects=False
        )
        assert response.status_code == 200, f"models HTTP {response.status_code}"
        models = response.json()
        model = "Qwen/Qwen3-0.6B"
        assert any(item.get("id") == model for item in models["data"]), models

        def completion(_):
            response = requests.post(
                base_url + "/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Say hello briefly. /no_think"}
                    ],
                    "max_tokens": 128,
                    "stream": False,
                },
                timeout=120,
                allow_redirects=False,
            )
            assert (
                response.status_code == 200
            ), f"completion HTTP {response.status_code}"
            body = response.json()
            assert body["choices"][0]["message"].get("content", "").strip(), body
            return body

        completions = [completion(0), completion(1)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            completions.extend(pool.map(completion, range(4)))
        save(f"inference-{phase}.json", {"models": models, "completions": completions})

    attempted_create = False
    try:
        group = client.nodegroup.get(config["node_group"])
        report["quota_enabled"] = group.status.quota_enabled
        available_nodes = client.nodegroup.list_idle_nodes(config["node_group"])
        report["idle_nodes"] = [n.metadata.id_ for n in available_nodes]
        eligible = [
            n
            for n in available_nodes
            if not n.spec.unschedulable
            and n.spec.resource
            and n.spec.resource.gpu
            and (n.spec.resource.gpu.total or 0) >= config["gpus_per_node"]
        ]
        if len(eligible) < peak_nodes:
            report["outcome"] = "blocked_capacity"
            pytest.skip(
                f"Need {peak_nodes} idle GPU nodes in {config['node_group']}; found"
                f" {len(eligible)}"
            )
        shapes = client.shapes.list_shapes(
            node_group=config["node_group"], purpose="deployment"
        )
        shape = next(
            s
            for s in shapes
            if config["worker_shape"] in (s.metadata.id_, s.metadata.name, s.spec.name)
        )
        assert shape.spec.accelerator_num == config["gpus_per_node"]
        assert shape.spec.accelerator_fraction in (None, 0, 1)
        report["shape"] = shape.model_dump(mode="json", by_alias=True)
        args = ["-n", name, "--framework", framework, "--serving-mode", mode]
        services = [
            "-svc",
            "frontend",
            "--resource-shape",
            config["frontend_shape"],
            "--node-group",
            config["node_group"],
        ]
        for worker in workers:
            services.extend([
                "-svc",
                worker,
                "--resource-shape",
                config["worker_shape"],
                "--node-count",
                str(nodes),
            ])
        preview = json.loads(cli("create", *args, "--dry-run", *services))
        assert preview["spec"]["dynamo_version"] == "1.3.1"
        for worker in workers:
            assert preview["spec"]["services"][worker]["multinode"] == {
                "node_count": nodes
            }
        save("request.json", preview)
        # Check ownership before creating so cleanup cannot delete an existing deployment.
        try:
            client.dynamo.get(name)
        except ClientError as exc:
            assert exc.response.status_code == 404
        else:
            pytest.fail(f"Generated test name already exists: {name}")
        attempted_create = True
        cli("create", *args, *services)
        dep, replicas = wait_ready(nodes)
        for worker in workers:
            actual = dep.spec.services[worker]
            assert actual.multinode.node_count == nodes
            assert (
                actual.extra_pod_spec.main_container.command
                == preview["spec"]["services"][worker]["extra_pod_spec"][
                    "main_container"
                ]["command"]
            )
            assert actual.extra_pod_spec.main_container.image.endswith(":1.3.1")
        infer(dep, "created")
        cli("status", "-n", name)
        cli("service", "list", "-n", name)
        cli("replica", "list", "-n", name)
        for service, pods in replicas.items():
            for pod in pods:
                cli(
                    "replica",
                    "log",
                    "-n",
                    name,
                    "-s",
                    service,
                    "-r",
                    pod.metadata.id_ or pod.id_,
                    "--tail",
                    "100",
                )
        before = dep.spec.model_dump(mode="json")
        cli(
            "update",
            "-n",
            name,
            "--dry-run",
            "-svc",
            workers[0],
            "--node-count",
            str(update_nodes or nodes + 2),
        )
        assert client.dynamo.get(name).spec.model_dump(mode="json") == before
        report["create_inference_logs_dryrun"] = "passed"
        if update_nodes is None:
            report["outcome"] = "inference_passed_update_not_run"
            pytest.skip(
                "Base flow passed; update_nodes is required for full qualification"
            )
        update_args = []
        for worker in workers:
            update_args.extend(["-svc", worker, "--node-count", str(update_nodes)])
        cli("update", "-n", name, "-y", *update_args)
        dep, _ = wait_ready(update_nodes)
        for worker in workers:
            assert dep.spec.services[worker].multinode.node_count == update_nodes
            assert (
                dep.spec.services[worker].extra_pod_spec.main_container.command
                != before["services"][worker]["extra_pod_spec"]["main_container"][
                    "command"
                ]
            )
        infer(dep, "updated")
        report["outcome"] = "passed"
    except BaseException as exc:
        if not isinstance(exc, pytest.skip.Exception):
            report["outcome"] = "failed"
            report["error"] = str(exc)
        raise
    finally:
        try:
            if attempted_create:
                try:
                    _, final_replicas = snapshot()
                    for service, pods in final_replicas.items():
                        for pod in pods:
                            pod_id = pod.metadata.id_ or pod.id_
                            try:
                                log = client.dynamo.get_replica_log(
                                    name, pod_id, service=service, tail=100
                                )
                                save(
                                    f"final-log-{pod_id}.json",
                                    log.model_dump(mode="json"),
                                )
                            except Exception as exc:
                                save(f"final-log-{pod_id}.json", {"error": str(exc)})
                    for worker in workers:
                        save(
                            f"service-{worker}.json",
                            client.dynamo.get_service(name, worker).model_dump(
                                mode="json"
                            ),
                        )
                except Exception as exc:
                    report["diagnostics_error"] = str(exc)
                try:
                    client.dynamo.get(name)
                except ClientError as exc:
                    assert exc.response.status_code == 404
                else:
                    cli("remove", "-n", name, "-y")
                deadline = time.monotonic() + 180
                while True:
                    try:
                        client.dynamo.get(name)
                    except ClientError as exc:
                        assert exc.response.status_code == 404
                        report["cleanup"] = "404 confirmed"
                        break
                    assert time.monotonic() < deadline, f"Cleanup timed out for {name}"
                    time.sleep(5)
        except BaseException as exc:
            report["outcome"] = "failed"
            report["cleanup_error"] = str(exc)
            raise
        finally:
            save("report.json", report)
