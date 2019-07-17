# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2016  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import contextlib
import functools
import inspect
import logging
import multiprocessing
import os
import signal
import tempfile

from benchexec import container, containerexecutor, libc, util
import benchexec.tools.template


class ContainerizedTool(benchexec.tools.template.BaseTool):
    """Wrapper for an instance of any subclass of benchexec.tools.template.BaseTool.
    The module and the subclass instance will be loaded in a subprocess that has been
    put into a container. This means, for example, that the code of this module cannot
    make network connections and that any changes made to files on disk have no effect.
    """

    def __init__(self, tool_module, config):
        """Load tool-info module in subprocess.
        @param tool_module: The name of the module to load.
            Needs to define class named Tool.
        @param config: A config object suitable for
            benchexec.containerexecutor.handle_basic_container_args()
        """
        # We use multiprocessing.Pool as an easy way for RPC with another process.
        self._pool = multiprocessing.Pool(1, _init_worker_process)

        container_options = containerexecutor.handle_basic_container_args(config)
        temp_dir = tempfile.mkdtemp(prefix="Benchexec_tool_info_container_")

        # Call function that loads tool module and returns its doc or an exception
        init_result = self._pool.apply(
            _init_container_and_load_tool, [tool_module, temp_dir], container_options
        )

        # Outside the container, the temp_dir is just an empty directory, because the
        # tmpfs mount is only visible inside. We can remove it immediately.
        with contextlib.suppress(OSError):
            os.rmdir(temp_dir)

        if isinstance(init_result, BaseException):
            raise init_result  # Loading failed
        else:
            self.__doc__ = init_result

    def _forward_call(self, method_name, args, kwargs):
        """Call given method indirectly on the tool instance in the container."""
        result = self._pool.apply(_call_tool_func, [method_name, list(args), kwargs])
        if isinstance(result, BaseException):
            # None of the methods are expected to return exceptions,
            # so we can assume that any exception should be raised.
            raise result
        return result

    @classmethod
    def _add_proxy_function(cls, method_name, method):
        """Add function to given class that calls the specified method indirectly."""

        @functools.wraps(method)  # lets proxy_function look like method (name and doc)
        def proxy_function(self, *args, **kwargs):
            return self._forward_call(method_name, args, kwargs)

        setattr(cls, member_name, proxy_function)

    # All methods inherited from BaseTool will be overwritten by the following loop


for member_name, member in inspect.getmembers(ContainerizedTool, inspect.isfunction):
    if member_name[0] == "_":
        continue
    ContainerizedTool._add_proxy_function(member_name, member)


def _init_worker_process():
    """Initial setup of worker process from multiprocessing module."""

    # Need to reset signal handling because multiprocessing relies on SIGTERM
    # but benchexec adds a handler for it.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # If Ctrl+C is pressed, each process receives SIGINT. We need to ignore it because
    # concurrent worker threads of benchexec might still attempt to use the tool-info
    # module until all of them are stopped, so this process must stay alive.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _init_container_and_load_tool(
    tool_module,
    temp_dir,
    network_access,
    dir_modes,
    container_system_config,
    container_tmpfs,  # ignored, tmpfs is always used
):
    """Initialize container for the current process and load given tool-info module."""
    # Prepare for private home directory, some tools write there
    if container_system_config:
        dir_modes.setdefault(container.CONTAINER_HOME, container.DIR_HIDDEN)
        os.environ["HOME"] = container.CONTAINER_HOME

    # Preparations
    temp_dir = temp_dir.encode()
    dir_modes = collections.OrderedDict(
        sorted(
            ((path.encode(), kind) for (path, kind) in dir_modes.items()),
            key=lambda tupl: len(tupl[0]),
        )
    )
    uid = container.CONTAINER_UID if container_system_config else os.getuid()
    gid = container.CONTAINER_GID if container_system_config else os.getgid()

    # Create container.
    # Contrary to ContainerExecutor, which uses clone to start a new process in new
    # namespaces, we use unshare, which puts the current process (the multiprocessing
    # worker process) into new namespaces.
    # The exception is the PID namespace, which will only apply to children processes.
    flags = (
        libc.CLONE_NEWNS
        | libc.CLONE_NEWUTS
        | libc.CLONE_NEWIPC
        | libc.CLONE_NEWUSER
        | libc.CLONE_NEWPID
    )
    if not network_access:
        flags |= libc.CLONE_NEWNET
    libc.unshare(flags)

    # Container config
    container.setup_user_mapping(os.getpid(), uid, gid)
    _setup_container_filesystem(temp_dir, dir_modes, container_system_config)
    if container_system_config:
        libc.sethostname(container.CONTAINER_HOSTNAME)
    if not network_access:
        container.activate_network_interface("lo")

    # Because this process is not actually in the new PID namespace, we fork.
    # The child will be in the new PID namespace and will assume the role of the acting
    # multiprocessing worker (which it can do because it inherits the file descriptors
    # that multiprocessing uses for communication).
    # The original multiprocessing worker (the parent of the fork) must do nothing in
    # order to not confuse multiprocessing.
    pid = os.fork()
    if pid:
        container.drop_capabilities()
        # block parent such that it does nothing
        os.waitpid(pid, 0)
        os._exit(0)

    # Finalize container setup in child
    container.mount_proc(container_system_config)  # only possible in child
    container.drop_capabilities()
    libc.prctl(libc.PR_SET_DUMPABLE, libc.SUID_DUMP_DISABLE, 0, 0, 0)

    logging.debug("Loading tool-info module %s in container", tool_module)
    global tool
    try:
        tool = __import__(tool_module, fromlist=["Tool"]).Tool()
    except BaseException as e:
        tool = None
        return e
    return tool.__doc__


def _setup_container_filesystem(temp_dir, dir_modes, container_system_config):
    # We put all temp files on a RAM disk
    libc.mount(None, temp_dir, b"tmpfs", 0, b"size=100%")

    mount_base = os.path.join(temp_dir, b"mount")  # base dir for container mounts
    temp_base = os.path.join(temp_dir, b"temp")  # upper layer for overlayfs
    work_base = os.path.join(temp_dir, b"overlayfs")  # work dir for overlayfs
    os.mkdir(mount_base)
    os.mkdir(temp_base)
    os.mkdir(work_base)
    container.duplicate_mount_hierarchy(mount_base, temp_base, work_base, dir_modes)

    def make_tmpfs_dir(path):
        """Ensure that a tmpfs is mounted on path, if the path exists"""
        if path in dir_modes:
            return  # explicitly configured by user
        mount_tmpfs = mount_base + path
        if os.path.isdir(mount_tmpfs):
            temp_tmpfs = temp_base + path
            util.makedirs(temp_tmpfs, exist_ok=True)
            container.make_bind_mount(temp_tmpfs, mount_tmpfs)

    make_tmpfs_dir(b"/dev/shm")
    make_tmpfs_dir(b"/run/shm")

    if container_system_config:
        container.setup_container_system_config(temp_base, mount_base, dir_modes)

    cwd = os.getcwd()
    container.chroot(mount_base)
    os.chdir(cwd)


def _call_tool_func(name, args, kwargs):
    """Call a method on the tool instance.
    @param name: The method name to call.
    @param args: List of arguments to be passed as positional arguments.
    @param kwargs: Dict of arguments to be passed as keyword arguments.
    """
    global tool
    try:
        return getattr(tool, name)(*args, **kwargs)
    except BaseException as e:
        return e
