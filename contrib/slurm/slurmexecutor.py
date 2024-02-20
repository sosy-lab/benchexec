# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2024 Levente Bajczi
# SPDX-FileCopyrightText: Critical Systems Research Group
# SPDX-FileCopyrightText: Budapest University of Technology and Economics <https://www.ftsrg.mit.bme.hu>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time

from benchexec import BenchExecException, tooladapter
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

    assert (
        not benchmark.config.use_hyperthreading
    ), "SLURM can only work properly without hyperthreading enabled. See README.md for details."

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
            )

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)


def _execute_run_set(
    runSet,
    benchmark,
    output_handler,
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
        WORKER_THREADS.append(_Worker(benchmark, output_handler, run_finished))

    # wait until workers are finished (all tasks done or STOPPED_BY_INTERRUPT)
    for worker in WORKER_THREADS:
        worker.join()
    assert unfinished_runs == 0 or STOPPED_BY_INTERRUPT

    # get times after runSet
    walltime_after = time.monotonic()
    usedWallTime = walltime_after - walltime_before

    if STOPPED_BY_INTERRUPT:
        output_handler.set_error("interrupted", runSet)
    output_handler.output_after_run_set(
        runSet,
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

    def __init__(self, benchmark, output_handler, run_finished_callback):
        threading.Thread.__init__(self)  # constuctor of superclass
        self.run_finished_callback = run_finished_callback
        self.benchmark = benchmark
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

            run_result = run_slurm(
                benchmark,
                args,
                run.log_file,
            )

        except KeyboardInterrupt:
            # If the run was interrupted, we ignore the result and cleanup.
            stop()

        if STOPPED_BY_INTERRUPT:
            try:
                if benchmark.config.debug:
                    os.rename(run.log_file, run.log_file + ".killed")
                else:
                    os.remove(run.log_file)
            except OSError:
                pass
            return 1

        run.set_result(run_result)
        self.output_handler.output_after_run(run)
        return None


jobid_pattern = re.compile(r"job (\d*) queued")


def run_slurm(benchmark, args, log_file):
    timelimit = benchmark.rlimits.cputime
    cpus = benchmark.rlimits.cpu_cores
    memory = benchmark.rlimits.memory

    srun_timelimit_h = int(timelimit / 3600)
    srun_timelimit_m = int((timelimit % 3600) / 60)
    srun_timelimit_s = int(timelimit % 60)
    srun_timelimit = f"{srun_timelimit_h}:{srun_timelimit_m}:{srun_timelimit_s}"

    mem_per_cpu = int(memory / cpus / 1000000)

    assert benchmark.config.scratchdir and os.path.exists(benchmark.config.scratchdir)

    with tempfile.TemporaryDirectory(dir=benchmark.config.scratchdir) as tempdir:

        os.makedirs(os.path.join(tempdir, "upper"))
        os.makedirs(os.path.join(tempdir, "work"))

        tool_command = " ".join(args)
        singularity_command = (
            f"singularity exec "
            f'-B "$PWD":/lower --no-home '
            f'-B "{tempdir}":/overlay '
            f'--fusemount "container:fuse-overlayfs -o lowerdir=/lower -o upperdir=/overlay/upper -o workdir=/overlay/work ""$HOME""" '
            f"{benchmark.config.singularity} {tool_command}"
            if benchmark.config.singularity
            else tool_command
        )
        srun_command = (
            f"srun "
            f"-t {srun_timelimit} "
            f"-c {cpus} "
            f"-o {log_file} "
            f"--mem-per-cpu {mem_per_cpu} "
            f"--threads-per-core=1 " # --use_hyperthreading=False is always given here
            f"--ntasks=1 "
            f"{singularity_command}"
        )
        srun_result = subprocess.run(
            ["bash", "-c", srun_command],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logging.debug(
            "srun: returncode: %d, output: %s",
            srun_result.returncode,
            srun_result.stdout,
        )
        jobid_match = jobid_pattern.search(str(srun_result.stdout))
        if jobid_match:
            jobid = int(jobid_match.group(1))
        else:
            logging.debug("Jobid not found in stderr, aborting")
            stop()
            return -1

        seff_command = f"seff {jobid}"
        logging.debug("Command to run: %s", seff_command)
        result = subprocess.run(
            ["bash", "-c", seff_command],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    # Runexec would populate the first 6 lines with metadata
    with open(log_file, "r+") as file:
        content = file.read()
        file.seek(0, 0)
        empty_lines = "\n" * 6
        file.write(empty_lines + content)

    exit_code, cpu_time, wall_time, memory_usage = parse_seff(str(result.stdout))

    return {
        "walltime": wall_time,
        "cputime": cpu_time,
        "memory": memory_usage,
        "exitcode": ProcessExitCode.create(value=exit_code),
    }


exit_code_pattern = re.compile(r"exit code (\d+)")
cpu_time_pattern = re.compile(r"CPU Utilized: (\d+):(\d+):(\d+)")
wall_time_pattern = re.compile(r"Job Wall-clock time: (\d+):(\d+):(\d+)")
memory_pattern = re.compile(r"Memory Utilized: (\d+\.\d+) MB")


def parse_seff(result):
    logging.debug(f"Got output from seff: {result}")
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

    logging.debug(
        f"Exit code: {exit_code}, memory usage: {memory_usage}, walltime: {wall_time}, cpu time: {cpu_time}"
    )

    return exit_code, cpu_time, wall_time, memory_usage
