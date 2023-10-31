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
    Test-Case Generation Git Branch: https://github.com/ultimate-pa/ultimate/tree/TestGeneration
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
        treeautomizer_sat = "TreeAutomizerSatResult"
        treeautomizer_unsat = "TreeAutomizerUnsatResult"
        unsupported_syntax_errorstring = "ShortDescription: Unsupported Syntax"
        incorrect_syntax_errorstring = "ShortDescription: Incorrect Syntax"
        type_errorstring = "Type Error"
        witness_errorstring = "InvalidWitnessErrorResult"
        exception_errorstring = "ExceptionOrErrorResult"
        safety_string = "Ultimate proved your program to be correct"
        all_spec_string = "AllSpecificationsHoldResult"
        unsafety_string = "Ultimate proved your program to be incorrect"
        mem_deref_false_string = "pointer dereference may fail"
        mem_deref_false_string_2 = "array index can be out of bounds"
        mem_free_false_string = "free of unallocated memory possible"
        mem_memtrack_false_string = "not all allocated memory was freed"
        termination_false_string = (
            "Found a nonterminating execution for the following "
            "lasso shaped sequence of statements"
        )
        termination_true_string = "TerminationAnalysisResult: Termination proven"
        ltl_false_string = "execution that violates the LTL property"
        ltl_true_string = "Buchi Automizer proved that the LTL property"
        overflow_false_string = "overflow possible"

        for line in run.output:
            if line.startswith("DONE"):
                return result.RESULT_DONE
            if unsupported_syntax_errorstring in line:
                return "ERROR: UNSUPPORTED SYNTAX"
            if incorrect_syntax_errorstring in line:
                return "ERROR: INCORRECT SYNTAX"
            if type_errorstring in line:
                return "ERROR: TYPE ERROR"
            if witness_errorstring in line:
                return "ERROR: INVALID WITNESS FILE"
            if exception_errorstring in line:
                return "ERROR: EXCEPTION"
            if self._contains_overapproximation_result(line):
                return "UNKNOWN: OverapproxCex"
            if termination_false_string in line:
                return result.RESULT_FALSE_TERMINATION
            if termination_true_string in line:
                return result.RESULT_TRUE_PROP
            if ltl_false_string in line:
                return "FALSE(valid-ltl)"
            if ltl_true_string in line:
                return result.RESULT_TRUE_PROP
            if unsafety_string in line:
                return result.RESULT_FALSE_REACH
            if mem_deref_false_string in line:
                return result.RESULT_FALSE_DEREF
            if mem_deref_false_string_2 in line:
                return result.RESULT_FALSE_DEREF
            if mem_free_false_string in line:
                return result.RESULT_FALSE_FREE
            if mem_memtrack_false_string in line:
                return result.RESULT_FALSE_MEMTRACK
            if overflow_false_string in line:
                return result.RESULT_FALSE_OVERFLOW
            if safety_string in line or all_spec_string in line:
                return result.RESULT_TRUE_PROP
            if treeautomizer_unsat in line:
                return "unsat"
            if treeautomizer_sat in line or all_spec_string in line:
                return "sat"

        return result.RESULT_UNKNOWN

    @staticmethod
    def _determine_result_with_property_file(run):
        for line in run.output:
            if line.startswith("DONE"):
                return result.RESULT_DONE
            elif line.startswith("FALSE(valid-free)"):
                return result.RESULT_FALSE_FREE
            elif line.startswith("FALSE(valid-deref)"):
                return result.RESULT_FALSE_DEREF
            elif line.startswith("FALSE(valid-memtrack)"):
                return result.RESULT_FALSE_MEMTRACK
            elif line.startswith("FALSE(valid-memcleanup)"):
                return result.RESULT_FALSE_MEMCLEANUP
            elif line.startswith("FALSE(TERM)"):
                return result.RESULT_FALSE_TERMINATION
            elif line.startswith("FALSE(OVERFLOW)"):
                return result.RESULT_FALSE_OVERFLOW
            elif line.startswith("FALSE"):
                return result.RESULT_FALSE_REACH
            elif line.startswith("TRUE"):
                return result.RESULT_TRUE_PROP
            elif line.startswith("UNKNOWN"):
                return result.RESULT_UNKNOWN
            elif line.startswith("ERROR"):
            	if not line.startswith("ERROR: Caught known exception: Unsupported non-linear arithmetic"):
                    status = result.RESULT_ERROR
                    if line.startswith("ERROR: INVALID WITNESS FILE"):
                        status += " (invalid witness file)"
                    return status
        return result.RESULT_UNKNOWN
