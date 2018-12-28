"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2015 Daniel Dietsch (dietsch@informatik.uni-freiburg.de)
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from . import ultimate


class Tool(ultimate.UltimateTool):
    """
    This is the tool info module for ULTIMATE Automizer.

    You can download the latest release from GitHub or build the latest development snapshot by following the
    instructions at https://github.com/ultimate-pa/ultimate/wiki/Usage

    Please report any issues to our issue tracker at https://github.com/ultimate-pa/ultimate/issues

    Latest release: https://github.com/ultimate-pa/ultimate/releases/latest
    Git repository: https://github.com/ultimate-pa/ultimate.git
    """

    REQUIRED_PATHS_SVCOMP17 = [
        "artifacts.xml",
        "AutomizerTermination.xml",
        "AutomizerWitnessValidation.xml",
        "AutomizerReach.xml",
        "AutomizerMemDerefMemtrack.xml",
        "configuration",
        "cvc4",
        "features",
        "LICENSE",
        "LICENSE.GPL",
        "LICENSE.GPL.LESSER",
        "p2",
        "plugins",
        "README",
        "svcomp-DerefFreeMemtrack-32bit-Automizer_Bitvector.epf",
        "svcomp-DerefFreeMemtrack-32bit-Automizer_Default.epf",
        "svcomp-DerefFreeMemtrack-64bit-Automizer_Bitvector.epf",
        "svcomp-DerefFreeMemtrack-64bit-Automizer_Default.epf",
        "svcomp-Overflow-32bit-Automizer_Default.epf",
        "svcomp-Overflow-64bit-Automizer_Default.epf",
        "svcomp-Reach-32bit-Automizer_Bitvector.epf",
        "svcomp-Reach-32bit-Automizer_Default.epf",
        "svcomp-Reach-64bit-Automizer_Bitvector.epf",
        "svcomp-Reach-64bit-Automizer_Default.epf",
        "svcomp-Termination-32bit-Automizer_Default.epf",
        "svcomp-Termination-64bit-Automizer_Default.epf",
        "Ultimate",
        "Ultimate.ini",
        "Ultimate.py",
        "z3",
        "mathsat"
    ]

    def name(self):
        return 'ULTIMATE Automizer'
