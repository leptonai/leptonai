"""Tests for the `lep secret list` filters."""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
from click.testing import CliRunner

from leptonai.api.v2.types.secret import SecretItem
from leptonai.cli.secret import _filter_secrets, console as secret_console, secret


@pytest.fixture
def secrets():
    return [
        SecretItem(
            name="HF_TOKEN", owner="alice@example.com", visibility="public", tags=["hf"]
        ),
        SecretItem(
            name="SSH_PUBLIC_KEY.alice", owner="alice@example.com", visibility="private"
        ),
        SecretItem(name="ssh_key_bob", owner="bob@example.com", visibility="private"),
        SecretItem(name="LEGACY", owner=None, visibility=None),
    ]


def _names(items):
    return [item.name for item in items]


def test_filter_secrets_keyword_matches_name_case_insensitively(secrets):
    assert _names(_filter_secrets(secrets, keyword="ssh")) == [
        "SSH_PUBLIC_KEY.alice",
        "ssh_key_bob",
    ]
    assert _filter_secrets(secrets, keyword="hf", owners=["bob"]) == []


def test_filter_secrets_owner_prefix_and_visibility(secrets):
    assert _names(_filter_secrets(secrets, owners=["ALICE"])) == [
        "HF_TOKEN",
        "SSH_PUBLIC_KEY.alice",
    ]
    assert _names(_filter_secrets(secrets, visibility="private")) == [
        "SSH_PUBLIC_KEY.alice",
        "ssh_key_bob",
    ]
    assert _names(_filter_secrets(secrets, owners=["alice"], visibility="public")) == [
        "HF_TOKEN"
    ]
    assert _filter_secrets(secrets, visibility="public", owners=["legacy"]) == []


def _invoke(items, args):
    fake_client = SimpleNamespace(secret=SimpleNamespace(list_all=lambda: list(items)))
    with patch("leptonai.cli.secret.APIClient", return_value=fake_client):
        return CliRunner().invoke(secret, ["list", *args])


def test_secret_list_applies_filters(secrets, monkeypatch):
    monkeypatch.setattr(secret_console, "width", 240)
    result = _invoke(secrets, ["-q", "ssh", "--visibility", "Private", "-u", "alice"])
    assert result.exit_code == 0, result.output
    assert "SSH_PUBLIC_KEY.alice" in result.output
    assert "ssh_key_bob" not in result.output
    assert "HF_TOKEN" not in result.output


def test_secret_list_reports_when_nothing_matches(secrets):
    result = _invoke(secrets, ["--owner", "carol"])
    assert result.exit_code == 0, result.output
    assert "No secrets match the specified filters." in result.output


def test_secret_list_rejects_unknown_visibility(secrets):
    result = _invoke(secrets, ["--visibility", "internal"])
    assert result.exit_code == 2
    assert "Invalid value for '--visibility'" in result.output
