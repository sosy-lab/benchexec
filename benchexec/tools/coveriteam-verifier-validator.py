# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.coveriteam as coveriteam
import benchexec.result as result
from benchexec.tools.template import UnsupportedFeatureException
import ast


class Tool(coveriteam.Tool):
    """
    Tool info for a verifier or a validator based on
    CoVeriTeam: a Configurable Software-Verification Platform.
    URL: https://gitlab.com/sosy-lab/software/coveriteam.
    """

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        """
        Prepare command for the coveriteam program for a verifier or a validator.
        These two programs are shipped with the CoVeriTeam package,
        and can be used with multiple verifiers and validators.
        """
        self.check_inputs(tasks, propertyfile)

        spec = ["--input", "spec_path=" + propertyfile]
        prog = ["--input", "prog_path=" + tasks[0]]
        additional_options = prog + spec

        return [executable] + options + additional_options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        It assumes that any verifier or validator implemented in CoVeriTeam
        will print out the produced aftifacts.
        If more than one dict is printed, the first matching one.
        """
        for line in output:
            line = line.strip()
            if "verdict" in line:
                # CoVeriTeam outputs benchexec result categories as verdicts.
                try:
                    d = ast.literal_eval(line)
                    if isinstance(d, dict):
                        return d.get("verdict", result.RESULT_ERROR)
                except SyntaxError:
                    pass
        return result.RESULT_ERROR

    def check_inputs(self, tasks, propertyfile):
        # We expect one tasks and a propertyfile.
        if not tasks:
            raise UnsupportedFeatureException(
                "Can't execute CoVeriTeam-Verifier-Validator: "
                "Input program is missing."
            )
        if len(tasks) > 1:
            raise UnsupportedFeatureException(
                "Can't execute CoVeriTeam-Verifier-Validator: "
                "Too many input files to analyze"
            )
        if not propertyfile:
            raise UnsupportedFeatureException(
                "Can't execute CoVeriTeam-Verifier-Validator: "
                "Specification is missing."
            )
