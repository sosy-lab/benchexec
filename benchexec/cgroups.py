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
import shutil
import signal
import stat
import sys
import tempfile
import time

from benchexec import BenchExecException
from benchexec import systeminfo
from benchexec import util

__all__ = [
    "find_my_cgroups",
    "BLKIO",
    "CPUACCT",
    "CPUSET",
    "FREEZER",
    "MEMORY",
]

CGROUP_FALLBACK_PATH = "system.slice/benchexec-cgroup.service"
"""If we do not have write access to the current cgroup,
attempt to use this cgroup as fallback."""

CGROUP_NAME_PREFIX = "benchmark_"

BLKIO = "blkio"
CPUACCT = "cpuacct"
CPUSET = "cpuset"
FREEZER = "freezer"
MEMORY = "memory"
ALL_KNOWN_SUBSYSTEMS = {
    # cgroups for BenchExec
    BLKIO,
    CPUACCT,
    CPUSET,
    FREEZER,
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

CGROUPS_V1 = 1
CGROUPS_V2 = 2

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

_ERROR_MSG_CGROUPS_V2 = """
Required cgroups are not available because this system is using cgroupsv2 exclusively.

This version of BenchExec does not yet support cgroupsv2.
Please check at https://github.com/sosy-lab/benchexec/issues/133
whether a new version of BenchExec with support for cgroupsv2 is available
and update if applicable.

Alternatively, you could try switching back to cgroupsv1
with the kernel command-line parameter systemd.unified_cgroup_hierarchy=0
or use BenchExec without the features that need cgroups
(i.e., disable cpu-time limit, memory limit, and core limit).
"""

_ERROR_MSG_OTHER = """
Required cgroups are not available.
If you are using BenchExec within a container, please make "/sys/fs/cgroup" available."""


def _get_cgroup_version():
    version = None
    try:
        with open("/proc/mounts") as mountsFile:
            for mount in mountsFile:
                mount = mount.split(" ")
                if mount[2] == "cgroup":
                    version = CGROUPS_V1

                # only set v2 if it's the only active mount
                # we don't support crippled hybrid mode
                elif mount[2] == "cgroup2" and version != CGROUPS_V1:
                    version = CGROUPS_V2

            if version is None:
                raise BenchExecException("Could not detect Cgroup Version")
    except OSError:
        logging.exception("Cannot read /proc/mounts")

    return version


def find_my_cgroups(cgroup_paths=None, fallback=True):
    """
    Return a Cgroup object with the cgroups of the current process.
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
            cgroupsParents[subsystem] = cgroupPath

    return Cgroup(cgroupsParents)


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
                        if option in ALL_KNOWN_SUBSYSTEMS:
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


def kill_all_tasks_in_cgroup(cgroup, ensure_empty=True):
    tasksFile = os.path.join(cgroup, "tasks")

    i = 0
    while True:
        i += 1
        # TODO We can probably remove this loop over signals and just send
        # SIGKILL. We added this loop when killing sub-processes was not reliable
        # and we did not know why, but now it is reliable.
        for sig in [signal.SIGKILL, signal.SIGINT, signal.SIGTERM]:
            with open(tasksFile, "rt") as tasks:
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

                if task is None or not ensure_empty:
                    return  # No process was hanging, exit
            # wait for the process to exit, this might take some time
            time.sleep(i * 0.5)


def remove_cgroup(cgroup):
    if not os.path.exists(cgroup):
        logging.warning("Cannot remove CGroup %s, because it does not exist.", cgroup)
        return
    assert os.path.getsize(os.path.join(cgroup, "tasks")) == 0
    try:
        os.rmdir(cgroup)
    except OSError:
        # sometimes this fails because the cgroup is still busy, we try again once
        try:
            os.rmdir(cgroup)
        except OSError as e:
            logging.warning(
                "Failed to remove cgroup %s: error %s (%s)", cgroup, e.errno, e.strerror
            )


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


class Cgroup(object):
    def __init__(self, cgroupsPerSubsystem):
        assert set(cgroupsPerSubsystem.keys()) <= ALL_KNOWN_SUBSYSTEMS
        assert all(cgroupsPerSubsystem.values())
        # Also update self.paths on every update to this!
        self.per_subsystem = cgroupsPerSubsystem
        self.paths = set(cgroupsPerSubsystem.values())  # without duplicates
        # for error messages:
        self.unusable_subsystems = set()
        self.denied_subsystems = {}

    def __contains__(self, key):
        return key in self.per_subsystem

    def __getitem__(self, key):
        return self.per_subsystem[key]

    def __str__(self):
        return str(self.paths)

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
            if subsystem not in self.unusable_subsystems:
                self.unusable_subsystems.add(subsystem)
                log_method(
                    "Cgroup subsystem %s is not available. "
                    "Please make sure it is supported by your kernel and mounted.",
                    subsystem,
                )
            return False

        try:
            test_cgroup = self.create_fresh_child_cgroup(subsystem)
            test_cgroup.remove()
        except OSError as e:
            log_method(
                "Cannot use cgroup %s for subsystem %s, reason: %s (%s).",
                self.per_subsystem[subsystem],
                subsystem,
                e.strerror,
                e.errno,
            )
            self.unusable_subsystems.add(subsystem)
            if e.errno == errno.EACCES:
                self.denied_subsystems[subsystem] = self.per_subsystem[subsystem]
            del self.per_subsystem[subsystem]
            self.paths = set(self.per_subsystem.values())
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
                    return util.escape_string_shell(name or str(gid))

                groups = " ".join(sorted(set(map(get_group_name, groups))))
                permission_hint = _PERMISSION_HINT_GROUPS.format(groups)

            elif systeminfo.has_systemd():
                if systeminfo.is_debian():
                    permission_hint = _PERMISSION_HINT_DEBIAN
                else:
                    permission_hint = _PERMISSION_HINT_SYSTEMD

            else:
                permission_hint = _PERMISSION_HINT_OTHER

            paths = " ".join(map(util.escape_string_shell, paths))
            sys.exit(_ERROR_MSG_PERMISSIONS.format(permission_hint, paths))

        elif _get_cgroup_version() == CGROUPS_V2:
            sys.exit(_ERROR_MSG_CGROUPS_V2)
        else:
            sys.exit(_ERROR_MSG_OTHER)  # e.g., subsystem not mounted

    def create_fresh_child_cgroup(self, *subsystems):
        """
        Create child cgroups of the current cgroup for at least the given subsystems.
        @return: A Cgroup instance representing the new child cgroup(s).
        """
        assert set(subsystems).issubset(self.per_subsystem.keys())
        createdCgroupsPerSubsystem = {}
        createdCgroupsPerParent = {}
        for subsystem in subsystems:
            parentCgroup = self.per_subsystem[subsystem]
            if parentCgroup in createdCgroupsPerParent:
                # reuse already created cgroup
                createdCgroupsPerSubsystem[subsystem] = createdCgroupsPerParent[
                    parentCgroup
                ]
                continue

            cgroup = tempfile.mkdtemp(prefix=CGROUP_NAME_PREFIX, dir=parentCgroup)
            createdCgroupsPerSubsystem[subsystem] = cgroup
            createdCgroupsPerParent[parentCgroup] = cgroup

            # add allowed cpus and memory to cgroup if necessary
            # (otherwise we can't add any tasks)
            def copy_parent_to_child(name):
                shutil.copyfile(
                    os.path.join(parentCgroup, name), os.path.join(cgroup, name)
                )

            try:
                copy_parent_to_child("cpuset.cpus")
                copy_parent_to_child("cpuset.mems")
            except OSError:
                # expected to fail if cpuset subsystem is not enabled in this hierarchy
                pass

        return Cgroup(createdCgroupsPerSubsystem)

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
        with open(
            os.path.join(self.per_subsystem[subsystem], "tasks"), "r"
        ) as tasksFile:
            for line in tasksFile:
                yield int(line)

    def kill_all_tasks(self):
        """
        Kill all tasks in this cgroup and all its children cgroups forcefully.
        Additionally, the children cgroups will be deleted.
        """

        def kill_all_tasks_in_cgroup_recursively(cgroup, delete):
            for dirpath, dirs, _files in os.walk(cgroup, topdown=False):
                for subCgroup in dirs:
                    subCgroup = os.path.join(dirpath, subCgroup)
                    kill_all_tasks_in_cgroup(subCgroup, ensure_empty=delete)

                    if delete:
                        remove_cgroup(subCgroup)

            kill_all_tasks_in_cgroup(cgroup, ensure_empty=delete)

        # First, we go through all cgroups recursively while they are frozen and kill
        # all processes. This helps against fork bombs and prevents processes from
        # creating new subgroups while we are trying to kill everything.
        # But this is only possible if we have freezer, and all processes will stay
        # until they are thawed (so we cannot check for cgroup emptiness and we cannot
        # delete subgroups).
        if FREEZER in self.per_subsystem:
            cgroup = self.per_subsystem[FREEZER]
            freezer_file = os.path.join(cgroup, "freezer.state")

            util.write_file("FROZEN", freezer_file)
            kill_all_tasks_in_cgroup_recursively(cgroup, delete=False)
            util.write_file("THAWED", freezer_file)

        # Second, we go through all cgroups again, kill what is left,
        # check for emptiness, and remove subgroups.
        # Furthermore, we do this for all hierarchies, not only the one with freezer.
        for cgroup in self.paths:
            kill_all_tasks_in_cgroup_recursively(cgroup, delete=True)

    def has_value(self, subsystem, option):
        """
        Check whether the given value exists in the given subsystem.
        Does not make a difference whether the value is readable, writable, or both.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        return os.path.isfile(
            os.path.join(self.per_subsystem[subsystem], f"{subsystem}.{option}")
        )

    def get_value(self, subsystem, option):
        """
        Read the given value from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self, f"Subsystem {subsystem} is missing"
        return util.read_file(self.per_subsystem[subsystem], f"{subsystem}.{option}")

    def get_file_lines(self, subsystem, option):
        """
        Read the lines of the given file from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        with open(
            os.path.join(self.per_subsystem[subsystem], f"{subsystem}.{option}")
        ) as f:
            for line in f:
                yield line

    def get_key_value_pairs(self, subsystem, filename):
        """
        Read the lines of the given file from the given subsystem
        and split the lines into key-value pairs.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        return util.read_key_value_pairs_from_file(
            self.per_subsystem[subsystem], f"{subsystem}.{filename}"
        )

    def set_value(self, subsystem, option, value):
        """
        Write the given value for the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        util.write_file(
            str(value), self.per_subsystem[subsystem], f"{subsystem}.{option}"
        )

    def remove(self):
        """
        Remove all cgroups this instance represents from the system.
        This instance is afterwards not usable anymore!
        """
        for cgroup in self.paths:
            remove_cgroup(cgroup)

        del self.paths
        del self.per_subsystem

    def read_cputime(self):
        """
        Read the cputime usage of this cgroup. CPUACCT cgroup needs to be available.
        @return cputime usage in seconds
        """
        # convert nano-seconds to seconds
        return float(self.get_value(CPUACCT, "usage")) / 1_000_000_000

    def read_allowed_memory_banks(self):
        """Get the list of all memory banks allowed by this cgroup."""
        return util.parse_int_list(self.get_value(CPUSET, "mems"))
