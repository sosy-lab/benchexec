# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class SatProofCheckerBase(benchexec.tools.template.BaseTool2):
    """
    Base class for SATnproof checker tools that use the standardized output format
    from the SAT Competition: a line starting with "s VERIFIED" on success or
    "s ERROR" on failure.
    """

    def determine_result(self, run):
        for line in reversed(run.output):
            if line.startswith("s "):
                verdict = line.removeprefix("s ").strip().upper()
                if verdict.startswith("VERIFIED"):
                    return result.RESULT_TRUE_PROP
                if verdict.startswith("NOT VERIFIED"):
                    return result.RESULT_FALSE_PROP
                elif "ERROR" in verdict:
                    return result.RESULT_ERROR
        return result.RESULT_ERROR

    def cmdline(self, executable, options, task, rlimits):
        return [executable, task.single_input_file, *options]
