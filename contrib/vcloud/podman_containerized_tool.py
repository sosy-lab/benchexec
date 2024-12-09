# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import errno
import functools
import inspect
import logging
import multiprocessing
import os
import shlex
import signal
import subprocess
import sys

from benchexec import (
    BenchExecException,
    container,
    libc,
    tooladapter,
    util,
)

tool: tooladapter.CURRENT_BASETOOL = None

TOOL_DIRECTORY_MOUNT_POINT = "/mnt/__benchexec_tool_directory"


@tooladapter.CURRENT_BASETOOL.register  # mark as instance of CURRENT_BASETOOL
class PodmanContainerizedTool(object):
    """Wrapper for an instance of any subclass of one of the base-tool classes in
    benchexec.tools.template.
    The module and the subclass instance will be loaded in a subprocess that has been
    put into a container. This means, for example, that the code of this module cannot
    make network connections and that any changes made to files on disk have no effect.

    Because we use the multiprocessing module and thus communication is done
    via serialization with pickle, this is not a secure solution:
    Code from the tool-info module can use pickle to execute arbitrary code
    in the main BenchExec process.
    But the use of containers in BenchExec is for safety and robustness, not security.

    This class is heavily inspired by ContainerizedTool and it will create a podman
    container and move the multiprocessing process into the namespace of the podman container.
    """

    def __init__(self, tool_module, config, image):
        """Load tool-info module in subprocess.
        @param tool_module: The name of the module to load.
            Needs to define class named Tool.
        @param config: A config object suitable for
            benchexec.containerexecutor.handle_basic_container_args()
        """
        assert (
            config.tool_directory
        ), "Tool directory must be set when using podman for tool info module."

        # We use multiprocessing.Pool as an easy way for RPC with another process.
        self._pool = multiprocessing.Pool(1, _init_worker_process)

        self.container_id = None
        # Call function that loads tool module and returns its doc
        try:
            self.__doc__, self.container_id = self._pool.apply(
                _init_container_and_load_tool,
                [tool_module],
                {
                    "image": image,
                    "tool_directory": config.tool_directory,
                },
            )
        except BaseException as e:
            self._pool.terminate()
            raise e

    def close(self):
        self._forward_call("close", [], {})
        self._pool.close()
        if self.container_id is None:
            return
        try:
            # FIXME: Unexpected terminations could lead to the container not being stopped and removed
            # SIGTERM sent by stop does not stop the container running tail -F /dev/null or sleep infinity
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

    def _forward_call(self, method_name, args, kwargs):
        """Call given method indirectly on the tool instance in the container."""
        return self._pool.apply(_call_tool_func, [method_name, list(args), kwargs])

    @classmethod
    def _add_proxy_function(cls, method_name, method):
        """Add function to given class that calls the specified method indirectly."""

        @functools.wraps(method)  # lets proxy_function look like method (name and doc)
        def proxy_function(self, *args, **kwargs):
            return self._forward_call(method_name, args, kwargs)

        if method_name == "working_directory":
            # Add a cache. This method is called per run but would always return the
            # same result. On some systems the calls are slow and this is worth it:
            # https://github.com/python/cpython/issues/98493
            proxy_function = functools.lru_cache()(proxy_function)

        setattr(cls, member_name, proxy_function)


# The following will automatically add forwarding methods for all methods defined by the
# current tool-info API. This should work without any version-specific adjustments,
# so we declare compatibility with the latest version with @CURRENT_BASETOOL.register.
# We do not inherit from a BaseTool class to ensure that no default methods will be used
# accidentally.
for member_name, member in inspect.getmembers(
    tooladapter.CURRENT_BASETOOL, inspect.isfunction
):
    if member_name[0] == "_" or member_name == "close":
        continue
    PodmanContainerizedTool._add_proxy_function(member_name, member)


def _init_worker_process():
    """Initial setup of worker process from multiprocessing module."""

    # Need to reset signal handling because multiprocessing relies on SIGTERM
    # but benchexec adds a handler for it.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # If Ctrl+C is pressed, each process receives SIGINT. We need to ignore it because
    # concurrent worker threads of benchexec might still attempt to use the tool-info
    # module until all of them are stopped, so this process must stay alive.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _init_container_and_load_tool(tool_module, *args, **kwargs):
    """Initialize container for the current process and load given tool-info module."""
    try:
        container_id = _init_container(*args, **kwargs)
    except OSError as e:
        if container.check_apparmor_userns_restriction(e):
            raise BenchExecException(container._ERROR_MSG_USER_NS_RESTRICTION)
        raise BenchExecException(f"Failed to configure container: {e}")
    return _load_tool(tool_module), container_id


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

