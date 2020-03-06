"""
CPAchecker is a tool for configurable software verification.
This file is part of CPAchecker.

Copyright (C) 2007-2020  Dirk Beyer
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


CPAchecker web page:
  http://cpachecker.sosy-lab.org
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import http.client
import json
import logging
import os
import shutil
import sys
import time
import urllib.request
import zipfile

import benchexec.util

from benchexec.model import MEMLIMIT, TIMELIMIT, CORELIMIT

sys.dont_write_bytecode = True  # prevent creation of .pyc files

AWS_URL = "v7ozqsjfod.execute-api.eu-central-1.amazonaws.com"

HTTP_GET = "GET"
HTTP_POST = "POST"


DEFAULT_CLOUD_TIMELIMIT = 300  # s
DEFAULT_CLOUD_MEMLIMIT = None

DEFAULT_CLOUD_MEMORY_REQUIREMENT = 7000000000  # 7 GB
DEFAULT_CLOUD_CPUCORE_REQUIREMENT = 2  # one core with hyperthreading
DEFAULT_CLOUD_CPUMODEL_REQUIREMENT = ""  # empty string matches every model

STOPPED_BY_INTERRUPT = False


def init(config, benchmark):
    benchmark.executable = benchmark.tool.executable()
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    logging.info("Using %s version %s.", benchmark.tool_name, benchmark.tool_version)


def get_system_info():
    return None


def execute_benchmark(benchmark, output_handler):
    (awsInput, numberOfRuns) = getAWSInput(benchmark)
    awsToken = benchmark.config.token

    start_time = benchexec.util.read_local_time()

    try:
        conn = http.client.HTTPSConnection(AWS_URL)
        payload = ""
        headers = {}

        # Create
        conn.request(
            HTTP_GET,
            "/dev/"
            + awsToken
            + "/execution/create?benchmark=https://cloud-mgr.s3.eu-central-1.amazonaws.com/test.zip&parallelization=best",
            payload,
            headers,
        )
        data = conn.getresponse().read()
        servermsg = json.loads(data.decode("utf-8").replace("'", '"'))
        if (
            servermsg.get("message") is not None
            and servermsg.get("message") == "Token not authorized."
        ):
            sys.exit("Invalid token submitted: " + awsToken)

        requestId = servermsg.get("requestId")
        logging.debug(data.decode("utf-8"))

        # Progress
        logging.info(
            "Waiting for the AWS EC2-instance to set everything up. This will take several minutes."
        )
        initialized = False
        # Take a break to give the ec2-instance some time for instantiation
        while not initialized:
            conn.request(
                HTTP_GET,
                "/dev/" + awsToken + "/execution/" + requestId + "/progress",
                payload,
                headers,
            )
            data = conn.getresponse().read()
            logging.info("waiting...")
            servermsg = json.loads(data.decode("utf-8").replace("'", '"'))
            if (
                servermsg.get("message") is not None
                and servermsg.get("message") == "Internal server error"
            ):
                time.sleep(10)
                continue
            elif (
                servermsg.get("instancesNotTerminatedTotal") is not None
                and servermsg.get("instancesNotTerminatedTotal") > 0
            ):
                time.sleep(10)
                continue
            initialized = True

        # Results
        conn.request(
            HTTP_GET,
            "/dev/" + awsToken + "/execution/" + requestId + "/results",
            payload,
            headers,
        )
        res = conn.getresponse()
        data = res.read()
        urls = json.loads(data.decode("utf-8").replace("'", '"')).get("urls")
        for url in urls:
            logging.debug("Downloading file from url: %s", url)
            dirname, filename = os.path.split(url)
            zipFileDir = os.path.join(benchmark.log_folder, filename)
            urllib.request.urlretrieve(url, zipFileDir)

            with zipfile.ZipFile(zipFileDir, "r") as zip_file:
                zip_file.extractall(benchmark.log_folder)

    except KeyboardInterrupt:
        stop()

    if STOPPED_BY_INTERRUPT:
        output_handler.set_error("interrupted")

    end_time = benchexec.util.read_local_time()

    handleCloudResults(benchmark, output_handler, start_time, end_time)

    # Clean
    conn.request(HTTP_GET, "/dev/" + awsToken + "/clean", payload, headers)


def stop():
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True


def getAWSInput(benchmark):
    (
        requirements,
        numberOfRuns,
        limitsAndNumRuns,
        runDefinitions,
        sourceFiles,
    ) = getBenchmarkDataForCloud(benchmark)
    workingDir = benchmark.working_directory()
    if not os.path.isdir(workingDir):
        sys.exit("Missing working directory '{0}', cannot run tool.".format(workingDir))
    logging.debug("Working dir: " + workingDir)

    outputDir = benchmark.log_folder
    absOutputDir = os.path.abspath(outputDir)
    absWorkingDir = os.path.abspath(workingDir)
    absSourceFiles = list(map(os.path.abspath, sourceFiles))
    absBaseDir = benchexec.util.common_base_dir(absSourceFiles)

    if absBaseDir == "":
        sys.exit("No common base dir found.")

    awsInput = [
        toTabList([absBaseDir, absOutputDir, absWorkingDir]),
        toTabList(requirements),
    ]
    if benchmark.result_files_patterns:
        if len(benchmark.result_files_patterns) > 1:
            sys.exit("Multiple result-files patterns not supported in cloud mode.")
        awsInput.append(benchmark.result_files_patterns[0])

    awsInput.extend([toTabList(limitsAndNumRuns)])
    awsInput.extend(runDefinitions)
    return ("\n".join(awsInput), numberOfRuns)


def getBenchmarkDataForCloud(benchmark):

    # get requirements
    r = benchmark.requirements
    requirements = [
        bytes_to_mb(DEFAULT_CLOUD_MEMORY_REQUIREMENT if r.memory is None else r.memory),
        DEFAULT_CLOUD_CPUCORE_REQUIREMENT if r.cpu_cores is None else r.cpu_cores,
        DEFAULT_CLOUD_CPUMODEL_REQUIREMENT if r.cpu_model is None else r.cpu_model,
    ]

    # get limits and number of Runs
    timeLimit = benchmark.rlimits.get(TIMELIMIT, DEFAULT_CLOUD_TIMELIMIT)
    memLimit = bytes_to_mb(benchmark.rlimits.get(MEMLIMIT, DEFAULT_CLOUD_MEMLIMIT))
    coreLimit = benchmark.rlimits.get(CORELIMIT, None)
    numberOfRuns = sum(
        len(runSet.runs) for runSet in benchmark.run_sets if runSet.should_be_executed()
    )
    limitsAndNumRuns = [numberOfRuns, timeLimit, memLimit]
    if coreLimit is not None:
        limitsAndNumRuns.append(coreLimit)

    # get Runs with args and sourcefiles
    sourceFiles = []
    runDefinitions = []
    for runSet in benchmark.run_sets:
        if not runSet.should_be_executed():
            continue
        if STOPPED_BY_INTERRUPT:
            break

        # get runs
        for run in runSet.runs:
            cmdline = run.cmdline()

            # we assume, that VCloud-client only splits its input at tabs,
            # so we can use all other chars for the info, that is needed to run the tool.
            argString = json.dumps(cmdline)
            assert "\t" not in argString  # cannot call toTabList(), if there is a tab

            log_file = os.path.relpath(run.log_file, benchmark.log_folder)
            if os.path.exists(run.identifier):
                runDefinitions.append(
                    toTabList(
                        [argString, log_file] + run.sourcefiles + run.required_files
                    )
                )
            else:
                runDefinitions.append(
                    toTabList([argString, log_file] + run.required_files)
                )
            sourceFiles.extend(run.sourcefiles)

    if not runDefinitions:
        sys.exit("Benchmark has nothing to run.")

    return (requirements, numberOfRuns, limitsAndNumRuns, runDefinitions, sourceFiles)


def bytes_to_mb(mb):
    if mb is None:
        return None
    return int(mb / 1000 / 1000)


def toTabList(l):
    return "\t".join(map(str, l))


def handleCloudResults(benchmark, output_handler, start_time, end_time):

    outputDir = benchmark.log_folder
    if not os.path.isdir(outputDir) or not os.listdir(outputDir):
        # outputDir does not exist or is empty
        logging.warning(
            "Cloud produced no results. Output-directory is missing or empty: %s",
            outputDir,
        )

    if start_time and end_time:
        usedWallTime = (end_time - start_time).total_seconds()
    else:
        usedWallTime = None

    # write results in runs and handle output after all runs are done
    executedAllRuns = True
    runsProducedErrorOutput = False
    for runSet in benchmark.run_sets:
        if not runSet.should_be_executed():
            output_handler.output_for_skipping_run_set(runSet)
            continue

        output_handler.output_before_run_set(runSet, start_time=start_time)

        for run in runSet.runs:
            filename = os.path.split(run.log_file)[1]
            resultFilesDir = os.path.splitext(filename)[0]
            prop, filedirTrimmed = resultFilesDir.split(".", 1)
            logFile = os.path.join(
                benchmark.log_folder, filedirTrimmed, filename.split(".", 1)[1]
            )
            shutil.move(logFile, run.log_file)

            dataFile = run.log_file + ".data"
            shutil.move(logFile + ".data", dataFile)

            shutil.move(
                os.path.join(benchmark.log_folder, filedirTrimmed),
                os.path.join(benchmark.log_folder, resultFilesDir),
            )

            zipfile = os.path.join(benchmark.log_folder, filedirTrimmed + ".zip")
            if os.path.isfile(zipfile):
                os.remove(zipfile)

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

            # The directory structure differs between direct and webclient mode when using VCloud.
            # Move all output files from "sibling of log-file" to "sibling of parent directory".
            rawPath = run.log_file[: -len(".log")]
            dirname, filename = os.path.split(rawPath)
            vcloudFilesDirectory = rawPath + ".files"
            benchexecFilesDirectory = os.path.join(
                dirname[: -len(".logfiles")] + ".files", filename
            )
            if os.path.isdir(vcloudFilesDirectory) and not os.path.isdir(
                benchexecFilesDirectory
            ):
                shutil.move(vcloudFilesDirectory, benchexecFilesDirectory)

        output_handler.output_after_run_set(
            runSet, walltime=usedWallTime, end_time=end_time
        )

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

    if not executedAllRuns:
        logging.warning("Some expected result files could not be found!")
    if runsProducedErrorOutput and not benchmark.config.debug:
        logging.warning(
            "Some runs produced unexpected warnings on stderr, please check the %s files!",
            os.path.join(outputDir, "*.stdError"),
        )


def parseCloudRunResultFile(filePath):
    def read_items():
        with open(filePath, "rt") as file:
            for line in file:
                key, value = line.split("=", 1)
                yield key, value

    return parse_vcloud_run_result(read_items())


def parse_vcloud_run_result(values):
    result_values = collections.OrderedDict()

    def parse_time_value(s):
        if s[-1] != "s":
            raise ValueError('Cannot parse "{0}" as a time value.'.format(s))
        return float(s[:-1])

    def set_exitcode(new):
        if "exitcode" in result_values:
            old = result_values["exitcode"]
            assert (
                old == new
            ), "Inconsistent exit codes {} and {} from VerifierCloud".format(old, new)
        else:
            result_values["exitcode"] = new

    for key, value in values:
        value = value.strip()
        if key in ["cputime", "walltime"]:
            result_values[key] = parse_time_value(value)
        elif key == "memory":
            result_values["memory"] = int(value.strip("B"))
        elif key == "exitcode":
            set_exitcode(benchexec.util.ProcessExitCode.from_raw(int(value)))
        elif key == "returnvalue":
            set_exitcode(benchexec.util.ProcessExitCode.create(value=int(value)))
        elif key == "exitsignal":
            set_exitcode(benchexec.util.ProcessExitCode.create(signal=int(value)))
        elif (
            key in ["host", "terminationreason", "cpuCores", "memoryNodes", "starttime"]
            or key.startswith("blkio-")
            or key.startswith("cpuenergy")
            or key.startswith("energy-")
            or key.startswith("cputime-cpu")
        ):
            result_values[key] = value
        elif key not in ["command", "timeLimit", "coreLimit", "memoryLimit"]:
            result_values["vcloud-" + key] = value

    return result_values
