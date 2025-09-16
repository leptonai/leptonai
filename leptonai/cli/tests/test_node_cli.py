import os
import tempfile
import unittest
from types import SimpleNamespace as NS

from click.testing import CliRunner
from unittest.mock import patch

# Set cache dir to a temp dir before importing CLI
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai.cli import lep as cli  # noqa: E402


def _make_node_group(id_: str, name: str, ready_nodes: int = 1):
    return NS(
        metadata=NS(id_=id_, name=name),
        status=NS(ready_nodes=ready_nodes),
    )


def _make_node(id_: str):
    return NS(
        metadata=NS(id_=id_),
        spec=NS(
            unschedulable=False,
            resource=NS(
                cpu=NS(type_="x86"),
                gpu=NS(product="Fake"),
            ),
        ),
        status=NS(status=["Ready"], workloads=None),
    )


class _FakeNodeGroupAPI:
    def __init__(self, groups, nodes_map):
        self._groups = groups
        self._nodes_map = nodes_map

    def list_all(self):
        return self._groups

    def list_nodes(self, name_or_ng):
        ng_id = name_or_ng if isinstance(name_or_ng, str) else name_or_ng.metadata.id_
        return self._nodes_map.get(ng_id, [])


class _FakeAPIClient:
    def __init__(self, groups, nodes_map):
        self.nodegroup = _FakeNodeGroupAPI(groups, nodes_map)


class TestNodeCli(unittest.TestCase):
    def test_list_deduplicates_when_multiple_filters_match(self):
        # Given a node group whose id matches both filters 'sw-qa' and '200'
        ng = _make_node_group(
            id_="sw-qa-200-1-id",
            name="sw-qa-200-1",
        )
        nodes = [_make_node("node-1")]

        def _fake_client_factory():
            return _FakeAPIClient(groups=[ng], nodes_map={ng.metadata.id_: nodes})

        runner = CliRunner()
        with (
            patch("leptonai.cli.util.get_client", side_effect=_fake_client_factory),
            patch("leptonai.cli.node.get_client", side_effect=_fake_client_factory),
        ):
            result = runner.invoke(cli, ["node", "list", "-ng", "sw-qa", "-ng", "200"])

        self.assertEqual(result.exit_code, 0, msg=result.output)
        # There should be exactly one data row in the table (lines starting with light vertical bar)
        data_rows = [
            line for line in result.output.splitlines() if line.startswith("│")
        ]
        self.assertEqual(len(data_rows), 1, msg=result.output)


if __name__ == "__main__":
    unittest.main()
