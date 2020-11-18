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
import ast


class Tool(coveriteam.Tool):
    """
    Tool info for a verifier or a validator based on
    CoVeriTeam: a Configurable Software-Verification Platform.
    URL: https://gitlab.com/sosy-lab/software/coveriteam.
    """

    def cmdline(self, executable, options, task, rlimits):
        """
        Prepare command for the coveriteam program for a verifier or a validator.
        These two programs are shipped with the CoVeriTeam package,
        and can be used with multiple verifiers and validators.
        """

        data_model_param = get_data_model_from_task(
            task, {ILP32: "ILP32", LP64: "LP64"}
        )
        if data_model_param and "--data-model" not in options:
            options += ["--data-model", data_model_param]

        if task.property_file:
            options += ["--input", "spec_path=" + task.property_file]
        else:
            raise UnsupportedFeatureException(
                "Can't execute CoVeriTeam-Verifier-Validator: "
                "Specification is missing."
            )

        options += ["--input", "prog_path=" + task.single_input_file]

        return [executable] + options

    def determine_result(self, run):
        """
        It assumes that any verifier or validator implemented in CoVeriTeam
        will print out the produced aftifacts.
        If more than one dict is printed, the first matching one.
        """
        for line in run.output:
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
