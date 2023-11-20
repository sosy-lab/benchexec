# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for CETFUZZ
    An Automatic Test Suit Generator

    Testing tool namely cetfuzz for testing C programs. Our tool uses AFL++, a
    genetic algorithm based fuzz test generator as a basic building block.
    AFL++ is parameterised to enable a user to configure fuzzing by assigning
    permissible values to its parameters. It supports several parameters yielding
    to a large number of configurations. Finding an optimal configuration for
    maximising given test objective (specified via a property) for a given C
    program is a challenging task. We have selected 20 most important  AFL++
    configurations based on some heuristics. We trained a supervised model that
    can infer one out of the 20 as the best configurations for the given
    test objective and the program. We use AFL++ to fuzz the program with
    the suggested configuration and output the test vectors for validation.
    """

    REQUIRED_PATH = [
        "fuzzer",
        "verifier_codes",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("runTool.py")

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def name(self):
        return "cetfuzz"

    def project_url(self):
        return "https://gitlab.com/Sarathkrishnan/cetfuzz"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyFile", task.property_file]

        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and "--bit" not in options:
            options += ["--bit", data_model_param]

        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        for line in run.output:
            if "TEST_SUIT_CREATED" in line:
                return result.RESULT_DONE
            elif "NOT_SUPPORTED" in line or "CETFUZZ_UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
