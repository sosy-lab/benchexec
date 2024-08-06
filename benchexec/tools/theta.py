# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0
import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Theta
    A generic, modular and configurable model checking framework developed
    at the Critical Systems Research Group of Budapest University
    of Technology and Economics, aiming to support the design and
    evaluation of abstraction refinement-based algorithms for the
    reachability analysis of various formalisms.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("theta-start.sh")

    def name(self):
        return "Theta"

    def project_url(self):
        return "https://github.com/ftsrg/theta"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        # Theta supports data race and unreach call
        if task.property_file:
            options += ["--property", task.property_file]
        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model:
                options += ["--architecture", data_model]

        return [executable, task.single_input_file] + options

    def determine_result(self, run):
        if run.was_terminated:
            return result.RESULT_ERROR
        status = result.RESULT_UNKNOWN
        for line in run.output:
            if "SafetyResult Unsafe" in line:
                status = result.RESULT_FALSE_REACH
            elif "SafetyResult Safe" in line:
                status = result.RESULT_TRUE_PROP
            elif "ParsingResult Success" in line:
                status = "Parsing OK"

        if (
            not run.was_timeout
            and status == result.RESULT_UNKNOWN
            and run.exit_code.value != 0
        ):
            if run.exit_code.value == 1:
                status = "ERROR (generic error)"
            elif run.exit_code.value == 200:
                status = "ERROR (out of memory)"
            elif run.exit_code.value == 201:
                status = "ERROR (inner timeout)"
            elif run.exit_code.value == 202:
                status = "ERROR (server error)"
            elif run.exit_code.value == 203:
                status = "ERROR (portfolio error)"
            elif run.exit_code.value == 210:
                status = "ERROR (frontend failed)"
            elif run.exit_code.value == 211:
                status = "ERROR (invalid parameter)"
            elif run.exit_code.value == 220:
                status = "ERROR (verification stuck)"
            elif run.exit_code.value == 221:
                status = "ERROR (solver error)"
            else:
                status = result.RESULT_ERROR

        return status
