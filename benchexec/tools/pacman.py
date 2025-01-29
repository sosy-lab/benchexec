# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Wrapper for PAC-MAN
    """

    REQUIRED_PATHS = [
        "array",
        "build.sh",
        "CPAchecker-1.4-svn",
        "crest-0.1.2",
        "genWitness",
        "ocaml",
        "pacman.sh",
        "releases",
        "scripts",
        "yices-1.0.40",
    ]

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        The path returned should be relative to the current directory.
        """
        executable = util.find_executable("pacman.sh")
        return executable

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return "PAC-MAN"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        status = result.RESULT_UNKNOWN
        if "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        return status
