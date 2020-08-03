# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.coveriteam as coveriteam
import benchexec.result as result
import sys


class Tool(coveriteam.Tool):
    """
    Tool info for a verifier or a validator based on
    CoVeriTeam: a Configurable Software-Verification Platform.
    URL: https://gitlab.com/sosy-lab/software/coveriteam.
    """

    def name(self):
        return "CoVeriTeam-Verifier-Validator"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        """
        Prepare command for the example coveriteam program for a verifier.
        """
        # We expect one tasks and a propertyfile.
        if len(tasks) != 1 or not propertyfile:
            sys.exit(
                "Can't execute CoVeriTeam-Verifier-Validator."
                "Either propertyfile is missing or the number of tasks is not 1."
            )

        spec = ["--input", "spec_path=" + propertyfile]
        prog = ["--input", "prog_path=" + tasks[0]]
        additional_options = prog + spec

        return [executable] + options + additional_options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        It assumes that any verifier or validator implemented in CoVeriTeam
        will print out the produced aftifacts.
        If more than one dict is printed, the last one is taken.
        """
        res = {}
        for line in output:
            line = line.strip()
            if "verdict" in line:
                s = line.rstrip().strip("{}")
                # TODO find a better way to do it.
                # Reconstruct the dict from the printed string. Simple literal_eval does not work.
                for x in s.split(","):
                    k = x.split(":")[0].strip("\"' ")
                    v = x.split(":")[1].strip("\"' ")
                    res[k] = v
        return res.get("verdict", result.RESULT_ERROR)
