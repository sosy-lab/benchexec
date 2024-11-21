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
    Tool info for Btor2C: A translator from Btor2 circuits to C programs
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("btor2c", subdir="build")

    def name(self):
        return "Btor2C"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/btor2c"

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="Btor2C version")

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def get_value_from_output(self, output, identifier):
        # search for the text in output and get its value,
        # search the first line, that starts with the searched text
        # warn if there are more lines
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
