"""
CPAchecker is a tool for configurable software verification.
This file is part of CPAchecker.

Copyright (C) 2007-2014  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


CPAchecker web page:
  http://cpachecker.sosy-lab.org
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import signal
import threading

from . import util

_BYTE_FACTOR = 1000 # byte in kilobyte

class KillProcessOnOomThread(threading.Thread):
    """
    Thread that kills the process when they run out of memory.
    Usually the kernel would do this by itself,
    but sometimes the process still hangs because it does not even have
    enough memory left to get killed
    (the memory limit also effects some kernel-internal memory related to our process).
    So we disable the kernel-side killing,
    and instead let the kernel notify us via an event when the cgroup ran out of memory.
    Then we kill the process ourselves and increase the memory limit a little bit.

    The notification works by opening an "event file descriptor" with eventfd,
    and telling the kernel to notify us about OOMs by writing the event file
    descriptor and an file descriptor of the memory.oom_control file
    to cgroup.event_control.
    The kernel-side process killing is disabled by writing 1 to memory.oom_control.
    Sources:
    https://www.kernel.org/doc/Documentation/cgroups/memory.txt
    https://access.redhat.com/site/documentation//en-US/Red_Hat_Enterprise_Linux/6/html/Resource_Management_Guide/sec-memory.html#ex-OOM-control-notifications

    @param cgroup: The memory cgroup the process is in
    @param process: The process instance to kill
    @param callbackFn: A one-argument function that is called in case of OOM with a string for the reason as argument
    """
    def __init__(self, cgroup, process, callbackFn=lambda reason: None):
        super(KillProcessOnOomThread, self).__init__()
        self.daemon = True
        self._finished = threading.Event()
        self._process = process
        self._cgroup = cgroup
        self._callback = callbackFn

        ofd = os.open(os.path.join(cgroup, 'memory.oom_control'), os.O_WRONLY)
        try:
            from ctypes import cdll
            libc = cdll.LoadLibrary('libc.so.6')

            # Important to use CLOEXEC, otherwise the benchmarked tool inherits
            # the file descriptor.
            EFD_CLOEXEC = 0x80000 # from <sys/eventfd.h>
            self._efd = libc.eventfd(0, EFD_CLOEXEC)

            try:
                util.write_file('{} {}'.format(self._efd, ofd),
                                     cgroup, 'cgroup.event_control')

                # If everything worked, disable Kernel-side process killing.
                # This is not allowed if memory.use_hierarchy is enabled,
                # but we don't care.
                try:
                    os.write(ofd, '1'.encode('ascii'))
                except OSError as e:
                    logging.debug("Failed to disable kernel-side OOM killer: error {0} ({1})".format(e.errno, e.strerror))
            except EnvironmentError as e:
                os.close(self._efd)
                raise e
        finally:
            os.close(ofd)

    def run(self):
        try:
            # In an eventfd, there are always 8 bytes
            eventNumber = os.read(self._efd, 8) # blocks
            # If read returned, this means the kernel sent us an event.
            # It does so either on OOM or if the cgroup is removed.
            if not self._finished.is_set():
                self._callback('memory')
                logging.debug('Killing process {0} due to out-of-memory event from kernel.'.format(self._process.pid))
                util.kill_process(self._process.pid)
                # Also kill all children of subprocesses directly.
                with open(os.path.join(self._cgroup, 'tasks'), 'rt') as tasks:
                    for task in tasks:
                        util.kill_process(int(task))

                # We now need to increase the memory limit of this cgroup
                # to give the process a chance to terminate
                self._reset_memory_limit('memory.memsw.limit_in_bytes')
                self._reset_memory_limit('memory.limit_in_bytes')

        finally:
            try:
                os.close(self._efd)
            except AttributeError:
                pass # when the Python process is shutting down, "os" is sometimes already missing

    def _reset_memory_limit(self, limitFile):
        if os.path.exists(os.path.join(self._cgroup, limitFile)):
            try:
                # Write a high value (1 PB) as the limit
                util.write_file(str(1 * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR),
                                     self._cgroup, limitFile)
            except IOError as e:
                logging.warning('Failed to increase {0} after OOM: error {1} ({2})'.format(limitFile, e.errno, e.strerror))


    def cancel(self):
        self._finished.set()
