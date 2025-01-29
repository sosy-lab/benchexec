# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import queue
import resource
import sys
import threading
import time

from benchexec import BenchExecException
from benchexec.cgroups import Cgroups
from benchexec import containerexecutor
from benchexec import resources
from benchexec.runexecutor import RunExecutor
from benchexec.pqos import Pqos
from benchexec import systeminfo
from benchexec import tooladapter
from benchexec import util
from benchexec.intel_cpu_energy import EnergyMeasurement


WORKER_THREADS = []
STOPPED_BY_INTERRUPT = False


def init(config, benchmark):
    config.containerargs = {}
    if config.container:
        config.containerargs = containerexecutor.handle_basic_container_args(config)
        if config.containerargs["container_tmpfs"] and (
            config.filesCountLimit or config.filesSizeLimit
        ):
            sys.exit(
                "Files-count limit and files-size limit are not supported "
                "if tmpfs is used in container. "
                "Use --no-tmpfs to make these limits work or disable them "
                "(typically they are unnecessary if a tmpfs is used)."
            )
    config.containerargs["use_namespaces"] = config.container

    tool_locator = tooladapter.create_tool_locator(config)
    benchmark.executable = benchmark.tool.executable(tool_locator)
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)


def get_system_info():
    return systeminfo.SystemInfo()


def execute_benchmark(benchmark, output_handler):
    logging.debug("I will use %s threads.", benchmark.num_of_threads)

    if (
        benchmark.requirements.cpu_model
        or benchmark.requirements.cpu_cores != benchmark.rlimits.cpu_cores
        or benchmark.requirements.memory != benchmark.rlimits.memory
    ):
        logging.warning(
            "Ignoring specified resource requirements in local-execution mode, "
            "only resource limits are used."
        )

    my_cgroups = Cgroups.initialize()
    required_cgroups = set()

    coreAssignment = None  # cores per run
    memoryAssignment = None  # memory banks per run
    cpu_packages = None
    pqos = Pqos(show_warnings=True)  # The pqos class instance for cache allocation
    pqos.reset_monitoring()

    if benchmark.rlimits.cpu_cores:
        if not my_cgroups.require_subsystem(my_cgroups.CPUSET):
            required_cgroups.add(my_cgroups.CPUSET)
            logging.error(
                "Cgroup subsystem cpuset is required "
                "for limiting the number of CPU cores/memory nodes."
            )
        else:
            coreAssignment = resources.get_cpu_cores_per_run(
                benchmark.rlimits.cpu_cores,
                benchmark.num_of_threads,
                benchmark.config.use_hyperthreading,
                my_cgroups,
                benchmark.config.coreset,
            )
            pqos.allocate_l3ca(coreAssignment)
            memoryAssignment = resources.get_memory_banks_per_run(
                coreAssignment, my_cgroups
            )
            cpu_packages = {
                resources.get_cpu_package_for_core(core)
                for cores_of_run in coreAssignment
                for core in cores_of_run
            }
    elif benchmark.config.coreset:
        sys.exit(
            "Please limit the number of cores first if you also want to limit the set of available cores."
        )

    if benchmark.rlimits.memory:
        if not my_cgroups.require_subsystem(my_cgroups.MEMORY):
            required_cgroups.add(my_cgroups.MEMORY)
            logging.error("Cgroup subsystem memory is required for memory limit.")
        else:
            # check whether we have enough memory in the used memory banks for all runs
            resources.check_memory_size(
                benchmark.rlimits.memory,
                benchmark.num_of_threads,
                memoryAssignment,
                my_cgroups,
            )

    if benchmark.rlimits.cputime:
        if not my_cgroups.require_subsystem(my_cgroups.CPU):
            required_cgroups.add(my_cgroups.CPU)
            logging.error("Cgroup subsystem cpuacct is required for cputime limit.")

    my_cgroups.handle_errors(required_cgroups)

    if benchmark.num_of_threads > 1 and systeminfo.is_turbo_boost_enabled():
        logging.warning(
            "Turbo boost of CPU is enabled. "
            "Starting more than one benchmark in parallel affects the CPU frequency "
            "and thus makes the performance unreliable."
        )

    throttle_check = systeminfo.CPUThrottleCheck()
    swap_check = systeminfo.SwapCheck()

    # iterate over run sets
    for runSet in benchmark.run_sets:
        if STOPPED_BY_INTERRUPT:
            break

        if not runSet.should_be_executed():
            output_handler.output_for_skipping_run_set(runSet)

        elif not runSet.runs:
            output_handler.output_for_skipping_run_set(
                runSet, "because it has no files"
            )

        else:
            _execute_run_set(
                runSet,
                benchmark,
                output_handler,
                coreAssignment,
                memoryAssignment,
                cpu_packages,
            )

    if throttle_check.has_throttled():
        logging.warning(
            "CPU throttled itself during benchmarking due to overheating. "
            "Benchmark results are unreliable!"
        )
    if swap_check.has_swapped():
        logging.warning(
            "System has swapped during benchmarking. "
            "Benchmark results are unreliable!"
        )
    pqos.reset_resources()
    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

    return 0


def _execute_run_set(
    runSet, benchmark, output_handler, coreAssignment, memoryAssignment, cpu_packages
):
    # get times before runSet
    energy_measurement = EnergyMeasurement.create_if_supported()
    ruBefore = resource.getrusage(resource.RUSAGE_CHILDREN)
    walltime_before = time.monotonic()
    if energy_measurement:
        energy_measurement.start()

    output_handler.output_before_run_set(runSet)

    # put all runs into a queue
    for run in runSet.runs:
        _Worker.working_queue.put(run)

    # keep a counter of unfinished runs for the below assertion
    unfinished_runs = len(runSet.runs)
    unfinished_runs_lock = threading.Lock()

    def run_finished():
        nonlocal unfinished_runs
        with unfinished_runs_lock:
            unfinished_runs -= 1

    if not containerexecutor.NATIVE_CLONE_CALLBACK_SUPPORTED:
        logging.debug(
            "Using sys.setswitchinterval() workaround for #435 in container "
            "mode because native callback is not available."
        )
        py_switch_interval = sys.getswitchinterval()
        sys.setswitchinterval(1000)

    # create some workers
    for i in range(min(benchmark.num_of_threads, unfinished_runs)):
        if STOPPED_BY_INTERRUPT:
            break
        cores = coreAssignment[i] if coreAssignment else None
        memBanks = memoryAssignment[i] if memoryAssignment else None
        WORKER_THREADS.append(
            _Worker(benchmark, cores, memBanks, output_handler, run_finished)
        )

    # wait until workers are finished (all tasks done or STOPPED_BY_INTERRUPT)
    for worker in WORKER_THREADS:
        worker.join()
    assert unfinished_runs == 0 or STOPPED_BY_INTERRUPT

    # get times after runSet
    walltime_after = time.monotonic()
    energy = energy_measurement.stop() if energy_measurement else None
    usedWallTime = walltime_after - walltime_before
    ruAfter = resource.getrusage(resource.RUSAGE_CHILDREN)
    usedCpuTime = (ruAfter.ru_utime + ruAfter.ru_stime) - (
        ruBefore.ru_utime + ruBefore.ru_stime
    )
    if energy and cpu_packages:
        energy = {pkg: energy[pkg] for pkg in energy if pkg in cpu_packages}

    if not containerexecutor.NATIVE_CLONE_CALLBACK_SUPPORTED:
        sys.setswitchinterval(py_switch_interval)

    if STOPPED_BY_INTERRUPT:
        output_handler.set_error("interrupted", runSet)
    output_handler.output_after_run_set(
        runSet, cputime=usedCpuTime, walltime=usedWallTime, energy=energy
    )


def stop():
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True

    # kill running jobs
    util.printOut("killing subprocesses...")
    for worker in WORKER_THREADS:
        worker.stop()


class _Worker(threading.Thread):
    """
    A Worker is a deamonic thread, that takes jobs from the working_queue and runs them.
    """

    working_queue = queue.Queue()

    def __init__(
        self, benchmark, my_cpus, my_memory_nodes, output_handler, run_finished_callback
    ):
        threading.Thread.__init__(self)  # constuctor of superclass
        self.run_finished_callback = run_finished_callback
        self.benchmark = benchmark
        self.my_cpus = my_cpus
        self.my_memory_nodes = my_memory_nodes
        self.output_handler = output_handler
        self.run_executor = RunExecutor(**benchmark.config.containerargs)
        self.setDaemon(True)

        self.start()

    def run(self):
        while not STOPPED_BY_INTERRUPT:
            try:
                currentRun = _Worker.working_queue.get_nowait()
            except queue.Empty:
                return

            try:
                logging.debug('Executing run "%s"', currentRun.identifier)
                self.execute(currentRun)
                logging.debug('Finished run "%s"', currentRun.identifier)
            except SystemExit as e:
                logging.critical(e)
            except BenchExecException as e:
                logging.critical(e)
            except BaseException:
                logging.exception("Exception during run execution")
            self.run_finished_callback()
            _Worker.working_queue.task_done()

    def execute(self, run):
        """
        This function executes the tool with a sourcefile with options.
        It also calls functions for output before and after the run.
        """
        self.output_handler.output_before_run(run)
        benchmark = self.benchmark

        args = run.cmdline()
        logging.debug("Command line of run is %s", args)
        pqos = Pqos()
        if self.my_cpus:
            pqos.start_monitoring([self.my_cpus])
        run_result = self.run_executor.execute_run(
            args,
            output_filename=run.log_file,
            output_dir=run.result_files_folder,
            result_files_patterns=benchmark.result_files_patterns,
            hardtimelimit=benchmark.rlimits.cputime_hard,
            softtimelimit=benchmark.rlimits.cputime,
            walltimelimit=benchmark.rlimits.walltime,
            cores=self.my_cpus,
            memory_nodes=self.my_memory_nodes,
            memlimit=benchmark.rlimits.memory,
            environments=benchmark.environment(),
            workingDir=benchmark.working_directory(),
            maxLogfileSize=benchmark.config.maxLogfileSize,
            files_count_limit=benchmark.config.filesCountLimit,
            files_size_limit=benchmark.config.filesSizeLimit,
        )
        mon_data = pqos.stop_monitoring()
        run_result.update(mon_data)
        if not mon_data:
            logging.debug(
                "Could not monitor cache and memory bandwidth events for run: %s",
                run.identifier,
            )

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
            run_result["cpuCores"] = self.my_cpus
        if self.my_memory_nodes:
            run_result["memoryNodes"] = self.my_memory_nodes

        run.set_result(run_result)
        self.output_handler.output_after_run(run)
        return None

    def stop(self):
        # asynchronous call to runexecutor,
        # the worker will stop asap, but not within this method.
        self.run_executor.stop()
