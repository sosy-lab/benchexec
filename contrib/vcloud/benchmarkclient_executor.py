# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

import benchexec.util
from benchexec import BenchExecException
from benchexec.tooladapter import CURRENT_BASETOOL, create_tool_locator

from . import vcloudutil

sys.dont_write_bytecode = True  # prevent creation of .pyc files

DEFAULT_CLOUD_MEMORY_REQUIREMENT = 7_000_000_000  # 7 GB
DEFAULT_CLOUD_CPUCORE_REQUIREMENT = 2  # one core with hyperthreading

STOPPED_BY_INTERRUPT = False

_JustReprocessResults = False


def set_vcloud_jar_path(p):
    global vcloud_jar
    vcloud_jar = p


def init(config, benchmark):
    global _JustReprocessResults
    _JustReprocessResults = config.reprocessResults

    if not benchmark.rlimits.cputime_hard:
        sys.exit("A CPU-time limit is required when running on Cloud.")

    if config.containerImage:
        from vcloud.podman_containerized_tool import TOOL_DIRECTORY_MOUNT_POINT

        tool_locator = CURRENT_BASETOOL.ToolLocator(
            tool_directory=TOOL_DIRECTORY_MOUNT_POINT
        )
        executable_for_version = benchmark.tool.executable(tool_locator)
        benchmark.tool_version = benchmark.tool.version(executable_for_version)

        executable_for_version = Path(executable_for_version)

        # ensure executable_for_version is relative
        if executable_for_version.is_absolute():
            try:
                executable_for_version = executable_for_version.relative_to(
                    TOOL_DIRECTORY_MOUNT_POINT
                )
            except ValueError as e:
                raise BenchExecException(
                    f"Executable path {executable_for_version} is not relative"
                    " and is not containing the expected mount point in the container"
                    f" {TOOL_DIRECTORY_MOUNT_POINT}."
                ) from e

        # ensure that executable_for_version is not pointing to a directory
        # outside of the tool directory

        executable_for_cloud = Path(config.tool_directory) / executable_for_version

        # Paths must be resolved to properly detect when the executable would
        # escape the tool dir with '..'
        if not executable_for_cloud.resolve().is_relative_to(
            Path(config.tool_directory).resolve()
        ):
            raise BenchExecException(
                f"Executable path {executable_for_cloud} is not within the tool directory"
                f" {config.tool_directory}."
            )

        # The vcloud uses the tool location later to determine which files need to be uploaded
        # So this needs to point to the actual path where the executable is on the host
        if not executable_for_cloud.is_absolute() and "/" not in str(
            executable_for_cloud
        ):
            # add ./ to the beginning of the path if the executable is just the executable name
            # otherwise os.path.dirname will return '' causing problems with some tool info modules
            executable_for_cloud = "./" + str(executable_for_cloud)

        benchmark.executable = str(executable_for_cloud)

    else:
        tool_locator = create_tool_locator(config)
        benchmark.executable = benchmark.tool.executable(tool_locator)
        benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    environment = benchmark.environment()
    if environment.get("keepEnv", None) or environment.get("additionalEnv", None):
        sys.exit(
            "Unsupported environment configuration in tool-info module, "
            'only "newEnv" is supported by VerifierCloud'
        )


def get_system_info():
    return None


def execute_benchmark(benchmark, output_handler):
    if not _JustReprocessResults:
        # build input for cloud
        (cloudInput, numberOfRuns) = getCloudInput(benchmark)
        if benchmark.config.debug:
            cloudInputFile = os.path.join(benchmark.log_folder, "cloudInput.yml")
            benchexec.util.write_file(cloudInput, cloudInputFile)
            output_handler.all_created_files.add(cloudInputFile)
        meta_information = json.dumps(
            {
                "tool": {
                    "name": benchmark.tool_name,
                    "revision": benchmark.tool_version,
                    "benchexec-module": benchmark.tool_module,
                },
                "benchmark": benchmark.name,
                "timestamp": benchmark.instance,
                "generator": "benchmark.vcloud.py",
            }
        )

        # start cloud and wait for exit
        logging.debug("Starting cloud.")
        if benchmark.config.debug:
            logLevel = "FINER"
        else:
            logLevel = "INFO"
        # heuristic for heap size: 100 MB and 100 kB per run
        heapSize = benchmark.config.cloudClientHeap + numberOfRuns // 10
        # vcloud_jar is to be set by the calling script, i.e., (vcloud-)benchmark.py
        cmdLine = [
            "java",
            f"-Xmx{heapSize}m",
            "-jar",
            vcloud_jar,
            "benchmark",
            "--loglevel",
            logLevel,
            "--run-collection-meta-information",
            meta_information,
            "--environment",
            formatEnvironment(benchmark.environment()),
            "--max-log-file-size",
            str(benchmark.config.maxLogfileSize),
            "--debug",
            str(benchmark.config.debug),
        ]
        if benchmark.config.cloudMaster:
            cmdLine.extend(["--master", benchmark.config.cloudMaster])
        if benchmark.config.zipResultFiles:
            cmdLine.extend(["--zip-result-files", str(benchmark.config.zipResultFiles)])
        if benchmark.config.cgroupAccess:
            cmdLine.extend(["--cgroupAccess", str(benchmark.config.cgroupAccess)])
        if benchmark.config.tryLessMemory:
            cmdLine.extend(["--try-less-memory", str(benchmark.config.tryLessMemory)])
        if benchmark.config.debug:
            cmdLine.extend(["--print-new-files", "true"])
        if benchmark.config.containerImage:
            cmdLine.extend(["--containerImage", str(benchmark.config.containerImage)])
        cmdLine.extend(["--input-format", "yaml"])
        cmdLine.extend(["--output-dir", benchmark.log_folder])

        start_time = benchexec.util.read_local_time()

        cloud = subprocess.Popen(
            cmdLine,
            stdin=subprocess.PIPE,
            universal_newlines=True,
            shell=vcloudutil.is_windows(),  # noqa: S602
        )
        try:
            cloud.communicate(cloudInput)
        except KeyboardInterrupt:
            stop()
        returnCode = cloud.wait()

        end_time = benchexec.util.read_local_time()

        if returnCode:
            if STOPPED_BY_INTERRUPT:
                output_handler.set_error("interrupted")
            else:
                errorMsg = f"Cloud return code: {returnCode}"
                logging.warning(errorMsg)
                output_handler.set_error(errorMsg)
    else:
        returnCode = 0
        start_time = None
        end_time = None

    handleCloudResults(benchmark, output_handler, start_time, end_time)

    return returnCode


def stop():
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True
    # kill cloud-client, should be done automatically, when the subprocess is aborted


def formatEnvironment(environment):
    return ";".join(f"{k}={v}" for k, v in environment.get("newEnv", {}).items())


def getCloudInput(benchmark):
    (workingDir, toolpaths) = getToolDataForCloud(benchmark)

    absWorkingDir = os.path.abspath(workingDir)
    absToolpaths = list(map(os.path.abspath, toolpaths))

    absBaseDir, numberOfRuns = computeBaseDir(benchmark, absToolpaths)

    # get requirements
    r = benchmark.requirements

    # get limits
    rlimits = benchmark.rlimits
    timeLimit = int(rlimits.cputime_hard or DEFAULT_CLOUD_TIMELIMIT)

    limits_cpu = {"time": {"hard": timeLimit}}
    if rlimits.cpu_cores is not None:
        limits_cpu["cores"] = rlimits.cpu_cores

    limits = {"cpu": limits_cpu}
    if rlimits.walltime is not None:
        limits["walltime"] = int(rlimits.walltime)
    if rlimits.memory is not None:
        limits["memory"] = rlimits.memory

    runDefinitions = buildRunDefinitions(benchmark, limits, absBaseDir)

    if not runDefinitions:
        sys.exit("Benchmark has nothing to run.")

    cloud_input = {
        "formatVersion": "1.0",
        "files": [os.path.relpath(p, absBaseDir) for p in absToolpaths],
        "basedir": os.path.relpath(absBaseDir),
        "execdir": os.path.relpath(absWorkingDir, absBaseDir),
    }

    if benchmark.config.cloudPriority:
        cloud_input["priority"] = benchmark.config.cloudPriority

    cloud_input["memoryreq"] = (
        r.memory if r.memory is not None else DEFAULT_CLOUD_MEMORY_REQUIREMENT
    )
    cloud_input["corereq"] = (
        r.cpu_cores if r.cpu_cores is not None else DEFAULT_CLOUD_CPUCORE_REQUIREMENT
    )
    if r.cpu_model:
        cloud_input["cpumodels"] = [r.cpu_model]

    if benchmark.result_files_patterns:
        cloud_input["resultFilePatterns"] = list(benchmark.result_files_patterns)

    cloud_input["runsets"] = runDefinitions

    return yaml.dump(
        cloud_input, default_flow_style=False, allow_unicode=True
    ), numberOfRuns


def getToolDataForCloud(benchmark):
    workingDir = benchmark.working_directory()
    if not os.path.isdir(workingDir):
        sys.exit(f"Missing working directory '{workingDir}', cannot run tool.")
    logging.debug("Working dir: %s", workingDir)

    toolpaths = benchmark.required_files()
    if benchmark.config.additional_files:
        toolpaths.update(set(benchmark.config.additional_files))
    validToolpaths = set()
    for file in toolpaths:
        if not os.path.exists(file):
            sys.exit(
                f"Missing file '{os.path.normpath(file)}', "
                f"cannot run benchmark within cloud."
            )
        if os.path.isdir(file) and not os.listdir(file):
            # VCloud can not handle empty directories, lets ignore them
            logging.warning(
                "Empty directory '%s', ignoring directory for cloud execution.",
                os.path.normpath(file),
            )
        else:
            validToolpaths.add(file)

    return (workingDir, validToolpaths)


def computeBaseDir(benchmark, absToolpaths):
    absSourceFiles = []
    numberOfRuns = 0
    for runSet in activeRunSets(benchmark):
        for run in runSet.runs:
            if os.path.exists(run.identifier):
                absSourceFiles.extend(map(os.path.abspath, run.sourcefiles))
            numberOfRuns += 1

    absBaseDir = benchexec.util.common_base_dir(absSourceFiles + absToolpaths)
    if absBaseDir == "":
        sys.exit("No common base dir found.")

    return absBaseDir, numberOfRuns


def buildRunDefinitions(benchmark, limits, absBaseDir):
    runDefinitions = []
    for runSet in activeRunSets(benchmark):
        runs = []
        for run in runSet.runs:
            cmdline = list(map(vcloudutil.force_linux_path, run.cmdline()))
            log_file = os.path.relpath(run.log_file, benchmark.log_folder)
            run_def = {"logfile": log_file, "command": cmdline}
            run_files = []
            if os.path.exists(run.identifier):
                run_files.extend(run.sourcefiles)
            run_files.extend(run.required_files)
            if run_files:
                run_def["files"] = [os.path.relpath(f, absBaseDir) for f in run_files]
            runs.append(run_def)
        if runs:
            runDefinitions.append({"limits": limits, "runs": runs})
    return runDefinitions


def activeRunSets(benchmark):
    for runSet in benchmark.run_sets:
        if STOPPED_BY_INTERRUPT:
            break
        if runSet.should_be_executed():
            yield runSet


def handleCloudResults(benchmark, output_handler, start_time, end_time):
    outputDir = benchmark.log_folder
    if not os.path.isdir(outputDir) or not os.listdir(outputDir):
        # outputDir does not exist or is empty
        logging.warning(
            "Cloud produced no results. Output-directory is missing or empty: %s",
            outputDir,
        )

    # Write worker host informations in xml
    parseAndSetCloudWorkerHostInformation(outputDir, output_handler, benchmark)

    # write results in runs and handle output after all runs are done
    executedAllRuns = True
    runsProducedErrorOutput = False
    for runSet in benchmark.run_sets:
        if not runSet.should_be_executed():
            output_handler.output_for_skipping_run_set(runSet)
            continue

        output_handler.output_before_run_set(runSet, start_time=start_time)

        for run in runSet.runs:
            run.cmdline()  # ignore result, but necessary, otherwise _cmdline is not set
            dataFile = run.log_file + ".data"
            if os.path.exists(dataFile) and os.path.exists(run.log_file):
                try:
                    values = parseCloudRunResultFile(dataFile)
                    if not benchmark.config.debug:
                        os.remove(dataFile)
                except IOError as e:
                    logging.warning(
                        "Cannot extract measured values from output for file %s: %s",
                        run.identifier,
                        e,
                    )
                    output_handler.all_created_files.add(dataFile)
                    output_handler.set_error("missing results", runSet)
                    executedAllRuns = False
                else:
                    output_handler.output_before_run(run)
                    run.set_result(values, ["host"])
                    output_handler.output_after_run(run)
            else:
                logging.warning("No results exist for file %s.", run.identifier)
                output_handler.set_error("missing results", runSet)
                executedAllRuns = False

            if os.path.exists(run.log_file + ".stdError"):
                runsProducedErrorOutput = True

            # Execution using this executor produces a different directory name than what
            # BenchExec expects.
            # Move all output files from "sibling of log-file" to "sibling of parent directory".
            rawPath = run.log_file[: -len(".log")]
            dirname, filename = os.path.split(rawPath)
            vcloudFilesDirectory = rawPath + ".files"
            benchexecFilesDirectory = run.result_files_folder
            if os.path.isdir(vcloudFilesDirectory) and not os.path.isdir(
                benchexecFilesDirectory
            ):
                shutil.move(vcloudFilesDirectory, benchexecFilesDirectory)

        output_handler.output_after_run_set(runSet, end_time=end_time)

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

    if not executedAllRuns:
        logging.warning("Some expected result files could not be found!")
    if runsProducedErrorOutput and not benchmark.config.debug:
        logging.warning(
            "Some runs produced unexpected warnings on stderr, please check the %s files!",
            os.path.join(outputDir, "*.stdError"),
        )


def parseAndSetCloudWorkerHostInformation(outputDir, output_handler, benchmark):
    filePath = os.path.join(outputDir, "hostInformation.txt")
    try:
        with open(filePath, "rt") as file:
            # Parse first part of information about hosts until first blank line
            line = file.readline().strip()
            while True:
                if not line:
                    break
                name = line.split("=")[-1].strip()
                osName = file.readline().split("=")[-1].strip()
                memory = file.readline().split("=")[-1].strip()
                cpuName = file.readline().split("=")[-1].strip()
                frequency = vcloudutil.parse_frequency_value(
                    file.readline().split("=")[-1]
                )
                cores = file.readline().split("=")[-1].strip()
                turboBoostSupported = False
                turboBoostEnabled = False
                line = file.readline().strip()
                if line.startswith("turboboost-supported="):
                    turboBoostSupported = line.split("=")[1].lower() == "true"
                    line = file.readline().strip()
                if line.startswith("turboboost-enabled="):
                    turboBoostEnabled = line.split("=")[1].lower() == "true"
                    line = file.readline().strip()
                output_handler.store_system_info(
                    osName,
                    cpuName,
                    cores,
                    frequency,
                    memory,
                    name,
                    None,
                    {},
                    turboBoostEnabled if turboBoostSupported else None,
                )

            # Ignore second part of information about runs
            # (we read the run-to-host mapping from the .data file for each run).

        if benchmark.config.debug:
            output_handler.all_created_files.add(filePath)
        else:
            os.remove(filePath)
    except IOError:
        logging.warning("Host information file not found: %s", filePath)


def parseCloudRunResultFile(filePath):
    def read_items():
        with open(filePath, "rt") as file:
            for line in file:
                key, value = line.split("=", 1)
                yield key, value

    return vcloudutil.parse_vcloud_run_result(read_items())
