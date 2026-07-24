import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from leptonai.api.v2.dedicated_node_groups import DedicatedNodeGroupAPI
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.dedicated_node_group import (
    DedicatedNodeGroup,
    DedicatedNodeGroupSpec,
    DedicatedNodeGroupStatus,
    MountOptions,
    Volume,
)
from leptonai.api.v2.types.storage_data_source import StorageDataSource
from leptonai.api.v2.types.storage_permission import StoragePermission
from leptonai.cli import lep as cli


def _make_node_group():
    local_volume = Volume(**{
        "from": "local",
        "name": "scratch",
        "size_in_gb": 512,
        "creation_mode": "mkdir",
        "from_path": "/srv/scratch",
        "default_mount_path": "/mnt/scratch",
    })
    nfs_volume = Volume(**{
        "from": "nfs",
        "name": "shared-data",
        "size_in_gb": 1024,
        "mount_options": MountOptions(
            mount_workload_type="nfs",
            host_mount_cache_size_in_mib=4096,
        ),
        "creation_mode": "mount",
        "from_path": "/srv/shared-data",
        "default_mount_path": "/mnt/shared-data",
    })
    return DedicatedNodeGroup(
        metadata=Metadata(id="ng-123", name="h100-cluster"),
        spec=DedicatedNodeGroupSpec(
            volumes=[local_volume, nfs_volume],
            enable_object_storage=True,
        ),
        status=DedicatedNodeGroupStatus(),
    )


def _make_object_storage():
    return StorageDataSource(**{
        "metadata": {
            "id": "ws-test/model-data",
            "name": "model-data",
            "created_at": 1784690860,
        },
        "spec": {
            "name": "model-data",
            "workspace": "ws-test",
            "description": "",
            "object": {
                "bucket": "model-bucket",
                "provider": {
                    "type": "s3",
                    "s3": {
                        "endpoint": "https://objects.example.com",
                        "region": "auto",
                    },
                },
                "credentials": {
                    "type": "leptonSecret",
                    "leptonSecret": {
                        "s3Credentials": {
                            "accessKeySecretName": "model-access-key",
                            "secretKeySecretName": "model-secret-key",
                        },
                    },
                },
                "aistore": {"enabled": True},
            },
            "permissions": {
                "allowed_users": ["researcher@example.com"],
            },
        },
        "status": {
            "state": "active",
            "ready": True,
            "observedGeneration": 1,
        },
    })


class _FakeNodeGroupAPI:
    def __init__(self):
        self.node_group = _make_node_group()
        self.object_storage = _make_object_storage()
        self.added_volumes = []
        self.deleted_volumes = []
        self.set_permissions = []
        self.deleted_permissions = []
        self.created_data_sources = []
        self.updated_data_sources = []
        self.deleted_data_sources = []

    def list_all(self):
        return [self.node_group]

    def list_storage_data_sources(self, node_group):
        assert node_group.metadata.id_ == "ng-123"
        return [self.object_storage]

    def get_storage_data_source(self, node_group, data_source_name):
        assert node_group.metadata.id_ == "ng-123"
        assert data_source_name == self.object_storage.metadata.name
        return self.object_storage

    def list_storage_permissions(self, node_group, volume_name):
        assert node_group.metadata.id_ == "ng-123"
        if volume_name == "scratch":
            return []
        assert volume_name == "shared-data"
        return [
            StoragePermission(
                path_prefix="/datasets",
                allowed_users=["researcher@example.com"],
                nodegroup_id="ng-123",
            ),
            StoragePermission(
                path_prefix="/users",
                subfolder_policy="by_user",
                nodegroup_id="ng-123",
            ),
        ]

    def set_storage_permission(self, node_group, volume_name, permission):
        self.set_permissions.append((node_group, volume_name, permission))
        return True

    def delete_storage_permission(self, node_group, volume_name, path_prefix):
        self.deleted_permissions.append((node_group, volume_name, path_prefix))
        return True

    def update_storage_data_source(
        self,
        node_group,
        data_source_name,
        spec,
    ):
        self.updated_data_sources.append((node_group, data_source_name, spec))
        return self.object_storage

    def create_storage_data_source(self, node_group, spec):
        self.created_data_sources.append((node_group, spec))
        return self.object_storage

    def delete_storage_data_source(self, node_group, data_source_name):
        self.deleted_data_sources.append((node_group, data_source_name))
        return True

    def add_volume(self, node_group, volume):
        self.added_volumes.append((node_group, volume))
        return _make_node_group()

    def delete_volume(self, node_group, volume_name):
        self.deleted_volumes.append((node_group, volume_name))
        return _make_node_group()


class _FakeAPIClient:
    def __init__(self, *args, **kwargs):
        self.workspace_id = "ws-test"
        self.nodegroup = _FakeNodeGroupAPI()


def test_storage_list_shows_path_and_preserves_direct_invocation():
    runner = CliRunner()

    with patch("leptonai.cli.node.APIClient", _FakeAPIClient):
        result = runner.invoke(
            cli,
            ["node", "storage", "--node-group", "h100"],
        )

    assert result.exit_code == 0, result.output
    assert "Storage Name" in result.output
    assert "Type" in result.output
    assert "Path" in result.output
    assert result.output.index("Type") < result.output.index("Storage Name")
    assert "shared-data" in result.output
    assert "node-nfs" in result.output
    assert "/srv/shared-data" in result.output
    assert "model-data" in result.output
    assert "object-storage" in result.output
    assert "s3://model-bucket" in result.output


def test_storage_get_prints_full_volume():
    runner = CliRunner()

    with patch("leptonai.cli.node.APIClient", _FakeAPIClient):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "get",
                "--node-group",
                "h100-cluster",
                "--name",
                "shared-data",
            ],
        )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["node_group"] == {"id": "ng-123", "name": "h100-cluster"}
    assert data["storage"]["from"] == "nfs"
    assert data["storage"]["name"] == "shared-data"
    assert data["storage"]["size_in_gb"] == 1024
    assert data["storage"]["from_path"] == "/srv/shared-data"
    assert data["storage"]["default_mount_path"] == "/mnt/shared-data"
    assert data["storage"]["creation_mode"] == "mount"
    assert data["storage"]["mount_options"]["host_mount_cache_size_in_mib"] == 4096


def test_storage_get_reports_missing_volume():
    runner = CliRunner()

    with patch("leptonai.cli.node.APIClient", _FakeAPIClient):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "get",
                "--node-group",
                "ng-123",
                "--name",
                "missing",
            ],
        )

    assert result.exit_code != 0
    assert "Storage 'missing' was not found" in result.output
    assert "shared-data" in result.output
    assert "model-data" in result.output


def test_storage_get_prints_full_object_storage_data_source():
    runner = CliRunner()

    with patch("leptonai.cli.node.APIClient", _FakeAPIClient):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "get",
                "--node-group",
                "ng-123",
                "--name",
                "model-data",
            ],
        )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["storage"]["metadata"]["name"] == "model-data"
    assert data["storage"]["spec"]["object"]["bucket"] == "model-bucket"
    assert data["storage"]["spec"]["object"]["provider"]["type"] == "s3"
    assert data["storage"]["spec"]["permissions"]["allowed_users"] == [
        "researcher@example.com"
    ]
    assert data["storage"]["status"]["state"] == "active"


def test_storage_add_node_local_uses_mkdir_creation_mode():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "add",
                "-ng",
                "ng-123",
                "--type",
                "node-local",
                "--name",
                "cache-local",
                "--path",
                "/mnt/cache-local",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Added node-local storage cache-local" in result.output
    assert len(fake_client.nodegroup.added_volumes) == 1
    node_group, volume = fake_client.nodegroup.added_volumes[0]
    assert node_group.metadata.id_ == "ng-123"
    assert volume.from_.value == "local"
    assert volume.creation_mode.value == "mkdir"
    assert volume.size_in_gb == 0
    assert volume.from_path == "/mnt/cache-local"


def test_storage_add_node_nfs_uses_existing_mount_creation_mode():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "add",
                "-ng",
                "h100-cluster",
                "-t",
                "node-nfs",
                "-n",
                "team-nfs",
                "-p",
                "/volume-02",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Added node-nfs storage team-nfs" in result.output
    _, volume = fake_client.nodegroup.added_volumes[0]
    assert volume.from_.value == "nfs"
    assert volume.creation_mode.value == "none"
    assert volume.size_in_gb == 0
    assert volume.from_path == "/volume-02"


def test_storage_add_s3_compatible_object_storage():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "add",
                "-ng",
                "ng-123",
                "-t",
                "object-storage",
                "-n",
                "training-data",
                "--provider",
                "s3",
                "--bucket",
                "training-bucket",
                "--region",
                "auto",
                "--endpoint",
                "https://objects.example.com",
                "--access-key-secret-name",
                "training-access-key",
                "--secret-key-secret-name",
                "training-secret-key",
                "--user",
                "alice@example.com",
                "--user",
                "bob@example.com",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Added object-storage training-data" in result.output
    assert "s3://training-bucket" in result.output
    assert len(fake_client.nodegroup.created_data_sources) == 1
    node_group, spec = fake_client.nodegroup.created_data_sources[0]
    assert node_group.metadata.id_ == "ng-123"
    assert spec.name == "training-data"
    assert spec.workspace == "ws-test"
    assert spec.object_.bucket == "training-bucket"
    assert spec.object_.provider.type_ == "s3"
    assert spec.object_.provider.s3 == {
        "region": "auto",
        "endpoint": "https://objects.example.com",
    }
    assert spec.object_.credentials == {
        "type": "leptonSecret",
        "leptonSecret": {
            "s3Credentials": {
                "accessKeySecretName": "training-access-key",
                "secretKeySecretName": "training-secret-key",
            },
        },
    }
    assert spec.object_.aistore is None
    assert spec.permissions.allowed_users == [
        "alice@example.com",
        "bob@example.com",
    ]


def test_storage_add_gcs_forces_wif_and_aistore():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "add",
                "-ng",
                "h100-cluster",
                "-t",
                "object-storage",
                "-n",
                "gcs-data",
                "--provider",
                "gcs",
                "--bucket",
                "gcs-bucket",
                "--project-id",
                "gcp-project",
            ],
        )

    assert result.exit_code == 0, result.output
    _, spec = fake_client.nodegroup.created_data_sources[0]
    assert spec.object_.provider.type_ == "gcs"
    assert spec.object_.provider.gcs == {"projectId": "gcp-project"}
    assert spec.object_.credentials == {"type": "wif"}
    assert spec.object_.aistore == {"enabled": True}
    assert spec.permissions is None


def test_storage_add_s3_requires_endpoint():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "add",
                "-ng",
                "ng-123",
                "-t",
                "object-storage",
                "-n",
                "training-data",
                "--provider",
                "s3",
                "--bucket",
                "training-bucket",
                "--region",
                "auto",
                "--wif",
            ],
        )

    assert result.exit_code != 0
    assert "'--endpoint' is required" in result.output
    assert fake_client.nodegroup.created_data_sources == []


def test_storage_edit_object_storage_preserves_immutable_fields():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "edit",
                "-ng",
                "ng-123",
                "-n",
                "model-data",
                "--wif",
                "--user",
                "alice@example.com",
                "--user",
                "bob@example.com",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Updated authentication and bucket allowlist" in result.output
    assert len(fake_client.nodegroup.updated_data_sources) == 1
    node_group, data_source_name, spec = fake_client.nodegroup.updated_data_sources[0]
    assert node_group.metadata.id_ == "ng-123"
    assert data_source_name == "model-data"
    assert spec.object_.bucket == "model-bucket"
    assert spec.object_.provider.type_ == "s3"
    assert spec.object_.provider.s3 == {
        "endpoint": "https://objects.example.com",
        "region": "auto",
    }
    assert spec.object_.aistore == {"enabled": True}
    assert spec.object_.credentials == {"type": "wif"}
    assert spec.permissions.allowed_users == [
        "alice@example.com",
        "bob@example.com",
    ]
    assert (
        fake_client.nodegroup.object_storage.spec.object_.credentials["type"]
        == "leptonSecret"
    )


def test_storage_edit_all_members_clears_allowlist_only():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "edit",
                "-ng",
                "ng-123",
                "-n",
                "model-data",
                "--all-members",
            ],
        )

    assert result.exit_code == 0, result.output
    _, _, spec = fake_client.nodegroup.updated_data_sources[0]
    assert spec.permissions is None
    assert spec.object_.credentials["type"] == "leptonSecret"
    assert spec.object_.aistore == {"enabled": True}


def test_storage_delete_node_volume_with_yes():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "delete",
                "-ng",
                "ng-123",
                "-n",
                "scratch",
                "--yes",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Deleted node-local storage scratch" in result.output
    assert len(fake_client.nodegroup.deleted_volumes) == 1
    node_group, volume_name = fake_client.nodegroup.deleted_volumes[0]
    assert node_group.metadata.id_ == "ng-123"
    assert volume_name == "scratch"


def test_storage_delete_aborts_without_confirmation():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "delete",
                "-ng",
                "ng-123",
                "-n",
                "scratch",
            ],
            input="n\n",
        )

    assert result.exit_code == 0, result.output
    assert "Deletion cancelled." in result.output
    assert fake_client.nodegroup.deleted_volumes == []


def test_storage_delete_rejects_lepton_managed_volume():
    runner = CliRunner()
    fake_client = _FakeAPIClient()
    fake_client.nodegroup.node_group.spec.volumes[0].managed_by_lepton = True

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "delete",
                "-ng",
                "ng-123",
                "-n",
                "scratch",
                "--yes",
            ],
        )

    assert result.exit_code != 0
    assert "managed by Lepton" in result.output
    assert fake_client.nodegroup.deleted_volumes == []


def test_storage_delete_object_storage_with_yes():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "delete",
                "-ng",
                "ng-123",
                "-n",
                "model-data",
                "--yes",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Deleted object-storage model-data" in result.output
    assert fake_client.nodegroup.deleted_volumes == []
    assert len(fake_client.nodegroup.deleted_data_sources) == 1
    node_group, data_source_name = fake_client.nodegroup.deleted_data_sources[0]
    assert node_group.metadata.id_ == "ng-123"
    assert data_source_name == "model-data"


def test_node_group_volume_api_uses_dedicated_routes_and_payload():
    transport = Mock()
    response = Mock(status_code=200, text="")
    response.json.return_value = _make_node_group().model_dump(
        mode="json",
        by_alias=True,
    )
    transport._post.return_value = response
    transport._delete.return_value = response
    api = DedicatedNodeGroupAPI(transport)
    volume = Volume(**{
        "from": "local",
        "name": "cache-local",
        "size_in_gb": 0,
        "creation_mode": "mkdir",
        "from_path": "/mnt/cache-local",
    })

    api.add_volume("ng-123", volume)
    transport._post.assert_called_once()
    add_call = transport._post.call_args
    assert add_call.args[0] == "/dedicated-node-groups/ng-123/volumes"
    assert add_call.kwargs["json"]["from"] == "local"
    assert add_call.kwargs["json"]["name"] == "cache-local"
    assert add_call.kwargs["json"]["size_in_gb"] == 0
    assert add_call.kwargs["json"]["creation_mode"] == "mkdir"
    assert add_call.kwargs["json"]["from_path"] == "/mnt/cache-local"

    api.delete_volume("ng-123", "cache/local")
    transport._delete.assert_called_once_with(
        "/dedicated-node-groups/ng-123/volumes/cache%2Flocal"
    )


def test_node_group_object_storage_api_uses_dedicated_routes_and_payload():
    transport = Mock()
    response = Mock(status_code=200, text="")
    response.json.return_value = _make_object_storage().model_dump(
        mode="json",
        by_alias=True,
    )
    transport._post.return_value = response
    transport._delete.return_value = response
    api = DedicatedNodeGroupAPI(transport)
    spec = _make_object_storage().spec

    api.create_storage_data_source("ng-123", spec)
    transport._post.assert_called_once()
    create_call = transport._post.call_args
    assert create_call.args[0] == "/dedicated-node-groups/ng-123/datasources"
    assert create_call.kwargs["json"]["name"] == "model-data"
    assert create_call.kwargs["json"]["object"]["bucket"] == "model-bucket"
    assert create_call.kwargs["json"]["object"]["provider"]["type"] == "s3"

    api.delete_storage_data_source("ng-123", "model/data")
    transport._delete.assert_called_once_with(
        "/dedicated-node-groups/ng-123/datasources/model%2Fdata"
    )


def test_node_group_permission_api_uses_type_specific_routes():
    transport = Mock()
    response = Mock(status_code=200, text="")
    response.json.return_value = _make_object_storage().model_dump(
        mode="json",
        by_alias=True,
    )
    transport._post.return_value = response
    transport._delete.return_value = response
    transport._patch.return_value = response
    api = DedicatedNodeGroupAPI(transport)
    permission = StoragePermission(
        path_prefix="/team data",
        allowed_users=["alice@example.com"],
    )

    api.set_storage_permission("ng-123", "shared/data", permission)
    transport._post.assert_called_once_with(
        "/storage-permission/shared%2Fdata",
        json={
            "path_prefix": "/team data",
            "allowed_users": ["alice@example.com"],
            "subfolder_policy": "",
            "nodegroup_id": "ng-123",
        },
    )

    api.delete_storage_permission(
        "ng-123",
        "shared/data",
        "/team data",
    )
    transport._delete.assert_called_once_with(
        "/storage-permission/shared%2Fdata/team%20data",
        params={"nodegroup_id": "ng-123"},
    )

    data_source = _make_object_storage()
    api.update_storage_data_source(
        "ng-123",
        "model/data",
        data_source.spec,
    )
    update_call = transport._patch.call_args
    assert (
        update_call.args[0] == "/dedicated-node-groups/ng-123/datasources/model%2Fdata"
    )
    assert update_call.kwargs["json"]["name"] == "model-data"
    assert update_call.kwargs["json"]["object"]["bucket"] == "model-bucket"
    assert update_call.kwargs["json"]["permissions"]["allowed_users"] == [
        "researcher@example.com"
    ]


def test_storage_permission_distinguishes_permission_models():
    runner = CliRunner()

    with patch("leptonai.cli.node.APIClient", _FakeAPIClient):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "--node-group",
                "ng-123",
            ],
        )

    assert result.exit_code == 0, result.output
    assert result.output.index("Storage") < result.output.index("Type")
    assert "scratch" in result.output
    assert "node-local" in result.output
    assert "All paths" in result.output
    assert "Default access" in result.output
    assert "shared-data" in result.output
    assert "node-nfs" in result.output
    assert "/datasets" in result.output
    assert "Path allow rule" in result.output
    assert "/users/<email_username>" in result.output
    assert "Username subfolder rule" in result.output
    assert "model-data" in result.output
    assert "object-storage" in result.output
    assert "s3://model-bucket" in result.output
    assert "Bucket" in result.output
    assert "allowlist" in result.output
    assert "researcher@example.com" in result.output


def test_storage_permission_filters_by_storage_name():
    runner = CliRunner()

    with patch("leptonai.cli.node.APIClient", _FakeAPIClient):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "-ng",
                "h100-cluster",
                "-n",
                "model-data",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "model-data" in result.output
    assert "Bucket" in result.output
    assert "allowlist" in result.output
    assert "shared-data" not in result.output
    assert "scratch" not in result.output


def test_storage_permission_adds_node_path_rule():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "add",
                "-ng",
                "ng-123",
                "-n",
                "shared-data",
                "-p",
                "/projects",
                "-u",
                "alice@example.com",
                "-u",
                "bob@example.com",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Added permission for /projects" in result.output
    assert len(fake_client.nodegroup.set_permissions) == 1
    node_group, volume_name, permission = fake_client.nodegroup.set_permissions[0]
    assert node_group.metadata.id_ == "ng-123"
    assert volume_name == "shared-data"
    assert permission.path_prefix == "/projects"
    assert permission.allowed_users == [
        "alice@example.com",
        "bob@example.com",
    ]
    assert permission.subfolder_policy == ""
    assert permission.nodegroup_id == "ng-123"


def test_storage_permission_adds_by_user_rule():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "add",
                "-ng",
                "h100-cluster",
                "-n",
                "scratch",
                "-p",
                "/users",
                "--by-user",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "first path rule" in result.output
    _, _, permission = fake_client.nodegroup.set_permissions[0]
    assert permission.path_prefix == "/users"
    assert permission.allowed_users == []
    assert permission.subfolder_policy == "by_user"


def test_storage_permission_deletes_node_path_rule():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "delete",
                "-ng",
                "ng-123",
                "-n",
                "shared-data",
                "-p",
                "/datasets",
                "--yes",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Deleted permission for /datasets" in result.output
    assert len(fake_client.nodegroup.deleted_permissions) == 1
    node_group, volume_name, path_prefix = fake_client.nodegroup.deleted_permissions[0]
    assert node_group.metadata.id_ == "ng-123"
    assert volume_name == "shared-data"
    assert path_prefix == "/datasets"


def test_storage_permission_adds_object_storage_members():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "add",
                "-ng",
                "ng-123",
                "-n",
                "model-data",
                "-u",
                "engineer@example.com",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Updated bucket allowlist" in result.output
    assert len(fake_client.nodegroup.updated_data_sources) == 1
    node_group, data_source_name, spec = fake_client.nodegroup.updated_data_sources[0]
    assert node_group.metadata.id_ == "ng-123"
    assert data_source_name == "model-data"
    assert spec.permissions.allowed_users == [
        "researcher@example.com",
        "engineer@example.com",
    ]
    assert spec.object_.bucket == "model-bucket"
    assert spec.object_.provider.type_ == "s3"


def test_storage_permission_deleting_last_object_member_restores_default():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "delete",
                "-ng",
                "ng-123",
                "-n",
                "model-data",
                "-u",
                "researcher@example.com",
                "--yes",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Cleared the bucket allowlist" in result.output
    assert "All workspace members now have default access" in result.output
    _, _, spec = fake_client.nodegroup.updated_data_sources[0]
    assert spec.permissions is None
    assert spec.object_.bucket == "model-bucket"


def test_storage_permission_rejects_path_for_object_storage():
    runner = CliRunner()
    fake_client = _FakeAPIClient()

    with patch("leptonai.cli.node.APIClient", return_value=fake_client):
        result = runner.invoke(
            cli,
            [
                "node",
                "storage",
                "permission",
                "add",
                "-ng",
                "ng-123",
                "-n",
                "model-data",
                "-p",
                "/datasets",
                "-u",
                "researcher@example.com",
            ],
        )

    assert result.exit_code != 0
    assert "bucket-wide" in result.output
    assert fake_client.nodegroup.updated_data_sources == []
