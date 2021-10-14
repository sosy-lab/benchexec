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
import pathlib
import stat
import sys

from benchexec import BenchExecException
from benchexec import systeminfo
from benchexec import util


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

        raise BenchExecException("Could not detect Cgroup Version")

    def __init__(self, subsystems=None, cgroup_procinfo=None, fallback=True):
        if subsystems is None:
            self.subsystems = self._supported_subsystems()
        else:
            self.subsystems = subsystems

        assert set(self.subsystems.keys()) <= self.known_subsystems
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

    def _remove_cgroup(self, path: pathlib.Path):
        if not os.path.exists(path):
            logging.warning("Cannot remove CGroup %s, because it does not exist.", path)
            return
        assert not self.has_tasks(path)
        try:
            os.rmdir(path)
        except OSError:
            # sometimes this fails because the cgroup is still busy, we try again once
            try:
                os.rmdir(path)
            except OSError as e:
                logging.warning(
                    "Failed to remove cgroup %s: error %s (%s)",
                    path,
                    e.errno,
                    e.strerror,
                )

    def has_value(self, subsystem, option):
        """
        Check whether the given value exists in the given subsystem.
        Does not make a difference whether the value is readable, writable, or both.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        return os.path.isfile(self.subsystems[subsystem] / f"{subsystem}.{option}")

    def get_value(self, subsystem, option):
        """
        Read the given value from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self, f"Subsystem {subsystem} is missing"
        return util.read_file(self.subsystems[subsystem] / f"{subsystem}.{option}")

    def get_file_lines(self, subsystem, option):
        """
        Read the lines of the given file from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        with open(self.subsystems[subsystem] / f"{subsystem}.{option}") as f:
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
            self.subsystems[subsystem] / f"{subsystem}.{filename}"
        )

    def set_value(self, subsystem, option, value):
        """
        Write the given value for the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        util.write_file(
            str(value), self.subsystems[subsystem] / f"{subsystem}.{option}"
        )

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

        try:
            test_cgroup = self.create_fresh_child_cgroup(subsystem)
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
                if all(stat.S_IWGRP & path.stat().st_mode for path in paths):
                    groups = {path.stat().st_gid for path in paths}
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

    def remove(self):
        """
        Remove all cgroups this instance represents from the system.
        This instance is afterwards not usable anymore!
        """
        for cgroup in self.paths:
            self._remove_cgroup(cgroup)

        del self.paths
        del self.subsystems

    @property
    @abstractmethod
    def known_subsystems(self):
        pass

    @abstractmethod
    def _supported_subsystems(self, cgroup_procinfo=None, fallback=True):
        pass

    @abstractmethod
    def create_fresh_child_cgroup(self, subsystem):
        pass

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

    @abstractmethod
    def read_io_stat(self):
        pass

    # TODO improve interface
    @abstractmethod
    def has_tasks(self, path):
        pass

    @abstractmethod
    def disable_swap(self):
        pass

    @abstractmethod
    def set_oom_handler(self):
        pass

    @abstractmethod
    def reset_memory_limit(self):
        pass
