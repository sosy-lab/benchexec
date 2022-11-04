# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
import logging

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for ABC: A System for Sequential Synthesis and Verification
    URL: https://people.eecs.berkeley.edu/~alanmi/abc/
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("abc", subdir="bin")

    def name(self):
        return "ABC"

    def cmdline(self, executable, options, task, rlimits):
        return (
            [executable]
            + ["-c", "&r {}; &put".format(task.single_input_file)]
            + options
        )

    def determine_result(self, run):
        """
        @return: status of ABC after executing a run
        """
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        status = None
        for line in run.output:
            if line.startswith("Property proved") or line.startswith(
                "Networks are equivalent"
            ):
                status = result.RESULT_TRUE_PROP
            elif "was asserted in frame" in line or line.startswith(
                "Networks are NOT EQUIVALENT"
            ):
                status = result.RESULT_FALSE_PROP
            elif line.startswith("Networks are UNDECIDED"):
                status = result.RESULT_UNKNOWN
        if not status:
            status = result.RESULT_ERROR
        return status

    def get_value_from_output(self, output, identifier):
        # search for the identifier in the output and return the number after it
        # the number can be an integer, a decimal, or a scientific notation
        # warn if there are repeated matches (multiple statistics from sequential analysis?)
        regex_integer = r"(\d+)"
        regex_decimal = r"(\d+\.\d*|\d*\.\d+)"
        regex_scinote = r"(\d\.?\d*[Ee][+\-]?\d+)"
        regex_pattern = (
            re.escape(identifier)
            + r"\s*[:=]?\s*(-?("
            + regex_integer
            + r"|"
            + regex_decimal
            + r"|"
            + regex_scinote
            + r"))(\s|$)"
        )
        regex = re.compile(regex_pattern)
        match = None
        for line in output:
            result = regex.search(line)
            if result:
                if match is None:
                    match = result.group(1)
                else:
                    logging.warning(
                        "skipping repeated matches for identifier '%s': '%s'",
                        identifier,
                        line,
                    )
        return match
