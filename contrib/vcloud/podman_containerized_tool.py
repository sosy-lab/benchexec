# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import shlex
import subprocess
import sys

from benchexec import (
    BenchExecException,
    libc,
    tooladapter,
)
from benchexec.containerized_tool import ContainerizedToolBase

TOOL_DIRECTORY_MOUNT_POINT = "/mnt/__benchexec_tool_directory"


def _init_container(
    image,
    tool_directory,
):
    """
    Move this process into a container.
    """
    volumes = []

    tool_directory = os.path.abspath(tool_directory)

    # Mount the python loaded paths into the container
    # The modules are mounted at the exact same path in the container
    # because we do not yet know a solution to tell python to use
    # different paths for the modules in the container.
    python_paths = [path for path in sys.path if os.path.isdir(path)]
    for path in python_paths:
        abs_path = os.path.abspath(path)
        volumes.extend(["--volume", f"{abs_path}:{abs_path}:ro"])

    # Mount the tool directory into the container at a known location
    volumes.extend(
        [
            "--volume",
            f"{tool_directory}:{TOOL_DIRECTORY_MOUNT_POINT}:O",
            # :O creates an overlay mount. The tool can write files in the container
            # but they are not visible outside the container.
            "--workdir",
            "/mnt",
        ]
    )

    # Create a container that does nothing but keeps running
    command = (
        ["podman", "run", "--entrypoint", "tail", "--rm", "-d"]
        + volumes
        + [image, "-F", "/dev/null"]
    )

    logging.debug(
        "Command to start container: %s",
        shlex.join(map(str, command)),
    )
    res = subprocess.run(
        command,
        stdout=subprocess.PIPE,
    )

    res.check_returncode()
    container_id = res.stdout.decode().strip()

    container_pid = (
        subprocess.run(
            ["podman", "inspect", "--format", "{{.State.Pid}}", container_id],
            stdout=subprocess.PIPE,
        )
        .stdout.decode()
        .strip()
    )

    def join_ns(namespace):
        namespace = f"/proc/{container_pid}/ns/{namespace}"
        logging.debug("Joining namespace %s .", namespace)
        with open(namespace, "rb") as f:
            libc.setns(f.fileno(), 0)

    try:
        logging.debug("Joining namespaces of container %s.", container_id)

        necessary_namespaces = frozenset(("user", "mnt"))

        # The user namespace must be joined first
        # because the other namespaces depend on it
        join_ns("user")

        for namespace in os.listdir(f"/proc/{container_pid}/ns"):
            if namespace in necessary_namespaces:
                continue
            try:
                # We try to mount all listed namespaces, but some might not be available
                join_ns(namespace)

            except OSError as e:
                logging.debug(
                    "Failed to join namespace %s: %s", namespace, os.strerror(e.errno)
                )

        # The mount namespace must be joined so we want
        # to fail if we cannot join the mount namespace.
        # mnt must be joined last because after joining it,
        # we can no longer access /proc/<container_pid>/ns
        join_ns("mnt")

        os.chdir(TOOL_DIRECTORY_MOUNT_POINT)
        return container_id

    except OSError as e:
        raise BenchExecException(
            "Joining the podman container failed: " + os.strerror(e.errno)
        )


@tooladapter.CURRENT_BASETOOL.register  # mark as instance of CURRENT_BASETOOL
class PodmanContainerizedTool(ContainerizedToolBase):
    def __init__(self, tool_module, config, image):
        assert (
            config.tool_directory
        ), "Tool directory must be set when using podman for tool info module."

        self.tool_directory = config.tool_directory
        self.image = image

        super().__init__(tool_module, config, _init_container)

    def mk_args(self, tool_module, config, tmp_dir):
        return [tool_module]

    def mk_kwargs(self, container_options):
        return {
            "image": self.image,
            "tool_directory": self.tool_directory,
        }

    def _cleanup(self):
        logging.debug("Stopping container with global id %s", self.container_id)
        if self.container_id is None:
            return
        try:
            subprocess.run(
                ["podman", "kill", "--signal", "SIGKILL", self.container_id],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            logging.warning(
                "Failed to stop container %s: %s",
                self.container_id,
                e.stderr.decode(),
            )
