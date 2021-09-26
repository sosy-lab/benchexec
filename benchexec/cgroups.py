# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
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

CGROUP_FALLBACK_PATH = "system.slice/benchexec-cgroup.service"
"""If we do not have write access to the current cgroup,
attempt to use this cgroup as fallback."""

CGROUP_NAME_PREFIX = "benchmark_"

CGROUPS_V1 = 1
CGROUPS_V2 = 2

_PERMISSION_HINT_GROUPS = """
You need to add your account to the following groups: {0}
Remember to logout and login again afterwards to make group changes effective."""

_PERMISSION_HINT_DEBIAN = """
The recommended way to fix this is to install the Debian package for BenchExec and add your account to the group "benchexec":
https://github.com/sosy-lab/benchexec/blob/master/doc/INSTALL.md#debianubuntu
Alternatively, you can install benchexec-cgroup.service manually:
https://github.com/sosy-lab/benchexec/blob/master/doc/INSTALL.md#setting-up-cgroups-on-machines-with-systemd"""

_PERMISSION_HINT_SYSTEMD = """
The recommended way to fix this is to add your account to a group named "benchexec" and install benchexec-cgroup.service:
https://github.com/sosy-lab/benchexec/blob/master/doc/INSTALL.md#setting-up-cgroups-on-machines-with-systemd"""

_PERMISSION_HINT_OTHER = """
Please configure your system in way to allow your user to use cgroups:
https://github.com/sosy-lab/benchexec/blob/master/doc/INSTALL.md#setting-up-cgroups-on-machines-without-systemd"""

_ERROR_MSG_PERMISSIONS = """
Required cgroups are not available because of missing permissions.{0}

As a temporary workaround, you can also run
"sudo chmod o+wt {1}"
Note that this will grant permissions to more users than typically desired and it will only last until the next reboot."""

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


class Cgroups(ABC):
    @staticmethod
    def from_system(cgroup_procinfo=None, fallback=True):
        version = _get_cgroup_version()
        if version == CGROUPS_V1:
            from .cgroupsv1 import CgroupsV1

            return CgroupsV1(cgroup_procinfo=cgroup_procinfo, fallback=fallback)
        elif version == CGROUPS_V2:
            from .cgroupsv2 import CgroupsV2

            return CgroupsV2(cgroup_procinfo=cgroup_procinfo, fallback=fallback)

    def __init__(self, subsystems=None, cgroup_procinfo=None, fallback=True):
        if subsystems is None:
            self.subsystems = self._supported_cgroup_subsystems()
        else:
            self.subsystems = subsystems

        assert set(self.subsystems.keys()) <= self.KNOWN_SUBSYSTEMS
        assert all(self.subsystems.values())

        self.paths = set(self.subsystems.values())  # without duplicates

        # for error messages:
        self.unusable_subsystems = set()
        self.denied_subsystems = {}

        logging.debug("Available Cgroups: %s", self.subsystems)

    def __contains__(self, key):
        return key in self.subsystems

    def __getitem__(self, key):
        return self.subsystems[key]

    def __str__(self):
        return str(self.paths)

    # FIXME improve message for v2
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
        if self.version == 2 or FREEZER in self.impl.per_subsystem:
            self.impl.freeze()
            kill_all_tasks_in_cgroup_recursively(cgroup, delete=False)
            self.impl.unfreeze()

        # Second, we go through all cgroups again, kill what is left,
        # check for emptiness, and remove subgroups.
        # Furthermore, we do this for all hierarchies, not only the one with freezer.
        for cgroup in self.paths:
            kill_all_tasks_in_cgroup_recursively(cgroup, delete=True)

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
        return self.impl.read_cputime()

    def read_allowed_memory_banks(self):
        """Get the list of all memory banks allowed by this cgroup."""
        return util.parse_int_list(self.get_value(CPUSET, "mems"))

    @abstractmethod
    def read_max_mem_usage(self):
        pass

    @abstractmethod
    def read_usage_per_cpu(self):
        pass

    @abstractmethod
    def read_available_cpus(self):
        pass

    @abstractmethod
    def read_available_mems(self):
        pass
