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
import weakref
from pathlib import Path, PurePath

from benchexec import (
    BenchExecException,
    libc,
    tooladapter,
)
from benchexec.containerized_tool import (
    ContainerizedTool,
    _init_container_and_load_tool,
)

TOOL_DIRECTORY_MOUNT_POINT = "/mnt/__benchexec_tool_directory"
PYTHON_PATH_MOUNT_POINT = "/mnt/__benchexec_python_path"


def _plan_python_path_mounts():
    """
    Decide where the directories from which Python loads modules (sys.path)
    are mounted in the container.
    We do not mount them at their original paths because this would hide whatever
    the container image has at these paths, for example its own Python packages,
    and tools that are implemented in Python could break.

    @return a tuple of the Podman arguments for the mounts and a dict that maps
        paths on the host (as they appear in sys.path, and with symlinks resolved)
        to paths in the container, to be passed to _redirect_python_path()
    """
    volumes = []
    path_translation = {}
    for path in sys.path:
        resolved_path = Path(path).resolve()
        if not resolved_path.is_dir():
            continue

        # Podman rejects duplicates, so we mount each directory only once
        mount_point = path_translation.get(PurePath(resolved_path))
        if mount_point is None:
            mount_count = len(set(path_translation.values()))
            mount_point = PurePath(PYTHON_PATH_MOUNT_POINT, str(mount_count))
            volumes += ["--volume", f"{resolved_path}:{mount_point}:ro"]
            path_translation[PurePath(resolved_path)] = mount_point
        path_translation[PurePath(path)] = mount_point

    return volumes, path_translation


def _redirect_python_path(path_translation):
    """
    Let Python load modules from where the directories of sys.path are mounted
    in the container. This needs to be called right after this process
    has joined the mount namespace of the container.
    """

    def translate(path):
        # Look for the longest prefix of path that is mounted in the container
        pure_path = PurePath(path)
        for prefix in (pure_path, *pure_path.parents):
            if prefix in path_translation:
                return str(path_translation[prefix] / pure_path.relative_to(prefix))
        return path  # nothing from sys.path

    sys.path[:] = [translate(path) for path in sys.path]

    for module in list(sys.modules.values()):
        # Packages that are already loaded remember where to look for their modules
        module_path = getattr(module, "__path__", None)
        if isinstance(module_path, list):
            module_path[:] = [translate(path) for path in module_path]

        # Loaders remember the source file, which is needed for lines in tracebacks
        loader = getattr(module, "__loader__", None)
        if isinstance(getattr(loader, "path", None), str):
            loader.path = translate(loader.path)

    # Python caches a finder for each directory from which it loads modules
    sys.path_importer_cache.clear()


def _create_container(
    image,
    tool_directory,
):
    """
    Create a container into which this process can be moved with _join_container().

    @return a tuple of the id of the container
        and the dict that _join_container() needs as second argument
    """
    tool_directory = os.path.abspath(tool_directory)

    # Mount the directories from which Python loads modules into the container
    volumes, python_path_translation = _plan_python_path_mounts()

    # Mount the tool directory into the container at a known location
    volumes += [
        "--volume",
        f"{tool_directory}:{TOOL_DIRECTORY_MOUNT_POINT}:O",
        # :O creates an overlay mount. The tool can write files in the container
        # but they are not visible outside the container.
        "--workdir",
        "/mnt",
    ]

    # Create a container that does nothing but keeps running
    command = (
        ["podman", "create", "--entrypoint", '[""]', "--rm"]
        + volumes
        + [image, "/bin/sh"]
    )

    logging.debug(
        "Command to start container: %s",
        shlex.join(map(str, command)),
    )
    try:
        res = subprocess.run(
            command,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise BenchExecException(
            "Creating of the podman container failed:\n" + e.stderr.decode()
        )

    return res.stdout.decode().strip(), python_path_translation


def _join_container(container_id, python_path_translation):
    """
    Move this process into a container that was created with _create_container().
    """
    try:
        subprocess.run(
            ["podman", "init", container_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise BenchExecException(
            "Initializing the podman container failed:\n" + e.stderr.decode()
        )

    try:
        container_pid = (
            subprocess.run(
                ["podman", "inspect", "--format", "{{.State.Pid}}", container_id],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                check=True,
            )
            .stdout.decode()
            .strip()
        )
    except subprocess.CalledProcessError as e:
        raise BenchExecException(
            "Inspecting the podman container failed:\n" + e.stderr.decode()
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

        # From now on, the modules of Python exist only at their mount points
        _redirect_python_path(python_path_translation)

        os.chdir(TOOL_DIRECTORY_MOUNT_POINT)

    except OSError as e:
        raise BenchExecException(
            "Joining the podman container failed: " + os.strerror(e.errno)
        )


def _remove_container(container_id):
    """
    Remove a container that was created with _create_container().
    """
    logging.debug("Removing container with global id %s", container_id)
    try:
        subprocess.run(
            # Podman may already have removed the container if "podman init" failed.
            ["podman", "rm", "--ignore", container_id],
            check=True,
            stdout=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        logging.warning(
            "Failed to remove container %s: %s", container_id, e.stderr.decode()
        )


@tooladapter.CURRENT_BASETOOL.register  # mark as instance of CURRENT_BASETOOL
class PodmanContainerizedTool(ContainerizedTool):
    tool_directory: str
    image: str
    container_id: str | None

    def __init__(self, tool_module, config, image):
        assert config.tool_directory, (
            "Tool directory must be set when using podman for tool info module."
        )

        self.tool_directory = config.tool_directory
        self.image = image
        self.container_id = None
        # replaced in _setup_container() as soon as the container exists
        self._container_finalizer = lambda: None

        try:
            super().__init__(tool_module, config)
        except BaseException:
            # For example, the tool-info module could not be loaded.
            self._container_finalizer()
            raise

    def _setup_container(self, tool_module, config):
        # We create the container in a separate step, because we need to know it
        # in order to remove it if one of the following steps fails.
        try:
            self.container_id, python_path_translation = self._pool.apply(
                _create_container, [self.image, self.tool_directory]
            )
        except OSError as e:
            # for example, if Podman is not installed
            raise BenchExecException(f"Failed to configure container: {e}")

        # The finalizer runs at most once: when it is called explicitly,
        # or otherwise when this object is garbage collected or Python exits.
        # The latter is the safety net for the case that close() is never called.
        # The arguments must not reference self, otherwise self would never
        # be garbage collected.
        self._container_finalizer = weakref.finalize(
            self, _remove_container, self.container_id
        )

        self.__doc__, _ = self._pool.apply(
            _init_container_and_load_tool,
            [_join_container, tool_module, self.container_id, python_path_translation],
        )

    def close(self):
        try:
            super().close()
        finally:
            self._container_finalizer()
