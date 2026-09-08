"""Tests for the `lep template list` filters."""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
from click.testing import CliRunner

from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.template import LeptonTemplate, LeptonTemplateUserSpec
from leptonai.cli.template import (
    _filter_templates,
    console as template_console,
    template,
)


def _template(name, workload):
    return LeptonTemplate(
        metadata=Metadata(id=f"{name}-id", name=name),
        spec=LeptonTemplateUserSpec(workload_type=workload),
    )


@pytest.fixture
def public_templates():
    return [_template("nemo-train", "job"), _template("Dev-Notebook", "pod")]


@pytest.fixture
def private_templates():
    return [_template("vllm-serve", "deployment"), _template("nemo-eval", "job")]


def _names(items):
    return [item.metadata.name for item in items]


def test_filter_templates_keyword_matches_name_or_id(public_templates):
    assert _names(_filter_templates(public_templates, keyword="NEMO")) == ["nemo-train"]
    assert _names(_filter_templates(public_templates, keyword="notebook-id")) == [
        "Dev-Notebook"
    ]


def test_filter_templates_workload_treats_endpoint_and_deployment_alike(
    private_templates,
):
    assert _names(_filter_templates(private_templates, workloads=["endpoint"])) == [
        "vllm-serve"
    ]
    assert _names(_filter_templates(private_templates, workloads=["deployment"])) == [
        "vllm-serve"
    ]
    assert _names(_filter_templates(private_templates, workloads=["job", "pod"])) == [
        "nemo-eval"
    ]
    assert _filter_templates(private_templates, workloads=["pod"], keyword="nemo") == []


def _invoke(public_items, private_items, args):
    fake_client = SimpleNamespace(
        template=SimpleNamespace(
            list_public=Mock(return_value=public_items),
            list_private=Mock(return_value=private_items),
        )
    )
    with patch("leptonai.cli.template.APIClient", return_value=fake_client):
        result = CliRunner().invoke(template, ["list", *args])
    return result, fake_client.template


def test_template_list_applies_filters_across_public_and_private(
    public_templates, private_templates, monkeypatch
):
    monkeypatch.setattr(template_console, "width", 240)
    result, _ = _invoke(
        public_templates, private_templates, ["-w", "job", "-q", "nemo"]
    )
    assert result.exit_code == 0, result.output
    assert "nemo-train" in result.output
    assert "nemo-eval" in result.output
    assert "Dev-Notebook" not in result.output
    assert "vllm-serve" not in result.output


def test_template_list_private_only_skips_the_public_collection(
    public_templates, private_templates, monkeypatch
):
    monkeypatch.setattr(template_console, "width", 240)
    result, api = _invoke(public_templates, private_templates, ["--private"])
    assert result.exit_code == 0, result.output
    api.list_public.assert_not_called()
    assert "vllm-serve" in result.output
    assert "nemo-train" not in result.output


def test_template_list_rejects_public_with_private(public_templates, private_templates):
    result, _ = _invoke(public_templates, private_templates, ["--public", "--private"])
    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_template_list_reports_when_nothing_matches(
    public_templates, private_templates
):
    result, _ = _invoke(
        public_templates, private_templates, ["--workload", "pod", "--search", "vllm"]
    )
    assert result.exit_code == 0, result.output
    assert "No templates match the specified filters." in result.output
