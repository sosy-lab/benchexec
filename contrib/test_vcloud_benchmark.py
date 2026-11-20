# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import os
import subprocess
import unittest
from unittest import mock

from benchexec import BenchExecException

# The script has a name that is not a valid module name, so we load it manually.
_spec = importlib.util.spec_from_file_location(
    "vcloud_benchmark",
    os.path.join(os.path.dirname(__file__), "vcloud-benchmark.py"),
)
vcloud_benchmark = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vcloud_benchmark)

DIGEST = "sha256:" + "0123456789abcdef" * 4


def fake_podman(pull_returncode=0, inspect_stdout=DIGEST + "\n", exists_returncode=0):
    """Create a replacement for subprocess.run that behaves like podman."""

    def run(cmd, **_kwargs):
        if cmd[:3] == ["podman", "image", "exists"]:
            return subprocess.CompletedProcess(cmd, exists_returncode)
        if cmd[:3] == ["podman", "image", "pull"]:
            return subprocess.CompletedProcess(cmd, pull_returncode)
        if cmd[:3] == ["podman", "image", "inspect"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=inspect_stdout)
        raise AssertionError(f"Unexpected command {cmd}")

    return mock.patch.object(
        vcloud_benchmark.subprocess, "run", side_effect=run, autospec=True
    )


class TestResolveContainerImage(unittest.TestCase):
    def test_tag_is_replaced_by_digest(self):
        for image, repository in [
            ("image", "image"),
            ("image:latest", "image"),
            ("image:1.2.3", "image"),
            ("registry.example.org/group/image", "registry.example.org/group/image"),
            ("registry.example.org/group/image:1", "registry.example.org/group/image"),
            # A colon before the last slash is the port of the registry, not a tag.
            ("localhost:5000/image", "localhost:5000/image"),
            ("localhost:5000/image:1", "localhost:5000/image"),
            ("localhost:5000/group/image:1", "localhost:5000/group/image"),
        ]:
            with self.subTest(image=image), fake_podman():
                self.assertEqual(
                    vcloud_benchmark.resolve_container_image(image),
                    f"{repository}@{DIGEST}",
                )

    def test_image_with_digest_is_unchanged(self):
        for image in [
            f"image@{DIGEST}",
            f"image:1@{DIGEST}",
            f"localhost:5000/group/image@{DIGEST}",
        ]:
            with self.subTest(image=image), fake_podman() as run:
                self.assertEqual(vcloud_benchmark.resolve_container_image(image), image)
                run.assert_not_called()

    def test_podman_is_called_with_given_image(self):
        image = "registry.example.org/group/image:1"
        with fake_podman() as run:
            vcloud_benchmark.resolve_container_image(image)

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            commands,
            [
                ["podman", "image", "exists", image],
                ["podman", "image", "inspect", image, "--format", "{{.Digest}}"],
            ],
        )

    def test_missing_image_is_pulled(self):
        image = "registry.example.org/group/image:1"
        with fake_podman(exists_returncode=1) as run:
            self.assertEqual(
                vcloud_benchmark.resolve_container_image(image),
                f"registry.example.org/group/image@{DIGEST}",
            )

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            commands,
            [
                ["podman", "image", "exists", image],
                ["podman", "image", "pull", "--quiet", image],
                ["podman", "image", "inspect", image, "--format", "{{.Digest}}"],
            ],
        )

    def test_failing_pull_is_an_error(self):
        with fake_podman(exists_returncode=1, pull_returncode=125) as run:
            self.assertRaisesRegex(
                BenchExecException,
                "Cannot pull container image:missing",
                vcloud_benchmark.resolve_container_image,
                "image:missing",
            )
            # Stop after the existence check and failed pull.
            self.assertEqual(run.call_count, 2)

    def test_failing_exists_check_is_an_error(self):
        with fake_podman(exists_returncode=125) as run:
            self.assertRaisesRegex(
                BenchExecException,
                "Cannot check whether container image image:1 exists locally.",
                vcloud_benchmark.resolve_container_image,
                "image:1",
            )
            run.assert_called_once_with(
                ["podman", "image", "exists", "image:1"],
            )

    def test_missing_digest_is_an_error(self):
        for output in ["", "\n", "<none>\n", "Error: image not known\n"]:
            with self.subTest(output=output), fake_podman(inspect_stdout=output):
                self.assertRaisesRegex(
                    BenchExecException,
                    "Cannot determine digest of container image:1",
                    vcloud_benchmark.resolve_container_image,
                    "image:1",
                )
