from unittest import mock

import pytest

from leptonai.api.v2.workspace_record import WorkspaceRecord, _LocalWorkspaceRecord


@pytest.mark.parametrize("workspace_id", [None, "missing-workspace"])
def test_refresh_token_expiry_returns_none_for_missing_workspace(workspace_id):
    with mock.patch.object(
        WorkspaceRecord, "_singleton_record", _LocalWorkspaceRecord()
    ):
        assert WorkspaceRecord.refresh_token_expires_at(workspace_id) is None
