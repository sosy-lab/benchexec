# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
import errno
import logging
import os
import stat

from benchexec import util


CGROUPS_V1 = 1
CGROUPS_V2 = 2


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
    except OSError:
        logging.exception("Cannot read /proc/mounts")

    return version


class Cgroups(ABC):
    """
    A representation of a cgroup that attempts to abstract away the differences
    between cgroups v1 and v2.
    The typical way to get a usable instance is to call initialize().
    """

    @staticmethod
    def initialize(allowed_versions=None):
        """
        Try to find or create a usable cgroup and return a Cgroups instance
        that represents it.

        Calling this method may have an effect on the cgroup of the current process,
        e.g., it may be moved to a different cgroup.
        This will likely cause problems if other non-BenchExec components
        are also using cgroups in the same process.
        Even though it may change the cgroup state of the process,
        this method is safe to call more than once and it is expected that later calls
        do not produce further changes.

        The returned cgroup may or may not have child cgroups
        and the current process may or may not be contained in the returned cgroup
        or one of its children.

        This method cannot guarantee that a usable cgroup is found,
        but it will always return a Cgroups instance.
        Call require_subsystem() on it in order to find out which subsystems (if any)
        are usable.

        Typically, callers should use the returned cgroup instance only for creating
        child cgroups and not call any other modifying method such as add_task().

        @param allowed_versions: None, or a sequence of allowed cgroup versions (1 or 2).
            If the current system uses a different cgroup version, no attempt at
            returning a usable Cgroups instance is made.
        """
        version = _get_cgroup_version()
        if allowed_versions is not None and version not in allowed_versions:
            return Cgroups.dummy()

        if version == CGROUPS_V1:
            from .cgroupsv1 import CgroupsV1

            return CgroupsV1.from_system()

        elif version == CGROUPS_V2:
            from .cgroupsv2 import initialize

            return initialize()

        return Cgroups.dummy()

    @staticmethod
    def from_system(cgroup_procinfo=None):
        """
        Create a cgroups instance representing the current cgroup of the process.

        @param cgroup_procinfo: Optional, if given use this instead of /proc/self/cgroup
        """
        version = _get_cgroup_version()
        if version == CGROUPS_V1:
            from .cgroupsv1 import CgroupsV1

            return CgroupsV1.from_system(cgroup_procinfo, fallback=False)
        elif version == CGROUPS_V2:
            from .cgroupsv2 import CgroupsV2

            return CgroupsV2.from_system(cgroup_procinfo)

        return Cgroups.dummy()

    @staticmethod
    def dummy():
        return _DummyCgroups({})

    def __init__(self, subsystems):
        self.subsystems = subsystems

        assert all(self.subsystems.values())

        self.paths = set(self.subsystems.values())  # without duplicates

        logging.debug("Available Cgroups: %s", self.subsystems)

        # for error messages:
        self.unusable_subsystems = set()

    def __contains__(self, key):
        return key in self.subsystems

    def __getitem__(self, key):
        return self.subsystems[key]

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
                    "Please make sure it is supported by your kernel and available.",
                    subsystem,
                )
            return False

        return True

    @abstractmethod
    def handle_errors(self, critical_cgroups):
        """
        If there were errors in calls to require_subsystem() and critical_cgroups
        is not empty, terminate the program with an error message that explains how to
        fix the problem.

        @param critical_cgroups: set of unusable but required cgroups
        """
        pass

    @abstractmethod
    def create_fresh_child_cgroup(self, subsystems, prefix=None):
        pass

    @abstractmethod
    def create_fresh_child_cgroup_for_delegation(self):
        pass

    @abstractmethod
    def add_task(self, pid):
        pass

    @abstractmethod
    def kill_all_tasks(self):
        pass

    def has_value(self, subsystem, option):
        """
        Check whether the given value exists in the given subsystem.
        Does not make a difference whether the value is readable, writable, or both.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        return os.path.isfile(
            os.path.join(self.subsystems[subsystem], f"{subsystem}.{option}")
        )

    def get_value(self, subsystem, option):
        """
        Read the given value from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self, f"Subsystem {subsystem} is missing"
        return util.read_file(self.subsystems[subsystem], f"{subsystem}.{option}")

    def get_file_lines(self, subsystem, option):
        """
        Read the lines of the given file from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        with open(
            os.path.join(self.subsystems[subsystem], f"{subsystem}.{option}")
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
            self.subsystems[subsystem], f"{subsystem}.{filename}"
        )

    def set_value(self, subsystem, option, value):
        """
        Write the given value for the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        util.write_file(str(value), self.subsystems[subsystem], f"{subsystem}.{option}")

    def remove(self):
        """
        Remove all cgroups this instance represents from the system.
        This instance is afterwards not usable anymore!
        """
        for cgroup in self.paths:
            self._remove_cgroup(cgroup)

        del self.paths
        del self.subsystems

    def _remove_cgroup(self, path):
        if not os.path.exists(path):
            logging.warning("Cannot remove CGroup %s, because it does not exist.", path)
            return
        assert not self._has_tasks(path)
        try:
            os.rmdir(path)
        except OSError:
            # sometimes this fails because the cgroup is still busy, we try again once
            try:
                parent = os.path.dirname(path)
                os.chmod(parent, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
                os.rmdir(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    logging.warning(
                        "Failed to remove cgroup %s: error %s (%s)",
                        path,
                        e.errno,
                        e.strerror,
                    )

    @abstractmethod
    def read_cputime(self):
        """
        Read the cputime usage of this cgroup. CPU cgroup needs to be available.
        @return cputime usage in seconds
        """
        pass

    @abstractmethod
    def read_max_mem_usage(self):
        pass

    @abstractmethod
    def read_mem_pressure(self):
        pass

    @abstractmethod
    def read_cpu_pressure(self):
        pass

    @abstractmethod
    def read_io_pressure(self):
        pass

    @abstractmethod
    def read_usage_per_cpu(self):
        pass

    @abstractmethod
    def read_allowed_cpus(self):
        """Get the list of all CPU cores allowed by this cgroup."""
        pass

    @abstractmethod
    def read_allowed_memory_banks(self):
        """Get the list of all memory banks allowed by this cgroup."""
        pass

    @abstractmethod
    def read_io_stat(self):
        pass

    @abstractmethod
    def _has_tasks(self, path):
        pass

    @abstractmethod
    def write_memory_limit(self, limit):
        pass

    @abstractmethod
    def read_memory_limit(self):
        pass

    @abstractmethod
    def read_hierarchical_memory_limit(self):
        """Read the memory limit that applies to the current cgroup or any parent."""
        pass

    @abstractmethod
    def read_oom_kill_count(self):
        pass

    @abstractmethod
    def can_limit_swap(self):
        """Check wether cgroups can be used to limit swap usage."""
        pass

    @abstractmethod
    def disable_swap(self):
        pass


class _DummyCgroups(Cgroups):
    version = 0
    IO = "io"
    CPU = "cpu"
    CPUSET = "cpuset"
    FREEZE = "freezer"
    MEMORY = "memory"

    def add_task(self, pid):
        pass

    def kill_all_tasks(self):
        pass

    def create_fresh_child_cgroup(self, subsystems, prefix=None):
        return self

    def create_fresh_child_cgroup_for_delegation(self):
        return self

    def handle_errors(self, critical_cgroups):
        pass

    def read_cputime(self):
        pass

    def read_max_mem_usage(self):
        pass

    def read_mem_pressure(self):
        pass

    def read_cpu_pressure(self):
        pass

    def read_io_pressure(self):
        pass

    def read_usage_per_cpu(self):
        pass

    def read_allowed_cpus(self):
        pass

    def read_allowed_memory_banks(self):
        pass

    def read_io_stat(self):
        pass

    def _has_tasks(self, path):
        pass

    def has_tasks(self):
        pass

    def write_memory_limit(self, limit):
        pass

    def read_memory_limit(self):
        pass

    def read_hierarchical_memory_limit(self):
        pass

    def read_oom_kill_count(self):
        pass

    def can_limit_swap(self):
        pass

    def disable_swap(self):
        pass
