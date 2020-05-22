# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    Symbiotic tool info object
    """

    REQUIRED_PATHS = [
        "bin",
        "include",
        "share",
        "instrumentations",
        "lib",
        "lib32",
        "symbiotic",
    ]

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable("symbiotic")

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return self._version_from_tool(executable, arg="--version-short")

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return "symbiotic"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        if propertyfile is not None:
            options = options + ["--prp={0}".format(propertyfile)]

        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return "timeout"

        if output is None:
            return "error (no output)"

        for line in output:
            line = line.strip()
            if line == "TRUE":
                return result.RESULT_TRUE_PROP
            elif line == "UNKNOWN":
                return result.RESULT_UNKNOWN
            elif line.startswith("FALSE (valid-deref)"):
                return result.RESULT_FALSE_DEREF
            elif line.startswith("FALSE (valid-free)"):
                return result.RESULT_FALSE_FREE
            elif line.startswith("FALSE (valid-memtrack)"):
                return result.RESULT_FALSE_MEMTRACK
            elif line.startswith("FALSE (overflow)"):
                return result.RESULT_FALSE_OVERFLOW
            elif line.startswith("FALSE"):
                return result.RESULT_FALSE_REACH

        return result.RESULT_ERROR
