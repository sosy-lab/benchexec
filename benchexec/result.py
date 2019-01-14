# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import functools
import os
import sys
from benchexec import BenchExecException

# CONSTANTS

# categorization of a run result
# 'correct' and 'wrong' refer to whether the tool's result matches the expected result.
# 'confirmed' and 'unconfirmed' refer to whether the tool's result was confirmed (e.g., by witness validation)
CATEGORY_CORRECT = 'correct'
"""run result given by tool is correct (we use 'correct' instead of 'correct-confirmed')"""

CATEGORY_CORRECT_UNCONFIRMED = 'correct-unconfirmed'
"""run result given by tool is correct but not confirmed"""

CATEGORY_WRONG   = 'wrong'
"""run result given by tool is wrong (we use 'wrong' instead of 'wrong-unconfirmed')"""

#CATEGORY_WRONG_CONFIRMED   = 'wrong-confirmed'
"""run result given by tool is wrong but confirmed by result validation"""

CATEGORY_UNKNOWN = 'unknown'
"""run result given by tool is "unknown" (i.e., no answer)"""

CATEGORY_ERROR   = 'error'
"""tool failed, crashed, or hit a resource limit"""

CATEGORY_MISSING = 'missing'
"""BenchExec could not determine whether run result was correct or wrong
because no property was defined, and no other categories apply."""


# internal property names used in this module (should not contain spaces)
# previously used by SV-COMP (http://sv-comp.sosy-lab.org/2014/rules.php):
_PROP_LABEL =        'unreach-label'
# currently used by SV-COMP (http://sv-comp.sosy-lab.org/2016/rules.php):
_PROP_CALL =         'unreach-call'
_PROP_TERMINATION =  'termination'
_PROP_OVERFLOW =     'no-overflow'
_PROP_DEADLOCK =     'no-deadlock'
_PROP_DEREF =        'valid-deref'
_PROP_FREE =         'valid-free'
_PROP_MEMTRACK =     'valid-memtrack'
_PROP_MEMCLEANUP =     'valid-memcleanup'
# for Java verification:
_PROP_ASSERT =       'assert'
# specification given as an automaton:
_PROP_AUTOMATON =    'observer-automaton'
# for solvers:
_PROP_SAT =          'sat'
# internal meta property
_PROP_MEMSAFETY =    'valid-memsafety'

# possible run results (output of a tool)
RESULT_DONE = 'done'
"""tool terminated properly and true/false does not make sense"""
RESULT_UNKNOWN =            'unknown'
"""tool could not find out an answer due to incompleteness"""
RESULT_ERROR =              'ERROR' # or any other value not listed here
"""tool could not complete due to an error
(it is recommended to instead use a string with more details about the error)"""
RESULT_TRUE_PROP =          'true'
"""property holds"""
RESULT_FALSE_PROP = 'false'
"""property does not hold"""
RESULT_FALSE_REACH =        RESULT_FALSE_PROP + '(' + _PROP_CALL + ')'
_RESULT_FALSE_REACH_OLD =   RESULT_FALSE_PROP + '(reach)'
"""SV-COMP reachability property violated"""
RESULT_FALSE_TERMINATION =  RESULT_FALSE_PROP + '(' + _PROP_TERMINATION + ')'
"""SV-COMP termination property violated"""
RESULT_FALSE_OVERFLOW =     RESULT_FALSE_PROP + '(' + _PROP_OVERFLOW    + ')'
"""SV-COMP overflow property violated"""
RESULT_FALSE_DEADLOCK =     RESULT_FALSE_PROP + '(' + _PROP_DEADLOCK    + ')'
"""deadlock property violated""" # not yet part of SV-COMP
RESULT_FALSE_DEREF =        RESULT_FALSE_PROP + '(' + _PROP_DEREF       + ')'
"""SV-COMP valid-deref property violated"""
RESULT_FALSE_FREE =         RESULT_FALSE_PROP + '(' + _PROP_FREE        + ')'
"""SV-COMP valid-free property violated"""
RESULT_FALSE_MEMTRACK =     RESULT_FALSE_PROP + '(' + _PROP_MEMTRACK    + ')'
"""SV-COMP valid-memtrack property violated"""
RESULT_FALSE_MEMCLEANUP =   RESULT_FALSE_PROP + '(' + _PROP_MEMCLEANUP  + ')'
"""SV-COMP valid-memcleanup property violated"""
RESULT_WITNESS_CONFIRMED =  'witness confirmed'
"""SV-COMP property violated and witness confirmed"""
RESULT_SAT =                'sat'
"""task is satisfiable"""
RESULT_UNSAT =              'unsat'
"""task is unsatisfiable"""

# List of all possible results.
# If a result is not in this list, it is handled as RESULT_CLASS_OTHER.
RESULT_LIST = [RESULT_TRUE_PROP,
               RESULT_FALSE_PROP,
               RESULT_FALSE_REACH,
               _RESULT_FALSE_REACH_OLD,
               RESULT_FALSE_TERMINATION,
               RESULT_FALSE_DEREF, RESULT_FALSE_FREE, RESULT_FALSE_MEMTRACK,
               RESULT_FALSE_MEMCLEANUP,
               RESULT_WITNESS_CONFIRMED,
               RESULT_SAT, RESULT_UNSAT,
               RESULT_FALSE_OVERFLOW, RESULT_FALSE_DEADLOCK
               ]
RESULT_LIST_OTHER = [RESULT_DONE, RESULT_ERROR, RESULT_UNKNOWN]
"""list of unspecific standard results besides true/false"""

# Classification of results
RESULT_CLASS_TRUE    = 'true'
RESULT_CLASS_FALSE   = 'false'
RESULT_CLASS_OTHER = 'other'

# This maps content of property files to property name.
_PROPERTY_NAMES = {'LTL(G ! label(':                    _PROP_LABEL,
                   'LTL(G ! call(__VERIFIER_error()))': _PROP_CALL,
                   'LTL(F end)':                        _PROP_TERMINATION,
                   'LTL(G valid-free)':                 _PROP_FREE,
                   'LTL(G valid-deref)':                _PROP_DEREF,
                   'LTL(G valid-memtrack)':             _PROP_MEMTRACK,
                   'LTL(G valid-memcleanup)':           _PROP_MEMCLEANUP,
                   'OBSERVER AUTOMATON':                _PROP_AUTOMATON,
                   'SATISFIABLE':                       _PROP_SAT,
                   'LTL(G ! overflow)':                 _PROP_OVERFLOW,
                   'LTL(G ! deadlock)':                 _PROP_DEADLOCK,
                  }

# This maps a possible result substring of a file name
# to the expected result string of the tool and the set of properties
# for which this result is relevant.
_FILE_RESULTS = {
              '_true-unreach-label':   (RESULT_TRUE_PROP, {_PROP_LABEL}),
              '_true-unreach-call':    (RESULT_TRUE_PROP, {_PROP_CALL}),
              '_true_assert':          (RESULT_TRUE_PROP, {_PROP_ASSERT}),
              '_true-termination':     (RESULT_TRUE_PROP, {_PROP_TERMINATION}),
              '_true-valid-deref':     (RESULT_TRUE_PROP, {_PROP_DEREF}),
              '_true-valid-free':      (RESULT_TRUE_PROP, {_PROP_FREE}),
              '_true-valid-memtrack':  (RESULT_TRUE_PROP, {_PROP_MEMTRACK}),
              '_true-valid-memcleanup':(RESULT_TRUE_PROP, {_PROP_MEMCLEANUP}),
              '_true-valid-memsafety': (RESULT_TRUE_PROP, {_PROP_DEREF, _PROP_FREE, _PROP_MEMTRACK}),
              '_true-no-overflow':     (RESULT_TRUE_PROP, {_PROP_OVERFLOW}),
              '_true-no-deadlock':     (RESULT_TRUE_PROP, {_PROP_DEADLOCK}),

              '_false-unreach-label':  (RESULT_FALSE_REACH,       {_PROP_LABEL}),
              '_false-unreach-call':   (RESULT_FALSE_REACH,       {_PROP_CALL}),
              '_false_assert':         (RESULT_FALSE_REACH,       {_PROP_ASSERT}),
              '_false-termination':    (RESULT_FALSE_TERMINATION, {_PROP_TERMINATION}),
              '_false-valid-deref':    (RESULT_FALSE_DEREF,       {_PROP_DEREF}),
              '_false-valid-free':     (RESULT_FALSE_FREE,        {_PROP_FREE}),
              '_false-valid-memtrack': (RESULT_FALSE_MEMTRACK,    {_PROP_MEMTRACK}),
              '_false-valid-memcleanup':(RESULT_FALSE_MEMCLEANUP, {_PROP_MEMCLEANUP}),
              '_false-no-overflow':    (RESULT_FALSE_OVERFLOW,    {_PROP_OVERFLOW}),
              '_false-no-deadlock':    (RESULT_FALSE_DEADLOCK,    {_PROP_DEADLOCK}),

              '_sat':                  (RESULT_SAT,   {_PROP_SAT}),
              '_unsat':                (RESULT_UNSAT, {_PROP_SAT}),
              }

_MEMSAFETY_SUBPROPERTIES = {_PROP_DEREF, _PROP_FREE, _PROP_MEMTRACK}

# Map a property to all possible results for it.
_VALID_RESULTS_PER_PROPERTY = {
    _PROP_ASSERT:      {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_LABEL:       {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_CALL:        {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_AUTOMATON:   {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_DEREF:       {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_DEREF},
    _PROP_FREE:        {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_FREE},
    _PROP_MEMTRACK:    {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_MEMTRACK},
    _PROP_MEMSAFETY:   {RESULT_TRUE_PROP, RESULT_FALSE_DEREF, RESULT_FALSE_FREE, RESULT_FALSE_MEMTRACK},
    _PROP_MEMCLEANUP:  {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_MEMCLEANUP},
    _PROP_OVERFLOW:    {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_OVERFLOW},
    _PROP_DEADLOCK:    {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_DEADLOCK},
    _PROP_TERMINATION: {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_TERMINATION},
    _PROP_SAT:         {RESULT_SAT, RESULT_UNSAT},
    }

# Score values taken from http://sv-comp.sosy-lab.org/
# (use values 0 to disable scores completely for a given property).
_SCORE_CORRECT_TRUE = 2
_SCORE_CORRECT_UNCONFIRMED_TRUE = 1
_SCORE_CORRECT_FALSE = 1
_SCORE_CORRECT_UNCONFIRMED_FALSE = 0
_SCORE_UNKNOWN = 0
_SCORE_WRONG_FALSE = -16
_SCORE_WRONG_TRUE = -32


ExpectedResult = collections.namedtuple("ExpectedResult", "result subproperty")
"""Stores the expected result and respective information for a task"""

class Property(object):
    """Stores information about a property"""

    def __init__(self, filename, is_well_known, is_svcomp, name, subproperties):
        self.filename = filename
        self.is_well_known = is_well_known
        self.is_svcomp = is_svcomp
        self.name = name
        self.subproperties = subproperties

    @property
    def names(self):
        return self.subproperties or [self.name]

    def compute_score(self, category, result):
        if not self.is_svcomp:
            return 0
        return _svcomp_score(category, result)

    def max_score(self, expected_result):
        """
        Return the maximum possible score for a task that uses this property.
        @param expected_result:
            an ExpectedResult indicating whether the property is expected to hold for the task
        """
        if not self.is_svcomp or not expected_result:
            return 0
        return _svcomp_max_score(expected_result.result)

    def __repr__(self):
        return "{}({self.filename!r}, {self.is_well_known!r}, {self.is_svcomp!r}, {self.name!r}, {self.subproperties!r})".format(self.__class__.__name__, self=self)

    def __str__(self):
        return (("SV-COMP-" if self.is_svcomp else "")
            + "Property "
            + (self.name if self.is_well_known else "from " + self.filename))

    @classmethod
    @functools.lru_cache() # cache because it reads files
    def create(cls, propertyfile, allow_unknown):
        """
        Create a Property instance by attempting to parse the given property file.
        @param propertyfile: A file name of a property file
        @param allow_unknown: Whether to accept unknown properties
        """
        with open(propertyfile) as f:
            content = f.read().strip()

        # parse content for known properties
        is_svcomp = False
        known_properties = []
        only_known_svcomp_property = True

        if content == 'OBSERVER AUTOMATON' or content == 'SATISFIABLE':
            known_properties = [_PROPERTY_NAMES[content]]

        elif content.startswith('CHECK'):
            is_svcomp = True
            for line in filter(None, content.splitlines()):
                if content.startswith('CHECK'):
                    # SV-COMP property, either a well-known one or a new one
                    props_in_line = [
                        prop for (substring, prop) in _PROPERTY_NAMES.items() if substring in line]
                    if len(props_in_line) == 1:
                        known_properties.append(props_in_line[0])
                    else:
                        only_known_svcomp_property = False
                else:
                    # not actually an SV-COMP property file
                    is_svcomp = False
                    known_properties = []
                    break

        # check if some known property content was found
        subproperties = None
        if only_known_svcomp_property and len(known_properties) == 1:
            is_well_known = True
            name = known_properties[0]

        elif only_known_svcomp_property and set(known_properties) == _MEMSAFETY_SUBPROPERTIES:
            is_well_known = True
            name = _PROP_MEMSAFETY
            subproperties = list(known_properties)

        else:
            if not allow_unknown:
                raise BenchExecException(
                    'File "{0}" does not contain a known property.'.format(propertyfile))
            is_well_known = False
            name = os.path.splitext(os.path.basename(propertyfile))[0]

        return cls(propertyfile, is_well_known, is_svcomp, name, subproperties)

    @classmethod
    def create_from_names(cls, property_names):
        """
        Create a Property instance from a list of well-known property names
        @param property_names: a non-empty list of property names
        """
        assert property_names

        if len(property_names) == 1:
            name = property_names[0]
            subproperties = None
        else:
            name = (_PROP_MEMSAFETY if set(property_names) == _MEMSAFETY_SUBPROPERTIES
                    else "unknown property")
            subproperties = list(property_names)

        is_well_known = name in _VALID_RESULTS_PER_PROPERTY.keys()
        is_svcomp = is_well_known and (_PROP_SAT not in property_names)

        return cls(None, is_well_known, is_svcomp, name, subproperties)


def expected_results_of_file(filename):
    """Create a dict of property->ExpectedResult from information encoded in a filename."""
    results = {}
    for (filename_part, (expected_result, for_properties)) in _FILE_RESULTS.items():
        if filename_part in filename:
            expected_result_class = get_result_classification(expected_result)
            assert expected_result_class in {RESULT_CLASS_TRUE, RESULT_CLASS_FALSE}
            expected_result = (expected_result_class == RESULT_CLASS_TRUE)
            subproperty = None
            if len(for_properties) > 1:
                assert for_properties == _MEMSAFETY_SUBPROPERTIES and expected_result
                property = _PROP_MEMSAFETY
            else:
                property = next(iter(for_properties))
                if property in _MEMSAFETY_SUBPROPERTIES and not expected_result:
                    subproperty = property
                    property = _PROP_MEMSAFETY
            if property in results:
                raise BenchExecException(
                    "Duplicate property {} in filename {}".format(property, filename))
            results[property] = ExpectedResult(expected_result, subproperty)
    return results

def _expected_result(filename, checked_properties):
    results = []
    for (filename_part, (expected_result, for_properties)) in _FILE_RESULTS.items():
        if filename_part in filename \
                and for_properties.intersection(checked_properties):
            results.append(expected_result)
    if not results:
        # No expected result for any of the properties
        return None
    if len(results) > 1:
        # Multiple checked properties per file not supported
        return None
    return results[0]


def _svcomp_max_score(expected_result):
    """
    Return the maximum possible score for a task according to the SV-COMP scoring scheme.
    @param expected_result: whether the property is fulfilled for the task or not
    """
    if expected_result == True:
        return _SCORE_CORRECT_TRUE
    elif expected_result == False:
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

def score_for_task(properties, category, result):
    """
    Return the possible score of task, depending on whether the result is correct or not.
    """
    assert result is not None
    if properties and Property.create_from_names(properties).is_svcomp:
        return _svcomp_score(category, result)
    return None


def get_result_classification(result):
    '''
    Classify the given result into "true" (property holds),
    "false" (property does not hold), "unknown", and "error".
    @param result: The result given by the tool (needs to be one of the RESULT_* strings to be recognized).
    @return One of RESULT_CLASS_* strings
    '''
    if result not in RESULT_LIST:
        if result and result.startswith(RESULT_FALSE_PROP + "(") and result.endswith(")"):
            return RESULT_CLASS_FALSE
        return RESULT_CLASS_OTHER

    if result == RESULT_TRUE_PROP or result == RESULT_SAT:
        return RESULT_CLASS_TRUE
    else:
        return RESULT_CLASS_FALSE


def get_result_category(expected_results, result, properties):
    '''
    This function determines the relation between actual result and expected result
    for the given file and properties.
    @param filename: The file name of the input file.
    @param result: The result given by the tool (needs to be one of the RESULT_* strings to be recognized).
    @param properties: The list of property names to check.
    @return One of the CATEGORY_* strings.
    '''
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

    if prop.is_well_known:
        # for well-known properties, only support hard-coded results
        is_valid_result = result in _VALID_RESULTS_PER_PROPERTY[prop.name]
    elif expected_result.subproperty:
        is_valid_result = result in {
            RESULT_TRUE_PROP, RESULT_FALSE_PROP + "(" + expected_result.subproperty + ")"}
    else:
        is_valid_result = (result == RESULT_TRUE_PROP) or result.startswith(RESULT_FALSE_PROP)

    if not is_valid_result:
        return CATEGORY_UNKNOWN # result does not match property

    if expected_result.result:
        return CATEGORY_CORRECT if result_class == RESULT_CLASS_TRUE else CATEGORY_WRONG
    else:
        if expected_result.subproperty:
            return CATEGORY_CORRECT if result == RESULT_FALSE_PROP + "(" + expected_result.subproperty + ")" else CATEGORY_WRONG
        else:
            return CATEGORY_CORRECT if result_class == RESULT_CLASS_FALSE else CATEGORY_WRONG

