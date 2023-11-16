# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2016-2020 Daniel Dietsch <dietsch@informatik.uni-freiburg.de>
# SPDX-FileCopyrightText: 2016-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from . import ultimate


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
