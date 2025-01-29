# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2024 Levente Bajczi
# SPDX-FileCopyrightText: Critical Systems Research Group
# SPDX-FileCopyrightText: Budapest University of Technology and Economics <https://www.ftsrg.mit.bme.hu>
#
# SPDX-License-Identifier: Apache-2.0
import itertools
import logging
import os
import queue
import re
import shlex
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


def get_system_info():
    return None


def execute_benchmark(benchmark, output_handler):
    if benchmark.config.use_hyperthreading:
        sys.exit(
            "SLURM can only work properly without hyperthreading enabled, by passing the --no-hyperthreading option. See README.md for details."
        )

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
    for _ in range(min(benchmark.num_of_threads, unfinished_runs)):
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

        args = run.cmdline()
        logging.debug("Command line of run is %s", args)

        try:
            attempts = 0
            while True:
                run_result = run_slurm(
                    self.benchmark,
                    args,
                    run.log_file,
                )
                if (
                    "terminationreason" not in run_result
                    or not run_result["terminationreason"] == "killed"
                    or (attempts >= self.benchmark.config.retry >= 0)
                    or STOPPED_BY_INTERRUPT
                ):
                    break
                attempts += 1
                time.sleep(1)  # as to not overcrowd a failing scheduler
                logging.debug(
                    "Retrying after %d attempts, limit: %d",
                    attempts,
                    self.benchmark.config.retry,
                )

        except KeyboardInterrupt:
            # If the run was interrupted, we ignore the result and cleanup.
            stop()

        if STOPPED_BY_INTERRUPT:
            try:
                if self.benchmark.config.debug:
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


def wait_for(func, timeout_sec=None, poll_interval_sec=1):
    """
    Waits until the func() returns non-None
    :param func: function to call until a value is returned
    :param timeout_sec: How much time to give up after
    :param poll_interval_sec: How frequently to check the result
    """
    start_time = time.monotonic()

    while True:
        ret = func()
        if ret is not None:
            return ret

        if timeout_sec is not None and time.monotonic() - start_time > timeout_sec:
            raise BenchExecException(
                "Timeout exceeded for waiting for job to realize it has finished. Scheduler may be failing."
            )

        time.sleep(poll_interval_sec)


def run_slurm(benchmark, args, log_file):
    timelimit = benchmark.rlimits.cputime
    cpus = benchmark.rlimits.cpu_cores
    memory = benchmark.rlimits.memory

    srun_timelimit_h = int(timelimit / 3600)
    srun_timelimit_m = int((timelimit % 3600) / 60)
    srun_timelimit_s = int(timelimit % 60)
    srun_timelimit = f"{srun_timelimit_h}:{srun_timelimit_m}:{srun_timelimit_s}"

    if not benchmark.config.scratchdir:
        sys.exit("No scratchdir present. Please specify using --scratchdir <path>.")
    elif not os.path.exists(benchmark.config.scratchdir):
        os.makedirs(benchmark.config.scratchdir)
        logging.debug(f"Created scratchdir: {benchmark.config.scratchdir}")
    elif not os.path.isdir(benchmark.config.scratchdir):
        sys.exit(
            f"Scratchdir {benchmark.config.scratchdir} not a directory. Please specify using --scratchdir <path>."
        )

    with tempfile.TemporaryDirectory(dir=benchmark.config.scratchdir) as tempdir:
        tmp_log = os.path.join(tempdir, "log")

        os.makedirs(os.path.join(tempdir, "upper"))
        os.makedirs(os.path.join(tempdir, "work"))

        exitcode_file = f"{tempdir}/upper/exitcode"

        srun_command = [
            "srun",
            "--quit-on-interrupt",
            "-t",
            str(srun_timelimit),
            "-c",
            str(cpus),
            "--mem",
            str(int(memory / 1000000)) + "M",
            "--threads-per-core=1",  # --use_hyperthreading=False is always given here
            "--ntasks=1",
        ]
        if benchmark.config.singularity:
            srun_command.extend(
                [
                    "singularity",
                    "exec",
                    "-B",
                    "./:/lower",
                    "--no-home",
                    "-B",
                    f"{tempdir}:/overlay",
                    "--fusemount",
                    f"container:fuse-overlayfs -o lowerdir=/lower -o upperdir=/overlay/upper -o workdir=/overlay/work /home/{os.getlogin()}",
                    benchmark.config.singularity,
                ]
            )
        srun_command.extend(
            [
                "sh",
                "-c",
                f"{shlex.join(args)}; echo $? > exitcode",
            ]
        )

        logging.debug("Command to run: %s", shlex.join(srun_command))
        jobid = None
        while jobid is None:
            with open(tmp_log, "w") as tmp_log_f:
                subprocess.run(
                    srun_command,
                    stdout=tmp_log_f,
                    stderr=subprocess.STDOUT,
                )

            # we try to read back the log, in the first two lines there should be the jobid
            with open(tmp_log, "r") as tmp_log_f:
                for line in itertools.islice(tmp_log_f, 2):
                    jobid_match = jobid_pattern.search(line)
                    if jobid_match:
                        jobid = int(jobid_match.group(1))
                        break

        seff_command = ["seff", str(jobid)]
        logging.debug("Command to run: %s", shlex.join(seff_command))

        def get_checked_seff_result():
            seff_result = subprocess.run(
                seff_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if "exit code" in str(seff_result.stdout):
                return seff_result
            else:
                return None

        # sometimes `seff` needs a few extra seconds to realize the task has ended
        result = wait_for(get_checked_seff_result, 30, 2)

        slurm_status, exit_code, cpu_time, wall_time, memory_usage = parse_seff(
            str(result.stdout)
        )

        if os.path.exists(exitcode_file):
            with open(exitcode_file, "r") as f:
                returncode = int(f.read())
                logging.debug("Exit code in file %s: %d", exitcode_file, returncode)
        else:
            assert (
                slurm_status != "COMPLETED"
            ), "Should never happen: exit code not found, but task was reported COMPLETED."
            logging.debug("Exit code not found in file: %s", exitcode_file)
            returncode = 0

        ret = {
            "walltime": wall_time,
            "cputime": cpu_time,
            "memory": memory_usage,
            "exitcode": ProcessExitCode.create(value=returncode),
        }

        if slurm_status != "COMPLETED":
            ret["terminationreason"] = {
                "OUT_OF_MEMORY": "memory",
                "OUT_OF_ME+": "memory",
                "TIMEOUT": "cputime",
                "ERROR": "failed",
                "FAILED": "killed",
                "CANCELLED": "killed",
            }.get(slurm_status, slurm_status)

        # Runexec would populate the first 6 lines with metadata
        with open(log_file, "w+") as file:
            with open(tmp_log, "r") as log_source:
                content = log_source.read()
                file.write(shlex.join(args))
                file.write("\n\n\n" + "-" * 80 + "\n\n\n")
                file.write(content)
                if content == "":
                    file.write("Original log file did not contain anything.")

        if benchmark.config.debug:
            with open(log_file + ".debug_info", "w+") as file:
                file.write(f"jobid: {jobid}\n")
                file.write(f"seff output: {str(result.stdout)}\n")
                file.write(f"Parsed data: {str(ret)}\n")

        return ret


exit_code_pattern = re.compile(r"State: ([A-Z-_]*) \(exit code (\d+)\)")
cpu_time_pattern = re.compile(r"CPU Utilized: (\d+):(\d+):(\d+)")
wall_time_pattern = re.compile(r"Job Wall-clock time: (\d+):(\d+):(\d+)")
memory_pattern = re.compile(r"Memory Utilized: (\d+\.\d+) MB")


def parse_seff(result):
    logging.debug(f"Got output from seff: {result}")
    exit_code_match = exit_code_pattern.search(result)
    cpu_time_match = cpu_time_pattern.search(result)
    wall_time_match = wall_time_pattern.search(result)
    memory_match = memory_pattern.search(result)
    exit_code = None
    if exit_code_match:
        slurm_status = str(exit_code_match.group(1))
        exit_code = int(exit_code_match.group(2))
    else:
        slurm_status = "ERROR"
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

    return slurm_status, exit_code, cpu_time, wall_time, memory_usage
