# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import io
import json
import logging
import os
import requests
import shutil
import sys
import tempfile
from threading import Event
import urllib
import zipfile

import benchexec.util

from benchexec import BenchExecException

sys.dont_write_bytecode = True  # prevent creation of .pyc files

REQUEST_URL = {
    "create": "{0}{1}/execution/create",
    "upload": "{0}{1}/upload/{2}",
    "launchBatch": "{0}{1}/execution/{2}/launchBatch",
    "progressBatch": "{0}{1}/execution/{2}/progressBatch",
    "results": "{0}{1}/execution/{2}/results",
    "clean": "{0}{1}/clean",
}

STOPPED_BY_INTERRUPT = False
event_handler = Event()

# Number of seconds a http request will wait to establish a connection to the
# remote machine.
HTTP_REQUEST_TIMEOUT = 10


def init(config, benchmark):
    benchmark.executable = benchmark.tool.executable()
    benchmark.tool_version = benchmark.tool.version(benchmark.executable)

    logging.info("Using %s version %s.", benchmark.tool_name, benchmark.tool_version)


def get_system_info():
    return None


def execute_benchmark(benchmark, output_handler):
    (toolpaths, aws_input) = getAWSInput(benchmark)

    conf_file_path = (
        benchmark.config.aws_config
        if benchmark.config.aws_config is not None
        else os.path.join(
            os.path.expanduser("~"), ".config", "sv-comp-aws", "aws.client.config"
        )
    )
    with open(conf_file_path, "r") as conf_file:
        conf = json.load(conf_file)[0]
        aws_endpoint = conf["Endpoint"]
        aws_token = conf["UserToken"]

    try:
        start_time = benchexec.util.read_local_time()

        # Create
        logging.info("Sending http-request for the specific upload destinations")
        url = REQUEST_URL["create"].format(aws_endpoint, aws_token)
        logging.debug("Url of the 'create' HTTP -request: \n%s", url)
        http_response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
        http_response.raise_for_status()

        msg = http_response.json()
        requestId = msg["requestId"]

        # Upload verifier
        prefix = f"{benchmark.tool_name}_{benchmark.instance}_"
        with tempfile.SpooledTemporaryFile(
            mode="w+b", prefix=prefix, suffix=".zip"
        ) as tempfile_verifier:
            logging.info("Building archive for verifier-tool...")
            _createArchiveFile(
                tempfile_verifier, toolpaths["absBaseDir"], toolpaths["absToolpaths"]
            )

            tempfile_verifier.seek(0)  # resets the file pointer

            payload = {"file": prefix + ".zip"}
            url = REQUEST_URL["upload"].format(aws_endpoint, aws_token, requestId)
            logging.debug("Sending http-request for uploading the verifier: \n%s", url)
            http_response = requests.get(
                url, params=payload, timeout=HTTP_REQUEST_TIMEOUT
            )
            http_response.raise_for_status()

            msg = http_response.json()
            verifier_upload_url = msg["uploadUrl"]
            verifier_s3_key = msg["S3Key"]
            verifier_aws_public_url = msg["publicURL"]

            headers = {"Content-Type": "application/zip"}
            logging.info("Uploading the verifier to AWS...")
            http_request = requests.request(
                "PUT", verifier_upload_url, headers=headers, data=tempfile_verifier
            )
            http_request.raise_for_status()

        # Upload tasks
        prefix = f"BenchExec_tasks_{benchmark.instance}_"
        with tempfile.SpooledTemporaryFile(
            mode="w+b", prefix=prefix, suffix=".zip"
        ) as tempfile_tasks:
            logging.info("Building archive for the tasks...")
            _createArchiveFile(
                tempfile_tasks, toolpaths["absBaseDir"], toolpaths["absSourceFiles"]
            )

            tempfile_tasks.seek(0)  # resets the file pointer

            payload = {"file": prefix + ".zip"}
            url = REQUEST_URL["upload"].format(aws_endpoint, aws_token, requestId)
            logging.debug("Sending http-request for uploading tasks: \n%s", url)
            http_response = requests.get(
                url, params=payload, timeout=HTTP_REQUEST_TIMEOUT
            )
            http_response.raise_for_status()

            msg = http_response.json()
            tasks_upload_url = msg["uploadUrl"]
            tasks_s3_key = msg["S3Key"]
            tasks_aws_public_url = msg["publicURL"]

            headers = {"Content-Type": "application/zip"}
            logging.info("Uploading tasks to AWS...")
            http_request = requests.request(
                "PUT", tasks_upload_url, headers=headers, data=tempfile_tasks
            )
            http_request.raise_for_status()

        # Upload commands
        payload = {"file": "commands.json"}
        url = REQUEST_URL["upload"].format(aws_endpoint, aws_token, requestId)
        logging.debug("Sending http-request for uploading commands: \n%s", url)
        http_response = requests.get(url, params=payload, timeout=HTTP_REQUEST_TIMEOUT)
        http_response.raise_for_status()

        msg = http_response.json()
        commands_upload_url = msg["uploadUrl"]
        commands_s3_key = msg["S3Key"]

        payload = json.dumps(aws_input)
        headers = {"Content-Type": "application/json"}
        logging.info("Uploading the commands to AWS...")
        http_request = requests.request(
            "PUT", commands_upload_url, headers=headers, data=payload
        )
        http_request.raise_for_status()

        # Launch
        payload = {
            "verifier": verifier_aws_public_url,
            "verifierS3": verifier_s3_key,
            "tasks": tasks_aws_public_url,
            "tasksS3": tasks_s3_key,
            "commandsS3": commands_s3_key,
        }
        url = REQUEST_URL["launchBatch"].format(aws_endpoint, aws_token, requestId)
        logging.debug("Sending http-request for launch: \n%s", url)
        http_response = requests.get(url, params=payload, timeout=HTTP_REQUEST_TIMEOUT)
        http_response.raise_for_status()

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
            http_response = requests.get(progress_url, timeout=HTTP_REQUEST_TIMEOUT)
            # There is currently an issue on the server side in which the
            # status code of the response is on rare occasions not 200.
            # TODO: Once this is fixed, check the above http_response for a valid
            # status code (i.e., call raise_for_status() )

            msg = http_response.json()
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
        http_response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
        http_response.raise_for_status()
        for aws_s3_link in http_response.json()["urls"]:
            logging.debug("Handling url: %s", aws_s3_link)
            aws_s3_link_encoded = urllib.parse.quote(aws_s3_link, safe=":/")
            logging.debug("Downloading file from url: %s", aws_s3_link_encoded)
            result_file = requests.get(aws_s3_link_encoded)  # noqa: S113
            with zipfile.ZipFile(io.BytesIO(result_file.content)) as zipf:
                zipf.extractall(benchmark.log_folder)
    except KeyboardInterrupt:
        stop()
    finally:
        # Clean
        url = REQUEST_URL["clean"].format(aws_endpoint, aws_token)
        logging.debug(
            "Sending http-request for cleaning the aws services up: \n%s", url
        )
        requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)

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
        number_of_runs,
        limits_and_num_runs,
        run_definitions,
        source_files,
    ) = getBenchmarkData(benchmark)
    (working_dir, toolpaths) = getToolData(benchmark)

    abs_working_dir = os.path.abspath(working_dir)
    abs_tool_paths = list(map(os.path.abspath, toolpaths))
    abs_source_files = list(map(os.path.abspath, source_files))
    abs_base_dir = benchexec.util.common_base_dir(abs_source_files + abs_tool_paths)

    if abs_base_dir == "":
        raise BenchExecException("No common base dir found.")

    toolpaths = {
        "absBaseDir": abs_base_dir,
        "workingDir": working_dir,
        "absWorkingDir": abs_working_dir,
        "toolpaths": toolpaths,
        "absToolpaths": abs_tool_paths,
        "sourceFiles": source_files,
        "absSourceFiles": abs_source_files,
    }

    aws_input = {
        "requirements": requirements,
        "workingDir": os.path.relpath(abs_working_dir, abs_base_dir),
    }
    if benchmark.result_files_patterns:
        if len(benchmark.result_files_patterns) > 1:
            raise BenchExecException(
                "Multiple result-file patterns not supported in cloud mode."
            )
        aws_input.update({"resultFilePatterns": benchmark.result_files_patterns[0]})

    aws_input.update({"limitsAndNumRuns": limits_and_num_runs})
    aws_input.update({"runDefinitions": run_definitions})

    return (toolpaths, aws_input)


def _zipdir(path, zipfile, abs_base_dir):
    for root, _dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            zipfile.write(filepath, os.path.relpath(filepath, abs_base_dir))


def _createArchiveFile(archive_path, abs_base_dir, abs_paths):
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in abs_paths:
            if not os.path.exists(file):
                zipf.close()
                if os.path.isfile(archive_path):
                    os.remove(archive_path)

                raise BenchExecException(
                    f"Missing file '{os.path.normpath(file)}', "
                    f"cannot run benchmark without it."
                )

            if os.path.isdir(file):
                _zipdir(file, zipf, abs_base_dir)
            else:
                zipf.write(file, os.path.relpath(file, abs_base_dir))


def getBenchmarkData(benchmark):
    r = benchmark.requirements
    # These values are currently not used internally, but the goal is
    # to eventually integrate them in a later stage.
    if r.cpu_model is None:
        r.cpu_model = "AmazonAWS"
    if r.cpu_cores is None or r.memory is None:
        raise BenchExecException(
            "The entry for either the amount of used cpu cores or memory "
            "is missing from the benchmark definition"
        )
    requirements = {
        "cpu_cores": r.cpu_cores,
        "cpu_model": r.cpu_model,
        "memory_in_mb": bytes_to_mb(r.memory),
    }

    # get limits and number of runs
    time_limit = benchmark.rlimits.cputime_hard
    mem_limit = bytes_to_mb(benchmark.rlimits.memory)
    if time_limit is None or mem_limit is None:
        raise BenchExecException(
            "An entry for either the time- or memory-limit is missing "
            "in the benchmark definition"
        )

    core_limit = benchmark.rlimits.cpu_cores
    number_of_runs = sum(
        len(run_set.runs)
        for run_set in benchmark.run_sets
        if run_set.should_be_executed()
    )
    limits_and_num_runs = {
        "number_of_runs": number_of_runs,
        "time_limit_in_sec": time_limit,
        "mem_limit_in_mb": mem_limit,
    }
    if core_limit is not None:
        limits_and_num_runs.update({"core_limit": core_limit})

    # get runs with args and source_files
    source_files = set()
    run_definitions = []
    for run_set in benchmark.run_sets:
        if not run_set.should_be_executed():
            continue
        if STOPPED_BY_INTERRUPT:
            break

        # get runs
        for run in run_set.runs:
            run_definition = {}

            # wrap list-elements in quotations-marks if they contain whitespace
            cmdline = [f"'{x}'" if " " in x else x for x in run.cmdline()]
            cmdline = " ".join(cmdline)
            log_file = os.path.relpath(run.log_file, benchmark.log_folder)

            run_definition.update(
                {
                    "cmdline": cmdline,
                    "log_file": log_file,
                    "sourcefile": run.sourcefiles,
                    "required_files": run.required_files,
                }
            )

            run_definitions.append(run_definition)
            source_files.update(run.sourcefiles)
            source_files.update(run.required_files)

    if not run_definitions:
        raise BenchExecException("Benchmark has nothing to run.")

    return (
        requirements,
        number_of_runs,
        limits_and_num_runs,
        run_definitions,
        source_files,
    )


def getToolData(benchmark):
    working_dir = benchmark.working_directory()
    if not os.path.isdir(working_dir):
        raise BenchExecException(
            f"Missing working directory '{working_dir}', cannot run tool."
        )
    logging.debug("Working dir: %s", working_dir)

    toolpaths = benchmark.required_files()
    valid_toolpaths = set()
    for file in toolpaths:
        if not os.path.exists(file):
            raise BenchExecException(
                f"Missing file '{os.path.normpath(file)}', "
                f"not running benchmark without it."
            )
        for glob in benchexec.util.expand_filename_pattern(file, working_dir):
            valid_toolpaths.add(glob)

    return (working_dir, valid_toolpaths)


def bytes_to_mb(mb):
    if mb is None:
        return None
    return int(mb / 1000 / 1000)


def handleCloudResults(benchmark, output_handler, start_time, end_time):
    output_dir = benchmark.log_folder
    if not os.path.isdir(output_dir) or not os.listdir(output_dir):
        # output_dir does not exist or is empty
        logging.warning(
            "Received no results from AWS. Output-directory is missing or empty: %s",
            output_dir,
        )

    if start_time and end_time:
        used_wall_time = (end_time - start_time).total_seconds()
    else:
        used_wall_time = None

    # write results in runs and handle output after all runs are done
    executed_all_runs = True
    runs_produced_error_output = False
    for run_set in benchmark.run_sets:
        if not run_set.should_be_executed():
            output_handler.output_for_skipping_run_set(run_set)
            continue

        output_handler.output_before_run_set(run_set, start_time=start_time)

        for run in run_set.runs:
            data_file = run.log_file + ".data"

            if os.path.exists(data_file) and os.path.exists(run.log_file):
                try:
                    values = parse_aws_run_result_file(data_file)
                    if not benchmark.config.debug:
                        os.remove(data_file)
                except OSError as e:
                    logging.warning(
                        "Cannot extract measured values from output for file %s: %s",
                        run.identifier,
                        e,
                    )
                    output_handler.all_created_files.add(data_file)
                    output_handler.set_error("missing results", run_set)
                    executed_all_runs = False
                else:
                    output_handler.store_system_info(
                        values.get("aws_instance_os"),  # opSystem
                        values.get("aws_instance_cpu_name"),  # cpuModel
                        values.get("aws_instance_cores"),  # numCores
                        values.get("aws_instance_frequency"),  # max freq
                        values.get("aws_instance_memory"),  # memory
                        values.get("aws_instance_type"),  # hostname
                        run_set,  # runset
                        {},  # environment
                        None,  # cpu turboboost
                    )

                    output_handler.output_before_run(run)
                    run.set_result(values, ["host"])
                    output_handler.output_after_run(run)
            else:
                logging.warning("No results exist for file %s.", run.identifier)
                output_handler.set_error("missing results", run_set)
                executed_all_runs = False

            if os.path.exists(run.log_file + ".stdError"):
                runs_produced_error_output = True

            # Move all output files from "sibling of log-file" to
            # "sibling of parent directory".
            raw_path = run.log_file[: -len(".log")]
            dirname, filename = os.path.split(raw_path)
            aws_files_directory = raw_path + ".files"
            benchexec_files_directory = run.result_files_folder
            if os.path.isdir(aws_files_directory) and not os.path.isdir(
                benchexec_files_directory
            ):
                shutil.move(aws_files_directory, benchexec_files_directory)

        output_handler.output_after_run_set(
            run_set, walltime=used_wall_time, end_time=end_time
        )

    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

    if not executed_all_runs:
        logging.warning("Some expected result files could not be found!")
    if runs_produced_error_output and not benchmark.config.debug:
        logging.warning(
            "Some runs produced unexpected warnings on stderr, "
            "please check the %s files!",
            os.path.join(output_dir, "*.stdError"),
        )


def parse_aws_run_result_file(file_path):
    def read_items():
        with open(file_path, "rt") as file:
            for line in file:
                key, value = line.split("=", 1)
                yield key, value

    return parse_aws_run_result(read_items())


def parse_aws_run_result(values):
    result_values = collections.OrderedDict()

    def parse_time_value(s):
        if s[-1] != "s":
            raise ValueError(f'Cannot parse "{s}" as a time value.')
        return float(s[:-1])

    def set_exitcode(new):
        if "exitcode" in result_values:
            old = result_values["exitcode"]
            assert (
                old == new
            ), f"Inconsistent exit codes {old} and {new} from AWS execution"
        else:
            result_values["exitcode"] = new

    for key, value in values:
        value = value.strip()
        if key in ["cputime", "walltime"]:
            result_values[key] = parse_time_value(value)
        elif key == "memory":
            result_values["memory"] = benchexec.util.parse_memory_value(value)
        elif key == "exitcode":
            set_exitcode(benchexec.util.ProcessExitCode.from_raw(int(value)))
        elif key == "returnvalue":
            set_exitcode(benchexec.util.ProcessExitCode.create(value=int(value)))
        elif key == "exitsignal":
            set_exitcode(benchexec.util.ProcessExitCode.create(signal=int(value)))
        elif key == "aws_instance_frequency":
            result_values[key] = benchexec.util.parse_frequency_value(value)
        elif key in [
            "starttime",
            "aws_instance_os",
            "aws_instance_cpu_name",
            "aws_instance_cores",
            "aws_instance_memory",
            "aws_instance_type",
        ]:
            result_values[key] = value

    return result_values
