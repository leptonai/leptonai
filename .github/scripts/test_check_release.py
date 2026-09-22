# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile


SCRIPT = Path(__file__).with_name("check_release.py")


class TestReleaseChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        (self.repository / "README.md").write_text("Release fixture\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "Initial release fixture")
        self.git("tag", "-a", "0.47.0", "-m", "Release 0.47.0")

    def git(self, *args):
        subprocess.run(
            ["git", *args], cwd=self.repository, check=True, capture_output=True
        )

    def run_check(self, *, version="0.47.0", publish=True, name="leptonai", **env):
        wheel = self.artifacts / f"{name}-{version}-py3-none-any.whl"
        with ZipFile(wheel, "w") as archive:
            archive.writestr(
                f"{name}-{version}.dist-info/METADATA",
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
            )
        command = [sys.executable, str(SCRIPT), str(self.artifacts)]
        if publish:
            command.append("--publish")
        return subprocess.run(
            command,
            cwd=self.repository,
            env={
                **os.environ,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REF_TYPE": "tag",
                "GITHUB_REF_NAME": "0.47.0",
                **env,
            },
            capture_output=True,
            text=True,
        )

    def test_clean_tag_can_publish(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.47.0", result.stdout)

    def test_development_build_does_not_require_a_release_tag(self):
        result = self.run_check(
            version="0.47.0.post1.dev1+gabcdef0",
            publish=False,
            GITHUB_EVENT_NAME="pull_request",
            GITHUB_REF_TYPE="branch",
            GITHUB_REF_NAME="feature",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_automatic_run_cannot_publish(self):
        result = self.run_check(GITHUB_EVENT_NAME="push")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manual workflow_dispatch", result.stderr)

    def test_branch_cannot_publish_even_if_its_name_matches_the_version(self):
        result = self.run_check(GITHUB_REF_TYPE="branch")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MAJOR.MINOR.PATCH tag", result.stderr)

    def test_invalid_release_tags_are_rejected(self):
        for tag in ("v0.47.0", "0.47", "0.47.0rc1", "00.47.0"):
            with self.subTest(tag=tag):
                result = self.run_check(GITHUB_REF_NAME=tag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("MAJOR.MINOR.PATCH tag", result.stderr)

    def test_wheel_must_match_tag(self):
        result = self.run_check(version="0.48.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match release tag", result.stderr)

    def test_commits_after_tag_cannot_publish(self):
        self.git("commit", "--allow-empty", "-qm", "After release tag")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HEAD does not match", result.stderr)

    def test_dirty_working_tree_cannot_publish(self):
        (self.repository / "README.md").write_text("Uncommitted change\n")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean working tree", result.stderr)

    def test_multiple_artifacts_are_rejected(self):
        (self.artifacts / "stale.whl").touch()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one wheel", result.stderr)

    def test_other_packages_are_rejected(self):
        result = self.run_check(name="another-package")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected a leptonai wheel", result.stderr)


if __name__ == "__main__":
    unittest.main()
