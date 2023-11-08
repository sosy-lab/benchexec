# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging

import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for BTOR2C: A Converter from BTOR2 models to C programs
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("btor2code", subdir="build")

    def name(self):
        return "BTOR2C"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/btor2c"

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def get_value_from_output(self, output, identifier):
        # search for the text in output and get its value,
        # search the first line, that starts with the searched text
        # warn if there are more lines (multiple statistics from sequential analysis?)
        match = None
        for line in output:
            if line.lstrip().startswith(identifier):
                startPosition = line.find(":") + 1
                endPosition = line.find("(", startPosition)
                if endPosition == -1:
                    endPosition = len(line)
                if match is None:
                    match = line[startPosition:endPosition].strip()
                else:
                    logging.warning(
                        "skipping repeated match for identifier '%s': '%s'",
                        identifier,
                        line,
                    )
        return match
