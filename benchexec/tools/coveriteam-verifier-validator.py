# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.coveriteam as coveriteam
import benchexec.result as result


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
        spec = (
            ["--input", "spec_path=" + propertyfile] if propertyfile is not None else []
        )
        # We don't support more than one tasks at the moment.
        prog = ["--input", "prog_path=" + tasks[0]]
        additional_options = prog + spec

        return [executable] + options + additional_options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        This function will be useful in case of a verifier and a validator.
        It assumes that any verifier or validator implemented in CoVeriTeam
        will print out the produced aftifacts in the end.
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
