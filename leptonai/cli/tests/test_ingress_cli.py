import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from loguru import logger

from leptonai import config
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.ingress import (
    LeptonIngress,
    LeptonIngressStatus,
    LeptonIngressUserSpec,
)
from leptonai.cli import lep as cli
from leptonai.cli.ingress import _filter_ingresses, console as ingress_console, ingress

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestIngressCliLocal(unittest.TestCase):
    def test_ingress_import(self):
        """Test that ingress commands can be imported without errors."""
        runner = CliRunner()

        # Test ingress help command works
        result = runner.invoke(cli, ["ingress", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ingress", result.output.lower())

    def test_ingress_list_no_auth(self):
        """Test that ingress list fails gracefully when not authenticated."""
        runner = CliRunner()

        # Should fail because not authenticated, but should not crash
        result = runner.invoke(cli, ["ingress", "list"])
        # Exit code will be non-zero due to auth failure
        self.assertNotEqual(result.exit_code, 0)

    def test_add_endpoint_help(self):
        """Test that add-endpoint command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "add-endpoint", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("add-endpoint", result.output.lower())
        self.assertIn("canary", result.output.lower())

    def test_update_endpoint_help(self):
        """Test that update-endpoint command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "update-endpoint", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("update-endpoint", result.output.lower())

    def test_set_endpoints_help(self):
        """Test that set-endpoints command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "set-endpoints", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("set-endpoints", result.output.lower())

    def test_remove_endpoint_help(self):
        """Test that remove-endpoint command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "remove-endpoint", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("remove-endpoint", result.output.lower())


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# `lep ingress list` filters (pytest style)
# ---------------------------------------------------------------------------


def _ingress(name, domain, *, validation_status=None, message=None):
    return LeptonIngress(
        metadata=Metadata(id=f"{name}-id", name=name, created_at=1000),
        spec=LeptonIngressUserSpec(domain_name=domain),
        status=LeptonIngressStatus(
            validation_status=validation_status, message=message
        ),
    )


@pytest.fixture
def ingresses():
    return [
        _ingress(
            "default-li-api",
            "ws-api.example.run",
            validation_status="active",
            message="domain name active",
        ),
        _ingress(
            "custom-shop",
            "Shop.Example.com",
            validation_status="failed",
            message="dns check failed",
        ),
        _ingress("custom-new", "new.example.com", validation_status=None, message="-"),
    ]


def _ingress_names(items):
    return [item.metadata.name for item in items]


def test_filter_ingresses_keyword_matches_domain_name_or_id(ingresses):
    assert _ingress_names(_filter_ingresses(ingresses, keyword="EXAMPLE.COM")) == [
        "custom-shop",
        "custom-new",
    ]
    assert _ingress_names(_filter_ingresses(ingresses, keyword="default-li")) == [
        "default-li-api"
    ]
    assert _ingress_names(_filter_ingresses(ingresses, keyword="shop-id")) == [
        "custom-shop"
    ]


def test_filter_ingresses_status_treats_missing_as_pending(ingresses):
    assert _ingress_names(_filter_ingresses(ingresses, statuses=["pending"])) == [
        "custom-new"
    ]
    assert _ingress_names(
        _filter_ingresses(ingresses, statuses=["Active", "FAILED"])
    ) == ["default-li-api", "custom-shop"]
    assert _filter_ingresses(ingresses, statuses=["active"], keyword="shop") == []


def _invoke_ingress_list(items, args):
    fake_client = SimpleNamespace(ingress=SimpleNamespace(list_all=lambda: items))
    with patch("leptonai.cli.ingress.APIClient", return_value=fake_client):
        return CliRunner().invoke(ingress, ["list", *args])


def test_ingress_list_applies_filters(ingresses, monkeypatch):
    monkeypatch.setattr(ingress_console, "width", 240)
    result = _invoke_ingress_list(
        ingresses, ["-q", "example.com", "--status", "Failed"]
    )
    assert result.exit_code == 0, result.output
    assert "custom-shop" in result.output
    assert "custom-new" not in result.output
    assert "default-li-api" not in result.output


def test_ingress_list_reports_when_nothing_matches(ingresses):
    result = _invoke_ingress_list(
        ingresses, ["--status", "pending", "--search", "shop"]
    )
    assert result.exit_code == 0, result.output
    assert "No ingress entries match the specified filters." in result.output


def test_ingress_list_rejects_unknown_status(ingresses):
    result = _invoke_ingress_list(ingresses, ["--status", "bogus"])
    assert result.exit_code == 2
    assert "Invalid value for '--status'" in result.output
