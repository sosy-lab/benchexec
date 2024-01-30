# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import logging
import sys
import tempfile
import threading

from benchexec.cgroups import Cgroups
from benchexec.runexecutor import RunExecutor

sys.dont_write_bytecode = True  # prevent creation of .pyc files


def check_cgroup_availability(wait=1):
    """
    Basic utility to check the availability and permissions of cgroups.
    This will log some warnings for the user if necessary.
    On some systems, daemons such as cgrulesengd might interfere with the cgroups
    of a process soon after it was started. Thus this function starts a process,
    waits a configurable amount of time, and check whether the cgroups have been changed.
    @param wait: a non-negative int that is interpreted as seconds to wait during the check
    @raise SystemExit: if cgroups are not usable
    """
    logging.basicConfig(format="%(levelname)s: %(message)s")
    runexecutor = RunExecutor(use_namespaces=False)
    my_cgroups = runexecutor.cgroups

    if not (
        my_cgroups.CPU in my_cgroups
        # and FREEZER in my_cgroups # For now, we do not require freezer
        and my_cgroups.MEMORY in my_cgroups
    ):
        sys.exit(1)

    if my_cgroups.CPUSET in my_cgroups:
        cores = my_cgroups.read_allowed_cpus()
        mems = my_cgroups.read_allowed_memory_banks()
    else:
        # Use dummy value (does not matter which) to let execute_run() fail.
        cores = [0]
        mems = [0]

    with tempfile.NamedTemporaryFile(mode="rt") as tmp:
        execution = runexecutor.execute_run(
            ["sh", "-c", f"sleep {wait}; cat /proc/self/cgroup"],
            tmp.name,
            memlimit=100 * 1024 * 1024,  # set memlimit to force check for swapaccount
            # set cores and memory_nodes to force usage of CPUSET
            cores=cores,
            memory_nodes=mems,
        )
        if "terminationreason" in execution:
            logging.error(
                "Cgroup check terminated with reason '%s'.",
                execution["terminationreason"],
            )
            sys.exit(1)
        assert execution["exitcode"].raw == 0, execution
        lines = []
        for line in tmp:
            line = line.strip()
            if (
                line
                and not line == f"sh -c 'sleep {wait}; cat /proc/self/cgroup'"
                and not all(c == "-" for c in line)
            ):
                lines.append(line)
    task_cgroups = Cgroups.from_system(cgroup_procinfo=lines)

    fail = False
    expected_subsystems = [my_cgroups.FREEZE]
    if my_cgroups.version == 1:
        expected_subsystems += [my_cgroups.CPU, my_cgroups.CPUSET, my_cgroups.MEMORY]
    for subsystem in expected_subsystems:
        if subsystem in my_cgroups:
            if not str(task_cgroups[subsystem]).startswith(str(my_cgroups[subsystem])):
                logging.warning(
                    "Task was in cgroup %s for subsystem %s, "
                    "which is not the expected sub-cgroup of %s. "
                    "Maybe some other program is interfering with cgroup management?",
                    task_cgroups[subsystem],
                    subsystem,
                    my_cgroups[subsystem],
                )
                fail = True
    if fail:
        sys.exit(1)


def check_cgroup_availability_in_thread(options):
    """
    Run check_cgroup_availability() in a separate thread to detect the following problem:
    If "cgexec --sticky" is used to tell cgrulesengd to not interfere
    with our child processes, the sticky flag unfortunately works only
    for processes spawned by the main thread, not those spawned by other threads
    (and this will happen if "benchexec -N" is used).
    """
    thread = _CheckCgroupsThread(options)
    thread.daemon = True
    thread.start()
    thread.join()
    if thread.error:
        raise thread.error


class _CheckCgroupsThread(threading.Thread):
    error = None

    def __init__(self, options):
        super(_CheckCgroupsThread, self).__init__()
        self.options = options

    def run(self):
        try:
            check_cgroup_availability(self.options.wait)
        except BaseException as e:
            self.error = e


def main(argv=None):
    """
    A simple command-line interface for the cgroups check of BenchExec.
    """
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description="""Check whether cgroups are available and can be used for BenchExec.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=1,
        metavar="SECONDS",
        help="wait some time to ensure no process interferes with cgroups in the meantime (default: 1s)",
    )
    parser.add_argument(
        "--no-thread",
        action="store_true",
        help="run check on the main thread instead of a separate thread"
        " (behavior of cgrulesengd differs depending on this)",
    )

    options = parser.parse_args(argv[1:])

    if options.no_thread:
        check_cgroup_availability(options.wait)
    else:
        check_cgroup_availability_in_thread(options)


if __name__ == "__main__":
    main()
