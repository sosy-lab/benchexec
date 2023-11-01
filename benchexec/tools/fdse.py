# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
import benchexec.model
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64

class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for FDSE (https://github.com/zbchen/FDSE).
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("fdse")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return "fdse-testcomp"

    def cmdline(self, executable, options, task, rlimits):
        new_option = ["--testcomp"]
        if task.property_file:
            new_option += [f"--property-file={task.property_file}"]
        if rlimits.cputime:
            new_option += [f"-mt={rlimits.cputime}"]
        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})

        if data_model_param and "--arch" not in options:
            new_option += ["--arch=" + data_model_param]

        new_option += [f"-sf={task.single_input_file}"]
        return [executable] + new_option + options

    def name(self):
        return "FDSE"

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
        for line in run.output:
            if "[BUG]" in line:
                if line.find("ASSERTION FAIL!") != -1:
                    return result.RESULT_FALSE_REACH
                elif line.find("Index out-of-bound") != -1:
                    return result.RESULT_FALSE_DEREF
                elif line.find("overflow") != -1:
                    return result.RESULT_FALSE_OVERFLOW
                else:
                    return f"ERROR ({run.exit_code.value})"
            if "Done : End analysis" in line:
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, run):
        status = result.RESULT_UNKNOWN

        if run.output.any_line_contains("DONE"):
            status = result.RESULT_DONE

        return status
