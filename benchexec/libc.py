# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""This module contains function declarations for several functions of libc
(based on ctypes) and constants relevant for these functions.
"""

import ctypes as _ctypes
from ctypes import c_int, c_uint32, c_long, c_ulong, c_size_t, c_char_p, c_void_p
import os as _os

_libc = _ctypes.CDLL("libc.so.6", use_errno=True)
"""Reference to standard C library."""
_libc_with_gil = _ctypes.PyDLL("libc.so.6", use_errno=True)
"""Reference to standard C library, and we hold the GIL during all function calls."""


def _check_errno(result, func, arguments):
    assert func.restype in [c_int, c_void_p]
    if (func.restype == c_int and result == -1) or (
        func.restype == c_void_p and c_void_p(result).value == c_void_p(-1).value
    ):
        errno = _ctypes.get_errno()
        try:
            func_name = func.__name__
        except AttributeError:
            func_name = "__unknown__"
        msg = (
            func_name
            + "("
            + ", ".join(map(str, arguments))
            + ") failed: "
            + _os.strerror(errno)
        )
        raise OSError(errno, msg)
    return result


# off_t is a signed integer type required for mmap.
# In my tests it is equal to long on both 32bit and 64bit x86 Linux.
c_off_t = c_long

clone = _libc_with_gil.clone  # Important to have GIL, cf. container.py!
"""Create copy of current process, similar to fork()."""
CLONE_CALLBACK = _ctypes.CFUNCTYPE(c_int, c_void_p)
"""Type use for callback functions of clone, can be used as decorator."""
clone.argtypes = [
    CLONE_CALLBACK,
    c_void_p,
    c_int,
    c_void_p,
]  # fn, child_stack, flags, arg (varargs omitted)
clone.errcheck = _check_errno

# /usr/include/linux/sched.h
CLONE_NEWNS = 0x00020000
CLONE_NEWCGROUP = 0x02000000
CLONE_NEWUTS = 0x04000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWPID = 0x20000000
CLONE_NEWNET = 0x40000000

unshare = _libc.unshare
"""Put current process into new namespace(s)."""
unshare.argtypes = [c_int]
unshare.errcheck = _check_errno


mmap = _libc.mmap
"""Map file into memory."""
mmap.argtypes = [
    c_void_p,
    c_size_t,
    c_int,
    c_int,
    c_int,
    c_off_t,
]  # addr, length, prot, flags, fd, offset
mmap.restype = c_void_p
mmap.errcheck = _check_errno


def mmap_anonymous(length, prot, flags=0):
    """Allocate anonymous memory with mmap. Length must be multiple of page size."""
    return mmap(None, length, prot, flags | MAP_ANONYMOUS | MAP_PRIVATE, -1, 0)


munmap = _libc.munmap
"""Free mmap()ed memory."""
munmap.argtypes = [c_void_p, c_size_t]
munmap.errcheck = _check_errno

mprotect = _libc.mprotect
"""Set protection on a region of memory."""
mprotect.argtypes = [c_void_p, c_size_t, c_int]  # addr, length, prot
mprotect.errcheck = _check_errno

PROT_NONE = 0x0  # /usr/include/bits/mman-linux.h
MAP_GROWSDOWN = 0x00100  # /usr/include/bits/mman.h
MAP_STACK = 0x20000  # /usr/include/bits/mman.h
from mmap import (  # noqa: F401 E402
    PROT_EXEC,
    PROT_READ,
    PROT_WRITE,
    MAP_ANONYMOUS,
    MAP_PRIVATE,
)  # @UnusedImport imported for users of this module


mount = _libc.mount
"""Mount a filesystem."""
mount.argtypes = [
    c_char_p,
    c_char_p,
    c_char_p,
    c_ulong,
    c_void_p,
]  # source, target, fstype, mountflags, data
mount.errcheck = _check_errno

# /usr/include/sys/mount.h
MS_RDONLY = 1
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_REMOUNT = 32
MS_BIND = 4096
MS_MOVE = 8192
MS_REC = 16384
MS_PRIVATE = 262144
MOUNT_FLAGS = {
    b"ro": MS_RDONLY,
    b"nosuid": MS_NOSUID,
    b"nodev": MS_NODEV,
    b"noexec": MS_NOEXEC,
}

umount = _libc.umount
"""Unmount a filesystem."""
umount.argtypes = [c_char_p]  # target
umount.errcheck = _check_errno

umount2 = _libc.umount2
"""Unmount a filesystem."""
umount2.argtypes = [c_char_p, c_int]  # target, flags
umount2.errcheck = _check_errno

# /usr/include/sys/mount.h
MNT_DETACH = 2


pivot_root = _libc.pivot_root
"""Replace root file system with a different directory."""
pivot_root.argtypes = [c_char_p, c_char_p]
pivot_root.errcheck = _check_errno


class CapHeader(_ctypes.Structure):
    """Structure for first parameter of capset()."""

    _fields_ = ("version", c_uint32), ("pid", c_int)


class CapData(_ctypes.Structure):
    """Structure for second parameter of capset()."""

    _fields_ = (
        ("effective", c_uint32),
        ("permitted", c_uint32),
        ("inheritable", c_uint32),
    )


capset = _libc.capset
"""Configure the capabilities of the current thread."""
capset.errcheck = _check_errno
capset.argtypes = [
    _ctypes.POINTER(CapHeader),
    _ctypes.POINTER(CapData * 2),
]

capget = _libc.capget
"""Get the capabilities of the current thread."""
capget.errcheck = _check_errno
capget.argtypes = [
    _ctypes.POINTER(CapHeader),
    _ctypes.POINTER(CapData * 2),
]

LINUX_CAPABILITY_VERSION_3 = 0x20080522  # /usr/include/linux/capability.h
LINUX_CAPABILITY_U32S_3 = 2  # /usr/include/linux/capability.h
CAP_SYS_ADMIN = 21  # /usr/include/linux/capability.h
PR_CAP_AMBIENT = 47  # /usr/include/linux/prctl.h
PR_CAP_AMBIENT_RAISE = 2  # /usr/include/linux/prctl.h
PR_CAP_AMBIENT_CLEAR_ALL = 4  # /usr/include/linux/prctl.h

prctl = _libc.prctl
"""Modify options of processes: http://man7.org/linux/man-pages/man2/prctl.2.html"""
prctl.errcheck = _check_errno
prctl.argtypes = [c_int, c_ulong, c_ulong, c_ulong, c_ulong]


# /usr/include/linux/prctl.h
PR_SET_DUMPABLE = 4
PR_GET_SECCOMP = 21
PR_SET_SECCOMP = 22
SUID_DUMP_DISABLE = 0
SUID_DUMP_USER = 1
