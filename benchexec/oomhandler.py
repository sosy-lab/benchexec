# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import threading

from benchexec import util


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

    @param cgroups: The cgroups instance to monitor
    @param process: The process instance to kill
    @param callbackFn: A one-argument function that is called in case of OOM with a string for the reason as argument
    """

    def __init__(self, cgroups, pid_to_kill, callbackFn=lambda reason: None):
        super(KillProcessOnOomThread, self).__init__()
        self.name = "KillProcessOnOomThread-" + self.name
        self._finished = threading.Event()
        self._pid_to_kill = pid_to_kill
        self._cgroups = cgroups
        self._callback = callbackFn

        self._efd = self._cgroups.set_oom_handler()

    def run(self):
        # os.close gets called in finally,
        # which sometimes is executed while the process is shutting down already.
        # It happens that the Python interpreter has already cleaned up at this point
        # and "os" resolves to None, leading to an AttributeError.
        # Thus we keep our own reference to this function.
        # (Should not happen anymore since this is no longer a daemon thread,
        # but should not hurt anyway.)
        close = os.close
        try:
            # In an eventfd, there are always 8 bytes for the event number.
            # We just do a blocking read to wait for the event.
            _ = os.read(self._efd, 8)
            # If read returned, this means the kernel sent us an event.
            # It does so either on OOM or if the cgroup is removed.
            if not self._finished.is_set():
                self._callback("memory")
                logging.debug(
                    "Killing process %s due to out-of-memory event from kernel.",
                    self._pid_to_kill,
                )
                util.kill_process(self._pid_to_kill)

                # Also kill all children of subprocesses directly.
                self._cgroups.kill_all_tasks()

                # We now need to increase the memory limit of this cgroup
                # to give the process a chance to terminate
                self._cgroups.reset_memory_limit()

        finally:
            close(self._efd)

    def cancel(self):
        self._finished.set()
