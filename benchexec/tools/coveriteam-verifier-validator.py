# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.coveriteam as coveriteam


class Tool(coveriteam.Tool):
    """
    Tool info for a verifier or a validator based on
    CoVeriTeam: a Configurable Software-Verification Platform.
    URL: https://gitlab.com/sosy-lab/software/coveriteam.
    """

    def name(self):
        return "Verifier (or Validator) Based on CoVeriTeam"

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
