# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2024 Levente Bajczi
# SPDX-FileCopyrightText: Critical Systems Research Group
# SPDX-FileCopyrightText: Budapest University of Technology and Economics <https://www.ftsrg.mit.bme.hu>
#
# SPDX-License-Identifier: Apache-2.0
import functools
import json
import logging
import subprocess

from benchexec.systeminfo import SystemInfo


def version_in_container(singularity, tool_module):
    version_printer = f"""from benchexec import tooladapter
from benchexec.model import load_tool_info
class Config():
  pass

config = Config()
config.container = False
config.tool_directory = "."
locator = tooladapter.create_tool_locator(config)
tool = load_tool_info("{tool_module}", config)[1]
executable = tool.executable(locator)
print(tool.version(executable))"""

    @functools.lru_cache()
    def version_from_tool_in_container(executable):
        try:
            with open(".get_version.py", "w") as script:
                script.write(version_printer)
            process = subprocess.run(
                [
                    "singularity",
                    "exec",
                    singularity,
                    "python3",
                    ".get_version.py",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                universal_newlines=True,
            )
            if process.stdout:
                return process.stdout.strip()

        except Exception as e:
            logging.warning(
                "could not determine version (in container) due to error: %s", e
            )
        return ""

    return version_from_tool_in_container


def get_system_info_srun(singularity):
    try:
        process = subprocess.run(
            [
                "srun",
                "-t",
                "1"
                "singularity",
                "exec",
                singularity,
                "python3",
                "-c",
                "import benchexec.systeminfo; "
                "import json; "
                "print(json.dumps(benchexec.systeminfo.SystemInfo().__dict__))",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            universal_newlines=True,
        )
        if process.stdout:
            actual_sysinfo = json.loads(process.stdout.strip())
            blank_sysinfo = SystemInfo()
            blank_sysinfo.hostname = str(actual_sysinfo["hostname"]) + " (sample)"
            blank_sysinfo.os = actual_sysinfo["os"]
            blank_sysinfo.cpu_max_frequency = actual_sysinfo["cpu_max_frequency"]
            blank_sysinfo.cpu_number_of_cores = actual_sysinfo["cpu_number_of_cores"]
            blank_sysinfo.cpu_model = actual_sysinfo["cpu_model"]
            blank_sysinfo.cpu_turboboost = actual_sysinfo["cpu_turboboost"]
            blank_sysinfo.memory = actual_sysinfo["memory"]
            return blank_sysinfo

    except Exception as e:
        logging.warning("could not determine system info due to error: %s", e)
    return None


def get_cpu_cmd(concurrency_factor, cores):
    get_cpus = (
        "cpus=($(scontrol show job -d \"$SLURM_JOB_ID\" | grep -o 'CPU_IDs=[^ ]*' | "
        "awk -F= ' { print $2 } ' | head -n1 | "
        "awk -F, ' { for (i = 1; i <= NF; i++ ) { if ($i ~ /-/) "
        '{ split($i, range, "-"); for (j = range[1]; j <= range[2]; j++  ) { print j } } '
        "else { print $i } } }'))"
        '\necho "${cpus[@]}"'
    )
    for i in range(concurrency_factor):
        get_cpus = (
            get_cpus
            + f'\nexport cpuset{i}=$(IFS=,; echo "${{cpus[*]:{i * cores}:{cores}}}")'
        )
    return get_cpus


def lock_cpu_cmds(concurrency_factor, tempdir, bin):
    lock_cpus = 'CPUSET=""; while ! {'
    for i in range(concurrency_factor):
        lock_cpus = (
            lock_cpus
            + f' {{ mkdir {tempdir}/cpuset_{bin}_{i} 2>/dev/null && cpuset={i} && CPUSET="$cpuset{i}"; }}'
        )
        if i == concurrency_factor - 1:
            lock_cpus = lock_cpus + "; }; do sleep 1; done"
        else:
            lock_cpus = lock_cpus + " ||"
    unlock_cpus = f"rm -r {tempdir}/cpuset_{bin}_$cpuset"
    return lock_cpus, unlock_cpus
