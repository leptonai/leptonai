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


def test_filter_secrets_keyword_matches_name_only(secrets):
    # The dashboard searches secret names only, not tags.
    assert _names(_filter_secrets(secrets, keyword="HF")) == ["HF_TOKEN"]
    secrets[1].tags = ["github"]
    assert _filter_secrets(secrets, keyword="git") == []


def test_filter_secrets_owner_exact_and_visibility(secrets):
    # The dashboard matches the owner exactly and case-sensitively.
    assert _names(_filter_secrets(secrets, owners=["alice@example.com"])) == [
        "HF_TOKEN",
        "SSH_PUBLIC_KEY.alice",
    ]
    assert _filter_secrets(secrets, owners=["alice"]) == []
    assert _filter_secrets(secrets, owners=["ALICE@example.com"]) == []
    assert _names(_filter_secrets(secrets, visibility="private")) == [
        "SSH_PUBLIC_KEY.alice",
        "ssh_key_bob",
    ]
    assert _names(
        _filter_secrets(secrets, owners=["alice@example.com"], visibility="public")
    ) == ["HF_TOKEN"]
    assert _filter_secrets(secrets, visibility="public", owners=["legacy"]) == []


def _invoke(items, args):
    fake_client = SimpleNamespace(secret=SimpleNamespace(list_all=lambda: list(items)))
    with patch("leptonai.cli.secret.APIClient", return_value=fake_client):
        return CliRunner().invoke(secret, ["list", *args])


def test_secret_list_applies_filters(secrets, monkeypatch):
    monkeypatch.setattr(secret_console, "width", 240)
    result = _invoke(
        secrets,
        ["-q", "ssh", "--visibility", "Private", "-u", "alice@example.com"],
    )
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


def _invoke_remove(items, name):
    client = SimpleNamespace(
        secret=SimpleNamespace(
            list_all=lambda: items, delete=lambda n: setattr(client, "deleted", n)
        )
    )
    with patch("leptonai.cli.secret.APIClient", return_value=client):
        result = CliRunner().invoke(secret, ["remove", "-n", name])
    return result, client


def test_remove_missing_secret_exits_non_zero_with_suffix_hint(secrets):
    # LEP-7619: the delete API returns 200 for a missing key.
    result, client = _invoke_remove(secrets, "SSH_PUBLIC_KEY")
    assert result.exit_code == 1, result.output
    assert "does not exist" in result.output
    assert "Did you mean SSH_PUBLIC_KEY.alice?" in result.output
    assert not hasattr(client, "deleted")


def test_remove_missing_secret_without_candidates(secrets):
    result, _ = _invoke_remove(secrets, "nope")
    assert result.exit_code == 1, result.output
    assert "Did you mean" not in result.output


def test_remove_existing_secret(secrets):
    result, client = _invoke_remove(secrets, "HF_TOKEN")
    assert result.exit_code == 0, result.output
    assert client.deleted == "HF_TOKEN"
