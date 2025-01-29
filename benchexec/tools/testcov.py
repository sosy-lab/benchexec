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
    Tool info for TestCov.
    """

    REQUIRED_PATHS = ["suite_validation", "lib", "bin"]

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def executable(self, tool_locator):
        return tool_locator.find_executable("testcov", subdir="bin")

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "-32", LP64: "-64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        cmd = [executable] + options
        if task.property_file:
            cmd += ["--goal", task.property_file]

        return cmd + list(task.input_files_or_identifier)

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "TestCov"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/test-suite-validator"

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in reversed(run.output):
            if line.startswith("ERROR:"):
                if "timeout" in line.lower():
                    return result.RESULT_TIMEOUT
                else:
                    return f"ERROR ({run.exit_code.value})"
            elif line.startswith("Result: FALSE"):
                return result.RESULT_FALSE_REACH
            elif line.startswith("Result: TRUE"):
                return result.RESULT_TRUE_PROP
            elif line.startswith("Result: DONE"):
                return result.RESULT_DONE
            elif line.startswith("Result: ERROR"):
                # matches ERROR and ERROR followed by some reason in parantheses
                # e.g., "ERROR (TRUE)" or "ERROR(TRUE)"
                return re.search(r"ERROR(\s*\(.*\))?", line).group(0)
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        for line in reversed(lines):
            pattern = identifier
            if pattern[-1] != ":":
                pattern += ":"
            match = re.match(f"^{pattern}([^(]*)", line)
            if match and match.group(1):
                return match.group(1).strip()
        return None
