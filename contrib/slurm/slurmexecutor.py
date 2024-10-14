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
import subprocess
import sys
import tempfile
import threading
import time

from benchexec import BenchExecException, tooladapter, util
from benchexec.util import ProcessExitCode

sys.dont_write_bytecode = True  # prevent creation of .pyc files

WORKER_THREADS = []
STOPPED_BY_INTERRUPT = False


def init(config, benchmark):
    tool_locator = tooladapter.create_tool_locator(config)
    benchmark.executable = benchmark.tool.executable(tool_locator)
    try:
        benchmark.tool_version = benchmark.tool.version(benchmark.executable)
    except Exception as e:
        logging.warning("could not determine version due to error: %s", e)
        benchmark.tool_version = None


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
    global STOPPED_BY_INTERRUPT

    # get times before runSet
    walltime_before = time.monotonic()

    output_handler.output_before_run_set(runSet)

    if not benchmark.config.scratchdir:
        sys.exit("No scratchdir present. Please specify using --scratchdir <path>.")
    elif not os.path.exists(benchmark.config.scratchdir):
        os.makedirs(benchmark.config.scratchdir)
        logging.debug(f"Created scratchdir: {benchmark.config.scratchdir}")
    elif not os.path.isdir(benchmark.config.scratchdir):
        sys.exit(
            f"Scratchdir {benchmark.config.scratchdir} not a directory. Please specify using --scratchdir <path>."
        )

    os.makedirs("tmp")

    with tempfile.TemporaryDirectory(dir=benchmark.config.scratchdir) as tempdir:
        tempdir = "tmp"
        batch_lines = ["#!/bin/sh"]

        for setting in get_resource_limits(benchmark, tempdir):
            batch_lines.extend(["\n#SBATCH " + str(setting)])

        batch_lines.extend([f"\n#SBATCH --array=0-{len(runSet.runs) - 1}%{benchmark.num_of_threads}"])
        batch_lines.extend(["\n\ncase $SLURM_ARRAY_TASK_ID in"])

        # put all runs into a queue
        for i, run in enumerate(runSet.runs):
            batch_lines.extend(["\n" + str(i) + ") " + str(get_run_cli(benchmark, run.cmdline(), os.path.join(tempdir, str(i)))) + ";;"])

        batch_lines.extend(["\nesac"])

        batchfile = os.path.join(tempdir, "array.sbatch")
        with open(batchfile, "w") as f:
            f.writelines(batch_lines)

        try:
            sbatch_cmd = ["sbatch", "--wait", str(batchfile)]
            logging.debug(
                "Command to run: %s", " ".join(map(util.escape_string_shell, sbatch_cmd))
            )
            sbatch_result = subprocess.run(
                sbatch_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except KeyboardInterrupt:
            # If the run was interrupted, we ignore the result and cleanup.
            STOPPED_BY_INTERRUPT = True



        for i, run in enumerate(runSet.runs):
            run.set_result(get_run_result(benchmark, os.path.join(tempdir, str(i)), run))
            output_handler.output_after_run(run)

        # get times after runSet
        walltime_after = time.monotonic()
        usedWallTime = walltime_after - walltime_before

        if STOPPED_BY_INTERRUPT:
            output_handler.set_error("interrupted", runSet)
        output_handler.output_after_run_set(
            runSet,
            walltime=usedWallTime,
        )

jobid_pattern = re.compile(r"job (\d*) started")


def wait_for(func, timeout_sec=None, poll_interval_sec=1):
    """
    Waits until the func() returns non-None
    :param func: function to call until a value is returned
    :param timeout_sec: How much time to give up after
    :param poll_interval_sec: How frequently to check the result
    """
    start_time = time.monotonic()

    while not STOPPED_BY_INTERRUPT:
        ret = func()
        if ret is not None:
            return ret

        if timeout_sec is not None and time.monotonic() - start_time > timeout_sec:
            raise BenchExecException(
                "Timeout exceeded for waiting for job to realize it has finished. Scheduler may be failing."
            )

        time.sleep(poll_interval_sec)


def get_resource_limits(benchmark, tempdir):
    timelimit = benchmark.rlimits.cputime
    cpus = benchmark.rlimits.cpu_cores
    memory = benchmark.rlimits.memory
    os.makedirs(os.path.join(tempdir, "logs"), exist_ok=True)

    srun_timelimit_h = int(timelimit / 3600)
    srun_timelimit_m = int((timelimit % 3600) / 60)
    srun_timelimit_s = int(timelimit % 60)
    srun_timelimit = f"{srun_timelimit_h:02d}:{srun_timelimit_m:02d}:{srun_timelimit_s:02d}"

    ret = [f"--output={tempdir}/logs/%A_%a.out",
           "--time=" + str(srun_timelimit),
           "--cpus-per-task=" + str(cpus),
           "--mem=" + str(int(memory / 1000000)) + "M",
           "--threads-per-core=1",  # --use_hyperthreading=False is always given here
           "--mincpus=" + str(cpus),
           "--ntasks=1"]
    return ret


def get_run_cli(benchmark, args, tempdir):
    os.makedirs(os.path.join(tempdir, "upper"))
    os.makedirs(os.path.join(tempdir, "work"))
    cli = []

    if benchmark.config.singularity:
        cli.extend(
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
    cli.extend(
        [
            "sh",
            "-c",
            f"echo $SLURM_JOB_ID > jobid; {' '.join(map(util.escape_string_shell, args))} > log 2>&1; echo $? > exitcode",
        ]
    )

    logging.debug(
        "Command to run: %s", " ".join(map(util.escape_string_shell, cli))
    )
    return " ".join(map(util.escape_string_shell, cli))

def get_run_result(benchmark, tempdir, run):
    exitcode_file = f"{tempdir}/upper/exitcode"
    jobid_file = f"{tempdir}/upper/jobid"
    tmp_log = f"{tempdir}/upper/log"

    with open(jobid_file, "r") as f:
        jobid = int(f.read())

    raw_output, slurm_status, exit_code, cpu_time, wall_time, memory_usage = (
        run_seff(jobid) if benchmark.config.seff else run_sacct(jobid)
    )

    def get_returncode():
        if os.path.exists(exitcode_file):
            with open(exitcode_file, "r") as f:
                returncode = int(f.read())
                logging.debug("Exit code in file %s: %d", exitcode_file, returncode)
                return returncode
        else:
            return None


    if slurm_status == "COMPLETED":
        try:
            returncode = wait_for(get_returncode, 30, 2)
        except Exception as e:
            print(tempdir)
            raise e
    else:
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
    with open(run.log_file, "w+") as file:
        with open(tmp_log, "r") as log_source:
            content = log_source.read()
            file.write(f"{' '.join(map(util.escape_string_shell, run.cmdline()))}")
            file.write("\n\n\n" + "-" * 80 + "\n\n\n")
            file.write(content)
            if content == "":
                file.write("Original log file did not contain anything.")

    if benchmark.config.debug:
        with open(run.log_file + ".debug_info", "w+") as file:
            file.write(f"jobid: {jobid}\n")
            file.write(f"seff output: {str(raw_output)}\n")
            file.write(f"Parsed data: {str(ret)}\n")

    return ret


time_pattern = re.compile(r"(?:(\d+):)?(\d+):(\d+)(?:\.(\d+))?")


def get_seconds_from_time(time_str):
    time_match = time_pattern.search(time_str)
    if time_match:
        hours, minutes, seconds, millis = time_match.groups()
        if hours is None:
            hours = 0
        if minutes is None:
            minutes = 0  # realistically never None, but doesn't hurt
        if seconds is None:
            seconds = 0  # realistically never None, but doesn't hurt
        if millis is None:
            millis = 0
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def run_sacct(jobid):
    global STOPPED_BY_INTERRUPT

    sacct_command = [
        "sacct",
        "-j",
        str(jobid),
        "-n",
        "--format=State,ExitCode,TotalCpu,Elapsed,MaxVMSize",
    ]
    logging.debug(
        "Command to run: %s", " ".join(map(util.escape_string_shell, sacct_command))
    )

    def get_checked_sacct_result():
        sacct_result = subprocess.run(
            sacct_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        lines = sacct_result.stdout.splitlines()
        if len(lines) < 2:
            logging.debug("Sacct output not yet ready: %s", lines)
            return None  # jobs not yet ready
        parent_job = lines[-2].split()  # State is read from here
        child_job = lines[
            -1
        ].split()  # ExitCode, TotalCPU, Elapsed and MaxRSS read from here
        logging.debug("Sacct data: parent: %s; child: %s", parent_job, child_job)
        if parent_job[0].decode() in [
            "RUNNING",
            "PENDING",
            "REQUEUED",
            "RESIZING",
            "SUSPENDED",
            "R",
            "PD",
            "RQ",
            "RS",
            "S",
        ]:
            logging.debug(
                "Sacct output not yet ready due to state: %s", parent_job[0].decode()
            )
            return None  # not finished
        if len(child_job) < 5:
            logging.debug(
                "Sacct output not yet ready due to memory not available: %s", child_job
            )
            return None  # not finished

        stdout = sacct_result.stdout
        try:
            state = parent_job[0].decode()
        except Exception as e:
            logging.warning(
                "Could not get state due to error: %s", e
            )
            state = ""

        try:
            exitcode = child_job[1].decode().split(":")[0]
        except Exception as e:
            logging.warning(
                "Could not get exitcode due to error: %s", e
            )
            exitcode = "-1"

        try:
            totalcpu = get_seconds_from_time(child_job[2].decode())
        except Exception as e:
            logging.warning(
                "Could not get TotalCPU due to error: %s", e
            )
            totalcpu = 0

        try:
            elapsed = get_seconds_from_time(child_job[3].decode())
        except Exception as e:
            logging.warning(
                "Could not get Elapsed due to error: %s", e
            )
            elapsed = 0

        try:
            maxvmsize = float(child_job[4].decode()[:-1]) * 1000
        except Exception as e:
            logging.warning(
                "Could not get MaxVMSize due to error: %s", e
            )
            maxvmsize = 0

        return (
            stdout,
            state,
            exitcode,
            totalcpu,
            elapsed,
            maxvmsize
        )

    # sometimes `seff` needs a few extra seconds to realize the task has ended
    return wait_for(get_checked_sacct_result, 30, 2)


def run_seff(jobid):
    global STOPPED_BY_INTERRUPT

    seff_command = ["seff", str(jobid)]
    logging.debug(
        "Command to run: %s", " ".join(map(util.escape_string_shell, seff_command))
    )

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
    if STOPPED_BY_INTERRUPT:  # job was cancelled
        return

    return result.stdout, *parse_seff(str(result.stdout))


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
