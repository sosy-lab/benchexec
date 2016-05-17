# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import re
import resource
import subprocess
import sys
import threading
import time
from queue import Queue

from benchexec.model import CORELIMIT, MEMLIMIT, TIMELIMIT, SOFTTIMELIMIT
from benchexec import cgroups
from benchexec import containerexecutor
from benchexec.resources import *
from benchexec.runexecutor import RunExecutor
from benchexec import systeminfo
from benchexec import util


WORKER_THREADS = []
STOPPED_BY_INTERRUPT = False


def init(config, benchmark):
    config.containerargs = {}
    if config.container:
        if config.users is not None:
            sys.exit("Cannot use --user in combination with --container.")
        config.containerargs = containerexecutor.handle_basic_container_args(config)
        config.containerargs["use_namespaces"] = True
    elif not config.no_container:
        logging.warning(
            "Neither --container or --no-container was specified, "
            "not using containers for isolation of runs. "
            "Either specify --no-container to silence this warning, "
            "or specify --container to use containers for better isolation of runs "
            "(this will be the default starting with BenchExec 2.0). "
            "Please read https://github.com/sosy-lab/benchexec/blob/master/doc/container.md "
            "for more information.")

    try:
        processes = subprocess.Popen(['ps', '-eo', 'cmd'], stdout=subprocess.PIPE).communicate()[0]
        if len(re.findall("python.*benchmark\.py", util.decode_to_string(processes))) > 1:
            logging.warning("Already running instance of this script detected. "
                            "Please make sure to not interfere with somebody else's benchmarks.")
    except OSError:
        pass # this does not work on Windows

    benchmark.executable = benchmark.tool.executable()
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

def get_system_info():
    return systeminfo.SystemInfo()

def execute_benchmark(benchmark, output_handler):

    run_sets_executed = 0

    logging.debug("I will use %s threads.", benchmark.num_of_threads)

    if benchmark.requirements.cpu_model \
            or benchmark.requirements.cpu_cores != benchmark.rlimits.get(CORELIMIT, None) \
            or benchmark.requirements.memory != benchmark.rlimits.get(MEMLIMIT, None):
        logging.warning("Ignoring specified resource requirements in local-execution mode, "
                        "only resource limits are used.")

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
        check_memory_size(benchmark.rlimits[MEMLIMIT], benchmark.num_of_threads,
                          memoryAssignment, my_cgroups)

    if benchmark.num_of_threads > 1 and systeminfo.is_turbo_boost_enabled():
        logging.warning("Turbo boost of CPU is enabled. "
                        "Starting more than one benchmark in parallel affects the CPU frequency "
                        "and thus makes the performance unreliable.")

    if benchmark.num_of_threads > 1 and benchmark.config.users:
        if len(benchmark.config.users) == 1:
            logging.warning(
                'Executing multiple parallel benchmarks under same user account. '
                'Consider specifying multiple user accounts for increased separation of runs.')
            benchmark.config.users = [benchmark.config.users[0] for i in range(benchmark.num_of_threads)]
        elif len(benchmark.config.users) < benchmark.num_of_threads:
            sys.exit('Distributing parallel runs to different user accounts was requested, but not enough accounts were given. Please specify {} user accounts, or only one account.'.format(benchmark.num_of_threads))
        elif len(benchmark.config.users) != len(set(benchmark.config.users)):
            sys.exit('Same user account was specified multiple times, please specify {} separate accounts, or only one account.'.format(benchmark.num_of_threads))

    throttle_check = systeminfo.CPUThrottleCheck()
    swap_check = systeminfo.SwapCheck()

    # iterate over run sets
    for runSet in benchmark.run_sets:

        if STOPPED_BY_INTERRUPT:
            break

        if not runSet.should_be_executed():
            output_handler.output_for_skipping_run_set(runSet)

        elif not runSet.runs:
            output_handler.output_for_skipping_run_set(runSet, "because it has no files")

        else:
            run_sets_executed += 1
            # get times before runSet
            ruBefore = resource.getrusage(resource.RUSAGE_CHILDREN)
            walltime_before = util.read_monotonic_time()
            energyBefore = util.measure_energy()

            output_handler.output_before_run_set(runSet)

            # put all runs into a queue
            for run in runSet.runs:
                _Worker.working_queue.put(run)

            # create some workers
            for i in range(benchmark.num_of_threads):
                cores = coreAssignment[i] if coreAssignment else None
                memBanks = memoryAssignment[i] if memoryAssignment else None
                user = benchmark.config.users[i] if benchmark.config.users else None
                WORKER_THREADS.append(_Worker(benchmark, cores, memBanks, user, output_handler))

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
            walltime_after = util.read_monotonic_time()
            energy = util.measure_energy(energyBefore)
            usedWallTime = walltime_after - walltime_before
            ruAfter = resource.getrusage(resource.RUSAGE_CHILDREN)
            usedCpuTime = (ruAfter.ru_utime + ruAfter.ru_stime) \
                        - (ruBefore.ru_utime + ruBefore.ru_stime)

            if STOPPED_BY_INTERRUPT:
                output_handler.set_error('interrupted', runSet)
            output_handler.output_after_run_set(runSet, cputime=usedCpuTime, walltime=usedWallTime, energy=energy)

            for worker in WORKER_THREADS:
                worker.cleanup()

    if throttle_check.has_throttled():
        logging.warning('CPU throttled itself during benchmarking due to overheating. '
                        'Benchmark results are unreliable!')
    if swap_check.has_swapped():
        logging.warning('System has swapped during benchmarking. '
                        'Benchmark results are unreliable!')

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

    return 0


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
    working_queue = Queue()

    def __init__(self, benchmark, my_cpus, my_memory_nodes, my_user, output_handler):
        threading.Thread.__init__(self) # constuctor of superclass
        self.benchmark = benchmark
        self.my_cpus = my_cpus
        self.my_memory_nodes = my_memory_nodes
        self.output_handler = output_handler
        self.run_executor = RunExecutor(user=my_user, **benchmark.config.containerargs)
        self.setDaemon(True)

        self.start()


    def run(self):
        while not _Worker.working_queue.empty() and not STOPPED_BY_INTERRUPT:
            currentRun = _Worker.working_queue.get_nowait()
            try:
                logging.debug('Executing run "%s"', currentRun.identifier)
                self.execute(currentRun)
                logging.debug('Finished run "%s"', currentRun.identifier)
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

        memlimit = benchmark.rlimits.get(MEMLIMIT)

        args = run.cmdline()
        logging.debug('Command line of run is %s', args)
        run_result = \
            self.run_executor.execute_run(
                args,
                output_filename=run.log_file,
                output_dir=run.result_files_folder,
                result_files_patterns=benchmark.result_files_patterns,
                hardtimelimit=benchmark.rlimits.get(TIMELIMIT),
                softtimelimit=benchmark.rlimits.get(SOFTTIMELIMIT),
                cores=self.my_cpus,
                memory_nodes=self.my_memory_nodes,
                memlimit=memlimit,
                environments=benchmark.environment(),
                workingDir=benchmark.working_directory(),
                maxLogfileSize=benchmark.config.maxLogfileSize)

        if self.run_executor.PROCESS_KILLED:
            # If the run was interrupted, we ignore the result and cleanup.
            try:
                if benchmark.config.debug:
                    os.rename(run.log_file, run.log_file + ".killed")
                else:
                    os.remove(run.log_file)
            except OSError:
                pass
            return 1

        if self.my_cpus:
            run_result['cpuCores'] = self.my_cpus
        if self.my_memory_nodes:
            run_result['memoryNodes'] = self.my_memory_nodes

        run.set_result(run_result)
        self.output_handler.output_after_run(run)


    def stop(self):
        # asynchronous call to runexecutor,
        # the worker will stop asap, but not within this method.
        self.run_executor.stop()

    def cleanup(self):
        self.run_executor.check_for_new_files_in_home()
