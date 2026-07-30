# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import re
import subprocess
import tempfile

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for AProVE.
    Only the binary (jar) distribution of AProVE is supported.
    """

    REQUIRED_PATHS = [
        "aprove.jar",
        "AProVE.sh",
        "bin",
        "newstrategy.strategy",
        "lib",
        "fake_include",
    ]
    BIT_WIDTH_PARAMETER_NAME = "--bit-width"

    def executable(self, tool_locator):
        return tool_locator.find_executable("AProVE.sh")

    def name(self):
        return "AProVE"

    def project_url(self):
        return "http://aprove.informatik.rwth-aachen.de/"

    def version(self, executable):
        with tempfile.NamedTemporaryFile(suffix=".c") as trivial_example:
            trivial_example.write(b"int main() { return 0; }\n")
            trivial_example.flush()

            cmd = [executable, trivial_example.name]
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except OSError as e:
                logging.warning("Unable to determine AProVE version: %s", e.strerror)
                return ""

            version_aprove_match = re.search(
                r"^# AProVE Commit ID: (.*)",
                process.stdout,
                re.MULTILINE,
            )
            if not version_aprove_match:
                logging.warning(
                    "Unable to determine AProVE version: %s",
                    process.stdout,
                )
                return ""
            return version_aprove_match.group(1)[:10]

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and self.BIT_WIDTH_PARAMETER_NAME not in options:
            options += [self.BIT_WIDTH_PARAMETER_NAME, data_model_param]

        return [executable, *options, task.single_input_file]

    def determine_result(self, run):
        if not run.output:
            return result.RESULT_ERROR

        first_output_line = run.output[0]
        if "YES" in first_output_line or "TRUE" in first_output_line:
            return result.RESULT_TRUE_PROP
        elif "FALSE" in first_output_line or "NO" in first_output_line:
            return result.RESULT_FALSE_TERMINATION
        else:
            return result.RESULT_UNKNOWN
