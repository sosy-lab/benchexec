# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for fizzer.
    """

    REQUIRED_PATHS = ["lib", "lib32", "tools"]

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        This method always needs to be overriden, and typically just contains
        return "My Toolname"
        @return a non-empty string
        """
        return "Fizzer"

    def project_url(self):
        return "https://github.com/staticafi/sbt-fizzer"

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
        return tool_locator.find_executable("sbt-fizzer.py")

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

        compilation = None
        instrumentation = None
        linking = None
        termination_type = None
        termination_reason = None
        error_message = None
        fuzzing_stats_found = False
        for line in run.output:
            if fuzzing_stats_found is False:
                if line.startswith("Fuzzing was stopped. Details:"):
                    fuzzing_stats_found = True
                elif "Compiling...Done[" in line:
                    compilation = True
                elif "Instrumenting...Done[" in line:
                    instrumentation = True
                elif "Linking...Done[" in line:
                    linking = True
                continue
            if line.startswith("Optimization was stopped. Details:"):
                break
            line = line.strip()
            if "termination_type" in line:
                termination_type = line.split(": ")[1].split('"')[1]
            elif "termination_reason" in line:
                termination_reason = line.split(": ")[1].split('"')[1]
            elif "error_message" in line:
                error_message = line.split(": ")[1].split('"')[1]
            if termination_type is not None and termination_reason is not None:
                break

        # Now we are ready to compute the result string.

        def result_string(error_code, message=None):
            return error_code + ("" if message is None else " (" + message + ")")

        if compilation is None:
            return result_string(result.RESULT_ERROR, "compilation")
        elif instrumentation is None:
            return result_string(result.RESULT_ERROR, "instrumentation")
        elif linking is None:
            return result_string(result.RESULT_ERROR, "linking")

        if termination_type in [
            "SERVER_INTERNAL_ERROR",
            "CLIENT_COMMUNICATION_ERROR",
            "UNCLASSIFIED_ERROR",
        ]:
            result_code = result.RESULT_ERROR
            termination_reason = (
                error_message if error_message is not None else termination_reason
            )
        elif termination_type != "NORMAL":
            result_code = result.RESULT_UNKNOWN
        elif termination_reason in [
            "ALL_REACHABLE_BRANCHINGS_COVERED",
            "FUZZING_STRATEGY_DEPLETED",
            "EXECUTIONS_BUDGET_DEPLETED",
            "TIME_BUDGET_DEPLETED",
        ]:
            result_code = result.RESULT_DONE
        else:
            result_code = result.RESULT_UNKNOWN

        return result_string(
            result_code, str(termination_type) + "," + str(termination_reason)
        )
