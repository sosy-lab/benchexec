# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for TestCoCa.
    """

    REQUIRED_PATHS = ["lib", "lib32", "tools"]

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        This method always needs to be overriden, and typically just contains
        return "My Toolname"
        @return a non-empty string
        """
        return "TestCoCa"

    def project_url(self):
        return "https://github.com/staticafi/TestCoCa"

    def executable(self, tool_locator):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and should typically delegate to our utility method find_executable. Example:
        return tool_locator.find_executable("mytool")
        The path returned should be relative to the current directory.
        @param tool_locator: an instance of class ToolLocator
        @return a string pointing to an executable file
        """
        return tool_locator.find_executable("TestCoCa.py")

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        Do not hard-code a version in this function, either extract the version
        from the tool or do not return a version at all.
        There is a helper function `self._version_from_tool`
        that should work with most tools, you only need to extract the version number
        from the returned tool output.
        @return a (possibly empty) string
        """
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.
        All paths passed to this method (executable and fields of task)
        are either absolute or have been made relative to the designated working directory.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param task: An instance of of class Task, e.g., with the input files
        @param rlimits: An instance of class ResourceLimits with the limits for this run
        @return a list of strings that represent the command line to execute
        """
        data_model = get_data_model_from_task(task, {ILP32: ["--m32"], LP64: []})
        if data_model is None:
            data_model = []

        if task.property_file:
            options += ["--goal", task.property_file]

        return (
            [executable, "--input_file", task.single_input_file] + options + data_model
        )

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        For tools that do not output some true/false result, benchexec.result.RESULT_DONE
        can be returned (this is also the default implementation).
        BenchExec will then automatically add some more information

        if the tool was killed due to a timeout, segmentation fault, etc.
        @param run: information about the run as instanceof of class Run
        @return a non-empty string, usually one of the benchexec.result.RESULT_* constants
        """
        if not run.output:
            return result.RESULT_UNKNOWN

        for line in run.output:
            line = line.strip()

            if "Result: DONE" in line:
                return result.RESULT_DONE

            if "Result: TRUE" in line:
                return result.RESULT_TRUE_PROP

        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        pattern = identifier

        if pattern[-1] != ":":
            pattern += ":"

        for line in reversed(lines):
            match = re.match(f"^{pattern}([^(]*)", line)
            if match and match.group(1):
                if identifier == "Coverage":
                    return float(match.group(1).strip()) * 100
                return int(match.group(1).strip())

        return None
