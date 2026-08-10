import unittest
from unittest.mock import Mock

from leptonai.config import LEPTON_RESERVED_ENV_NAMES
from leptonai.api.v2.job import JobAPI
from leptonai.api.v2.job_validation import (
    LEPTON_RESERVED_MOUNT_PATHS,
    validate_job_create,
    validate_job_name,
    validate_label_key,
    validate_mount_path,
)
from leptonai.api.v2.spec_utils import (
    make_env_vars_from_strings,
    validate_environment_variable_name,
)
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import Mount
from leptonai.api.v2.types.job import LeptonJob, LeptonJobUserSpec


def _make_mount(mount_path):
    return Mount(path="/data", mount_path=mount_path, **{"from": "node-local"})


def _make_job(
    name="valid-job",
    *,
    mounts=None,
    labels=None,
    completions=1,
    parallelism=1,
):
    return LeptonJob(
        metadata=Metadata(id=name, labels=labels),
        spec=LeptonJobUserSpec(
            mounts=mounts,
            completions=completions,
            parallelism=parallelism,
        ),
    )


class TestJobNameValidation(unittest.TestCase):
    def test_accepts_valid_names(self):
        for name in ("a", "a1", "a-b", "a" * 36, "aby-lepton-x"):
            with self.subTest(name=name):
                validate_job_name(name)

    def test_rejects_invalid_names(self):
        invalid_names = (
            "",
            "a" * 37,
            "Uppercase",
            "1job",
            "job_name",
            "job-",
            "jobby-lepton",
        )

        for name in invalid_names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_job_name(name)


class TestEnvironmentVariableNameValidation(unittest.TestCase):
    def test_accepts_valid_names(self):
        for name in ("A", "_NAME", ".NAME", "-NAME", "Name.1-test_value"):
            with self.subTest(name=name):
                validate_environment_variable_name(name)

    def test_rejects_invalid_names(self):
        invalid_names = (
            "",
            "1NAME",
            "NAME@",
            "LEPTON_WORKSPACE_ID",
            "LEPTON_DEPLOYMENT_NAME",
            "LEPTON_JOB_NAME",
            "LEPTON_RESOURCE_ACCELERATOR_TYPE",
        )

        for name in invalid_names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_environment_variable_name(name)

    def test_preserves_reserved_environment_variable_error(self):
        expected = (
            "You have used a reserved environment variable name that is "
            "used by Lepton internally: LEPTON_JOB_NAME. Please use a different name. "
            "Here is a list of all reserved environment variable names:\n"
            f"{LEPTON_RESERVED_ENV_NAMES}"
        )

        with self.assertRaises(ValueError) as context:
            make_env_vars_from_strings(["LEPTON_JOB_NAME=value"], None)

        self.assertEqual(str(context.exception), expected)

    def test_preserves_reserved_secret_error(self):
        expected = (
            "You have used a reserved secret name that is "
            "used by Lepton internally: LEPTON_JOB_NAME. Please use a different name. "
            "Here is a list of all reserved environment variable names:\n"
            f"{LEPTON_RESERVED_ENV_NAMES}"
        )

        with self.assertRaises(ValueError) as context:
            make_env_vars_from_strings(None, ["LEPTON_JOB_NAME=secret-name"])

        self.assertEqual(str(context.exception), expected)


class TestMountPathValidation(unittest.TestCase):
    def test_rejects_every_reserved_path(self):
        for path in LEPTON_RESERVED_MOUNT_PATHS:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_mount_path(path)

    def test_normalizes_paths_before_checking(self):
        for path in ("/etc/", "/tmp/../etc", "//etc", "/sys//fs/cgroup/"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_mount_path(path)

    def test_allows_descendants_of_reserved_paths(self):
        for path in ("/var/data", "/opt/app", "/usr/local/share/data"):
            with self.subTest(path=path):
                validate_mount_path(path)


class TestLabelKeyValidation(unittest.TestCase):
    def test_accepts_valid_keys(self):
        for key in ("a", "1", "a.b_C-9", "a" * 63):
            with self.subTest(key=key):
                validate_label_key(key)

    def test_rejects_invalid_keys(self):
        invalid_keys = (
            "",
            "a" * 64,
            ".key",
            "_key",
            "-key",
            "key.",
            "key_",
            "key-",
            "key/value",
        )

        for key in invalid_keys:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_label_key(key)


class TestJobCreateValidation(unittest.TestCase):
    def test_validates_mounts_from_job_spec(self):
        job = _make_job(mounts=[_make_mount("/etc")])

        with self.assertRaisesRegex(ValueError, "reserved"):
            validate_job_create(job)

    def test_validates_metadata_label_keys(self):
        job = _make_job(labels={"invalid/key": "value"})

        with self.assertRaisesRegex(ValueError, "Label key"):
            validate_job_create(job)

    def test_requires_positive_worker_counts(self):
        for field, value in (("completions", 0), ("parallelism", -1)):
            with self.subTest(field=field):
                kwargs = {field: value}
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    validate_job_create(_make_job(**kwargs))

    def test_job_api_validates_name_before_posting(self):
        client = Mock()
        api = JobAPI(client)

        with self.assertRaises(ValueError):
            api.create(_make_job(name="Invalid-job"))

        client._post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
