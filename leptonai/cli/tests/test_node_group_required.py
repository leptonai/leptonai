"""LEP-7553: create commands need a dedicated node group, as in the dashboard."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from leptonai.cli import lep


def _flat(text):
    return " ".join(text.split())


def _invoke(args, module):
    client = MagicMock()
    with patch(f"leptonai.cli.{module}.APIClient", return_value=client):
        result = CliRunner().invoke(lep, args)
    return result, client


@pytest.mark.parametrize(
    "args, module, workload",
    [
        (
            ["endpoint", "create", "-n", "ep", "--container-image", "nginx"],
            "deployment",
            "Endpoints",
        ),
        (
            ["pod", "create", "-n", "dev", "--resource-shape", "cpu.small"],
            "pod",
            "Pods",
        ),
    ],
)
def test_create_without_node_group_fails_before_any_api_call(args, module, workload):
    result, client = _invoke(args, module)
    assert result.exit_code == 1, result.output
    assert "Missing option '--node-group'" in result.output
    assert f"{workload} must run on a dedicated node group" in _flat(result.output)
    client.deployment.list_all.assert_not_called()
    client.deployment.create.assert_not_called()
    client.pod.create.assert_not_called()


def test_endpoint_create_accepts_node_group_from_spec_file(tmp_path):
    spec = tmp_path / "ep.json"
    spec.write_text(
        json.dumps({
            "container": {"image": "nginx"},
            "resource_requirement": {
                "resource_shape": "cpu.small",
                "affinity": {"allowed_dedicated_node_groups": ["ng-1"]},
            },
        })
    )
    result, _ = _invoke(
        ["endpoint", "create", "-n", "ep", "-f", str(spec)], "deployment"
    )
    assert "Missing option '--node-group'" not in result.output


def test_finetune_create_without_node_group_fails():
    with patch("leptonai.cli.finetune._fetch_template_schema", return_value={}):
        result = CliRunner().invoke(
            lep, ["finetune", "create", "-n", "ft", "--resource-shape", "cpu.small"]
        )
    assert result.exit_code == 1, result.output
    assert "Fine-tune jobs must run on a dedicated node group" in _flat(result.output)
