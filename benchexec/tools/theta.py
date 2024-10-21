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
        parsing_status = "before"
        for line in run.output:
            if "SafetyResult Unsafe" in line:
                status = result.RESULT_FALSE_REACH
            elif "SafetyResult Safe" in line:
                status = result.RESULT_TRUE_PROP
            elif "ParsingResult Success" in line:
                parsing_status = "after"

        if run.was_timeout:
            status = result.RESULT_TIMEOUT + f" ({parsing_status} parsing finished)"
        elif (
            not run.was_timeout
            and status == result.RESULT_UNKNOWN
            and run.exit_code.value != 0
        ):
            if run.exit_code.value == 1:
                status = f"ERROR (generic error, {parsing_status} parsing finished)"
            elif run.exit_code.value == 200:
                status = f"ERROR (out of memory, {parsing_status} parsing finished)"
            elif run.exit_code.value == 201:
                status = f"ERROR (inner timeout, {parsing_status} parsing finished)"
            elif run.exit_code.value == 202:
                status = f"ERROR (server error, {parsing_status} parsing finished)"
            elif run.exit_code.value == 203:
                status = f"ERROR (portfolio error, {parsing_status} parsing finished)"
            elif run.exit_code.value == 209:
                status = f"ERROR (Unsupported source element, {parsing_status} parsing finished)"
            elif run.exit_code.value == 210:
                status = f"ERROR (frontend failed, {parsing_status} parsing finished)"
            elif run.exit_code.value == 211:
                status = f"ERROR (invalid parameter, {parsing_status} parsing finished)"
            elif run.exit_code.value == 220:
                status = (
                    f"ERROR (verification stuck, {parsing_status} parsing finished)"
                )
            elif run.exit_code.value == 221:
                status = f"ERROR (solver error, {parsing_status} parsing finished)"
            else:
                status = result.RESULT_ERROR + f" ({parsing_status} parsing finished)"

        return status
