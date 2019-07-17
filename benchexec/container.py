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

"""Utility functions for implementing a container using Linux namespaces
and for appropriately configuring such a container."""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

# THIS MODULE HAS TO WORK WITH PYTHON 2.7!

import contextlib
import ctypes
import errno
import fcntl
import logging
import os
import resource  # noqa: F401 @UnusedImport necessary to eagerly import this module
import signal
import socket
import struct

from benchexec import libc
from benchexec import util

__all__ = [
    "execute_in_namespace",
    "setup_user_mapping",
    "activate_network_interface",
    "duplicate_mount_hierarchy",
    "determine_directory_mode",
    "get_mount_points",
    "remount_with_additional_flags",
    "make_overlay_mount",
    "mount_proc",
    "make_bind_mount",
    "get_my_pid_from_procfs",
    "drop_capabilities",
    "forward_all_signals_async",
    "wait_for_child_and_forward_signals",
    "setup_container_system_config",
    "CONTAINER_UID",
    "CONTAINER_GID",
    "CONTAINER_HOME",
    "CONTAINER_HOSTNAME",
]


DEFAULT_STACK_SIZE = 1024 * 1024
GUARD_PAGE_SIZE = libc.sysconf(libc.SC_PAGESIZE)  # size of guard page at end of stack

CONTAINER_UID = 1000
CONTAINER_GID = 1000
CONTAINER_HOME = "/home/benchexec"
CONTAINER_HOSTNAME = "benchexec"

CONTAINER_ETC_NSSWITCH_CONF = """
passwd: files
group: files
shadow: files
hosts: files
networks: files

protocols:      db files
services:       db files
ethers:         db files
rpc:            db files

netgroup:       files
automount:      files
"""
CONTAINER_ETC_PASSWD = """
root:x:0:0:root:/root:/bin/bash
benchexec:x:{uid}:{gid}:benchexec:{home}:/bin/bash
nobody:x:65534:65534:nobody:/:/bin/false
""".format(
    uid=CONTAINER_UID, gid=CONTAINER_GID, home=CONTAINER_HOME
)

CONTAINER_ETC_GROUP = """
root:x:0:
benchexec:x:{gid}:
nogroup:x:65534:
""".format(
    uid=CONTAINER_UID, gid=CONTAINER_GID, home=CONTAINER_HOME
)

CONTAINER_ETC_HOSTS = """
127.0.0.1       localhost {host}
# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
""".format(
    host=CONTAINER_HOSTNAME
)

CONTAINER_ETC_FILE_OVERRIDE = {
    b"nsswitch.conf": CONTAINER_ETC_NSSWITCH_CONF,
    b"passwd": CONTAINER_ETC_PASSWD,
    b"group": CONTAINER_ETC_GROUP,
    b"hostname": CONTAINER_HOSTNAME + "\n",
    b"hosts": CONTAINER_ETC_HOSTS,
}

DIR_HIDDEN = "hidden"
DIR_READ_ONLY = "read-only"
DIR_OVERLAY = "overlay"
DIR_FULL_ACCESS = "full-access"
DIR_MODES = [DIR_HIDDEN, DIR_READ_ONLY, DIR_OVERLAY, DIR_FULL_ACCESS]
"""modes how a directory can be mounted in the container"""

LXCFS_PROC_DIR = b"/var/lib/lxcfs/proc"

# Python before 3.7 does not have BeforeFork and AfterFork_(Child|Parent)
if not hasattr(ctypes.pythonapi, "PyOS_BeforeFork"):
    ctypes.pythonapi.PyOS_BeforeFork = lambda: None
if not hasattr(ctypes.pythonapi, "PyOS_AfterFork_Parent"):
    ctypes.pythonapi.PyOS_AfterFork_Parent = lambda: None
if not hasattr(ctypes.pythonapi, "PyOS_AfterFork_Child"):
    ctypes.pythonapi.PyOS_AfterFork_Child = ctypes.pythonapi.PyOS_AfterFork

_CLONE_NESTED_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int)
"""Type for callback of execute_in_namespace, nested in our primary callback."""

# TODO Use named fields on Python 3
NATIVE_CLONE_CALLBACK_SUPPORTED = os.uname()[0] == "Linux" and os.uname()[4] == "x86_64"
"""Whether we use generated native code for clone or an unsafe Python fallback"""


@contextlib.contextmanager
def allocate_stack(size=DEFAULT_STACK_SIZE):
    """Allocate some memory that can be used as a stack.
    @return: a ctypes void pointer to the *top* of the stack.
    """
    # Allocate memory with appropriate flags for a stack as in
    # https://blog.fefe.de/?ts=a85c8ba7
    base = libc.mmap_anonymous(
        size + GUARD_PAGE_SIZE,
        libc.PROT_READ | libc.PROT_WRITE,
        libc.MAP_GROWSDOWN | libc.MAP_STACK,
    )

    try:
        # create a guard page that crashes the application when it is written to
        # (on stack overflow)
        libc.mprotect(base, GUARD_PAGE_SIZE, libc.PROT_NONE)

        yield ctypes.c_void_p(base + size + GUARD_PAGE_SIZE)
    finally:
        libc.munmap(base, size + GUARD_PAGE_SIZE)


def execute_in_namespace(func, use_network_ns=True):
    """Execute a function in a child process in separate namespaces.
    @param func: a parameter-less function returning an int
        (which will be the process' exit value)
    @return: the PID of the created child process
    """
    flags = (
        signal.SIGCHLD
        | libc.CLONE_NEWNS
        | libc.CLONE_NEWUTS
        | libc.CLONE_NEWIPC
        | libc.CLONE_NEWUSER
        | libc.CLONE_NEWPID
    )
    if use_network_ns:
        flags |= libc.CLONE_NEWNET

    # We need to use the syscall clone(), which is similar to fork(), but not available
    # in the Python API. We can call it directly using ctypes, but then the state of the
    # Python interpreter is inconsistent, so we need to fix that. Python >= 3.7 has
    # three C functions that should be called before and after fork/clone:
    # https://docs.python.org/3/c-api/sys.html#c.PyOS_BeforeFork
    # This is the same that os.fork() does (cf. os_fork_impl
    # in https://github.com/python/cpython/blob/master/Modules/posixmodule.c).
    # Furthermore, it is very important that we have the GIL during clone(),
    # otherwise the child will often deadlock when trying to execute Python code.
    # Luckily, the ctypes module allows us to hold the GIL while executing the
    # function by using ctypes.PyDLL as library access instead of ctypes.CLL.

    # Two difficulties remain:
    # 1. On Python < 3.7, only PyOS_AfterFork() (to be called in the child) exists.
    # Other cleanup done by os_fork_impl is not accessible to us, so we ignore it.
    # For example, we do not take the import lock because it is only
    # available via an internal API, and because the child should never import anything
    # anyway (inside the container, modules might not be visible).

    # 2. On all Python versions, the interpreter state in the child is inconsistent
    # until PyOS_AfterFork_Child() is called. However, if we pass the Python function
    # _python_clone_child_callback() as callback to clone and do the cleanup in
    # its first line, it is too late because the Python interpreter is already used.
    # This actually causes problems if benchexec is executed with a high number of
    # parallel runs because of thread contention, the gil_drop_request and a deadlock
    # in drop_gil (cf. https://github.com/sosy-lab/benchexec/issues/435).
    # So we should avoid executing Python code at all before PyOS_AfterFork_Child().
    # We do not want to take the hassle of shipping C code with BenchExec, so we use
    # _generate_native_clone_child_callback() to generate machine code on the fly
    # as replacement for _python_clone_child_callback(). This works for x86_64 Linux
    # and we expect practically all BenchExec users to fall in this category. For others
    # there is still the pure Python callback, which in practice works totally fine as
    # long as there does not exist a huge number of threads.
    # There is a workaround using sys.setswitchinterval(), however, it is too late to
    # apply it here in this function, because gil_drop_request could already be set.
    # Summary:
    # - For Linux x86_64 we use native code from _generate_native_clone_child_callback()
    # - Otherwise, we use sys.setswitchinterval() as workaround in localexecution.py.
    # - Direct users of ContainerExecutor are fine in practice if they use few threads.

    func_p = _CLONE_NESTED_CALLBACK(func)  # store in variable to avoid GC

    with allocate_stack() as stack:
        try:
            ctypes.pythonapi.PyOS_BeforeFork()
            pid = libc.clone(_clone_child_callback, stack, flags, func_p)
        finally:
            ctypes.pythonapi.PyOS_AfterFork_Parent()
    return pid


@libc.CLONE_CALLBACK
def _python_clone_child_callback(func_p):
    """Used as callback for clone, calls the passed function pointer."""
    # Strictly speaking, PyOS_AfterFork_Child should be called immediately after
    # clone calls our callback before executing any Python code because the
    # interpreter state is inconsistent, but here we are already in the Python
    # world, so it could be too late. For more information cf. execute_in_namespace()
    # and https://github.com/sosy-lab/benchexec/issues/435.
    # Thus we use this function only as fallback of architectures where we have no
    # native callback. For benchexec we combine it with the sys.setswitchinterval()
    # workaround in localexecution.py. Other users of ContainerExecutor should be safe
    # as long as they do not use many threads. We cannot do anything before cloning
    # because it might be too late anyway (gil_drop_request could be set already).
    ctypes.pythonapi.PyOS_AfterFork_Child()

    return _CLONE_NESTED_CALLBACK(func_p)()


def _generate_native_clone_child_callback():
    """Generate Linux x86_64 machine code
    that does the same as _python_clone_child_callback"""
    # Inspired by https://csl.name/post/python-jit/

    # Allocate one page of memory where we put the code
    page_size = libc.sysconf(libc.SC_PAGESIZE)
    mem = libc.mmap_anonymous(page_size, libc.PROT_READ | libc.PROT_WRITE)

    # Get address of PyOS_AfterFork_Child that we want to call
    # On Python 3 we could use to_bytes() instead of struct.pack
    afterfork_address = struct.pack(
        "Q", ctypes.cast(ctypes.pythonapi.PyOS_AfterFork_Child, ctypes.c_void_p).value
    )

    # Generate machine code that does the same as _python_clone_child_callback
    # We use this C code as template (with dummy address for PyOS_AfterFork_Child):
    """
    int clone_child_callback(int (*func_p)()) {
      void (*PyOS_AfterFork_Child)() = (void*)0xffeeddccbbaa9988;
      PyOS_AfterFork_Child();
      return func_p();
    }
    """
    # We compile this code and disassemble it with
    """
    gcc -Os -fPIC -shared -fomit-frame-pointer -march=native clone_child_callback.c \
        -o clone_child_callback.o
    objdump -d --disassembler-options=suffix clone_child_callback.o
    """
    # This gives the following code (machine code left, assembler right):
    #
    # <clone_child_callback>:
    # Store address in rdx:
    #     48 ba 88 99 aa bb cc    movabsq $0xffeeddccbbaa9988,%rdx
    #     dd ee ff
    # Allocate space on stack:
    #     48 83 ec 18             subq   $0x18,%rsp
    # Clear eax:
    #     31 c0                   xorl   %eax,%eax
    # Copy rdi (value of parameter func_p) to stack:
    #     48 89 7c 24 08          movq   %rdi,0x8(%rsp)
    # Call rdx (where address is stored):
    #     ff d2                   callq  *%rdx
    # Copy stack value func_p back to rdi:
    #     48 8b 7c 24 08          movq   0x8(%rsp),%rdi
    # Clear eax:
    #     31 c0                   xorl   %eax,%eax
    # Deallocate space on stack:
    #     48 83 c4 18             addq   $0x18,%rsp
    # Call function pointer in rdi (func_p) as tail call:
    #     ff e7                   jmpq   *%rdi
    #
    # The following creates exactly the same machine code, just with the real address:
    movabsq_address_rdx = b"\x48\xba" + afterfork_address
    subq_0x18_rsp = b"\x48\x83\xec\x18"
    xorl_eax_eax = b"\x32\xc0"
    movq_rdi_stack = b"\x48\x89\x7c\x24\x08"
    callq_rdx = b"\xff\xd2"
    movq_stack_rdi = b"\x48\x8b\x7c\x24\x08"
    addq_0x18_rsp = b"\x48\x83\xc4\x18"
    jmpq_rdi = b"\xff\xe7"
    code = (
        movabsq_address_rdx
        + subq_0x18_rsp
        + xorl_eax_eax
        + movq_rdi_stack
        + callq_rdx
        + movq_stack_rdi
        + xorl_eax_eax
        + addq_0x18_rsp
        + jmpq_rdi
    )
    ctypes.memmove(mem, code, len(code))

    # Make code executable
    libc.mprotect(mem, page_size, libc.PROT_READ | libc.PROT_EXEC)
    return libc.CLONE_CALLBACK(mem)


if NATIVE_CLONE_CALLBACK_SUPPORTED:
    _clone_child_callback = _generate_native_clone_child_callback()
else:
    _clone_child_callback = _python_clone_child_callback


def setup_user_mapping(
    pid,
    uid=os.getuid(),
    gid=os.getgid(),
    parent_uid=os.getuid(),
    parent_gid=os.getgid(),
):
    """Write uid_map and gid_map in /proc to create a user mapping
    that maps our user from outside the container to the same user inside the container
    (and no other users are mapped).
    @see: http://man7.org/linux/man-pages/man7/user_namespaces.7.html
    @param pid: The PID of the process in the container.
    @param uid: The UID that shall be used in the container.
    @param gid: The GID that shall be used in the container.
    @param parent_uid: The UID that is used in the parent namespace.
    @param parent_gid: The GID that is used in the parent namespace.
    """
    proc_child = os.path.join("/proc", str(pid))
    try:
        # map uid internally to our uid externally
        uid_map = "{0} {1} 1".format(uid, parent_uid)
        util.write_file(uid_map, proc_child, "uid_map")
    except IOError as e:
        logging.warning("Creating UID mapping into container failed: %s", e)

    try:
        util.write_file("deny", proc_child, "setgroups")
    except IOError as e:
        # Not all systems have this file (depends on the kernel version),
        # but if it does not exist, we do not need to write to it.
        if e.errno != errno.ENOENT:
            logging.warning("Could not write to setgroups file in /proc: %s", e)

    try:
        # map gid internally to our gid externally
        gid_map = "{0} {1} 1".format(gid, parent_gid)
        util.write_file(gid_map, proc_child, "gid_map")
    except IOError as e:
        logging.warning("Creating GID mapping into container failed: %s", e)


_SIOCGIFFLAGS = 0x8913  # /usr/include/bits/ioctls.h
_SIOCSIFFLAGS = 0x8914  # /usr/include/bits/ioctls.h
_IFF_UP = 0x1  # /usr/include/net/if.h

# We need to use instances of "struct ifreq" for communicating with the kernel.
# This struct is complex with a big contained union, we define here only the few
# necessary fields for the two cases we need.
# The layout is given in the format used by the struct module:
# ifr_name, ifr_addr.sa_family, padding
_STRUCT_IFREQ_LAYOUT_IFADDR_SAFAMILY = b"16sH14s"
# ifr_name, ifr_flags, padding
_STRUCT_IFREQ_LAYOUT_IFFLAGS = b"16sH14s"


def activate_network_interface(iface):
    """Bring up the given network interface.
    @raise OSError: if interface does not exist or permissions are missing
    """
    iface = iface.encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
    try:
        # Get current interface flags from kernel
        ifreq = struct.pack(
            _STRUCT_IFREQ_LAYOUT_IFADDR_SAFAMILY, iface, socket.AF_INET, b"0" * 14
        )
        ifreq = fcntl.ioctl(sock, _SIOCGIFFLAGS, ifreq)
        if_flags = struct.unpack(_STRUCT_IFREQ_LAYOUT_IFFLAGS, ifreq)[1]

        # Set new flags
        ifreq = struct.pack(
            _STRUCT_IFREQ_LAYOUT_IFFLAGS, iface, if_flags | _IFF_UP, b"0" * 14
        )
        fcntl.ioctl(sock, _SIOCSIFFLAGS, ifreq)
    finally:
        sock.close()


def duplicate_mount_hierarchy(mount_base, temp_base, work_base, dir_modes):
    """
    Setup a copy of the system's mount hierarchy below a specified directory,
    and apply all specified directory modes (e.g., read-only access or hidden)
    in that new hierarchy.
    Afterwards, the new mount hierarchy can be chroot'ed into.
    @param mount_base: the base directory of the new mount hierarchy
    @param temp_base: the base directory for all temporary files
    @param work_base: the base directory for all overlayfs work files
    @param dir_modes: the directory modes to apply (without mount_base prefix)
    """
    # Create a copy of all mountpoints.
    # Setting MS_PRIVATE flag discouples the new mounts from the original mounts,
    # i.e., mounts we do are not seen outside the mount namespace,
    # and any (un)mounts that are made later in the main system are not seen by us.
    # The latter is desired such that new mounts (e.g., USB sticks being plugged in)
    # do not appear in the container.
    # Blocking host-side unmounts from being propagated has the disadvantage
    # that any unmounts done by the sysadmin won't really unmount the device
    # because it stays mounted in the container and thus keep the device busy
    # (cf. https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=739593#85).
    # We could allow unmounts being propated with MS_SLAVE instead of MS_PRIVATE,
    # but we prefer to have the mount namespace of the container being
    # unchanged during run execution.
    make_bind_mount(b"/", mount_base, recursive=True, private=True)

    # Ensure each special dir is a mountpoint such that the next loop covers it.
    for special_dir in dir_modes.keys():
        mount_path = mount_base + special_dir
        temp_path = temp_base + special_dir
        try:
            make_bind_mount(mount_path, mount_path)
        except OSError as e:
            # on btrfs, non-recursive bind mounts fail
            if e.errno == errno.EINVAL:
                try:
                    make_bind_mount(mount_path, mount_path, recursive=True)
                except OSError as e2:
                    logging.debug(
                        "Failed to make %s a (recursive) bind mount: %s", mount_path, e2
                    )
            else:
                logging.debug("Failed to make %s a bind mount: %s", mount_path, e)
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

    for unused_source, full_mountpoint, fstype, options in list(get_mount_points()):
        if not util.path_is_below(full_mountpoint, mount_base):
            continue
        mountpoint = full_mountpoint[len(mount_base) :] or b"/"
        mode = determine_directory_mode(dir_modes, mountpoint, fstype)
        if not mode:
            continue

        if not os.access(os.path.dirname(mountpoint), os.X_OK):
            # If parent is not accessible we cannot mount something on mountpoint.
            # We mark the inaccessible directory as hidden
            # because otherwise the mountpoint could become accessible (directly!)
            # if the permissions on the parent are relaxed during container execution.
            original_mountpoint = mountpoint
            parent = os.path.dirname(mountpoint)
            while not os.access(parent, os.X_OK):
                mountpoint = parent
                parent = os.path.dirname(mountpoint)
            mode = DIR_HIDDEN
            logging.debug(
                "Marking inaccessible directory '%s' as hidden "
                "because it contains a mountpoint at '%s'",
                mountpoint.decode(),
                original_mountpoint.decode(),
            )
        else:
            logging.debug("Mounting '%s' as %s", mountpoint.decode(), mode)

        mount_path = mount_base + mountpoint
        temp_path = temp_base + mountpoint
        work_path = work_base + mountpoint

        if mode == DIR_OVERLAY:
            if not os.path.exists(temp_path):
                os.makedirs(temp_path)
            if not os.path.exists(work_path):
                os.makedirs(work_path)
            try:
                # Previous mount in this place not needed if replaced with overlay dir.
                libc.umount(mount_path)
            except OSError as e:
                logging.debug(e)
            try:
                make_overlay_mount(mount_path, mountpoint, temp_path, work_path)
            except OSError as e:
                mp = mountpoint.decode()
                raise OSError(
                    e.errno,
                    "Creating overlay mount for '{}' failed: {}. Please use "
                    "other directory modes, for example '--read-only-dir {}'.".format(
                        mp, os.strerror(e.errno), util.escape_string_shell(mp)
                    ),
                )

        elif mode == DIR_HIDDEN:
            if not os.path.exists(temp_path):
                os.makedirs(temp_path)
            try:
                # Previous mount in this place not needed if replaced with hidden dir.
                libc.umount(mount_path)
            except OSError as e:
                logging.debug(e)
            make_bind_mount(temp_path, mount_path)

        elif mode == DIR_READ_ONLY:
            try:
                remount_with_additional_flags(mount_path, options, libc.MS_RDONLY)
            except OSError as e:
                if e.errno == errno.EACCES:
                    logging.warning(
                        "Cannot mount '%s', directory may be missing from container.",
                        mountpoint.decode(),
                    )
                else:
                    # If this mountpoint is below an overlay/hidden dir,
                    # re-create mountpoint.
                    # Linux does not support making read-only bind mounts in one step:
                    # https://lwn.net/Articles/281157/
                    # http://man7.org/linux/man-pages/man8/mount.8.html
                    make_bind_mount(
                        mountpoint, mount_path, recursive=True, private=True
                    )
                    remount_with_additional_flags(mount_path, options, libc.MS_RDONLY)

        elif mode == DIR_FULL_ACCESS:
            try:
                # Ensure directory is still a mountpoint by attempting to remount.
                remount_with_additional_flags(mount_path, options, 0)
            except OSError as e:
                if e.errno == errno.EACCES:
                    logging.warning(
                        "Cannot mount '%s', directory may be missing from container.",
                        mountpoint.decode(),
                    )
                else:
                    # If this mountpoint is below an overlay/hidden dir,
                    # re-create mountpoint.
                    make_bind_mount(
                        mountpoint, mount_path, recursive=True, private=True
                    )

        else:
            assert False


def determine_directory_mode(dir_modes, path, fstype=None):
    """
    From a high-level mapping of desired directory modes, determine the actual mode
    for a given directory.
    """
    if fstype == b"proc":
        # proc is necessary for the grandchild to read PID, will be replaced later.
        return DIR_READ_ONLY
    if util.path_is_below(path, b"/proc"):
        # Irrelevant.
        return None

    parent_mode = None
    result_mode = None
    for special_dir, mode in dir_modes.items():
        if util.path_is_below(path, special_dir):
            if path != special_dir:
                parent_mode = mode
            result_mode = mode
    assert result_mode is not None

    if result_mode == DIR_OVERLAY and (
        util.path_is_below(path, b"/dev")
        or util.path_is_below(path, b"/sys")
        or fstype == b"fuse.lxcfs"
        or fstype == b"cgroup"
    ):
        # Silently use RO for /dev, /sys, cgroups, and lxcfs
        # because overlay makes no sense.
        return DIR_READ_ONLY

    if (
        result_mode == DIR_OVERLAY
        and fstype
        and (
            fstype.startswith(b"fuse.")
            or fstype == b"autofs"
            or fstype == b"vfat"
            or fstype == b"ntfs"
        )
    ):
        # Overlayfs does not support these as underlying file systems.
        logging.debug(
            "Cannot use overlay mode for %s because it has file system %s. "
            "Using read-only mode instead. "
            "You can override this by specifying a different directory mode.",
            path.decode(),
            fstype.decode(),
        )
        return DIR_READ_ONLY

    if result_mode == DIR_HIDDEN and parent_mode == DIR_HIDDEN:
        # No need to recursively recreate mountpoints in hidden dirs.
        return None
    return result_mode


def get_mount_points():
    """Get all current mount points of the system.
    Changes to the mount points during iteration may be reflected in the result.
    @return a generator of (source, target, fstype, options),
    where options is a list of bytes instances, and the others are bytes instances
    (this avoids encoding problems with mount points with problematic characters).
    """

    def decode_path(path):
        # Replace tab, space, newline, and backslash escapes with actual characters.
        # According to man 5 fstab, only tab and space escaped, but Linux escapes more:
        # https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/proc_namespace.c?id=12a54b150fb5b6c2f3da932dc0e665355f8a5a48#n85
        return (
            path.replace(br"\011", b"\011")
            .replace(br"\040", b"\040")
            .replace(br"\012", b"\012")
            .replace(br"\134", b"\134")
        )

    with open("/proc/self/mounts", "rb") as mounts:
        # The format of this file is the same as of /etc/fstab (cf. man 5 fstab)
        for mount in mounts:
            source, target, fstype, options, unused1, unused2 = mount.split(b" ")
            options = set(options.split(b","))
            yield (decode_path(source), decode_path(target), fstype, options)


def remount_with_additional_flags(mountpoint, existing_options, mountflags):
    """Remount an existing mount point with additional flags.
    @param mountpoint: the mount point as bytes
    @param existing_options: dict with current mount existing_options as bytes
    @param mountflags: int with additional mount existing_options
        (cf. libc.MS_* constants)
    """
    mountflags |= libc.MS_REMOUNT | libc.MS_BIND
    for option, flag in libc.MOUNT_FLAGS.items():
        if option in existing_options:
            mountflags |= flag

    libc.mount(None, mountpoint, None, mountflags, None)


def make_overlay_mount(mount, lower, upper, work):
    logging.debug(
        "Creating overlay mount: target=%s, lower=%s, upper=%s, work=%s",
        mount,
        lower,
        upper,
        work,
    )
    libc.mount(
        b"none",
        mount,
        b"overlay",
        0,
        b"lowerdir=" + lower + b",upperdir=" + upper + b",workdir=" + work,
    )


def mount_proc(container_system_config):
    """Mount the /proc filesystem.
    @param container_system_config: Whether to mount container-specific files in /proc
    """
    # We keep a reference to the outer /proc somewhere else because we need it
    # to convert our PID between the namespaces.
    libc.mount(b"proc", b"/proc", b"proc", 0, None)

    # lxcfs provides container-aware versions of several /proc files, e.g.  /proc/uptime
    # If lxcfs is available, bind-mount these files over the kernel-provided files.
    if container_system_config and os.access(LXCFS_PROC_DIR, os.R_OK):
        for f in os.listdir(LXCFS_PROC_DIR):
            make_bind_mount(
                os.path.join(LXCFS_PROC_DIR, f), os.path.join(b"/proc", f), private=True
            )

        # Making the above bind mounts on top of /proc breaks nested containers.
        # The reason for this is that the kernel does not allow mounting of a new proc
        # file system (in the nested container) if the nested container does not have
        # access to a clean and fully visible instance of the proc file system.
        # So we give the container two instances: One in the expected place, with lxcfs
        # bind mounts on top, and another one without these bind mounts that is hidden
        # somewhere and hopefully will never be used by anybody. It does not matter
        # where we hide the second proc instance, but we need a directory that always
        # exists and is never used. /proc/1/ns always exists and because we disable
        # PR_SET_DUMPABLE it would not be accessible anyway, so it fits the bill.
        libc.mount(b"proc", b"/proc/1/ns", b"proc", 0, None)


def make_bind_mount(source, target, recursive=False, private=False, read_only=False):
    """Make a bind mount.
    @param source: the source directory as bytes
    @param target: the target directory as bytes
    @param recursive: whether to also recursively bind mount all mounts below source
    @param private: whether to mark the bind as private,
        i.e., changes to the existing mounts won't propagate and vice-versa
        (changes to files/dirs will still be visible).
    """
    flags = libc.MS_BIND
    if recursive:
        flags |= libc.MS_REC
    if private:
        flags |= libc.MS_PRIVATE
    if read_only:
        flags |= libc.MS_RDONLY
    libc.mount(source, target, None, flags, None)


def chroot(target):
    """
    Chroot into a target directory. This also affects the working directory, make sure
    to call os.chdir() afterwards.
    """
    # We need to use pivot_root and not only chroot, and for this we need a place below
    # target where to move the old root directory.
    # Explanation: https://unix.stackexchange.com/a/456777/15398
    old_root = b"/proc"  # Does not matter, just needs to exist.
    # These three steps together are the recommended sequence for calling pivot_root
    # (http://man7.org/linux/man-pages/man8/pivot_root.8.html)
    os.chdir(target)
    libc.pivot_root(target, target + old_root)
    os.chroot(".")
    # Now the container file system is at /,
    # and the outer file system is visible at old_root in the container.
    # We can just unmount old_root and finally make it inaccessible from container.
    libc.umount2(old_root, libc.MNT_DETACH)


def get_my_pid_from_procfs():
    """
    Get the PID of this process by reading from /proc (this is the PID of this process
    in the namespace in which that /proc instance has originally been mounted),
    which may be different from our PID according to os.getpid().
    """
    return int(os.readlink("/proc/self"))


def drop_capabilities(keep=[]):
    """
    Drop all capabilities this process has.
    @param keep: list of capabilities to not drop
    """
    capdata = (libc.CapData * 2)()
    for cap in keep:
        capdata[0].effective |= 1 << cap
        capdata[0].permitted |= 1 << cap
    libc.capset(
        ctypes.byref(libc.CapHeader(version=libc.LINUX_CAPABILITY_VERSION_3, pid=0)),
        ctypes.byref(capdata),
    )


_ALL_SIGNALS = range(1, signal.NSIG)
_FORWARDABLE_SIGNALS = set(range(1, 32)).difference(
    [signal.SIGKILL, signal.SIGSTOP, signal.SIGCHLD]
)
_HAS_SIGWAIT = hasattr(signal, "sigwait")  # Does not exist on Python 2


def block_all_signals():
    """Block asynchronous delivery of all signals to this process."""
    if _HAS_SIGWAIT:
        signal.pthread_sigmask(signal.SIG_BLOCK, _ALL_SIGNALS)


def _forward_signal(signum, target_pid, process_name):
    logging.debug("Forwarding signal %d to process %s.", signum, process_name)
    try:
        os.kill(target_pid, signum)
    except OSError as e:
        logging.debug(
            "Could not forward signal %d to process %s: %s", signum, process_name, e
        )


def forward_all_signals_async(target_pid, process_name):
    """Install all signal handler that forwards all signals to the given process."""

    def forwarding_signal_handler(signum):
        _forward_signal(signum, forwarding_signal_handler.target_pid, process_name)

    # Somehow we get a Python SystemError sometimes
    # if we access target_pid directly from inside function.
    forwarding_signal_handler.target_pid = target_pid

    for signum in _FORWARDABLE_SIGNALS:
        # Need to directly access libc function,
        # the state of the signal module is incorrect due to the clone()
        # (it may think we are in a different thread than the main thread).
        libc.signal(signum, forwarding_signal_handler)

    # Reactivate delivery of signals such that our handler gets called.
    reset_signal_handling()


def wait_for_child_and_forward_signals(child_pid, process_name):
    """Wait for a child to terminate and in the meantime forward all signals
    that the current process receives to this child.
    @return a tuple of exit code and resource usage of the child as given by os.waitpid
    """
    assert _HAS_SIGWAIT
    block_all_signals()

    while True:
        logging.debug("Waiting for signals")
        signum = signal.sigwait(_ALL_SIGNALS)
        if signum == signal.SIGCHLD:
            pid, exitcode, ru_child = os.wait4(-1, os.WNOHANG)
            while pid != 0:
                if pid == child_pid:
                    return exitcode, ru_child
                else:
                    logging.debug("Received unexpected SIGCHLD for PID %s", pid)
                pid, exitcode, ru_child = os.wait4(-1, os.WNOHANG)

        else:
            _forward_signal(signum, child_pid, process_name)


def reset_signal_handling():
    if _HAS_SIGWAIT:
        signal.pthread_sigmask(signal.SIG_SETMASK, {})


def close_open_fds(keep_files=[]):
    """Close all open file descriptors except those in a given set.
    @param keep_files: an iterable of file descriptors or file-like objects.
    """
    keep_fds = set()
    for file in keep_files:
        if isinstance(file, int):
            keep_fds.add(file)
        else:
            try:
                keep_fds.add(file.fileno())
            except Exception:
                pass

    for fd in os.listdir("/proc/self/fd"):
        fd = int(fd)
        if fd not in keep_fds:
            try:
                os.close(fd)
            except OSError:
                # irrelevant and expected
                # (the fd that was used by os.listdir() of course always fails)
                pass


def setup_container_system_config(basedir, mountdir, dir_modes):
    """Create a minimal system configuration for use in a container.
    @param basedir: The directory where the configuration files should be placed (bytes)
    @param mountdir: The base directory of the mount hierarchy in the container (bytes).
    @param dir_modes: All directory modes in the container.
    """
    # If overlayfs is not used for /etc, we need additional bind mounts
    # for files in /etc that we want to override, like /etc/passwd
    symlinks_required = determine_directory_mode(dir_modes, b"/etc") != DIR_OVERLAY

    etc = os.path.join(basedir, b"etc")
    if not os.path.exists(etc):
        os.mkdir(etc)

    for file, content in CONTAINER_ETC_FILE_OVERRIDE.items():
        # Create "basedir/etc/file"
        util.write_file(content, etc, file)
        if symlinks_required:
            # Create bind mount to "mountdir/etc/file"
            make_bind_mount(
                os.path.join(etc, file),
                os.path.join(mountdir, b"etc", file),
                private=True,
            )

    os.symlink(b"/proc/self/mounts", os.path.join(etc, b"mtab"))
    # Bind bounds for symlinks are not possible, so do nothing for "mountdir/etc/mtab".
    # This is not a problem because most systems have the correct symlink anyway.

    if not os.path.isdir(mountdir.decode() + CONTAINER_HOME):
        logging.warning(
            "Home directory in container should be %(h)s but this directory "
            "cannot be created due to directory mode of parent directory. "
            "It is recommended to use '--overlay-dir %(p)s' or '--hidden-dir %(p)s' "
            "and overwrite directory modes for subdirectories where necessary.",
            {"h": CONTAINER_HOME, "p": os.path.dirname(CONTAINER_HOME)},
        )


def is_container_system_config_file(file):
    """Determine whether a given file is one of the files created by
    setup_container_system_config().
    @param file: Absolute file path as string.
    """
    if not file.startswith("/etc/"):
        return False
    return file in [
        os.path.join("/etc", f.decode()) for f in CONTAINER_ETC_FILE_OVERRIDE
    ]
