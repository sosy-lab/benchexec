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

import sys
sys.dont_write_bytecode = True # prevent creation of .pyc files

try:
    import Queue
except ImportError: # Queue was renamed to queue in Python 3
    import queue as Queue

import logging
import os
import re
import resource
import subprocess
import threading
import time

from .model import CORELIMIT, MEMLIMIT, TIMELIMIT, SOFTTIMELIMIT
from . import cgroups
from .resources import *
from .runexecutor import RunExecutor
from .systeminfo import *  # @UnusedWildImport
from . import util as util


WORKER_THREADS = []
STOPPED_BY_INTERRUPT = False

_BYTE_FACTOR = 1000 # byte in kilobyte

def init(config, benchmark):
    benchmark.executable = benchmark.tool.executable()
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    try:
        processes = subprocess.Popen(['ps', '-eo', 'cmd'], stdout=subprocess.PIPE).communicate()[0]
        if len(re.findall("python.*benchmark\.py", util.decode_to_string(processes))) > 1:
            logging.warning("Already running instance of this script detected. " + \
                         "Please make sure to not interfere with somebody else's benchmarks.")
    except OSError:
        pass # this does not work on Windows

def get_system_info():
    return SystemInfo()

def execute_benchmark(benchmark, output_handler):

    run_sets_executed = 0

    logging.debug("I will use {0} threads.".format(benchmark.num_of_threads))

    my_cgroups = cgroups.find_my_cgroups()

    coreAssignment = None # cores per run
    memoryAssignment = None # memory banks per run
    if CORELIMIT in benchmark.rlimits:
        if not my_cgroups.require_subsystem(cgroups.CPUSET):
            sys.exit("Cgroup subsystem cpuset is required for limiting the number of CPU cores/memory nodes.")
        coreAssignment = get_cpu_cores_per_run(benchmark.rlimits[CORELIMIT], benchmark.num_of_threads, my_cgroups)
        memoryAssignment = get_memory_banks_per_run(coreAssignment, my_cgroups)

    if MEMLIMIT in benchmark.rlimits:
        # check whether we have enough memory in the used memory banks for all runs
        memLimit = benchmark.rlimits[MEMLIMIT] * _BYTE_FACTOR * _BYTE_FACTOR # MB to Byte
        check_memory_size(memLimit, benchmark.num_of_threads, memoryAssignment, my_cgroups)

    if benchmark.num_of_threads > 1 and is_turbo_boost_enabled():
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
                output_handler.set_error('interrupted', runSet)
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
                run.walltime = value
            elif key == 'cputime':
                run.cputime = value
            elif key == 'memory':
                run.values['memUsage'] = result['memory']
            elif key == 'energy':
                for ekey, evalue in value.items():
                    run.values['energy-'+ekey] = evalue
            else:
                run.values['@' + key] = value

        if self.my_cpus:
            run.values['@cpuCores'] = self.my_cpus
        if self.my_memory_nodes:
            run.values['@memoryNodes'] = self.my_memory_nodes

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

        run.after_execution(result['exitcode'], termination_reason=result.get('terminationreason', None))
        self.output_handler.output_after_run(run)


    def stop(self):
        # asynchronous call to runexecutor,
        # the worker will stop asap, but not within this method.
        self.run_executor.stop()
