# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.coveriteam as coveriteam
import benchexec.result as result
from benchexec.tools.template import UnsupportedFeatureException
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import re

class Tool(coveriteam.Tool):
    """
    Tool infor for Graves, a verifier selector based on Graph Neural Networks 
    We inherit Coveriteam's infrastructure. 
    """

    REQUIRED_PATHS = [
        "coveriteam",
        "bin",
        "lib",
        "depends",
        "predict",
        "predict/build",
    ]

    def name(self):
        return "Graves"

    def executable(self, tool_locator):
        return tool_locator.find_executable("graves.sh")

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        """
        Modified from the CoVeriTeam definition
        """

        if task.property_file:
            options += [task.property_file]
        else:
            raise UnsupportedFeatureException(
                "Can't execute Graves: "
                "Specification is missing."
            )

        options += [task.single_input_file]

        return [executable] + options

    def determine_result(self, run):
        """
        It assumes that any verifier or validator implemented in CoVeriTeam
        will print out the produced aftifacts.
        If more than one dict is printed, the first matching one.
        """
        verdict = None
        verdict_regex = re.compile(r"'verdict': '([a-zA-Z\(\)\ \-]*)'")
        for line in reversed(run.output):
            line = line.strip()
            verdict_match = verdict_regex.search(line)
            if verdict_match and verdict is None:
                # CoVeriTeam outputs benchexec result categories as verdicts.
                verdict = verdict_match.group(1)
            if "Traceback (most recent call last)" in line:
                verdict = "EXCEPTION"
        if verdict is None:
            return result.RESULT_UNKNOWN
        return verdict