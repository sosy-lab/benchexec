# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template
import benchexec.model


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for FairFuzz.
    """

    REQUIRED_PATHS = ["bin", "helper"]

    def executable(self):
        return util.find_executable("bin/fairfuzz-svtestcomp")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        version = self._version_from_tool(executable, line_prefix="FairFuzz")
        return version.split("Version ")[1]

    def name(self):
        return "FairFuzz"

    def project_url(self):
        return "https://https://github.com/carolemieux/afl-rb/tree/testcomp"

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
        for line in output:
            if "All test cases time out or crash, giving up!" in line:
                return "Couldn't run: all seeds time out or crash"
            if "ERROR: couldn't run FairFuzz" in line:
                return "Couldn't run FairFuzz"
            if "CRASHES FOUND" in line:
                return result.RESULT_FALSE_REACH
            if "DONE RUNNING" in line:
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN
