# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
import logging

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
        return [executable] + options + [task.single_input_file]

    def get_value_from_output(self, output, identifier):
        # search for the identifier in the output and return the number after it
        # the number can be an integer, a decimal, or a scientific notation
        # warn if there are repeated matches (multiple statistics from sequential analysis?)
        regex_integer = r"(\d+)"
        regex_decimal = r"(\d+\.\d*|\d*\.\d+)"
        regex_scinote = r"(\d\.?\d*[Ee][+\-]?\d+)"
        regex_pattern = (
            re.escape(identifier)
            + r"\s*[:=]\s*(-?("
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
