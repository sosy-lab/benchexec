# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.util as util
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for CoVeriTeam: On-Demand Composition of Cooperative Verification Systems.
    URL: https://gitlab.com/sosy-lab/software/coveriteam.

    This class has 2 purposes:
        1. to serve as an abstract class for specific coveriteam programs like verifiers, validators, etc.
        2. to serve as the tool info module for any generic coveritea program.
    """

    # TODO: I am not sure about the following folders:
    # 1. examples and config: should be included or not? It can also be dealt with the required files tag in the behchdef.
    # 2. tools and toolinfocache: these are cache folders. Isn't it better just to wrap them in one folder called cache?
    # To be resolved before the final merge.
    REQUIRED_PATHS = [
        "coveriteam",
        "bin",
        "lib",
        "examples",
        "config",
        "tools",
        "toolinfocache",
    ]

    def __init__(self):
        super().__init__()

    def executable(self):
        return util.find_executable("bin/coveriteam")

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return [executable] + self.REQUIRED_PATHS

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        """
        CoVeriTeam in general, wouldn't be used on its own.
        Instead, we expect a tool to inherit from this class and that be executed.
        That tool should define its own cmdline method.
        """
        return [executable] + options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        This function will be useful in case of a verifier and a validator.
        It assumes that any verifier or validator implemented in CoVeriTeam
        will print out the produced aftifacts in the end.
        """

        # Assumption: the result dict is printed last
        s = output[-1].rstrip().strip("{}")
        # Reconstruct the dict from the printed string. Simple literal_eval does not work.
        res = {}
        for x in s.split(","):
            k = x.split(":")[0].strip("\"' ")
            v = x.split(":")[1].strip("\"' ")
            res[k] = v
        return res.get("verdict", result.RESULT_ERROR)
