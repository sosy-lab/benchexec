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

import sys
sys.dont_write_bytecode = True # prevent creation of .pyc files

try:
  import Queue
except ImportError: # Queue was renamed to queue in Python 3
  import queue as Queue

import collections
import itertools
import logging
import math
import os
import re
import resource
import subprocess
import threading
import time

from .model import CORELIMIT, MEMLIMIT, TIMELIMIT, SOFTTIMELIMIT
from . import cgroups
from .runexecutor import RunExecutor
from .systeminfo import SystemInfo
from . import util as util


WORKER_THREADS = []
STOPPED_BY_INTERRUPT = False

_BYTE_FACTOR = 1000 # byte in kilobyte

_TURBO_BOOST_FILE = "/sys/devices/system/cpu/cpufreq/boost"
_TURBO_BOOST_FILE_PSTATE = "/sys/devices/system/cpu/intel_pstate/no_turbo"

def init(config, benchmark):
    benchmark.executable = benchmark.tool.executable()
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    try:
        processes = subprocess.Popen(['ps', '-eo', 'cmd'], stdout=subprocess.PIPE).communicate()[0]
        if len(re.findall("python.*benchmark\.py", util.decode_to_string(processes))) > 1:
            logging.warn("Already running instance of this script detected. " + \
                         "Please make sure to not interfere with somebody else's benchmarks.")
    except OSError:
        pass # this does not work on Windows

def get_system_info():
    return SystemInfo()

def execute_benchmark(benchmark, output_handler):

    run_sets_executed = 0

    logging.debug("I will use {0} threads.".format(benchmark.num_of_threads))

    cgroupsParents = {}
    cgroups.init_cgroup(cgroupsParents, 'cpuset')
    cgroupCpuset = cgroupsParents['cpuset']

    coreAssignment = None # cores per run
    memoryAssignment = None # memory banks per run
    if CORELIMIT in benchmark.rlimits:
        if not cgroupCpuset:
            sys.exit("Cannot limit the number of CPU cores/memory nodes without cpuset cgroup.")
        coreAssignment = _get_cpu_cores_per_run(benchmark.rlimits[CORELIMIT], benchmark.num_of_threads, cgroupCpuset)
        memoryAssignment = _get_memory_banks_per_run(coreAssignment, cgroupCpuset)

    if MEMLIMIT in benchmark.rlimits:
        # check whether we have enough memory in the used memory banks for all runs
        memLimit = benchmark.rlimits[MEMLIMIT] * _BYTE_FACTOR * _BYTE_FACTOR # MB to Byte
        _check_memory_size(memLimit, benchmark.num_of_threads, memoryAssignment, cgroupsParents)

    if benchmark.num_of_threads > 1 and _is_turbo_boost_enabled():
        logging.warning("Turbo boost of CPU is enabled. Starting more than one benchmark in parallel affects the CPU frequency and thus makes the performance unreliable.")

    # iterate over run sets
    for runSet in benchmark.run_sets:

        if STOPPED_BY_INTERRUPT: break

        if not runSet.should_be_executed():
            output_handler.output_for_skipping_run_set(runSet)

        elif not runSet.runs:
            output_handler.output_for_skipping_run_set(runSet, "because it has no files")

        else:
            run_sets_executed += 1
            # get times before runSet
            ruBefore = resource.getrusage(resource.RUSAGE_CHILDREN)
            walltime_before = time.time()
            energyBefore = util.measure_energy()

            output_handler.output_before_run_set(runSet)

            # put all runs into a queue
            for run in runSet.runs:
                _Worker.working_queue.put(run)

            # create some workers
            for i in range(benchmark.num_of_threads):
                cores = coreAssignment[i] if coreAssignment else None
                memBanks = memoryAssignment[i] if memoryAssignment else None
                WORKER_THREADS.append(_Worker(benchmark, cores, memBanks, output_handler))

            # wait until all tasks are done,
            # instead of queue.join(), we use a loop and sleep(1) to handle KeyboardInterrupt
            finished = False
            while not finished and not STOPPED_BY_INTERRUPT:
                try:
                    _Worker.working_queue.all_tasks_done.acquire()
                    finished = (_Worker.working_queue.unfinished_tasks == 0)
                finally:
                    _Worker.working_queue.all_tasks_done.release()

                try:
                    time.sleep(0.1) # sleep some time
                except KeyboardInterrupt:
                    stop()

            # get times after runSet
            walltime_after = time.time()
            energy = util.measure_energy(energyBefore)
            usedWallTime = walltime_after - walltime_before
            ruAfter = resource.getrusage(resource.RUSAGE_CHILDREN)
            usedCpuTime = (ruAfter.ru_utime + ruAfter.ru_stime) \
                        - (ruBefore.ru_utime + ruBefore.ru_stime)

            if STOPPED_BY_INTERRUPT:
                output_handler.set_error('interrupted')
            output_handler.output_after_run_set(runSet, cputime=usedCpuTime, walltime=usedWallTime, energy=energy)

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)


def stop():
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True

    # kill running jobs
    util.printOut("killing subprocesses...")
    for worker in WORKER_THREADS:
        worker.stop()

    # wait until all threads are stopped
    for worker in WORKER_THREADS:
        worker.join()


def _get_cpu_cores_per_run(coreLimit, num_of_threads, cgroupCpuset):
    """
    Calculate an assignment of the available CPU cores to a number
    of parallel benchmark executions such that each run gets its own cores
    without overlapping of cores between runs.
    In case the machine has hyper-threading, this method tries to avoid
    putting two different runs on the same physical core
    (but it does not guarantee this if the number of parallel runs is too high to avoid it).
    In case the machine has multiple CPUs, this method avoids
    splitting a run across multiple CPUs if the number of cores per run
    is lower than the number of cores per CPU
    (splitting a run over multiple CPUs provides worse performance).
    It will also try to split the runs evenly across all available CPUs.

    A few theoretically-possible cases are not implemented,
    for example assigning three 10-core runs on a machine
    with two 16-core CPUs (this would have unfair core assignment
    and thus undesirable performance characteristics anyway).

    The list of available cores is read from the cgroup filesystem,
    such that the assigned cores are a subset of the cores
    that the current process is allowed to use.
    This script does currently not support situations
    where the available cores are assymetrically split over CPUs,
    e.g. 3 cores on one CPU and 5 on another.

    @param coreLimit: the number of cores for each run
    @param num_of_threads: the number of parallel benchmark executions
    @return a list of lists, where each inner list contains the cores for one run
    """
    try:
        # read list of available CPU cores
        allCpus = util.parse_int_list(util.read_file(cgroupCpuset, 'cpuset.cpus'))
        logging.debug("List of available CPU cores is {0}.".format(allCpus))

        # read mapping of core to CPU ("physical package")
        physical_packages = map(lambda core : int(util.read_file('/sys/devices/system/cpu/cpu{0}/topology/physical_package_id'.format(core))), allCpus)
        cores_of_package = collections.defaultdict(list)
        for core, package in zip(allCpus, physical_packages):
            cores_of_package[package].append(core)
        logging.debug("Physical packages of cores are {0}.".format(str(cores_of_package)))

        # read hyper-threading information (sibling cores sharing the same physical core)
        siblings_of_core = {}
        for core in allCpus:
            siblings = util.parse_int_list(util.read_file('/sys/devices/system/cpu/cpu{0}/topology/thread_siblings_list'.format(core)))
            siblings_of_core[core] = siblings
        logging.debug("Siblings of cores are {0}.".format(str(siblings_of_core)))
    except ValueError as e:
        sys.exit("Could not read CPU information from kernel: {0}".format(e))

    return _get_cpu_cores_per_run0(coreLimit, num_of_threads, allCpus, cores_of_package, siblings_of_core)

def _get_cpu_cores_per_run0(coreLimit, num_of_threads, allCpus, cores_of_package, siblings_of_core):
    """This method does the actual work of _get_cpu_cores_per_run
    without reading the machine architecture from the filesystem
    in order to be testable. For description, c.f. above.
    Note that this method might change the input parameters!
    Do not call it directly, call getCpuCoresPerRun()!
    @param allCpus: the list of all available cores
    @param cores_of_package: a mapping from package (CPU) ids to lists of cores that belong to this CPU
    @param siblings_of_core: a mapping from each core to a list of sibling cores including the core itself (a sibling is a core sharing the same physical core)
    """
    # First, do some checks whether this algorithm has a chance to work.
    if coreLimit > len(allCpus):
        sys.exit("Cannot run benchmarks with {0} CPU cores, only {1} CPU cores available.".format(coreLimit, len(allCpus)))
    if coreLimit * num_of_threads > len(allCpus):
        sys.exit("Cannot run {0} benchmarks in parallel with {1} CPU cores each, only {2} CPU cores available. Please reduce the number of threads to {3}.".format(num_of_threads, coreLimit, len(allCpus), len(allCpus) // coreLimit))

    package_size = None # Number of cores per package
    for package, cores in cores_of_package.items():
        if package_size is None:
            package_size = len(cores)
        elif package_size != len(cores):
            sys.exit("Assymetric machine architecture not supported: CPU package {0} has {1} cores, but other package has {2} cores.".format(package, len(cores), package_size)) 

    core_size = None # Number of threads per core
    for core, siblings in siblings_of_core.items():
        if core_size is None:
            core_size = len(siblings)
        elif core_size != len(siblings):
            sys.exit("Assymetric machine architecture not supported: CPU core {0} has {1} siblings, but other core has {2} siblings.".format(core, len(siblings), core_size)) 

    # Second, compute some values we will need.
    package_count = len(cores_of_package)

    coreLimit_rounded_up = int(math.ceil(coreLimit / core_size) * core_size)
    assert coreLimit <= coreLimit_rounded_up < (coreLimit + core_size)
    #assert coreLimit_rounded_up <= package_size
    if coreLimit_rounded_up * num_of_threads > len(allCpus):
        logging.warning("The number of threads is too high and hyper-threading sibling cores need to be split among different runs, which makes benchmarking unreliable. Please reduce the number of threads to {0}.".format(len(allCpus) // coreLimit_rounded_up))

    packages_per_run = int(math.ceil(coreLimit_rounded_up / package_size))
    if packages_per_run > 1 and packages_per_run * num_of_threads > package_count:
        sys.exit("Cannot split runs over multiple CPUs and at the same time assign multiple runs to the same CPU. Please reduce the number of threads to {0}.".format(package_count // packages_per_run))

    runs_per_package = int(math.ceil(num_of_threads / package_count))
    assert packages_per_run == 1 or runs_per_package == 1
    if packages_per_run == 1 and runs_per_package * coreLimit > package_size:
        sys.exit("Cannot run {} benchmarks with {} cores on {} CPUs with {} cores, because runs would need to be split across multiple CPUs. Please reduce the number of threads.".format(num_of_threads, coreLimit, package_count, package_size))

    logging.debug("Going to assign at most {0} runs per package, each one using {1} cores and blocking {2} cores on {3} packages.".format(runs_per_package, coreLimit, coreLimit_rounded_up, packages_per_run))

    # Third, do the actual core assignment.
    result = []
    used_cores = set()
    for run in range(num_of_threads):
        # this calculation ensures that runs are split evenly across packages
        start_package = (run * packages_per_run) % package_count
        cores = []
        for package in range(start_package, start_package + packages_per_run):
            for core in cores_of_package[package]:
                if core not in cores:
                    cores.extend(c for c in siblings_of_core[core] if not c in used_cores)
                if len(cores) >= coreLimit:
                    break
            cores = cores[:coreLimit] # shrink if we got more cores than necessary
            # remove used cores such that we do not try to use them again
            cores_of_package[package] = [core for core in cores_of_package[package] if core not in cores]

        assert len(cores) == coreLimit, "Wrong number of cores for run {} - previous results: {}, remaining cores per package: {}, current cores: {}".format(run, result, cores_of_package, cores)
        used_cores.update(cores)
        result.append(sorted(cores))

    assert len(result) == num_of_threads
    assert all(len(cores) == coreLimit for cores in result)
    assert len(set(itertools.chain(*result))) == num_of_threads * coreLimit, "Cores are not uniquely assigned to runs: " + result

    logging.debug("Final core assignment: {0}.".format(str(result)))
    return result


def _get_memory_banks_per_run(coreAssignment, cgroupCpuset):
    """Get an assignment of memory banks to runs that fits to the given coreAssignment,
    i.e., no run is allowed to use memory that is not local (on the same NUMA node)
    to one of its CPU cores."""
    try:
        # read list of available memory banks
        allMems = set(_get_allowed_memory_banks(cgroupCpuset))

        result = []
        for cores in coreAssignment:
            mems = set()
            for core in cores:
                coreDir = '/sys/devices/system/cpu/cpu{0}/'.format(core)
                mems.update(_get_memory_banks_listed_in_dir(coreDir))
            allowedMems = sorted(mems.intersection(allMems))
            logging.debug("Memory banks for cores {} are {}, of which we can use {}.".format(core, list(mems), allowedMems))

            result.append(allowedMems)

        assert len(result) == len(coreAssignment)

        if any(result) and os.path.isdir('/sys/devices/system/node/'):
            return result
        else:
            # All runs get the empty list of memory regions
            # because this system has no NUMA support
            return None
    except ValueError as e:
        sys.exit("Could not read memory information from kernel: {0}".format(e))


def _get_allowed_memory_banks(cgroupCpuset):
    """Get the list of all memory banks allowed by the given cgroup."""
    return util.parse_int_list(util.read_file(cgroupCpuset, 'cpuset.mems'))

def _get_memory_banks_listed_in_dir(dir):
    """Get all memory banks the kernel lists in a given directory.
    Such a directory can be /sys/devices/system/node/ (contains all memory banks)
    or /sys/devices/system/cpu/cpu*/ (contains all memory banks on the same NUMA node as that core)."""
    # Such directories contain entries named "node<id>" for each memory bank
    return [int(entry[4:]) for entry in os.listdir(dir) if entry.startswith('node')]


def _check_memory_size(memLimit, num_of_threads, memoryAssignment, cgroupsParents):
    """Check whether the desired amount of parallel benchmarks fits in the memory.
    Implemented are checks for memory limits via cgroup controller "memory" and
    memory bank restrictions via cgroup controller "cpuset",
    as well as whether the system actually has enough memory installed.
    @param memLimit: the memory limit in bytes per run
    @param num_of_threads: the number of parallel benchmark executions
    @param memoryAssignment: the allocation of memory banks to runs (if not present, all banks are assigned to all runs)
    """
    try:
        # Check amount of memory allowed via cgroups.
        def check_limit(actualLimit):
            if actualLimit < memLimit:
                sys.exit("Cgroups allow only {} bytes of memory to be used, cannot execute runs with {} bytes of memory.".format(actualLimit, memLimit))
            elif actualLimit < memLimit * num_of_threads:
                sys.exit("Cgroups allow only {} bytes of memory to be used, not enough for {} benchmarks with {} bytes each. Please reduce the number of threads".format(actualLimit, num_of_threads, memLimit))

        if not os.path.isdir('/sys/devices/system/node/'):
            logging.debug("System without NUMA support in Linux kernel, ignoring memory assignment.")
            return

        cgroups.init_cgroup(cgroupsParents, 'memory')
        cgroupMemory = cgroupsParents['memory']
        if cgroupMemory:
            # We use the entries hierarchical_*_limit in memory.stat and not memory.*limit_in_bytes
            # because the former may be lower if memory.use_hierarchy is enabled.
            with open(os.path.join(cgroupMemory, 'memory.stat')) as f:
                for line in f:
                    if line.startswith('hierarchical_memory_limit'):
                        check_limit(int(line.split()[1]))
                    elif line.startswith('hierarchical_memsw_limit'):
                        check_limit(int(line.split()[1]))

        # Get list of all memory banks, either from memory assignment or from system.
        if not memoryAssignment:
            cgroups.init_cgroup(cgroupsParents, 'cpuset')
            cgroupCpuset = cgroupsParents['cpuset']
            if cgroupCpuset:
                allMems = _get_allowed_memory_banks(cgroupCpuset)
            else:
                allMems = _get_memory_banks_listed_in_dir('/sys/devices/system/node/')
            memoryAssignment = [allMems] * num_of_threads # "fake" memory assignment: all threads on all banks
        else:
            allMems = set(itertools.chain(*memoryAssignment))

        memSizes = dict((mem, _get_memory_bank_size(mem)) for mem in allMems)
    except ValueError as e:
        sys.exit("Could not read memory information from kernel: {0}".format(e))

    # Check whether enough memory is allocatable on the assigned memory banks.
    # As the sum of the sizes of the memory banks is at most the total size of memory in the system,
    # and we do this check always even if the banks are not restricted,
    # this also checks whether the system has actually enough memory installed.
    usedMem = collections.Counter()
    for mems_of_run in memoryAssignment:
        totalSize = sum(memSizes[mem] for mem in mems_of_run)
        if totalSize < memLimit:
            sys.exit("Memory banks {} do not have enough memory for one run, only {} bytes available.".format(mems_of_run, totalSize))
        usedMem[tuple(mems_of_run)] += memLimit
        if usedMem[tuple(mems_of_run)] > totalSize:
            sys.exit("Memory banks {} do not have enough memory for all runs, only {} bytes available. Please reduce the number of threads.".format(mems_of_run, totalSize))

def _get_memory_bank_size(memBank):
    """Get the size of a memory bank in bytes."""
    fileName = '/sys/devices/system/node/node{0}/meminfo'.format(memBank)
    size = None
    with open(fileName) as f:
        for line in f:
            if 'MemTotal' in line:
                size = line.split(':')[1].strip()
                if size[-3:] != ' kB':
                    raise ValueError('"{}" in file {} is not a memory size.'.format(size, fileName))
                size = int(size[:-3]) * 1024 # kB to Byte
                logging.debug("Memory bank {} has size {} bytes.".format(memBank, size))
                return size
    raise ValueError('Failed to read total memory from {}.'.format(fileName))


def _is_turbo_boost_enabled():
    try:
        if os.path.exists(_TURBO_BOOST_FILE):
            boost_enabled = int(util.read_file(_TURBO_BOOST_FILE))
            if not (0 <= boost_enabled <= 1):
                raise ValueError('Invalid value {} for turbo boost activation'.format(boost_enabled))
            return boost_enabled != 0
        if os.path.exists(_TURBO_BOOST_FILE_PSTATE):
            boost_disabled = int(util.read_file(_TURBO_BOOST_FILE_PSTATE))
            if not (0 <= boost_disabled <= 1):
                raise ValueError('Invalid value {} for turbo boost activation'.format(boost_enabled))
            return boost_disabled != 1
    except ValueError as e:
        sys.exit("Could not read turbo-boost information from kernel: {0}".format(e))


class _Worker(threading.Thread):
    """
    A Worker is a deamonic thread, that takes jobs from the working_queue and runs them.
    """
    working_queue = Queue.Queue()

    def __init__(self, benchmark, my_cpus, my_memory_nodes, output_handler):
        threading.Thread.__init__(self) # constuctor of superclass
        self.benchmark = benchmark
        self.my_cpus = my_cpus
        self.my_memory_nodes = my_memory_nodes
        self.output_handler = output_handler
        self.run_executor = RunExecutor()
        self.setDaemon(True)

        self.start()


    def run(self):
        while not _Worker.working_queue.empty() and not STOPPED_BY_INTERRUPT:
            currentRun = _Worker.working_queue.get_nowait()
            try:
                self.execute(currentRun)
            except SystemExit as e:
                logging.critical(e)
            except BaseException as e:
                logging.exception('Exception during run execution')
            _Worker.working_queue.task_done()


    def execute(self, run):
        """
        This function executes the tool with a sourcefile with options.
        It also calls functions for output before and after the run.
        """
        self.output_handler.output_before_run(run)
        benchmark = self.benchmark

        memlimit = None
        if MEMLIMIT in benchmark.rlimits:
            memlimit = benchmark.rlimits[MEMLIMIT] * _BYTE_FACTOR * _BYTE_FACTOR # MB to Byte

        maxLogfileSize = benchmark.config.maxLogfileSize
        if maxLogfileSize:
            maxLogfileSize *= _BYTE_FACTOR * _BYTE_FACTOR # MB to Byte
        elif maxLogfileSize == -1:
            maxLogfileSize = None

        result = \
            self.run_executor.execute_run(
                run.cmdline(), run.log_file,
                hardtimelimit=benchmark.rlimits.get(TIMELIMIT),
                softtimelimit=benchmark.rlimits.get(SOFTTIMELIMIT),
                cores=self.my_cpus,
                memory_nodes=self.my_memory_nodes,
                memlimit=memlimit,
                environments=benchmark.environment(),
                workingDir=benchmark.working_directory(),
                maxLogfileSize=maxLogfileSize)

        for key, value in result.items():
            if key == 'walltime':
                run.walltime == value
            elif key == 'cputime':
                run.cputime = value
            elif key == 'memory':
                run.values['memUsage'] = result['memory']
            elif key == 'energy':
                for ekey, evalue in value.items():
                    run.values['energy-'+ekey] = evalue
            else:
                run.values['@' + key] = value

        if self.run_executor.PROCESS_KILLED:
            # If the run was interrupted, we ignore the result and cleanup.
            run.walltime = 0
            run.cputime = 0
            try:
                if benchmark.config.debug:
                   os.rename(run.log_file, run.log_file + ".killed")
                else:
                   os.remove(run.log_file)
            except OSError:
                pass
            return

        run.after_execution(result['exitcode'])
        self.output_handler.output_after_run(run)


    def stop(self):
        # asynchronous call to runexecutor,
        # the worker will stop asap, but not within this method.
        self.run_executor.stop()
