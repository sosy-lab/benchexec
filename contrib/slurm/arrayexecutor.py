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


sbatch_pattern = re.compile(r"Submitted batch job (\d+)")


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

    # get times after runSet
    walltime_after = time.monotonic()
    usedWallTime = walltime_after - walltime_before

    for i in range(0, len(runSet.runs), benchmark.config.batch_size):
        if not STOPPED_BY_INTERRUPT:
            chunk = runSet.runs[i:min(i + benchmark.config.batch_size, len(runSet.runs))]
            execute_batch(chunk, benchmark, output_handler)

    if STOPPED_BY_INTERRUPT:
        output_handler.set_error("interrupted", runSet)

    output_handler.output_after_run_set(
        runSet,
        walltime=usedWallTime,
    )


def get_cpu_cmd(concurrency_factor, cores):
    get_cpus = ("cpus=($(scontrol show job -d \"$SLURM_JOB_ID\" | grep -o 'CPU_IDs=[^ ]*' | "
                "awk -F= ' { print $2 } ' | head -n1 | "
                "awk -F, ' { for (i = 1; i <= NF; i++ ) { if ($i ~ /-/) "
                "{ split($i, range, \"-\"); for (j = range[1]; j <= range[2]; j++  ) { print j } } "
                "else { print $i } } }'))")
    for i in range(concurrency_factor):
        get_cpus = get_cpus + f"\nexport cpuset{i}=$(IFS=,; echo \"${{cpus[*]:{i * cores}:{cores}}}\")"
    return get_cpus


def lock_cpu_cmds(concurrency_factor, tempdir, bin):
    lock_cpus = "CPUSET=\"\"; while ! {"
    for i in range(concurrency_factor):
        lock_cpus = lock_cpus + f" {{ mkdir {tempdir}/cpuset_{bin}_{i} 2>/dev/null && cpuset={i} && CPUSET=\"$cpuset{i}\"; }}"
        if (i == concurrency_factor - 1):
            lock_cpus = lock_cpus + "; }; do sleep 1; done"
        else:
            lock_cpus = lock_cpus + " ||"
    unlock_cpus = f"rm -r {tempdir}/cpuset_{bin}_$cpuset"
    return lock_cpus, unlock_cpus


def execute_batch(
        runs,
        benchmark,
        output_handler,
):
    global STOPPED_BY_INTERRUPT
    number_of_bins = int(len(runs) / benchmark.config.aggregation_factor) + 1

    use_concurrency = benchmark.config.concurrency_factor != 1
    if use_concurrency:
        get_cpus = get_cpu_cmd(benchmark.config.concurrency_factor, benchmark.rlimits.cpu_cores)

    with tempfile.TemporaryDirectory(dir=benchmark.config.scratchdir) as tempdir:
        batch_lines = ["#!/bin/bash"]

        for setting in get_resource_limits(benchmark, tempdir):
            batch_lines.extend(["\n#SBATCH " + str(setting)])

        batch_lines.extend([f"\n#SBATCH --array=0-{number_of_bins - 1}%{benchmark.num_of_threads}"])
        batch_lines.extend(["\n\nTMPDIR=$(mktemp -d)"])

        bins = {}
        # put all runs into a queue
        for i, run in enumerate(runs):
            if i % number_of_bins not in bins:
                bins[i % number_of_bins] = []
            bins[i % number_of_bins].append((i, run))

        if use_concurrency:
            batch_lines.extend(["\n\n" + get_cpus])
            batch_lines.extend(["\n\ncase $SLURM_ARRAY_TASK_ID in"])
            for bin in bins:
                lock_cpus, unlock_cpus = lock_cpu_cmds(benchmark.config.concurrency_factor, tempdir, bin)
                batch_lines.extend(["\n" + str(bin) + ") "])
                taskfile_name = f"bin{str(bin)}.tasks"
                taskfile = os.path.join(tempdir, taskfile_name)
                with open(taskfile, "w") as f:
                    task_lines = []
                    for (i, run) in bins[bin]:
                        task_lines.extend(
                            [lock_cpus + " && " + str(get_run_cli(benchmark, run.cmdline(), os.path.join("$TMPDIR", str(i)), os.path.join(tempdir, str(i)))) + "; " + unlock_cpus + "\n"])
                    f.writelines(task_lines)
                batch_lines.extend(f"\n while read -r x; do /bin/sh -c \"$x\" & done < {taskfile}")
                batch_lines.extend("\n wait")
                batch_lines.extend(["\n;;"])
        else:
            batch_lines.extend(["\n\ncase $SLURM_ARRAY_TASK_ID in"])
            for bin in bins:
                batch_lines.extend(["\n" + str(bin) + ") "])
                for (i, run) in bins[bin]:
                    batch_lines.extend(
                        ["\n  " + str(get_run_cli(benchmark, run.cmdline(), os.path.join("$TMPDIR", str(i)), os.path.join(tempdir, str(i))))])
                batch_lines.extend(["\n;;"])

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
            STOPPED_BY_INTERRUPT = True

        if STOPPED_BY_INTERRUPT:
            logging.debug(f"Canceling sbatch job if already started")
            if sbatch_result and sbatch_result.stdout:
                for line in sbatch_result.stdout.splitlines():
                    jobid_match = sbatch_pattern.search(str(line))
                    if jobid_match:
                        jobid = int(jobid_match.group(1))
                        logging.debug(f"Canceling sbatch job #{jobid}")
                        subprocess.run(["scancel", str(jobid)])

        for i, run in enumerate(runs):
            try:
                run.set_result(get_run_result(os.path.join(tempdir, str(i)), run))
                output_handler.output_after_run(run)
            except:
                logging.debug(f"Output missing for run #{i}")


def stop():
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True


def get_resource_limits(benchmark, tempdir):
    timelimit = benchmark.rlimits.cputime * benchmark.config.aggregation_factor * 2  # safe overapprox
    cpus = benchmark.rlimits.cpu_cores * benchmark.config.concurrency_factor
    memory = benchmark.rlimits.memory * benchmark.config.concurrency_factor * 1.5  # so that runexec catches the OOM, not SLURM
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


def get_run_cli(benchmark, args, tempdir, resultdir):
    os.makedirs(resultdir)
    cli = []
    runexec = ["runexec", "--no-container"]
    if benchmark.rlimits.cputime_hard:
        runexec.extend(["--timelimit", str(benchmark.rlimits.cputime_hard)])
    if benchmark.rlimits.cputime:
        runexec.extend(["--softtimelimit", str(benchmark.rlimits.cputime)])
    if benchmark.rlimits.walltime:
        runexec.extend(["--walltimelimit", str(benchmark.rlimits.walltime)])
    if benchmark.config.concurrency_factor != 1:
        runexec.extend(["--cores", "$CPUSET"])
    if benchmark.rlimits.memory:
        runexec.extend(["--memlimit", str(benchmark.rlimits.memory)])

    args = [*runexec, "--", *args]

    if benchmark.config.singularity:
        cli.extend(
            [
                "singularity",
                "exec",
                "-B",
                "/sys/fs/cgroup:/sys/fs/cgroup",
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
            f"touch started; "
            f"{' '.join(map(util.escape_string_shell, ['echo', 'Running command: ', *args]))}; "
            f"{' '.join(map(util.escape_string_shell, args))} 2>&1 | tee log; "
            f"touch ended"
        ]
    )

    cli = " ".join(map(util.escape_string_shell, cli))
    cli = cli.replace("'\"'\"'$CPUSET'\"'\"'", "'$CPUSET'")
    cli = cli.replace("'$TMPDIR", "\"$TMPDIR").replace(":/overlay'", ":/overlay\"")
    cli = f"mkdir -p {tempdir}/{{upper,work}}; {cli}; mv {tempdir}/upper/* {resultdir}/; rm -r {tempdir}"
    logging.debug("Command to run: %s", cli)

    return cli


def get_run_result(tempdir, run):
    runexec_log = f"{tempdir}/log"
    tmp_log = f"{tempdir}/output.log"

    data_dict = {}
    with open(runexec_log, "r") as file:
        for line in file:
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                data_dict[key.strip()] = value.strip()

    ret = {}
    if "walltime" in data_dict:
        ret["walltime"] = float(data_dict["walltime"][:-1])  # ends in 's'
    if "cputime" in data_dict:
        ret["cputime"] = float(data_dict["cputime"][:-1])  # ends in 's'
    if "memory" in data_dict:
        ret["memory"] = int(data_dict["memory"][:-1])  # ends in 'B'
    if "returnvalue" in data_dict:
        ret["exitcode"] = ProcessExitCode.create(value=int(data_dict["returnvalue"]))
    if "exitsignal" in data_dict:
        ret["exitcode"] = ProcessExitCode.create(signal=int(data_dict["exitsignal"]))
    if "terminationreason" in data_dict:
        ret["terminationreason"] = data_dict["terminationreason"]

    with open(run.log_file, "w+") as file:
        with open(tmp_log, "r") as log_source:
            content = log_source.read()
            file.write(content)

    return ret