# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import errno
import grp
import logging
import os
import shlex
import shutil
import signal
import stat
import sys
import tempfile
import time

from benchexec import systeminfo
from benchexec import util
from benchexec.cgroups import Cgroups

CGROUP_FALLBACK_PATH = "system.slice/benchexec-cgroup.service"
"""If we do not have write access to the current cgroup,
attempt to use this cgroup as fallback."""

CGROUP_NAME_PREFIX = "benchmark_"

BLKIO_BYTES_FILE = "throttle.io_service_bytes"

_PERMISSION_HINT_GROUPS = """
You need to add your account to the following groups: {0}
Remember to logout and login again afterwards to make group changes effective."""

_PERMISSION_HINT_DEBIAN = """
The recommended way to fix this is to install the Debian package for BenchExec and add your account to the group "benchexec":
https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#debianubuntu
Alternatively, you can install benchexec-cgroup.service manually:
https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#setting-up-cgroups-on-machines-with-systemd"""

_PERMISSION_HINT_SYSTEMD = """
The recommended way to fix this is to add your account to a group named "benchexec" and install benchexec-cgroup.service:
https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#setting-up-cgroups-on-machines-with-systemd"""

_PERMISSION_HINT_OTHER = """
Please configure your system in way to allow your user to use cgroups:
https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#setting-up-cgroups-on-machines-without-systemd"""

_ERROR_MSG_PERMISSIONS = """
Required cgroups are not available because of missing permissions.{0}

As a temporary workaround, you can also run
"sudo chmod o+wt {1}"
Note that this will grant permissions to more users than typically desired and it will only last until the next reboot."""

_ERROR_MSG_OTHER = """
Required cgroups are not available.
If you are using BenchExec within a container, please make "/sys/fs/cgroup" available."""


def find_my_cgroups(cgroup_paths=None, fallback=True):
    """
    Return a dict with the cgroups of the current process.
    Note that it is not guaranteed that all subsystems are available
    in the returned object, as a subsystem may not be mounted.
    Check with "subsystem in <instance>" before using.
    A subsystem may also be present but we do not have the rights to create
    child cgroups, this can be checked with require_subsystem().
    @param cgroup_paths: If given, use this instead of reading /proc/self/cgroup.
    @param fallback: Whether to look for a default cgroup as fallback is our cgroup
        is not accessible.
    """
    logging.debug(
        "Analyzing /proc/mounts and /proc/self/cgroup for determining cgroups."
    )
    if cgroup_paths is None:
        my_cgroups = dict(_find_own_cgroups())
    else:
        my_cgroups = dict(_parse_proc_pid_cgroup(cgroup_paths))

    cgroupsParents = {}
    for subsystem, mount in _find_cgroup_mounts():
        # Ignore mount points where we do not have any access,
        # e.g. because a parent directory has insufficient permissions
        # (lxcfs mounts cgroups under /run/lxcfs in such a way).
        if os.access(mount, os.F_OK):
            cgroupPath = os.path.join(mount, my_cgroups[subsystem])
            fallbackPath = os.path.join(mount, CGROUP_FALLBACK_PATH)
            if (
                fallback
                and not os.access(cgroupPath, os.W_OK)
                and os.path.isdir(fallbackPath)
            ):
                cgroupPath = fallbackPath

            if subsystem == CgroupsV1.IO and not os.path.exists(
                os.path.join(cgroupPath, f"{CgroupsV1.IO}.{BLKIO_BYTES_FILE}")
            ):
                # At least on Docker Desktop blkio can exist in an incomplete way
                # (cf. 985). Instead of ignoring this later we can simply skip the
                # whole subsystem because we only need it for this single file.
                continue

            cgroupsParents[subsystem] = cgroupPath

    return cgroupsParents


def _find_cgroup_mounts():
    """
    Return the information which subsystems are mounted where.
    @return a generator of tuples (subsystem, mountpoint)
    """
    try:
        with open("/proc/mounts", "rt") as mountsFile:
            for mount in mountsFile:
                mount = mount.split(" ")
                if mount[2] == "cgroup":
                    mountpoint = mount[1]
                    options = mount[3]
                    for option in options.split(","):
                        if option in CgroupsV1.known_subsystems:
                            yield (option, mountpoint)
    except OSError:
        logging.exception("Cannot read /proc/mounts")


def _find_own_cgroups():
    """
    For all subsystems, return the information in which (sub-)cgroup this process is in.
    (Each process is in exactly cgroup in each hierarchy.)
    @return a generator of tuples (subsystem, cgroup)
    """
    try:
        with open("/proc/self/cgroup", "rt") as ownCgroupsFile:
            for cgroup in _parse_proc_pid_cgroup(ownCgroupsFile):
                yield cgroup
    except OSError:
        logging.exception("Cannot read /proc/self/cgroup")


def _parse_proc_pid_cgroup(content):
    """
    Parse a /proc/*/cgroup file into tuples of (subsystem,cgroup).
    @param content: An iterable over the lines of the file.
    @return: a generator of tuples
    """
    for ownCgroup in content:
        # each line is "id:subsystem,subsystem:path"
        ownCgroup = ownCgroup.strip().split(":")
        try:
            path = ownCgroup[2][1:]  # remove leading /
        except IndexError:
            raise IndexError(f"index out of range for {ownCgroup}")
        for subsystem in ownCgroup[1].split(","):
            yield (subsystem, path)


def _force_open_read(filename):
    """
    Open a file for reading even if we have no read permission,
    as long as we can grant it to us.
    """
    try:
        return open(filename, "rt")
    except OSError:
        os.chmod(filename, stat.S_IRUSR)
        return open(filename, "rt")


def kill_all_tasks_in_cgroup(cgroup):
    tasksFile = os.path.join(cgroup, "tasks")

    i = 0
    while True:
        i += 1
        # TODO We can probably remove this loop over signals and just send
        # SIGKILL. We added this loop when killing sub-processes was not reliable
        # and we did not know why, but now it is reliable.
        for sig in [signal.SIGKILL, signal.SIGINT, signal.SIGTERM]:
            with _force_open_read(tasksFile) as tasks:
                task = None
                for task in tasks:
                    task = task.strip()
                    if i > 1:
                        logging.warning(
                            "Run has left-over process with pid %s "
                            "in cgroup %s, sending signal %s (try %s).",
                            task,
                            cgroup,
                            sig,
                            i,
                        )
                    util.kill_process(int(task), sig)

                if task is None:
                    return  # No process was hanging, exit
            # wait for the process to exit, this might take some time
            time.sleep(i * 0.5)


def _register_process_with_cgrulesengd(pid):
    """Tell cgrulesengd daemon to not move the given process into other cgroups,
    if libcgroup is available.
    """
    # Logging/printing from inside preexec_fn would end up in the output file,
    # not in the correct logger, thus it is disabled here.
    from ctypes import cdll

    try:
        libcgroup = cdll.LoadLibrary("libcgroup.so.1")
        failure = libcgroup.cgroup_init()
        if failure:
            pass
        else:
            CGROUP_DAEMON_UNCHANGE_CHILDREN = 0x1
            failure = libcgroup.cgroup_register_unchanged_process(
                pid, CGROUP_DAEMON_UNCHANGE_CHILDREN
            )
            if failure:
                pass
                # print(f'Could not register process to cgrulesndg, error {success}. '
                #      'Probably the daemon will mess up our cgroups.')
    except OSError:
        pass


class CgroupsV1(Cgroups):
    version = 1

    IO = "blkio"
    CPU = "cpuacct"
    CPUSET = "cpuset"
    FREEZE = "freezer"
    MEMORY = "memory"

    known_subsystems = {
        # cgroups for BenchExec
        IO,
        CPU,
        CPUSET,
        FREEZE,
        MEMORY,
        # other cgroups users might want
        "cpu",
        "devices",
        "net_cls",
        "net_prio",
        "hugetlb",
        "perf_event",
        "pids",
    }

    def __init__(self, subsystems):
        assert set(subsystems.keys()) <= self.known_subsystems
        super(CgroupsV1, self).__init__(subsystems)

        # for error messages:
        self.denied_subsystems = {}

    @classmethod
    def from_system(cls, cgroup_procinfo=None, fallback=True):
        """
        Return a Cgroup object with the cgroups of the current process.
        Note that it is not guaranteed that all subsystems are available
        in the returned object, as a subsystem may not be mounted.
        Check with "subsystem in <instance>" before using.
        A subsystem may also be present but we do not have the rights to create
        child cgroups, this can be checked with require_subsystem().
        @param cgroup_procinfo: If given, use this instead of reading /proc/self/cgroup.
        @param fallback: Whether to look for a default cgroup as fallback if our cgroup
            is not accessible.
        """
        return cls(find_my_cgroups(cgroup_procinfo, fallback))

    def require_subsystem(self, subsystem, log_method=logging.warning):
        """
        Check whether the given subsystem is enabled and is writable
        (i.e., new cgroups can be created for it).
        Produces a log message for the user if one of the conditions is not fulfilled.
        If the subsystem is enabled but not writable, it will be removed from
        this instance such that further checks with "in" will return "False".
        @return A boolean value.
        """
        if subsystem not in self:
            return super().require_subsystem(subsystem, log_method)

        try:
            test_cgroup = self.create_fresh_child_cgroup([subsystem])
            test_cgroup.remove()
        except OSError as e:
            log_method(
                "Cannot use cgroup %s for subsystem %s, reason: %s (%s).",
                self.subsystems[subsystem],
                subsystem,
                e.strerror,
                e.errno,
            )
            self.unusable_subsystems.add(subsystem)
            if e.errno == errno.EACCES:
                self.denied_subsystems[subsystem] = self.subsystems[subsystem]
            del self.subsystems[subsystem]
            self.paths = set(self.subsystems.values())
            return False

        return True

    def handle_errors(self, critical_cgroups):
        """
        If there were errors in calls to require_subsystem() and critical_cgroups
        is not empty, terminate the program with an error message that explains how to
        fix the problem.

        @param critical_cgroups: set of unusable but required cgroups
        """
        if not critical_cgroups:
            return
        assert critical_cgroups.issubset(self.unusable_subsystems)

        if critical_cgroups.issubset(self.denied_subsystems):
            # All errors were because of permissions for these directories
            paths = sorted(set(self.denied_subsystems.values()))

            # Check if all cgroups have group permissions and user could just be added
            # to some groups to get access. But group 0 (root) of course does not count.
            groups = {}
            try:
                if all(stat.S_IWGRP & os.stat(path).st_mode for path in paths):
                    groups = {os.stat(path).st_gid for path in paths}
            except OSError:
                pass
            if groups and 0 not in groups:

                def get_group_name(gid):
                    try:
                        name = grp.getgrgid(gid).gr_name
                    except KeyError:
                        name = None
                    return shlex.quote(name or str(gid))

                groups = " ".join(sorted(set(map(get_group_name, groups))))
                permission_hint = _PERMISSION_HINT_GROUPS.format(groups)

            elif systeminfo.has_systemd():
                if systeminfo.is_debian():
                    permission_hint = _PERMISSION_HINT_DEBIAN
                else:
                    permission_hint = _PERMISSION_HINT_SYSTEMD

            else:
                permission_hint = _PERMISSION_HINT_OTHER

            paths = shlex.join(str(p) for p in paths)
            sys.exit(_ERROR_MSG_PERMISSIONS.format(permission_hint, paths))

        else:
            sys.exit(_ERROR_MSG_OTHER)  # e.g., subsystem not mounted

    def create_fresh_child_cgroup(self, subsystems, prefix=CGROUP_NAME_PREFIX):
        """
        Create child cgroups of the current cgroup for at least the given subsystems.
        @return: A Cgroup instance representing the new child cgroup(s).
        """
        assert set(subsystems).issubset(self.subsystems.keys())
        createdCgroupsPerSubsystem = {}
        createdCgroupsPerParent = {}
        for subsystem in subsystems:
            parentCgroup = self.subsystems[subsystem]
            if parentCgroup in createdCgroupsPerParent:
                # reuse already created cgroup
                createdCgroupsPerSubsystem[subsystem] = createdCgroupsPerParent[
                    parentCgroup
                ]
                continue

            cgroup = tempfile.mkdtemp(prefix=prefix, dir=parentCgroup)
            createdCgroupsPerSubsystem[subsystem] = cgroup
            createdCgroupsPerParent[parentCgroup] = cgroup

            # add allowed cpus and memory to cgroup if necessary
            # (otherwise we can't add any tasks)
            def copy_parent_to_child(name):
                shutil.copyfile(
                    os.path.join(parentCgroup, name),  # noqa: B023
                    os.path.join(cgroup, name),  # noqa: B023
                )

            try:
                copy_parent_to_child("cpuset.cpus")
                copy_parent_to_child("cpuset.mems")
            except OSError:
                # expected to fail if cpuset subsystem is not enabled in this hierarchy
                pass

        return CgroupsV1(createdCgroupsPerSubsystem)

    def create_fresh_child_cgroup_for_delegation(self, prefix="delegate_"):
        """
        Create a child cgroup with all controllers.
        On cgroupsv1 there is no difference to a regular child cgroup.
        """
        child_cgroup = self.create_fresh_child_cgroup(self.subsystems.keys(), prefix)
        assert (
            self.subsystems.keys() == child_cgroup.subsystems.keys()
        ), "delegation failed for at least one controller"

        return child_cgroup

    def add_task(self, pid):
        """
        Add a process to the cgroups represented by this instance.
        """
        _register_process_with_cgrulesengd(pid)
        for cgroup in self.paths:
            with open(os.path.join(cgroup, "tasks"), "w") as tasksFile:
                tasksFile.write(str(pid))

    def get_all_tasks(self, subsystem):
        """
        Return a generator of all PIDs currently in this cgroup for the given subsystem.
        """
        with open(os.path.join(self.subsystems[subsystem], "tasks"), "r") as tasksFile:
            for line in tasksFile:
                yield int(line)

    def kill_all_tasks(self):
        """
        Kill all tasks in this cgroup and all its children cgroups forcefully.
        Additionally, the children cgroups will be deleted.
        """
        # In this method we should attempt to guard against child cgroups
        # that have been created and manipulated by processes in the run.
        # For example, they could have removed permissions from files and directories.

        def recursive_child_cgroups(cgroup):
            def raise_error(e):
                raise e

            try:
                for dirpath, dirs, _files in os.walk(
                    cgroup, topdown=False, onerror=raise_error
                ):
                    for subCgroup in dirs:
                        yield os.path.join(dirpath, subCgroup)
            except OSError as e:
                # some process might have made a child cgroup inaccessible
                os.chmod(e.filename, stat.S_IRUSR | stat.S_IXUSR)
                # restart, which might yield already yielded cgroups again,
                # but this is ok for the callers of recursive_child_cgroups()
                yield from recursive_child_cgroups(cgroup)

        def try_unfreeze(cgroup):
            try:
                util.write_file("THAWED", cgroup, "freezer.state", force=True)
            except OSError:
                # With force=True this fails only if we are not owner, but then there is
                # nothing we can do. But the processes inside the run cannot change the
                # owner, so this should not happen.
                pass

        # First, we go through all cgroups recursively while they are frozen and kill
        # all processes. This helps against fork bombs and prevents processes from
        # creating new subgroups while we are trying to kill everything.
        # But this is only possible if we have freezer, and all processes will stay
        # until they are thawed (so we cannot check for cgroup emptiness and we cannot
        # delete subgroups).
        if self.FREEZE in self.subsystems:
            cgroup = self.subsystems[self.FREEZE]
            util.write_file("FROZEN", cgroup, "freezer.state", force=True)

            for child_cgroup in recursive_child_cgroups(cgroup):
                with _force_open_read(os.path.join(child_cgroup, "tasks")) as tasks:
                    for task in tasks:
                        util.kill_process(int(task))

                # This cgroup could be frozen, which would prevent processes from being
                # killed and would lead to an endless loop below. cf.
                # https://github.com/sosy-lab/benchexec/issues/840
                try_unfreeze(child_cgroup)

            util.write_file("THAWED", cgroup, "freezer.state", force=True)

        # Second, we go through all cgroups again, kill what is left,
        # check for emptiness, and remove subgroups.
        # Furthermore, we do this for all hierarchies, not only the one with freezer.
        for cgroup in self.paths:
            # Sometimes nested cgroups vanish while we iterate over them.
            # Not sure why because the freezing above should prevent any process
            # from still being alive, but maybe we are iterating here already
            # while the kernel is still doing some cleanup. So in order to prevent
            # crashes we handle this.
            while True:
                try:
                    for child_cgroup in recursive_child_cgroups(cgroup):
                        kill_all_tasks_in_cgroup(child_cgroup)
                        self._remove_cgroup(child_cgroup)
                    break
                except FileNotFoundError as e:
                    logging.debug(
                        "Cgroup vanished while we were trying to clean it up: %s", e
                    )
                continue

            kill_all_tasks_in_cgroup(cgroup)

    def read_cputime(self):
        # convert nano-seconds to seconds
        return float(self.get_value(self.CPU, "usage")) / 1_000_000_000

    def read_max_mem_usage(self):
        # This measurement reads the maximum number of bytes of RAM+Swap the process used.
        # For more details, c.f. the kernel documentation:
        # https://www.kernel.org/doc/Documentation/cgroups/memory.txt
        memUsageFile = "memsw.max_usage_in_bytes"
        if not self.has_value(self.MEMORY, memUsageFile):
            memUsageFile = "max_usage_in_bytes"
        if self.has_value(self.MEMORY, memUsageFile):
            try:
                return int(self.get_value(self.MEMORY, memUsageFile))
            except OSError as e:
                if e.errno == errno.ENOTSUP:
                    # kernel responds with operation unsupported if this is disabled
                    logging.critical(
                        "Kernel does not track swap memory usage, cannot measure memory usage."
                        " Please set swapaccount=1 on your kernel command line."
                    )
                else:
                    raise e

        return None

    def read_mem_pressure(self):
        return None

    def read_cpu_pressure(self):
        return None

    def read_io_pressure(self):
        return None

    def read_usage_per_cpu(self):
        usage = {}
        for core, coretime in enumerate(
            self.get_value(self.CPU, "usage_percpu").split(" ")
        ):
            try:
                coretime = int(coretime)
                if coretime != 0:
                    # convert nanoseconds to seconds
                    usage[core] = coretime / 1_000_000_000
            except (OSError, ValueError) as e:
                logging.debug(
                    "Could not read CPU time for core %s from kernel: %s", core, e
                )

        return usage

    def read_allowed_cpus(self):
        return util.parse_int_list(self.get_value(self.CPUSET, "cpus"))

    def read_allowed_memory_banks(self):
        return util.parse_int_list(self.get_value(self.CPUSET, "mems"))

    def read_io_stat(self):
        bytes_read = 0
        bytes_written = 0
        for blkio_line in self.get_file_lines(self.IO, BLKIO_BYTES_FILE):
            try:
                dev_no, io_type, bytes_amount = blkio_line.split(" ")
                if io_type == "Read":
                    bytes_read += int(bytes_amount)
                elif io_type == "Write":
                    bytes_written += int(bytes_amount)
            except ValueError:
                pass  # There are irrelevant lines in this file with a different structure
        return bytes_read, bytes_written

    def _has_tasks(self, path):
        return util.read_file(path, "tasks") != ""

    def write_memory_limit(self, limit):
        limit_file = "limit_in_bytes"
        self.set_value(self.MEMORY, limit_file, limit)

        swap_limit_file = "memsw.limit_in_bytes"
        # We need swap limit because otherwise the kernel just starts swapping
        # out our process if the limit is reached.
        # Some kernels might not have this feature,
        # which is ok if there is actually no swap.
        if not self.has_value(self.MEMORY, swap_limit_file):
            if systeminfo.has_swap():
                sys.exit(
                    'Kernel misses feature for accounting swap memory, but machine has swap. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".'
                )
        else:
            try:
                self.set_value(self.MEMORY, swap_limit_file, limit)
            except OSError as e:
                if e.errno == errno.ENOTSUP:
                    # kernel responds with operation unsupported if this is disabled
                    sys.exit(
                        'Memory limit specified, but kernel does not allow limiting swap memory. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".'
                    )
                raise e

    def read_memory_limit(self):
        return int(self.get_value(self.MEMORY, "limit_in_bytes"))

    def read_hierarchical_memory_limit(self):
        limit = self.read_memory_limit()
        # We also use the entries hierarchical_*_limit in memory.stat
        # because it may be lower if memory.use_hierarchy is enabled.
        for key, value in self.get_key_value_pairs(self.MEMORY, "stat"):
            if key == "hierarchical_memory_limit" or key == "hierarchical_memsw_limit":
                limit = min(limit, int(value))
        return limit

    def can_limit_swap(self):
        return self.has_value(self.MEMORY, "memsw.max_usage_in_bytes")

    def disable_swap(self):
        # Note that this disables swapping completely according to
        # https://www.kernel.org/doc/Documentation/cgroups/memory.txt
        # (unlike setting the global swappiness to 0).
        # Our process might get killed because of this.
        self.set_value(self.MEMORY, "swappiness", "0")

    def read_oom_kill_count(self):
        # not supported in v1, see oomhandler and memory_used > memlimit impl
        return None
