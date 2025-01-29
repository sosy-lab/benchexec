# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for tbf test-suite validator.
    """

    REQUIRED_PATHS = ["python_modules", "lib", "bin"]

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def executable(self):
        return util.find_executable(
            "tbf-testsuite-validator", "bin/tbf-testsuite-validator"
        )

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Tbf Test-suite Validator"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/test-format"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in reversed(output):
            if line.startswith("ERROR:"):
                if "timeout" in line.lower():
                    return result.RESULT_TIMEOUT
                else:
                    return f"ERROR ({returncode})"
            elif line.startswith("Result:") and "FALSE" in line:
                return result.RESULT_FALSE_REACH
            elif line.startswith("Result:") and "TRUE" in line:
                return result.RESULT_TRUE_PROP
            elif line.startswith("Result") and "DONE" in line:
                return result.RESULT_DONE
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
