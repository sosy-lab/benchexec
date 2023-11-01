# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2016-2020 Daniel Dietsch <dietsch@informatik.uni-freiburg.de>
# SPDX-FileCopyrightText: 2016-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from . import ultimate
import benchexec.result as result


class Tool(ultimate.UltimateTool):
    """
    This is the tool info module for ULTIMATE TestGen.

    You can download the latest release from GitHub or build the latest development snapshot by following the
    instructions at https://github.com/ultimate-pa/ultimate/wiki/Usage

    Please report any issues to our issue tracker at https://github.com/ultimate-pa/ultimate/issues

    Latest release: https://github.com/ultimate-pa/ultimate/releases/latest
    Git repository: https://github.com/ultimate-pa/ultimate.git
    """

    REQUIRED_PATHS_SVCOMP17 = [
        "artifacts.xml",
        "configuration",
        "cvc4",
        "features",
        "LICENSE",
        "LICENSE.GPL",
        "LICENSE.GPL.LESSER",
        "p2",
        "plugins",
        "README",
        "testcomp-CoverEdges-32bit-Automizer_Bitvector.epf",
        "testcomp-CoverEdges-32bit-Automizer_Default.epf",
        "testcomp-CoverEdges-64bit-Automizer_Bitvector.epf",
        "testcomp-CoverEdges-64bit-Automizer_Default.epf",
        "testcomp-CoverError-32bit-Automizer_Bitvector.epf",
        "testcomp-CoverError-32bit-Automizer_Default.epf",
        "testcomp-CoverError-64bit-Automizer_Bitvector.epf",
        "testcomp-CoverError-64bit-Automizer_Default.epf",
        "AutomizerCTestGeneratorCoverEdges.xml",
        "AutomizerCTestGeneratorCoverError.xml",
        "Ultimate",
        "Ultimate.ini",
        "Ultimate.py",
        "z3",
        "mathsat",
    ]

    def name(self):
        return "ULTIMATE TestGen"

    def _determine_result_without_property_file(self, run):
        # special strings in ultimate output
        unsupported_syntax_errorstring = "ShortDescription: Unsupported Syntax"
        incorrect_syntax_errorstring = "ShortDescription: Incorrect Syntax"
        type_errorstring = "Type Error"
        exception_errorstring = "ExceptionOrErrorResult"

        for line in run.output:
            if unsupported_syntax_errorstring in line:
                return "ERROR: UNSUPPORTED SYNTAX"
            if incorrect_syntax_errorstring in line:
                return "ERROR: INCORRECT SYNTAX"
            if type_errorstring in line:
                return "ERROR: TYPE ERROR"
            if exception_errorstring in line:
                return "ERROR: EXCEPTION"
            if self._contains_overapproximation_result(line):
                return "UNKNOWN: OverapproxCex"
            if line.startswith("DONE"):
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN

    @staticmethod
    def _determine_result_with_property_file(run):
        for line in run.output:
            if line.startswith("DONE"):
                return result.RESULT_DONE
            elif line.startswith("UNKNOWN"):
                return result.RESULT_UNKNOWN
            elif line.startswith("ERROR"):
                return result.RESULT_ERROR
        return result.RESULT_UNKNOWN
