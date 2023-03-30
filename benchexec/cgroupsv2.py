# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import pathlib
import secrets
import signal
import sys
import tempfile
import threading
import time
from decimal import Decimal

from benchexec import systeminfo, util
from benchexec.cgroups import Cgroups

_ERROR_MSG_UNKNOWN_SUBSYSTEMS = """
The following cgroup subsystems were required but are not supported by this kernel: {}.
Please avoid their usage or enable them in the kernel."""

_ERROR_MSG_MISSING_SUBSYSTEMS = """
The following cgroup subsystems were required but are not usable: {}.
Please enable them, e.g., by setting up delegation.
The cgroup that we attempted to use was: {}"""

_ERROR_NO_SYSTEMD = """
System is using cgroups v2 but not systemd.
If you are using BenchExec within a container, please ensure that cgroups are properly delegated into the container.
Otherwise please configure your system such that BenchExec can use cgroups."""

_ERROR_NO_PSYSTEMD = """
BenchExec was not able to use cgroups.
Please either start it within a fresh systemd scope by prefixing your command line with
  systemd-run --user --scope -p Delegate=yes
or install the Python library pystemd such that BenchExec can do this automatically."""

_ERROR_MSG_OTHER = """
BenchExec was not able to use cgroups and did not manage to create a systemd scope.
Please ensure that we can connect to systemd via DBus or try starting BenchExec within a fresh systemd scope by prefixing your command line with
  systemd-run --user --scope -p Delegate=yes"""

uid = os.getuid()
CGROUP_NAME_PREFIX = "benchmark_"

# Global state that stores the cgroup we have prepared for use.
# Global state is not nice, but here we have to use it because during cgroup
# initialization we have to move the current process into a cgroup,
# and this is inherently global state (because it affects the whole process).
# So we need to know whether we have done this already or not.
_usable_cgroup = None
_usable_cgroup_lock = threading.Lock()


def initialize():
    """
    Attempt to get a usable cgroup.
    This may involve moving the current process into a different cgroup,
    but this method is idempotent.
    """
    global _usable_cgroup
    if _usable_cgroup:
        return _usable_cgroup

    with _usable_cgroup_lock:
        if _usable_cgroup:
            return _usable_cgroup

        cgroup = CgroupsV2.from_system()

        allowed_pids = set(util.get_pgrp_pids(os.getpgid(0)))
        if set(cgroup.get_all_tasks()) <= allowed_pids:
            # If we are the only process, somebody prepared a cgroup for us. Use it.
            logging.debug("BenchExec was started in its own cgroup: %s", cgroup)

        elif _create_systemd_scope_for_us():
            # If we can create a systemd scope for us and move ourselves in it,
            # we have a usable cgroup afterwards.
            cgroup = CgroupsV2.from_system()

        else:
            # No usable cgroup. We might still be able to continue if we actually
            # do not require cgroups for benchmarking. So we do not fail here
            # but return an instance that will on produce an error later.
            return CgroupsV2({})

        # Now we are the only process in this cgroup. In order to make it usable for
        # benchmarking, we need to move ourselves into a child cgroup.
        child_cgroup = cgroup.create_fresh_child_cgroup(
            cgroup.subsystems.keys(), prefix="benchexec_process_"
        )
        for pid in cgroup.get_all_tasks():
            child_cgroup.add_task(pid)
        assert child_cgroup.has_tasks()
        assert not cgroup.has_tasks()

        # Now that the cgroup is empty, we can enable controller delegation.
        # We enable all controllers, even those that we do not need ourselves,
        # in order to allow nesting of other cgroup-using software.
        controllers = util.read_file(cgroup.path / "cgroup.controllers").split()
        util.write_file(
            " ".join(f"+{c}" for c in controllers),
            cgroup.path / "cgroup.subtree_control",
        )

        _usable_cgroup = cgroup

    return _usable_cgroup


def _create_systemd_scope_for_us():
    """
    Attempt to create a systemd scope for us (with pystemd).
    If it works this process is moved into the fresh scope.

    TODO: We should probably also move our child processes to the scope.

    @return: a boolean indicating whether this succeeded
    """
    try:
        from pystemd.dbuslib import DBus
        from pystemd.dbusexc import DBusFileNotFoundError
        from pystemd.systemd1 import Manager, Unit

        with DBus(user_mode=True) as bus, Manager(bus=bus) as manager:
            unit_params = {
                # workaround for not declared parameters, remove in the future
                b"_custom": (b"PIDs", b"au", [os.getpid()]),
                b"Delegate": True,
            }

            random_suffix = secrets.token_urlsafe(8)
            name = f"benchexec_{random_suffix}.scope".encode()
            manager.Manager.StartTransientUnit(name, b"fail", unit_params)
            # StartTransientUnit is async, so we need to ensure it has finished
            # and moved our process before we continue.
            # We might need a loop here (so far it always seems to work without,
            # maybe systemd serializes this request with the unit creation).
            with Unit(name, bus=bus) as unit:
                assert unit.LoadState == b"loaded"
                assert unit.ActiveState == b"active"
                assert unit.SubState == b"running"
                # Cgroup path would be accessible as unit.ControlGroup if we need it.

            logging.debug("Process moved to a fresh systemd scope: %s", name.decode())
            return True

    except ImportError:
        logging.debug("pystemd could not be imported.")
    except DBusFileNotFoundError as e:  # pytype: disable=name-error
        logging.debug("No user DBus found, not using pystemd: %s", e)

    return False


def _find_cgroup_mount():
    """
    Return the mountpoint of the cgroupv2 unified hierarchy.
    @return Path mountpoint
    """
    try:
        with open("/proc/mounts", "rt") as mountsFile:
            for mount in mountsFile:
                mount = mount.split(" ")
                if mount[2] == "cgroup2":
                    return pathlib.Path(mount[1])
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
            return _parse_proc_pid_cgroup(ownCgroupsFile)
    except OSError:
        logging.exception("Cannot read /proc/self/cgroup")


def _parse_proc_pid_cgroup(cgroup_file):
    """
    Parse a /proc/*/cgroup file into tuples of (subsystem,cgroup).
    @param content: An iterable over the lines of the file.
    @return: a generator of tuples
    """
    mountpoint = _find_cgroup_mount()
    for line in cgroup_file:
        own_cgroup = line.strip().split(":")[2][1:]
        path = mountpoint / own_cgroup

    return path


def kill_all_tasks_in_cgroup(cgroup, ensure_empty=True):
    tasksFile = cgroup / "cgroup.procs"

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


class CgroupsV2(Cgroups):
    version = 2

    IO = "io"
    CPU = "cpu"
    CPUSET = "cpuset"
    MEMORY = "memory"
    PID = "pids"
    FREEZE = "freeze"
    KILL = "kill"

    def __init__(self, subsystems):
        super(CgroupsV2, self).__init__(subsystems)

        self.path = (
            next(iter(self.subsystems.values())) if len(self.subsystems) else None
        )

    @classmethod
    def from_system(cls, cgroup_procinfo=None):
        logging.debug(
            "Analyzing /proc/mounts and /proc/self/cgroup to determine cgroups."
        )
        if cgroup_procinfo is None:
            cgroup_path = _find_own_cgroups()
        else:
            cgroup_path = _parse_proc_pid_cgroup(cgroup_procinfo)

        try:
            with open(cgroup_path / "cgroup.controllers") as subsystems_file:
                subsystems = set(subsystems_file.readline().strip().split())
        except OSError:
            # happens if we parse cgroup_procinfo of a deleted cgroup for check_cgroups
            subsystems = set()

        # introduced in 5.14
        if (cgroup_path / "cgroup.kill").exists():
            subsystems.add(cls.KILL)

        # always supported in v2
        subsystems.add(cls.FREEZE)

        # basic support always available in v2, this supports everything we use
        subsystems.add(cls.CPU)

        return cls({k: cgroup_path for k in subsystems})

    def create_fresh_child_cgroup(self, subsystems, prefix=CGROUP_NAME_PREFIX):
        """
        Create child cgroups of the current cgroup for at least the given subsystems.
        @return: A Cgroup instance representing the new child cgroup(s).
        """
        subsystems = set(subsystems)
        assert subsystems.issubset(self.subsystems.keys())

        if not subsystems:
            return Cgroups.dummy()

        child_path = pathlib.Path(tempfile.mkdtemp(prefix=prefix, dir=self.path))

        child_subsystems = set(
            util.read_file(child_path / "cgroup.controllers").split()
        )

        # basic cpu controller support without being enabled
        child_subsystems |= {self.CPU, self.FREEZE}
        if self.KILL in self.subsystems:
            child_subsystems.add(self.KILL)

        return CgroupsV2({c: child_path for c in child_subsystems})

    def require_subsystem(self, subsystem, log_method=logging.warning):
        """
        Check whether the given subsystem is enabled and is writable
        (i.e., new cgroups can be created for it).
        Produces a log message for the user if one of the conditions is not fulfilled.
        @return A boolean value.
        """
        # TODO
        # We can assume that creation of child cgroups works,
        # because we only use cgroups if we were able to move the current process
        # into a child cgroup in initialize().
        return subsystem in self

    def handle_errors(self, critical_cgroups):
        """
        If there were errors in calls to require_subsystem() and critical_cgroups
        is not empty, terminate the program with an error message that explains how to
        fix the problem.

        @param critical_cgroups: set of unusable but required cgroups
        """
        if not critical_cgroups:
            return

        if self.subsystems:
            # Some subsystems are available, but not the required ones.
            # Check if it is a delegation problem or if some subsystems do not exist.
            unknown_subsystems = set(critical_cgroups)
            with open("/proc/cgroups", mode="r") as cgroups:
                for line in cgroups:
                    if not line.startswith("#"):
                        unknown_subsystems.discard(line.split("\t", maxsplit=1)[0])
            if unknown_subsystems:
                sys.exit(
                    _ERROR_MSG_UNKNOWN_SUBSYSTEMS.format(", ".join(unknown_subsystems))
                )
            else:
                sys.exit(
                    _ERROR_MSG_MISSING_SUBSYSTEMS.format(
                        ", ".join(critical_cgroups), self.path
                    )
                )

        else:
            # no cgroup available at all
            if not systeminfo.has_systemd():
                sys.exit(_ERROR_NO_SYSTEMD)

            try:
                import pystemd  # noqa: F401
            except ImportError:
                sys.exit(_ERROR_NO_PSYSTEMD)
            else:
                sys.exit(_ERROR_MSG_OTHER)

    def add_task(self, pid):
        """
        Add a process to the cgroups represented by this instance.
        """
        with open(self.path / "cgroup.procs", "w") as tasksFile:
            tasksFile.write(str(pid))

    def get_all_tasks(self, subsystem=None):
        """
        Return a generator of all PIDs currently in this cgroup for the given subsystem.
        """
        with open(self.path / "cgroup.procs") as tasksFile:
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
                    subCgroup = pathlib.Path(dirpath) / subCgroup
                    kill_all_tasks_in_cgroup(subCgroup, ensure_empty=delete)

                    if delete:
                        self._remove_cgroup(subCgroup)

            kill_all_tasks_in_cgroup(cgroup, ensure_empty=delete)

        if self.KILL in self.subsystems:
            util.write_file("1", self.path / "cgroup.kill")
            return

        # First, we go through all cgroups recursively while they are frozen and kill
        # all processes. This helps against fork bombs and prevents processes from
        # creating new subgroups while we are trying to kill everything.
        # All processes will stay until they are thawed (so we cannot check for cgroup
        # emptiness and we cannot delete subgroups).
        freezer_file = self.path / "cgroup.freeze"

        util.write_file("1", freezer_file)
        kill_all_tasks_in_cgroup_recursively(self.path, delete=False)
        util.write_file("0", freezer_file)

        # Second, we go through all cgroups again, kill what is left,
        # check for emptiness, and remove subgroups.
        kill_all_tasks_in_cgroup_recursively(self.path, delete=True)

    def read_cputime(self):
        """
        Read the cputime usage of this cgroup. CPU cgroup needs to be available.
        @return cputime usage in seconds
        """
        cpu_stats = dict(self.get_key_value_pairs(self.CPU, "stat"))

        # TODO switch to Decimal together with all other float values
        return float(cpu_stats["usage_usec"]) / 1_000_000

    def read_max_mem_usage(self):
        logging.debug("Memory-usage not supported in cgroups v2")

        return

    def read_mem_pressure(self):
        mem_stats = dict(self.get_key_value_pairs(self.MEMORY, "pressure"))
        mem_some_stats = mem_stats["some"].split(" ")
        stats_map = {s[0]: s[1] for s in (s.split("=") for s in mem_some_stats)}

        return Decimal(stats_map["total"]) / 1_000_000

    def read_cpu_pressure(self):
        cpu_stats = dict(self.get_key_value_pairs(self.CPU, "pressure"))
        cpu_some_stats = cpu_stats["some"].split(" ")
        stats_map = {s[0]: s[1] for s in (s.split("=") for s in cpu_some_stats)}

        return Decimal(stats_map["total"]) / 1_000_000

    def read_io_pressure(self):
        io_stats = dict(self.get_key_value_pairs(self.IO, "pressure"))
        io_some_stats = io_stats["some"].split(" ")
        stats_map = {s[0]: s[1] for s in (s.split("=") for s in io_some_stats)}

        return Decimal(stats_map["total"]) / 1_000_000

    def read_usage_per_cpu(self):
        logging.debug("Usage per CPU not supported in cgroups v2")

        return {}

    def read_allowed_cpus(self):
        return util.parse_int_list(self.get_value(self.CPUSET, "cpus.effective"))

    def read_allowed_memory_banks(self):
        return util.parse_int_list(self.get_value(self.CPUSET, "mems.effective"))

    def read_io_stat(self):
        bytes_read = 0
        bytes_written = 0
        for io_line in self.get_file_lines(self.IO, "stat"):
            dev_no, *stats = io_line.split(" ")
            stats_map = {s[0]: s[1] for s in (s.split("=") for s in stats if s)}
            if "rbytes" in stats_map:
                bytes_read += int(stats_map["rbytes"])
            if "wbytes" in stats_map:
                bytes_written += int(stats_map["wbytes"])
        return bytes_read, bytes_written

    def has_tasks(self, path=None):
        path = path or self.path
        return bool((path / "cgroup.procs").read_bytes().strip())

    def write_memory_limit(self, limit):
        self.set_value(self.MEMORY, "max", limit)

    def read_memory_limit(self):
        return int(self.get_value(self.MEMORY, "max"))

    def disable_swap(self):
        self.set_value(self.MEMORY, "swap.max", "0")

    def read_oom_count(self):
        for line in self.get_file_lines(self.MEMORY, "events"):
            k, v = line.split(" ")
            if k == "oom_kill":
                return int(v)

        return 0
