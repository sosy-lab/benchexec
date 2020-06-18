# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
from getpass import getuser
import io
import json
import logging
import os
import requests
import shutil
import sys
from threading import Event
import zipfile

import benchexec.util

from benchexec import BenchExecException
from benchexec.model import MEMLIMIT, TIMELIMIT, CORELIMIT

sys.dont_write_bytecode = True  # prevent creation of .pyc files

REQUEST_URL = {
    "create": "{0}{1}/execution/create",
    "upload": "{0}{1}/upload/{2}?file={3}",
    "launchBatch": "{0}{1}/execution/{2}/launchBatch?verifier={3}&verifierS3={4}&tasks={5}&tasksS3={6}&commandsS3={7}",
    "progressBatch": "{0}{1}/execution/{2}/progressBatch",
    "results": "{0}{1}/execution/{2}/results",
    "clean": "{0}{1}/clean",
}

STOPPED_BY_INTERRUPT = False
event_handler = Event()


def init(config, benchmark):
    benchmark.executable = benchmark.tool.executable()
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    logging.info("Using %s version %s.", benchmark.tool_name, benchmark.tool_version)


def get_system_info():
    return None


def execute_benchmark(benchmark, output_handler):
    (toolpaths, awsInput) = getAWSInput(benchmark)

    conf_file_path = (
        benchmark.config.aws_config
        if benchmark.config.aws_config is not None
        else os.path.join(
            os.path.expanduser("~"),
            ".config",
            "sv-comp-aws",
            getuser() + ".client.config",
        )
    )
    with open(conf_file_path, "r") as conf_file:
        conf = json.load(conf_file)[0]
        aws_endpoint = conf["Endpoint"]
        aws_token = conf["UserToken"]

    try:
        logging.info("Building archive files for verifier-tool and tasks...")
        verifier_arc_name = benchmark.tool_name + "_" + benchmark.instance + ".zip"
        verifier_arc_path = _createArchiveFile(
            verifier_arc_name, toolpaths["absBaseDir"], toolpaths["absToolpaths"],
        )
        tasks_arc_name = "tasks_" + benchmark.instance + ".zip"
        tasks_arc_path = _createArchiveFile(
            tasks_arc_name, toolpaths["absBaseDir"], toolpaths["absSourceFiles"],
        )

        start_time = benchexec.util.read_local_time()

        logging.info("Waiting on the AWS EC2-instance to set everything up...")

        # Create
        url = REQUEST_URL["create"].format(aws_endpoint, aws_token)
        logging.debug("Sending http-request for aws instantiation (create): \n%s", url)
        http_request = requests.get(url)
        http_request.raise_for_status()

        msg = http_request.json()
        requestId = msg["requestId"]

        # Upload verifier
        url = REQUEST_URL["upload"].format(
            aws_endpoint, aws_token, requestId, verifier_arc_name
        )
        logging.debug("Sending http-request for uploading the verifier: \n%s", url)
        http_request = requests.get(url)
        http_request.raise_for_status()

        msg = http_request.json()
        verifier_upload_url = msg["uploadUrl"]
        verifier_s3_key = msg["S3Key"]
        verifier_aws_public_url = msg["publicURL"]
            msg["publicURL"],
        )

        with open(verifer_arc_path, "rb") as archive_file:
            payload = archive_file.read()
            headers = {"Content-Type": "application/zip"}
            logging.info("Uploading the verifier to AWS...")
            http_request = requests.request(
                "PUT", verifier_uploadUrl, headers=headers, data=payload
            )
        http_request.raise_for_status()

        # Upload tasks
        url = REQUEST_URL["upload"].format(
            aws_endpoint, aws_token, requestId, tasks_arc_name
        )
        logging.debug("Sending http-request for uploading tasks: \n%s", url)
        http_request = requests.get(url)
        http_request.raise_for_status()

        msg = http_request.json()
        tasks_upload_url = msg["uploadUrl"]
        tasks_s3_key = msg["S3Key"]
        tasks_aws_public_url = msg["publicURL"]
            msg["publicURL"],
        )

        with open(tasks_arc_path, "rb") as archive_file:
            payload = archive_file.read()
            headers = {"Content-Type": "application/zip"}
            logging.info("Uploading tasks to AWS...")
            http_request = requests.request(
                "PUT", tasks_uploadUrl, headers=headers, data=payload
            )
        http_request.raise_for_status()

        # Upload commands
        commands_file_name = "commands.json"
        url = REQUEST_URL["upload"].format(
            aws_endpoint, aws_token, requestId, commands_file_name
        )
        logging.debug("Sending http-request for uploading commands: \n%s", url)
        http_request = requests.get(url)
        http_request.raise_for_status()

        msg = http_request.json()
        commands_upload_url = msg["uploadUrl"]
        commands_s3_key = msg["S3Key"]

        payload = json.dumps(awsInput)
        headers = {"Content-Type": "application/json"}
        logging.info("Uploading the commands to AWS...")
        http_request = requests.request(
            "PUT", commands_upload_url, headers=headers, data=payload
        )
        http_request.raise_for_status()

        # Launch
        url = REQUEST_URL["launchBatch"].format(
            aws_endpoint,
            aws_token,
            requestId,
            verifier_aws_public_url,
            verifier_s3_key,
            tasks_aws_public_url,
            tasks_s3_key,
            commands_s3_key,
        )
        logging.debug("Sending http-request for launch: \n%s", url)
        http_request = requests.get(url)
        http_request.raise_for_status()

        # Progress
        logging.info(
            "Executing Runexec on the AWS workers. "
            "Depending on the size of the tasks, this might take a while."
        )
        progress_url = REQUEST_URL["progressBatch"].format(
            aws_endpoint, aws_token, requestId
        )
        logging.debug("Sending http-request for progress: \n%s", progress_url)
        printMsg = 0
        # Poll the current status in AWS by periodically sending an http-request
        # (for example, how much tasks have been verified so far)
        while not event_handler.is_set():
            http_request = requests.get(progress_url)
            # There is currently an issue on the server side in which the
            # status code of the response is rarely not 200.
            # This needs to be investigated before uncommenting the following line.
            # http_request.raise_for_status()

            msg = http_request.json()
            # poll every 15 sec and print a user message every second time
            if msg.get("message") == "Internal server error":
                # This message appears if the ec2-instances are not instantiated or
                # running yet
                printMsg += 1
                if printMsg % 2 == 0:
                    logging.info("Waiting for EC2 to launch the batch processes...")
                event_handler.wait(15)
            elif not msg["completed"]:
                printMsg += 1
                if printMsg % 2 == 0:
                    jobsCompleted = msg.get("totalNumberOfJobsCompleted")
                    totalJobs = msg.get("totalNumberOfJobs")
                    logging.info(
                        "Waiting until all tasks have been verified... "
                        "(Completed: %d/%d)",
                        jobsCompleted,
                        totalJobs,
                    )
                event_handler.wait(15)
            else:
                logging.info(
                    "Execution of %s tasks finished. "
                    "Collecting the results back from AWS.",
                    msg.get("totalNumberOfJobsCompleted"),
                )
                break

        # Results
        url = REQUEST_URL["results"].format(aws_endpoint, aws_token, requestId)
        logging.debug("Sending http-request for collecting the results: \n%s", url)
        http_request = requests.get(url)
        http_request.raise_for_status()
        for url in http_request.json()["urls"]:
            logging.debug("Downloading file from url: %s", url)
            result_file = requests.get(url)
            with zipfile.ZipFile(io.BytesIO(result_file.content)) as zipf:
                zipf.extractall(benchmark.log_folder)
    except KeyboardInterrupt:
        stop()
    finally:
        if os.path.exists(verifier_arc_path):
            os.remove(verifier_arc_path)
        if os.path.exists(tasks_arc_path):
            os.remove(tasks_arc_path)

        # Clean
        url = REQUEST_URL["clean"].format(aws_endpoint, aws_token)
        logging.debug(
            "Sending http-request for cleaning the aws services up: \n%s", url
        )
        requests.get(url)

    if STOPPED_BY_INTERRUPT:
        output_handler.set_error("interrupted")

    end_time = benchexec.util.read_local_time()

    handleCloudResults(benchmark, output_handler, start_time, end_time)


def stop():
    global event_handler
    event_handler.set()
    global STOPPED_BY_INTERRUPT
    STOPPED_BY_INTERRUPT = True


def getAWSInput(benchmark):
    (
        requirements,
        numberOfRuns,
        limitsAndNumRuns,
        runDefinitions,
        sourceFiles,
    ) = getBenchmarkData(benchmark)
    (workingDir, toolpaths) = getToolData(benchmark)

    absWorkingDir = os.path.abspath(workingDir)
    absToolpaths = list(map(os.path.abspath, toolpaths))
    absSourceFiles = list(map(os.path.abspath, sourceFiles))
    absBaseDir = benchexec.util.common_base_dir(absSourceFiles + absToolpaths)

    if absBaseDir == "":
        raise BenchExecException("No common base dir found.")

    toolpaths = {
        "absBaseDir": absBaseDir,
        "workingDir": workingDir,
        "absWorkingDir": absWorkingDir,
        "toolpaths": toolpaths,
        "absToolpaths": absToolpaths,
        "sourceFiles": sourceFiles,
        "absSourceFiles": absSourceFiles,
    }

    awsInput = {
        "requirements": requirements,
        "workingDir": os.path.relpath(absWorkingDir, absBaseDir),
    }
    if benchmark.result_files_patterns:
        if len(benchmark.result_files_patterns) > 1:
            raise BenchExecException(
                "Multiple result-file patterns not supported in cloud mode."
            )
        awsInput.update({"resultFilePatterns": benchmark.result_files_patterns[0]})

    awsInput.update({"limitsAndNumRuns": limitsAndNumRuns})
    awsInput.update({"runDefinitions": runDefinitions})

    return (toolpaths, awsInput)


def _zipdir(path, zipfile, absBaseDir):
    for root, dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            zipfile.write(filepath, os.path.relpath(filepath, absBaseDir))


def _createArchiveFile(archive_name, absBaseDir, abs_paths):

    archive_path = os.path.join(absBaseDir, archive_name)
    if os.path.isfile(archive_path):
        raise BenchExecException(
            "Zip file already exists: '{0}'; not going to overwrite it.".format(
                os.path.normpath(archive_path)
            )
        )

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in abs_paths:
            if not os.path.exists(file):
                zipf.close()
                if os.path.isfile(archive_path):
                    os.remove(archive_path)

                raise BenchExecException(
                    "Missing file '{0}', cannot run benchmark without it.".format(
                        os.path.normpath(file)
                    )
                )

            if os.path.isdir(file):
                _zipdir(file, zipf, absBaseDir)
            else:
                zipf.write(file, os.path.relpath(file, absBaseDir))

    return archive_path


def getBenchmarkData(benchmark):
    r = benchmark.requirements
    # These values are currently not used internally, but the goal is
    # to eventually integrate them in a later stage.
    if r.cpu_cores is None or r.cpu_model is None or r.memory is None:
        raise BenchExecException(
            "The entry for either the amount of used cpu cores, model, or memory "
            "is missing from the benchmark definition"
        )
    requirements = {
        "cpu_cores": r.cpu_cores,
        "cpu_model": r.cpu_model,
        "memory_in_mb": bytes_to_mb(r.memory),
    }

    # get limits and number of runs
    timeLimit = benchmark.rlimits.get(TIMELIMIT, None)
    memLimit = bytes_to_mb(benchmark.rlimits.get(MEMLIMIT, None))
    if timeLimit is None or memLimit is None:
        raise BenchExecException(
            "An entry for either the time- or memory-limit is missing "
            "in the benchmark definition"
        )

    coreLimit = benchmark.rlimits.get(CORELIMIT, None)
    numberOfRuns = sum(
        len(runSet.runs) for runSet in benchmark.run_sets if runSet.should_be_executed()
    )
    limitsAndNumRuns = {
        "number_of_runs": numberOfRuns,
        "time_limit_in_sec": timeLimit,
        "mem_limit_in_mb": memLimit,
    }
    if coreLimit is not None:
        limitsAndNumRuns.update({"core_limit": coreLimit})

    # get runs with args and sourcefiles
    sourceFiles = set()
    runDefinitions = []
    for runSet in benchmark.run_sets:
        if not runSet.should_be_executed():
            continue
        if STOPPED_BY_INTERRUPT:
            break

        # get runs
        for run in runSet.runs:
            runDefinition = {}

            # wrap list-elements in quotations-marks if they contain whitespace
            cmdline = ["'{}'".format(x) if " " in x else x for x in run.cmdline()]
            cmdline = " ".join(cmdline)
            log_file = os.path.relpath(run.log_file, benchmark.log_folder)

            runDefinition.update(
                {
                    "cmdline": cmdline,
                    "log_file": log_file,
                    "sourcefile": run.sourcefiles,
                    "required_files": run.required_files,
                }
            )

            runDefinitions.append(runDefinition)
            sourceFiles.update(run.sourcefiles)
            sourceFiles.update(run.required_files)

    if not runDefinitions:
        raise BenchExecException("Benchmark has nothing to run.")

    return (requirements, numberOfRuns, limitsAndNumRuns, runDefinitions, sourceFiles)


def getToolData(benchmark):

    workingDir = benchmark.working_directory()
    if not os.path.isdir(workingDir):
        raise BenchExecException(
            "Missing working directory '{0}', cannot run tool.".format(workingDir)
        )
    logging.debug("Working dir: %s", workingDir)

    toolpaths = benchmark.required_files()
    validToolpaths = set()
    for file in toolpaths:
        if not os.path.exists(file):
            raise BenchExecException(
                "Missing file '{0}', not runing benchmark without it.".format(
                    os.path.normpath(file)
                )
            )
        validToolpaths.add(file)

    return (workingDir, validToolpaths)


def bytes_to_mb(mb):
    if mb is None:
        return None
    return int(mb / 1000 / 1000)


def handleCloudResults(benchmark, output_handler, start_time, end_time):

    outputDir = benchmark.log_folder
    if not os.path.isdir(outputDir) or not os.listdir(outputDir):
        # outputDir does not exist or is empty
        logging.warning(
            "Received no results from AWS. Output-directory is missing or empty: %s",
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
            dataFile = run.log_file + ".data"

            if os.path.exists(dataFile) and os.path.exists(run.log_file):
                try:
                    values = parseAWSRunResultFile(dataFile)
                    if not benchmark.config.debug:
                        os.remove(dataFile)
                except OSError as e:
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

            # Move all output files from "sibling of log-file" to
            # "sibling of parent directory".
            rawPath = run.log_file[: -len(".log")]
            dirname, filename = os.path.split(rawPath)
            awsFilesDirectory = rawPath + ".files"
            benchexecFilesDirectory = os.path.join(
                dirname[: -len(".logfiles")] + ".files", filename
            )
            if os.path.isdir(awsFilesDirectory) and not os.path.isdir(
                benchexecFilesDirectory
            ):
                shutil.move(awsFilesDirectory, benchexecFilesDirectory)

        output_handler.output_after_run_set(
            runSet, walltime=usedWallTime, end_time=end_time
        )

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

    if not executedAllRuns:
        logging.warning("Some expected result files could not be found!")
    if runsProducedErrorOutput and not benchmark.config.debug:
        logging.warning(
            "Some runs produced unexpected warnings on stderr, "
            "please check the %s files!",
            os.path.join(outputDir, "*.stdError"),
        )


def parseAWSRunResultFile(filePath):
    def read_items():
        with open(filePath, "rt") as file:
            for line in file:
                key, value = line.split("=", 1)
                yield key, value

    return parse_cloud_run_result(read_items())


def parse_cloud_run_result(values):
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

    return result_values
