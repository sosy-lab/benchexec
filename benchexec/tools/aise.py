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
    Tool info for AISE.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("aise", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )


    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + list(task.input_files_or_identifier)

    def name(self):
        return "AISE"

    def version(self, executable):
        return "AISE 1.0.0"

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
            if line.startswith("KLEE: ERROR: "):
                if line.find("ASSERTION FAIL:") != -1:
                    return result.RESULT_FALSE_REACH
        for line in run.output:
            if line.startswith("CLAM ERROR:"):
                return f"ERROR ({run.exit_code.value})"
            if line.startswith("KLEE: WARNING"):
                if line.find("silently concretizing") != -1:
                    return result.RESULT_UNKNOWN
            if line.startswith("KLEE: ERROR: "):
                if line.find("memory error: out of bound pointer") != -1:
                    return result.RESULT_FALSE_DEREF
                elif line.find("overflow") != -1:
                    return result.RESULT_FALSE_OVERFLOW
                elif line.find("abort failure") != -1:
                    continue
                elif line.find("concretized symbolic size") != -1:
                    return result.RESULT_UNKNOWN
                else:
                    return f"ERROR ({run.exit_code.value})"

            if line.startswith("KLEE: done"):
                if "AISE_VERIFICATION_TRUE" in line:
                    return result.RESULT_TRUE_PROP
                elif "AISE_VERIFICATION_FALSE" in line:
                    return result.RESULT_FALSE_REACH
                elif "AISE_VERIFICATION_UNKNOWN" in line:
                    return result.RESULT_UNKNOWN
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        # search for the text in output and get its value,
        # stop after the first line, that contains the searched text
        for line in lines:
            if (
                line.startswith("KLEE: done: ") or line.startswith("AISE: done: ")
            ) and line.find(identifier + " = ") != -1:
                startPosition = line.rfind("=") + 2
                return line[startPosition:].strip()
            elif line.find("Number of total " + identifier) != -1:
                endPosition = line.find(" Number")
                return line[0:endPosition].strip()
        return None
