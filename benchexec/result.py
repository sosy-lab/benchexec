# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import functools
import os
import re

# CONSTANTS

# categorization of a run result
# 'correct' and 'wrong' refer to whether the tool's result matches the expected result.
CATEGORY_CORRECT = "correct"
"""run result given by tool is correct"""

CATEGORY_CORRECT_UNCONFIRMED = "correct-unconfirmed"
"""run result given by tool is correct but not confirmed according to SV-COMP rules"""

CATEGORY_WRONG = "wrong"
"""run result given by tool is wrong"""

CATEGORY_UNKNOWN = "unknown"
"""run result given by tool is "unknown" (i.e., no answer)"""

CATEGORY_ERROR = "error"
"""tool failed, crashed, or hit a resource limit"""

CATEGORY_MISSING = "missing"
"""BenchExec could not determine whether run result was correct or wrong
because no property was defined, and no other categories apply."""

# possible run results (output of a tool)
RESULT_DONE = "done"
"""tool terminated properly and true/false does not make sense"""
RESULT_UNKNOWN = "unknown"
"""tool could not find out an answer due to incompleteness"""
RESULT_ERROR = "ERROR"  # or any other value not listed here
"""tool could not complete due to an error
(it is recommended to instead use a string with more details about the error)"""
RESULT_TRUE_PROP = "true"
"""property holds"""
RESULT_FALSE_PROP = "false"
"""property does not hold"""

# shortcuts for tool-info modules that return results as required in SV-COMP
RESULT_FALSE_REACH = RESULT_FALSE_PROP + "(unreach-call)"
"""SV-COMP reachability property violated"""
RESULT_FALSE_TERMINATION = RESULT_FALSE_PROP + "(termination)"
"""SV-COMP termination property violated"""
RESULT_FALSE_OVERFLOW = RESULT_FALSE_PROP + "(no-overflow)"
"""SV-COMP overflow property violated"""
RESULT_FALSE_DEADLOCK = RESULT_FALSE_PROP + "(no-deadlock)"
"""deadlock property violated"""  # not yet part of SV-COMP
RESULT_FALSE_DEREF = RESULT_FALSE_PROP + "(valid-deref)"
"""SV-COMP valid-deref property violated"""
RESULT_FALSE_FREE = RESULT_FALSE_PROP + "(valid-free)"
"""SV-COMP valid-free property violated"""
RESULT_FALSE_MEMTRACK = RESULT_FALSE_PROP + "(valid-memtrack)"
"""SV-COMP valid-memtrack property violated"""
RESULT_FALSE_MEMCLEANUP = RESULT_FALSE_PROP + "(valid-memcleanup)"
"""SV-COMP valid-memcleanup property violated"""

RESULT_LIST_OTHER = [RESULT_DONE, RESULT_ERROR, RESULT_UNKNOWN]
"""list of unspecific standard results besides true/false"""

# Classification of results
RESULT_CLASS_TRUE = "true"
RESULT_CLASS_FALSE = "false"
RESULT_CLASS_OTHER = "other"

# Score values taken from http://sv-comp.sosy-lab.org/
# (use values 0 to disable scores completely for a given property).
_SCORE_CORRECT_TRUE = 2
_SCORE_CORRECT_UNCONFIRMED_TRUE = 0
_SCORE_CORRECT_FALSE = 1
_SCORE_CORRECT_UNCONFIRMED_FALSE = 0
_SCORE_UNKNOWN = 0
_SCORE_WRONG_FALSE = -16
_SCORE_WRONG_TRUE = -32


class ExpectedResult(collections.namedtuple("ExpectedResult", "result subproperty")):
    """Stores the expected result and respective information for a task"""

    __slots__ = ()  # reduce per-instance memory consumption

    def __str__(self):
        result = {True: "true", False: "false"}.get(self.result, "")
        if result and self.subproperty:
            return f"{result}({self.subproperty})"
        return result

    @classmethod
    def from_str(cls, s):
        if s == "":
            return ExpectedResult(None, None)
        match = re.match(r"^(true|false)(\((.+)\))?$", s)
        if not match:
            raise ValueError(f"Not a valid expected verdict: {s}")
        return ExpectedResult(match.group(1) == "true", match.group(3))


class Property(collections.namedtuple("Property", "filename is_svcomp name")):
    """Stores information about a property"""

    __slots__ = ()  # reduce per-instance memory consumption

    def compute_score(self, category, result):
        if not self.is_svcomp:
            return None
        return _svcomp_score(category, result)

    def max_score(self, expected_result):
        """
        Return the maximum possible score for a task that uses this property.
        @param expected_result:
            an ExpectedResult indicating whether the property is expected to hold for the task
        """
        if not self.is_svcomp or not expected_result:
            return None
        return _svcomp_max_score(expected_result.result)

    @property
    def nice_name(self):
        return (
            ("SV-COMP-" if self.is_svcomp else "")
            + "Property "
            + (f"from {self.filename}" if self.filename else self.name)
        )

    def __str__(self):
        return self.name

    @classmethod
    @functools.lru_cache()  # cache because it reads files
    def create(cls, propertyfile):
        """
        Create a Property instance by attempting to parse the given property file.
        @param propertyfile: A file name of a property file
        """
        with open(propertyfile) as f:
            # SV-COMP property files have every non-empty line start with CHECK,
            # and there needs to be at least one such line.
            is_svcomp = False
            for line in f.readlines():
                if line.rstrip():
                    if line.startswith("CHECK"):
                        # Found line with CHECK, might be an SV-COMP property
                        is_svcomp = True
                    else:
                        # Found line without CHECK, definitely not an SV-COMP property
                        is_svcomp = False
                        break

        name = os.path.splitext(os.path.basename(propertyfile))[0]

        return cls(propertyfile, is_svcomp, name)


def _svcomp_max_score(expected_result):
    """
    Return the maximum possible score for a task according to the SV-COMP scoring scheme.
    @param expected_result: whether the property is fulfilled for the task or not
    """
    if expected_result is True:
        return _SCORE_CORRECT_TRUE
    elif expected_result is False:
        return _SCORE_CORRECT_FALSE
    return 0


def _svcomp_score(category, result):
    """
    Return the achieved score of a task according to the SV-COMP scoring scheme.
    @param category: result category as determined by get_result_category
    @param result: the result given by the tool
    """
    assert result is not None
    result_class = get_result_classification(result)

    if category == CATEGORY_CORRECT_UNCONFIRMED:
        if result_class == RESULT_CLASS_TRUE:
            return _SCORE_CORRECT_UNCONFIRMED_TRUE
        elif result_class == RESULT_CLASS_FALSE:
            return _SCORE_CORRECT_UNCONFIRMED_FALSE
        else:
            assert False

    elif category == CATEGORY_CORRECT:
        if result_class == RESULT_CLASS_TRUE:
            return _SCORE_CORRECT_TRUE
        elif result_class == RESULT_CLASS_FALSE:
            return _SCORE_CORRECT_FALSE
        else:
            assert False, result

    elif category == CATEGORY_WRONG:
        if result_class == RESULT_CLASS_TRUE:
            return _SCORE_WRONG_TRUE
        elif result_class == RESULT_CLASS_FALSE:
            return _SCORE_WRONG_FALSE
        else:
            assert False

    else:
        return _SCORE_UNKNOWN


def get_result_classification(result):
    """
    Classify the given result into "true" (property holds),
    "false" (property does not hold), "unknown", and "error".
    @param result: The result given by the tool (needs to be one of the RESULT_* strings to be recognized).
    @return One of RESULT_CLASS_* strings
    """
    if not result:
        return RESULT_CLASS_OTHER

    if result == RESULT_FALSE_PROP:
        return RESULT_CLASS_FALSE

    if result.startswith(RESULT_FALSE_PROP + "(") and result.endswith(")"):
        return RESULT_CLASS_FALSE

    if result == RESULT_TRUE_PROP:
        return RESULT_CLASS_TRUE

    return RESULT_CLASS_OTHER


def get_result_category(expected_results, result, properties):
    """
    This function determines the relation between actual result and expected result
    for the given file and properties.
    @param filename: The file name of the input file.
    @param result: The result given by the tool (needs to be one of the RESULT_* strings to be recognized).
    @param properties: The list of property names to check.
    @return One of the CATEGORY_* strings.
    """
    result_class = get_result_classification(result)
    if result_class == RESULT_CLASS_OTHER:
        if result == RESULT_UNKNOWN:
            return CATEGORY_UNKNOWN
        elif result == RESULT_DONE:
            return CATEGORY_MISSING
        else:
            return CATEGORY_ERROR

    if not properties:
        # Without property we cannot return correct or wrong results.
        return CATEGORY_MISSING

    # For now, we have at most one property
    assert len(properties) == 1, properties
    prop = properties[0]

    expected_result = expected_results.get(prop.filename)
    if not expected_result or expected_result.result is None:
        # expected result of task is unknown
        return CATEGORY_MISSING

    if expected_result.subproperty:
        is_valid_result = result in {
            RESULT_TRUE_PROP,
            f"{RESULT_FALSE_PROP}({expected_result.subproperty})",
        }
    else:
        is_valid_result = (result == RESULT_TRUE_PROP) or result.startswith(
            RESULT_FALSE_PROP
        )

    if not is_valid_result:
        return CATEGORY_UNKNOWN  # result does not match property

    if expected_result.result:
        return CATEGORY_CORRECT if result_class == RESULT_CLASS_TRUE else CATEGORY_WRONG
    else:
        if expected_result.subproperty:
            return (
                CATEGORY_CORRECT
                if result == f"{RESULT_FALSE_PROP}({expected_result.subproperty})"
                else CATEGORY_WRONG
            )
        else:
            return (
                CATEGORY_CORRECT
                if result_class == RESULT_CLASS_FALSE
                else CATEGORY_WRONG
            )
