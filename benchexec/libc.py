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

"""This module contains function declarations for several functions of libc (based on ctypes),
and constants relevant for these functions.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

# THIS MODULE HAS TO WORK WITH PYTHON 2.7!

import ctypes as _ctypes
from ctypes import c_int, c_uint32, c_long, c_ulong, c_size_t, c_char_p, c_void_p
import os as _os

_libc = _ctypes.CDLL("libc.so.6", use_errno=True)
"""Reference to standard C library."""
_libc_with_GIL = _ctypes.PyDLL("libc.so.6", use_errno=True)
"""Reference to standard C library, and we will hold the GIL during all function calls."""

def _check_errno(result, func, arguments):
    assert func.restype in [c_int, c_void_p]
    if ((func.restype == c_int and result == -1) or
            (func.restype == c_void_p and c_void_p(result).value == c_void_p(-1).value)):
        errno = _ctypes.get_errno()
        try:
            func_name = func.__name__
        except AttributeError:
            func_name = "__unknown__"
        msg = func_name + "(" + ", ".join(map(str, arguments)) + ") failed: " + _os.strerror(errno)
        raise OSError(errno, msg)
    return result

# off_t is a signed integer type required for mmap.
# In my tests it is equal to long on both 32bit and 64bit x86 Linux.
c_off_t = c_long

clone = _libc_with_GIL.clone # Important to have GIL, cf. container.py!
"""Create copy of current process, similar to fork()."""
clone.argtypes = [_ctypes.CFUNCTYPE(c_int), c_void_p, c_int, c_void_p] # fn, child_stack, flags, arg (varargs omitted)
clone.errcheck = _check_errno

# /usr/include/linux/sched.h
CLONE_NEWNS = 0x00020000
CLONE_NEWUTS = 0x04000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWPID = 0x20000000
CLONE_NEWNET = 0x40000000


mmap = _libc.mmap
"""Map file into memory."""
mmap.argtypes = [c_void_p, c_size_t, c_int, c_int, c_int, c_off_t] # add, length, prot, flags, fd, offset
mmap.restype = c_void_p
mmap.errcheck = _check_errno

munmap = _libc.munmap
"""Free mmap()ed memory."""
munmap.argtypes = [c_void_p, c_size_t]
munmap.errcheck = _check_errno

mprotect = _libc.mprotect
"""Set protection on a region of memory."""
mprotect.argtypes = [c_void_p, c_size_t, c_int] # addr, length, prot
mprotect.errcheck = _check_errno

PROT_NONE = 0x0 # /usr/include/bits/mman-linux.h
MAP_GROWSDOWN = 0x00100 # /usr/include/bits/mman.h
MAP_STACK = 0x20000 # /usr/include/bits/mman.h
from mmap import PROT_EXEC, PROT_READ, PROT_WRITE, MAP_ANONYMOUS, MAP_PRIVATE  # @UnusedImport


mount = _libc.mount
"""Mount a filesystem."""
mount.argtypes = [c_char_p, c_char_p, c_char_p, c_ulong, c_void_p] # source, target, fstype, mountflags, data
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
umount.argtypes = [c_char_p] # target
umount.errcheck = _check_errno


_sighandler_t = _ctypes.CFUNCTYPE(None, c_int)
_libc.signal.argtypes = [c_int, _sighandler_t]
_libc.signal.restype = c_void_p
_libc.signal.errcheck = _check_errno
def signal(signal, handler):
    """Set a signal handler similar to signal.signal(), but directly via libc."""
    _libc.signal(signal, _sighandler_t(handler))


class CapHeader(_ctypes.Structure):
    """Structure for first parameter of capset()."""
    _fields_ = ("version", c_uint32), ("pid", c_int)

class CapData(_ctypes.Structure):
    """Structure for second parameter of capset()."""
    _fields_ = ("effective", c_uint32), ("permitted", c_uint32), ("inheritable", c_uint32)

capset = _libc.capset
"""Configure the capabilities of the current thread."""
capset.errcheck = _check_errno
capset.argtypes = [_ctypes.POINTER(CapHeader), _ctypes.POINTER(CapData * 2)]

LINUX_CAPABILITY_VERSION_3 = 0x20080522 # /usr/include/linux/capability.h
