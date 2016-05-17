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
import signal
import socket
import struct

from benchexec import libc
from benchexec import util

__all__ = [
    'execute_in_namespace',
    'setup_user_mapping',
    'activate_network_interface',
    'get_mount_points',
    'remount_with_additional_flags',
    'make_overlay_mount',
    'mount_proc',
    'make_bind_mount',
    'get_my_pid_from_proc',
    'drop_capabilities',
    'forward_all_signals',
    'setup_container_config',
    'CONTAINER_UID',
    'CONTAINER_GID',
    'CONTAINER_HOME',
    ]


DEFAULT_STACK_SIZE = 1024*1024
GUARD_PAGE_SIZE = 4096 # size of guard page at end of stack

CONTAINER_UID = 1000
CONTAINER_GID = 1000
CONTAINER_HOME = '/home/benchexec'

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
""".format(uid=CONTAINER_UID, gid=CONTAINER_GID, home=CONTAINER_HOME)

CONTAINER_ETC_GROUP = """
root:x:0:
benchexec:x:{gid}:
nogroup:x:65534:
""".format(uid=CONTAINER_UID, gid=CONTAINER_GID, home=CONTAINER_HOME)

CONTAINER_ETC_HOSTS = """
127.0.0.1       localhost {host} {fqdn}
# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
""".format(host=socket.gethostname(), fqdn=socket.getfqdn())

CONTAINER_ETC_FILE_OVERRIDE = {
    b'nsswitch.conf': CONTAINER_ETC_NSSWITCH_CONF,
    b'passwd': CONTAINER_ETC_PASSWD,
    b'group': CONTAINER_ETC_GROUP,
    b'hosts': CONTAINER_ETC_HOSTS,
    }


@contextlib.contextmanager
def allocate_stack(size=DEFAULT_STACK_SIZE):
    """Allocate some memory that can be used as a stack.
    @return: a ctypes void pointer to the *top* of the stack.
    """
    # Allocate memory with appropriate flags for a stack as in https://blog.fefe.de/?ts=a85c8ba7
    base = libc.mmap(
        None,
        size + GUARD_PAGE_SIZE,
        libc.PROT_READ | libc.PROT_WRITE,
        libc.MAP_PRIVATE | libc.MAP_ANONYMOUS | libc.MAP_GROWSDOWN | libc.MAP_STACK,
        -1, 0)

    try:
        # create a guard page that crashes the application when it is written to (on stack overflow)
        libc.mprotect(base, GUARD_PAGE_SIZE, libc.PROT_NONE)

        yield ctypes.c_void_p(base + size + GUARD_PAGE_SIZE)
    finally:
        libc.munmap(base, size + GUARD_PAGE_SIZE)

def execute_in_namespace(func, use_network_ns=True):
    """Execute a function in a child process in separate namespaces.
    @param func: a parameter-less function returning an int (which will be the process' exit value)
    @return: the PID of the created child process
    """
    flags = (signal.SIGCHLD |
        libc.CLONE_NEWNS | libc.CLONE_NEWUTS | libc.CLONE_NEWIPC | libc.CLONE_NEWUSER |
        libc.CLONE_NEWPID)
    if use_network_ns:
        flags |= libc.CLONE_NEWNET

    # We use the syscall clone() here, which is similar to fork().
    # Calling it without letting Python know about it is dangerous (especially because
    # we want to execute Python code in the child, too), but so far it seems to work.
    # Basically we attempt to do (almost) the same that os.fork() does (cf. function os_fork_impl
    # in https://github.com/python/cpython/blob/master/Modules/posixmodule.c).
    # We currently do not take the import lock os.lock() does because it is only available
    # via an internal API, and because the child should never import anything anyway
    # (inside the container, modules might not be visible).
    # It is very important, however, that we have the GIL during clone(),
    # otherwise the child will often deadlock when trying to execute Python code.
    # Luckily, the ctypes module allows us to hold the GIL while executing the
    # function by using ctypes.PyDLL as library access instead of ctypes.CLL.

    def child_func():
        # This is necessary for correcting the Python interpreter state after a
        # fork-like operation. For example, it resets the GIL and fixes state of
        # several modules like threading and signal.
        ctypes.pythonapi.PyOS_AfterFork()

        return func()

    with allocate_stack() as stack:
        pid = libc.clone(ctypes.CFUNCTYPE(ctypes.c_int)(child_func), stack, flags, None)
    return pid

def setup_user_mapping(pid, uid=os.getuid(), gid=os.getgid()):
    """Write uid_map and gid_map in /proc to create a user mapping
    that maps our user from outside the container to the same user inside the container
    (and no other users are mapped).
    @see: http://man7.org/linux/man-pages/man7/user_namespaces.7.html
    @param pid: The PID of the process in the container.
    """
    proc_child = os.path.join("/proc", str(pid))
    try:
        uid_map = "{0} {1} 1".format(uid, os.getuid()) # map uid internally to our uid externally
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
        gid_map = "{0} {1} 1".format(gid, os.getgid()) # map gid internally to our gid externally
        util.write_file(gid_map, proc_child, "gid_map")
    except IOError as e:
        logging.warning("Creating GID mapping into container failed: %s", e)

def activate_network_interface(iface):
    """Bring up the given network interface.
    @raise OSError: if interface does not exist or permissions are missing
    """
    iface = iface.encode()

    SIOCGIFFLAGS = 0x8913 # /usr/include/bits/ioctls.h
    SIOCSIFFLAGS = 0x8914 # /usr/include/bits/ioctls.h
    IFF_UP = 0x1 # /usr/include/net/if.h

    # We need to use instances of "struct ifreq" for communicating with the kernel.
    # This struct is complex with a big contained union, we define here only the few necessary
    # fields for the two cases we need.
    # The layout is given in the format used by the struct module:
    STRUCT_IFREQ_LAYOUT_IFADDR_SAFAMILY = b"16sH14s" # ifr_name, ifr_addr.sa_family, padding
    STRUCT_IFREQ_LAYOUT_IFFLAGS = b"16sH14s" # ifr_name, ifr_flags, padding

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
    try:
        # Get current interface flags from kernel
        ifreq = struct.pack(STRUCT_IFREQ_LAYOUT_IFADDR_SAFAMILY, iface, socket.AF_INET, b'0' * 14)
        ifreq = fcntl.ioctl(sock, SIOCGIFFLAGS, ifreq)
        if_flags = struct.unpack(STRUCT_IFREQ_LAYOUT_IFFLAGS, ifreq)[1]

        # Set new flags
        ifreq = struct.pack(STRUCT_IFREQ_LAYOUT_IFFLAGS, iface, if_flags | IFF_UP, b'0' * 14)
        fcntl.ioctl(sock, SIOCSIFFLAGS, ifreq)
    finally:
        sock.close()

def get_mount_points():
    """Get all current mount points of the system.
    Changes to the mount points during iteration may be reflected in the result.
    @return a generator of (source, target, fstype, options),
    where options is a list of bytes instances, and the others are bytes instances
    (this avoids encoding problems with mount points with problematic characters).
    """
    with open("/proc/self/mounts", "rb") as mounts:
        for mount in mounts:
            source, target, fstype, options, unused1, unused2 = mount.split(b" ")
            options = set(options.split(b","))
            yield (source, target, fstype, options)

def remount_with_additional_flags(mountpoint, existing_options, mountflags):
    """Remount an existing mount point with additional flags.
    @param mountpoint: the mount point as bytes
    @param existing_options: dict with current mount existing_options as bytes
    @param mountflags: int with additional mount existing_options (cf. libc.MS_* constants)
    """
    mountflags |= libc.MS_REMOUNT|libc.MS_BIND
    for option, flag in libc.MOUNT_FLAGS.items():
        if option in existing_options:
            mountflags |= flag

    libc.mount(None, mountpoint, None, mountflags, None)

def make_overlay_mount(mount, lower, upper, work):
    logging.debug("Creating overlay mount: target=%s, lower=%s, upper=%s, work=%s",
                  mount, lower, upper, work)
    libc.mount(b"none", mount, b"overlay", 0,
               b"lowerdir=" + lower + b",upperdir=" + upper + b",workdir=" + work)

def mount_proc():
    """Mount the /proc filesystem."""
    # We keep a reference to the outer /proc somewhere else because we need it
    # to convert our PID between the namespaces.
    libc.mount(b"proc", b"/proc", b"proc", 0, None)

def make_bind_mount(source, target, recursive=False, private=False):
    """Make a bind mount.
    @param source: the source directory as bytes
    @param target: the target directory as bytes
    @param recursive: whether to also recursively bind mount all mounts below source
    @param private: whether to mark the bind as private, i.e., changes to the existing mounts
        won't propagate and vice-versa (changes to files/dirs will still be visible).
    """
    flags = libc.MS_BIND
    if recursive:
        flags |= libc.MS_REC
    if private:
        flags |= libc.MS_PRIVATE
    libc.mount(source, target, None, flags, None)

def get_my_pid_from_procfs():
    """Get the PID of this process by reading from /proc (this is the PID of this process
    in the namespace in which that /proc instance has originally been mounted),
    which may be different from our PID according to os.getpid().
    """
    return int(os.readlink("/proc/self"))

def drop_capabilities():
    """Drop all capabilities this process has."""
    libc.capset(ctypes.byref(libc.CapHeader(version=libc.LINUX_CAPABILITY_VERSION_3, pid=0)),
                ctypes.byref((libc.CapData * 2)()))


_FORWARDABLE_SIGNALS = set(range(1, 32)).difference([signal.SIGKILL, signal.SIGSTOP, signal.SIGCHLD])

def forward_all_signals(target_pid, process_name):
    def forwarding_signal_handler(signum):
        logging.debug("Forwarding signal %d to process %s.", signum, process_name)
        try:
            os.kill(forwarding_signal_handler.target_pid, signum)
        except OSError as e:
            logging.debug("Could not forward signal %d to process %s: %s", signum, process_name, e)

    # Somehow we get a Python SystemError sometimes if we access target_pid directly from inside function.
    forwarding_signal_handler.target_pid = target_pid

    for signum in _FORWARDABLE_SIGNALS:
        # Need to directly access libc function,
        # the state of the signal module is incorrect due to the clone()
        # (it may think we are in a different thread than the main thread).
        libc.signal(signum, forwarding_signal_handler)

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

def setup_container_system_config(basedir):
    """Create a minimal system configuration for use in a container.
    @param basedir: The root directory of the container as bytes.
    """
    etc = os.path.join(basedir, b"etc")
    if not os.path.exists(etc):
        os.mkdir(etc)

    for file, content in CONTAINER_ETC_FILE_OVERRIDE.items():
        util.write_file(content, etc, file)

    os.symlink(b"/proc/self/mounts", os.path.join(etc, b"mtab"))

def is_container_system_config_file(file):
    """Determine whether a given file is one of the files created by setup_container_system_config().
    @param file: Absolute file path as string.
    """
    if not file.startswith("/etc/"):
        return False
    return file in [os.path.join("/etc", f.decode()) for f in CONTAINER_ETC_FILE_OVERRIDE]
