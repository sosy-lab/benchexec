# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import contextlib
import errno
import functools
import inspect
import logging
import multiprocessing
import os
import signal
import socket
import tempfile

from benchexec import (
    BenchExecException,
    container,
    containerexecutor,
    libc,
    tooladapter,
    util,
)


tool: tooladapter.CURRENT_BASETOOL = None


@tooladapter.CURRENT_BASETOOL.register  # mark as instance of CURRENT_BASETOOL
class ContainerizedTool(object):
    """Wrapper for an instance of any subclass of one of the base-tool classes in
    benchexec.tools.template.
    The module and the subclass instance will be loaded in a subprocess that has been
    put into a container. This means, for example, that the code of this module cannot
    make network connections and that any changes made to files on disk have no effect.

    Because we use the multiprocessing module and thus communication is done
    via serialization with pickle, this is not a secure solution:
    Code from the tool-info module can use pickle to execute arbitary code
    in the main BenchExec process.
    But the use of containers in BenchExec is for safety and robustness, not security.
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

        # Call function that loads tool module and returns its doc
        try:
            self.__doc__ = self._pool.apply(
                _init_container_and_load_tool,
                [tool_module, temp_dir],
                container_options,
            )
        except BaseException as e:
            self._pool.terminate()
            raise e
        finally:
            # Outside the container, the temp_dir is just an empty directory, because
            # the tmpfs mount is only visible inside. We can remove it immediately.
            with contextlib.suppress(OSError):
                os.rmdir(temp_dir)

    def close(self):
        self._forward_call("close", [], {})
        self._pool.close()

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


def _init_container_and_load_tool(tool_module, *args, **kwargs):
    """Initialize container for the current process and load given tool-info module."""
    try:
        _init_container(*args, **kwargs)
    except OSError as e:
        if container.check_apparmor_userns_restriction(e):
            raise BenchExecException(container._ERROR_MSG_USER_NS_RESTRICTION)
        raise BenchExecException(f"Failed to configure container: {e}")
    return _load_tool(tool_module)


def _init_container(
    temp_dir,
    network_access,
    dir_modes,
    container_system_config,
    container_tmpfs,  # ignored, tmpfs is always used
):
    """
    Create a fork of this process in a container. This method only returns in the fork,
    so calling it seems like moving the current process into a container.
    """
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
    try:
        libc.unshare(flags)
    except OSError as e:
        if (
            e.errno == errno.EPERM
            and util.try_read_file("/proc/sys/kernel/unprivileged_userns_clone") == "0"
        ):
            raise BenchExecException(
                "Unprivileged user namespaces forbidden on this system, please "
                "enable them with 'sysctl -w kernel.unprivileged_userns_clone=1' "
                "or disable container mode"
            )
        elif (
            e.errno in {errno.ENOSPC, errno.EINVAL}
            and util.try_read_file("/proc/sys/user/max_user_namespaces") == "0"
        ):
            # Ubuntu has ENOSPC, Centos seems to produce EINVAL in this case
            raise BenchExecException(
                "Unprivileged user namespaces forbidden on this system, please "
                "enable by using 'sysctl -w user.max_user_namespaces=10000' "
                "(or another value) or disable container mode"
            )
        else:
            raise BenchExecException(
                "Creating namespace for container mode failed: " + os.strerror(e.errno)
            )

    # Container config
    container.setup_user_mapping(os.getpid(), uid, gid)
    if container_system_config:
        socket.sethostname(container.CONTAINER_HOSTNAME)
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

    # We setup the container's filesystem in the child process.
    # Delaying this until after the fork can avoid "Transport endpoint not connected" issue.
    _setup_container_filesystem(temp_dir, dir_modes, container_system_config)

    # Finalize container setup in child
    container.mount_proc(container_system_config)  # only possible in child
    container.drop_capabilities()
    libc.prctl(libc.PR_SET_DUMPABLE, libc.SUID_DUMP_DISABLE, 0, 0, 0)
    container.setup_seccomp_filter()


def _load_tool(tool_module):
    logging.debug("Loading tool-info module %s in container", tool_module)
    global tool
    tool = __import__(tool_module, fromlist=["Tool"]).Tool()
    tool = tooladapter.adapt_to_current_version(tool)
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
            os.makedirs(temp_tmpfs, exist_ok=True)
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
    except SystemExit as e:
        # SystemExit would terminate the worker process instead of being propagated.
        raise BenchExecException(str(e.code))
