# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Validate the wheel and require a clean release tag before publishing."""

import argparse
from email.parser import BytesParser
import os
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile


def check_wheel(directory):
    wheels = list(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one wheel artifact")
    wheel = wheels[0]
    with ZipFile(wheel) as archive:
        metadata_files = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise ValueError("Expected exactly one wheel METADATA file")
        metadata = BytesParser().parsebytes(archive.read(metadata_files[0]))
    version = metadata.get("Version")
    if metadata.get("Name") != "leptonai" or not version:
        raise ValueError("Expected a leptonai wheel with a version")
    if not wheel.name.startswith(f"leptonai-{version}-"):
        raise ValueError("Wheel filename does not match its package metadata")
    return version


def check_publish(version):
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise ValueError("Publishing requires a manual workflow_dispatch run")
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if os.environ.get("GITHUB_REF_TYPE") != "tag" or not re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag
    ):
        raise ValueError("Publishing requires a MAJOR.MINOR.PATCH tag")
    if version != tag:
        raise ValueError(f"Wheel version {version} does not match release tag {tag}")

    def git(*args):
        return subprocess.check_output(["git", *args], text=True).strip()

    if git("rev-parse", "HEAD") != git("rev-parse", f"refs/tags/{tag}^{{commit}}"):
        raise ValueError("HEAD does not match the release tag")
    if git("status", "--porcelain"):
        raise ValueError("Publishing requires a clean working tree")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    try:
        version = check_wheel(args.directory)
        if args.publish:
            check_publish(version)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release validation failed: {error}\n")
    print(f"Validated leptonai wheel: {version}")


if __name__ == "__main__":
    main()
