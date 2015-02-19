"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
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
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import shutil
import signal
import tempfile
import time

from . import util as util

__all__ = [
           'find_my_cgroups',
           'init_cgroup',
           'create_cgroup',
           'add_task_to_cgroup',
           'kill_all_tasks_in_cgroup',
           'kill_all_tasks_in_cgroup_recursively',
           'remove_cgroup',
           'CPUACCT',
           'CPUSET',
           'FREEZER',
           'MEMORY',
           ]

CGROUP_NAME_PREFIX='benchmark_'

CPUACCT = 'cpuacct'
CPUSET = 'cpuset'
FREEZER = 'freezer'
MEMORY = 'memory'
ALL_KNOWN_SUBSYSTEMS = set([CPUACCT, CPUSET, FREEZER, MEMORY])


def find_my_cgroups():
    """
    Return a Cgroup object with the cgroups of the current process.
    Note that it is not guaranteed that all subsystems are available
    in the returned object, as a subsystem may not be mounted
    or may be inaccessible with current rights.
    Check with "subsystem in <instance>" before using.
    """
    logging.debug('Analyzing /proc/mounts and /proc/self/cgroup for determining cgroups.')
    mounts = _find_cgroup_mounts()
    cgroups = _find_own_cgroups()

    cgroupsParents = {}
    for mountedSubsystem, mount in mounts.items():
        cgroupsParents[mountedSubsystem] = os.path.join(mount, cgroups[mountedSubsystem])

    return Cgroup(cgroupsParents)


def init_cgroup(cgroupsParents, subsystem):
    """
    Initialize a cgroup subsystem.
    Call this before calling any other methods from this module for this subsystem.
    @param cgroupsParents: A dictionary with the cgroup mount points for each subsystem (filled by this method)
    @param subsystem: The subsystem to initialize
    """
    if not cgroupsParents:
        # first call to this method
        logging.debug('Analyzing /proc/mounts and /proc/self/cgroup for determining cgroups.')
        mounts = _find_cgroup_mounts()
        cgroups = _find_own_cgroups()

        for mountedSubsystem, mount in mounts.items():
            cgroupsParents[mountedSubsystem] = os.path.join(mount, cgroups[mountedSubsystem])

    if not subsystem in cgroupsParents:
        logging.warning(
'''Cgroup subsystem {0} not enabled.
Please enable it with "sudo mount -t cgroup none /sys/fs/cgroup".'''
            .format(subsystem)
            )
        cgroupsParents[subsystem] = None
        return

    cgroup = cgroupsParents[subsystem]
    logging.debug('My cgroup for subsystem {0} is {1}'.format(subsystem, cgroup))

    try: # only for testing?
        testCgroup = create_cgroup(cgroupsParents, subsystem)[subsystem]
        remove_cgroup(testCgroup)
    except OSError as e:
        logging.warning(
'''Cannot use cgroup hierarchy mounted at {0}, reason: {1}
If permissions are wrong, please run "sudo chmod o+wt \'{0}\'".'''
            .format(cgroup, e.strerror))
        cgroupsParents[subsystem] = None


def _find_cgroup_mounts():
    mounts = {}
    try:
        with open('/proc/mounts', 'rt') as mountsFile:
            for mount in mountsFile:
                mount = mount.split(' ')
                if mount[2] == 'cgroup':
                    mountpoint = mount[1]
                    options = mount[3]
                    for option in options.split(','):
                        if option in ALL_KNOWN_SUBSYSTEMS:
                            mounts[option] = mountpoint
    except IOError as e:
        logging.exception('Cannot read /proc/mounts')
    return mounts


def _find_own_cgroups():
    """
    Given a cgroup subsystem,
    find the cgroup in which this process is in.
    (Each process is in exactly cgroup in each hierarchy.)
    @return the path to the cgroup inside the hierarchy
    """
    ownCgroups = {}
    try:
        with open('/proc/self/cgroup', 'rt') as ownCgroupsFile:
            for ownCgroup in ownCgroupsFile:
                #each line is "id:subsystem,subsystem:path"
                ownCgroup = ownCgroup.strip().split(':')
                path = ownCgroup[2][1:] # remove leading /
                for subsystem in ownCgroup[1].split(','):
                    ownCgroups[subsystem] = path
    except IOError as e:
        logging.exception('Cannot read /proc/self/cgroup')
    return ownCgroups


def create_cgroup(cgroupsParents, *subsystems):
    """
    Try to create a cgroup for each of the given subsystems.
    If multiple subsystems are available in the same hierarchy,
    a common cgroup for theses subsystems is used.
    @param subsystems: a list of cgroup subsystems
    @return a map from subsystem to cgroup for each subsystem where it was possible to create a cgroup
    """
    createdCgroupsPerSubsystem = {}
    createdCgroupsPerParent = {}
    for subsystem in subsystems:
        if not subsystem in cgroupsParents:
            init_cgroup(cgroupsParents, subsystem)

        parentCgroup = cgroupsParents.get(subsystem)
        if not parentCgroup:
            # subsystem not enabled
            continue
        if parentCgroup in createdCgroupsPerParent:
            # reuse already created cgroup
            createdCgroupsPerSubsystem[subsystem] = createdCgroupsPerParent[parentCgroup]
            continue

        cgroup = tempfile.mkdtemp(prefix=CGROUP_NAME_PREFIX, dir=parentCgroup)
        createdCgroupsPerSubsystem[subsystem] = cgroup
        createdCgroupsPerParent[parentCgroup] = cgroup

        # add allowed cpus and memory to cgroup if necessary
        # (otherwise we can't add any tasks)
        try:
            shutil.copyfile(os.path.join(parentCgroup, 'cpuset.cpus'), os.path.join(cgroup, 'cpuset.cpus'))
            shutil.copyfile(os.path.join(parentCgroup, 'cpuset.mems'), os.path.join(cgroup, 'cpuset.mems'))
        except IOError:
            # expected to fail if cpuset subsystem is not enabled in this hierarchy
            pass

    return Cgroup(createdCgroupsPerSubsystem)

def add_task_to_cgroup(cgroup, pid):
    if cgroup:
        with open(os.path.join(cgroup, 'tasks'), 'w') as tasksFile:
            tasksFile.write(str(pid))


def kill_all_tasks_in_cgroup_recursively(cgroup):
    """
    Iterate through a cgroup and all its children cgroups
    and kill all processes in any of these cgroups forcefully.
    Additionally, the children cgroups will be deleted.
    """
    files = [os.path.join(cgroup,f) for f in os.listdir(cgroup)]
    subdirs = filter(os.path.isdir, files)

    for subCgroup in subdirs:
        kill_all_tasks_in_cgroup_recursively(subCgroup)
        remove_cgroup(subCgroup)

    kill_all_tasks_in_cgroup(cgroup)


def kill_all_tasks_in_cgroup(cgroup):
    tasksFile = os.path.join(cgroup, 'tasks')

    i = 0
    while True:
        i += 1
        for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGKILL]:
            with open(tasksFile, 'rt') as tasks:
                task = None
                for task in tasks:
                    task = task.strip()
                    if i > 1:
                        logging.warning('Run has left-over process with pid {0} in cgroup {1}, sending signal {2} (try {3}).'.format(task, cgroup, sig, i))
                    util.kill_process(int(task), sig)

                if task is None:
                    return # No process was hanging, exit

                time.sleep(i * 0.5) # wait for the process to exit, this might take some time


def remove_cgroup(cgroup):
    if cgroup:
        if not os.path.exists(cgroup):
            logging.warning('Cannot remove CGroup {0}, because it does not exist.'.format(cgroup))
            return
        assert os.path.getsize(os.path.join(cgroup, 'tasks')) == 0
        try:
            os.rmdir(cgroup)
        except OSError:
            # sometimes this fails because the cgroup is still busy, we try again once
            try:
                os.rmdir(cgroup)
            except OSError as e:
                logging.warning("Failed to remove cgroup {0}: error {1} ({2})"
                                .format(cgroup, e.errno, e.strerror))

class Cgroup(object):
    def __init__(self, cgroupsPerSubsystem):
        assert cgroupsPerSubsystem.keys() <= ALL_KNOWN_SUBSYSTEMS
        assert all(cgroupsPerSubsystem.values())
        self.per_subsystem = cgroupsPerSubsystem
        self.paths = set(cgroupsPerSubsystem.values()) # without duplicates

    def __contains__(self, key):
        return key in self.per_subsystem

    def __getitem__(self, key):
        return self.per_subsystem[key]

    def __str__(self):
        return str(self.paths)

    def require_subsystem(self, subsystem):
        """
        Check whether the given subsystem is enabled and is writable
        (i.e., new cgroups can be created for it).
        Produces a log message for the user if one of the conditions is not fulfilled.
        If the subsystem is enabled but not writable, it will be removed from
        this instance such that further checks with "in" will return "False".
        @return A boolean value.
        """
        if not subsystem in self:
            logging.warning('Cgroup subsystem {0} is not enabled. Please enable it with "sudo mount -t cgroup none /sys/fs/cgroup".'.format(subsystem))
            return False

        try:
            test_cgroup = create_cgroup(self.per_subsystem, subsystem)
            test_cgroup.remove()
        except OSError as e:
            del self.per_subsystem[subsystem]
            self.paths = set(self.per_subsystem.values())
            logging.warning('Cannot use cgroup hierarchy mounted at {0} for subsystem {1}, reason: {2}. If permissions are wrong, please run "sudo chmod o+wt \'{0}\'".'.format(self.per_subsystem[subsystem], subsystem, e.strerror))
            return False

        return True

    def add_task(self, pid):
        for cgroup in self.paths:
            add_task_to_cgroup(cgroup, pid)

    def kill_all_tasks(self):
        for cgroup in self.paths:
            kill_all_tasks_in_cgroup(cgroup)

    def has_value(self, subsystem, option):
        """
        Check whether the given value exists in the given subsystem.
        Does not make a difference whether the value is readable, writable, or both.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.  
        """
        assert subsystem in self
        return os.path.isfile(os.path.join(self.per_subsystem[subsystem], subsystem + '.' + option))

    def get_value(self, subsystem, option):
        """
        Read the given value from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.  
        """
        assert subsystem in self
        return util.read_file(self.per_subsystem[subsystem], subsystem + '.' + option)

    def get_file_lines(self, subsystem, option):
        """
        Read the lines of the given file from the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.
        """
        assert subsystem in self
        with open(os.path.join(self.per_subsystem[subsystem], subsystem + '.' + option)) as f:
            for line in f:
                yield line

    def set_value(self, subsystem, option, value):
        """
        Write the given value for the given subsystem.
        Do not include the subsystem name in the option name.
        Only call this method if the given subsystem is available.  
        """
        assert subsystem in self
        util.write_file(str(value), self.per_subsystem[subsystem], subsystem + '.' + option)

    def remove(self):
        for cgroup in self.paths:
            remove_cgroup(cgroup)
        del self.paths
        del self.per_subsystem

    def read_cputime(self):
        """
        Read the cputime usage of this cgroup. CPUACCT cgroup needs to be available.
        @return cputime usage in seconds
        """
        return float(self.get_value(CPUACCT, 'usage'))/1000000000 # nano-seconds to seconds

    def read_allowed_memory_banks(self):
        """Get the list of all memory banks allowed by this cgroup."""
        return util.parse_int_list(self.get_value(CPUSET, 'mems'))
