# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import queue
import re
import subprocess
import sys
import threading
import time

from benchexec import benchexec, BenchExecException, tooladapter
from benchexec.util import ProcessExitCode

sys.dont_write_bytecode = True  # prevent creation of .pyc files

WORKER_THREADS = []
STOPPED_BY_INTERRUPT = False


def init(config, benchmark):
    tool_locator = tooladapter.create_tool_locator(config)
    benchmark.executable = benchmark.tool.executable(tool_locator)
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    logging.info("Using %s version %s.", benchmark.tool_name, benchmark.tool_version)


def get_system_info():
    return None


def execute_benchmark(benchmark, output_handler):
    num_of_cores = benchmark.rlimits.cpu_cores
    mem_limit = benchmark.rlimits.memory
    run_sets_executed = 0

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
            run_sets_executed += 1
            _execute_run_set(
                runSet,
                benchmark,
                output_handler,
                num_of_cores,
                mem_limit,
            )

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)


def _execute_run_set(
    runSet,
    benchmark,
    output_handler,
    num_of_cores,
    mem_limit,
):
    # get times before runSet
    walltime_before = time.monotonic()

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

    # create some workers
    for i in range(min(benchmark.num_of_threads, unfinished_runs)):
        if STOPPED_BY_INTERRUPT:
            break
        WORKER_THREADS.append(
            _Worker(benchmark, num_of_cores, mem_limit, output_handler, run_finished)
        )

    # wait until workers are finished (all tasks done or STOPPED_BY_INTERRUPT)
    for worker in WORKER_THREADS:
        worker.join()
    assert unfinished_runs == 0 or STOPPED_BY_INTERRUPT

    # get times after runSet
    walltime_after = time.monotonic()
    usedWallTime = walltime_after - walltime_before
    usedCpuTime = 1000  # TODO

    if STOPPED_BY_INTERRUPT:
        output_handler.set_error("interrupted", runSet)
    output_handler.output_after_run_set(
        runSet,
        cputime=usedCpuTime,
        walltime=usedWallTime,
    )


def stop():
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True


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

        try:
            with open(run.log_file, "w") as f:
                for i in range(6):
                    f.write(os.linesep)

            timelimit = self.benchmark.rlimits.cputime

            run_result = run_slurm(
                benchmark,
                args,
                run.log_file,
                timelimit,
                self.my_cpus,
                benchmark.rlimits.memory,
            )

        except KeyboardInterrupt:
            # If the run was interrupted, we ignore the result and cleanup.
            stop()
            try:
                if benchmark.config.debug:
                    os.rename(run.log_file, run.log_file + ".killed")
                else:
                    os.remove(run.log_file)
            except OSError:
                pass
            return 1

        run.set_result(run_result)
        print(run.status)
        self.output_handler.output_after_run(run)
        return None


def run_slurm(benchmark, args, log_file, timelimit, cpus, memory):
    srun_timelimit_h = int(timelimit / 3600)
    srun_timelimit_m = int((timelimit % 3600) / 60)
    srun_timelimit_s = int(timelimit % 60)
    srun_timelimit = f"{srun_timelimit_h}:{srun_timelimit_m}:{srun_timelimit_s}"

    mem_per_cpu = int(memory / cpus / 1000000)

    tool_command = " ".join(args)
    singularity_command = (
        f"singularity exec --no-home --contain {benchmark.config.singularity} {tool_command}"
        if benchmark.config.singularity
        else tool_command
    )
    srun_command = f"srun -t {srun_timelimit} -c {cpus} -o {log_file} --mem-per-cpu {mem_per_cpu} --threads-per-core=1 {singularity_command}"
    jobid_command = (
        f"{srun_command} 2>&1 | grep -o 'job [0-9]* queued' | grep -o '[0-9]*'"
    )
    seff_command = f"seff $({jobid_command})"

    result = subprocess.run(
        ["bash", "-c", seff_command], shell=False, stdout=subprocess.PIPE
    )

    # Runexec would populate the first 6 lines with metadata
    with open(log_file, "r+") as file:
        content = file.read()
        file.seek(0, 0)
        empty_lines = "\n" * 6
        file.write(empty_lines + content)

    exit_code, cpu_time, wall_time, memory_usage = parse_seff(str(result.stdout))

    return {
        "starttime": benchexec.util.read_local_time(),
        "walltime": wall_time,
        "cputime": cpu_time,
        "memory": memory_usage,
        "exitcode": ProcessExitCode(raw=exit_code, value=exit_code, signal=None),
    }


def parse_seff(result):
    exit_code_pattern = re.compile(r"State: COMPLETED \(exit code (\d+)\)")
    cpu_time_pattern = re.compile(r"CPU Utilized: (\d+):(\d+):(\d+)")
    wall_time_pattern = re.compile(r"Job Wall-clock time: (\d+):(\d+):(\d+)")
    memory_pattern = re.compile(r"Memory Utilized: (\d+\.\d+) MB")
    exit_code_match = exit_code_pattern.search(result)
    cpu_time_match = cpu_time_pattern.search(result)
    wall_time_match = wall_time_pattern.search(result)
    memory_match = memory_pattern.search(result)
    exit_code = int(exit_code_match.group(1)) if exit_code_match else None
    cpu_time = None
    if cpu_time_match:
        hours, minutes, seconds = map(int, cpu_time_match.groups())
        cpu_time = hours * 3600 + minutes * 60 + seconds
    wall_time = None
    if wall_time_match:
        hours, minutes, seconds = map(int, wall_time_match.groups())
        wall_time = hours * 3600 + minutes * 60 + seconds
    memory_usage = float(memory_match.group(1)) * 1000000 if memory_match else None

    return exit_code, cpu_time, wall_time, memory_usage
