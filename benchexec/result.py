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

import os
import sys

# CONSTANTS

# categorization of a run result
CATEGORY_CORRECT = 'correct'
"""run result given by tool was correct"""

CATEGORY_WRONG   = 'wrong'
"""run result given by tool was wrong"""

CATEGORY_UNKNOWN = 'unknown'
"""run result given by tool was "unknown" (i.e., no answer)"""

CATEGORY_ERROR   = 'error'
"""tool failed, crashed, or hit a resource limit"""

CATEGORY_MISSING = 'missing'
"""BenchExec could not determine whether run result was correct or wrong
because no property was defined, and no other categories apply."""


# property names used in this module (should not contain spaces)
_PROP_LABEL =        'unreach-label'
_PROP_CALL =         'unreach-call'
_PROP_TERMINATION =  'termination'
_PROP_DEREF =        'valid-deref'
_PROP_FREE =         'valid-free'
_PROP_MEMTRACK =     'valid-memtrack'
_PROP_ASSERT =       'assert'
_PROP_AUTOMATON =    'observer-automaton'
_PROP_SAT =          'sat'
_PROP_OVERFLOW =     'no-overflow'

STR_FALSE = 'false' # only for special cases. STR_FALSE is no official result, because property is missing

# possible run results (output of a tool)
RESULT_UNKNOWN =            'unknown'
RESULT_ERROR =              'ERROR' # or any other value not listed here
RESULT_TRUE_PROP =          'true'
RESULT_FALSE_REACH =        STR_FALSE + '(reach)'
RESULT_FALSE_TERMINATION =  STR_FALSE + '(' + _PROP_TERMINATION + ')'
RESULT_FALSE_DEREF =        STR_FALSE + '(' + _PROP_DEREF       + ')'
RESULT_FALSE_FREE =         STR_FALSE + '(' + _PROP_FREE        + ')'
RESULT_FALSE_MEMTRACK =     STR_FALSE + '(' + _PROP_MEMTRACK    + ')'
RESULT_WITNESS_CONFIRMED =  'witness confirmed'
RESULT_SAT =                'sat'
RESULT_UNSAT =              'unsat'
RESULT_FALSE_OVERFLOW =     STR_FALSE + '(' + _PROP_OVERFLOW    + ')'

# List of all possible results.
# If a result is not in this list, it is handled as RESULT_CLASS_ERROR.
RESULT_LIST = [RESULT_TRUE_PROP, RESULT_UNKNOWN,
               RESULT_FALSE_REACH, RESULT_FALSE_TERMINATION,
               RESULT_FALSE_DEREF, RESULT_FALSE_FREE, RESULT_FALSE_MEMTRACK,
               RESULT_WITNESS_CONFIRMED,
               RESULT_SAT, RESULT_UNSAT,
               RESULT_FALSE_OVERFLOW
               ]

# Classification of results
RESULT_CLASS_TRUE    = 'true'
RESULT_CLASS_FALSE   = 'false'
RESULT_CLASS_UNKNOWN = 'unknown'
RESULT_CLASS_ERROR   = 'error'

# This maps content of property files to property name.
_PROPERTY_NAMES = {'LTL(G ! label(':                    _PROP_LABEL,
                   'LTL(G ! call(__VERIFIER_error()))': _PROP_CALL,
                   'LTL(F end)':                        _PROP_TERMINATION,
                   'LTL(G valid-free)':                 _PROP_FREE,
                   'LTL(G valid-deref)':                _PROP_DEREF,
                   'LTL(G valid-memtrack)':             _PROP_MEMTRACK,
                   'OBSERVER AUTOMATON':                _PROP_AUTOMATON,
                   'SATISFIABLE':                       _PROP_SAT,
                   'LTL(G ! overflow)':                 _PROP_OVERFLOW,
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
              '_true-valid-memsafety': (RESULT_TRUE_PROP, {_PROP_DEREF, _PROP_FREE, _PROP_MEMTRACK}),
              '_true-no-overflow':     (RESULT_TRUE_PROP, {_PROP_OVERFLOW}),

              '_false-unreach-label':  (RESULT_FALSE_REACH,       {_PROP_LABEL}),
              '_false-unreach-call':   (RESULT_FALSE_REACH,       {_PROP_CALL}),
              '_false_assert':         (RESULT_FALSE_REACH,       {_PROP_ASSERT}),
              '_false-termination':    (RESULT_FALSE_TERMINATION, {_PROP_TERMINATION}),
              '_false-valid-deref':    (RESULT_FALSE_DEREF,       {_PROP_DEREF}),
              '_false-valid-free':     (RESULT_FALSE_FREE,        {_PROP_FREE}),
              '_false-valid-memtrack': (RESULT_FALSE_MEMTRACK,    {_PROP_MEMTRACK}),
              '_false-no-overflow':    (RESULT_FALSE_OVERFLOW,    {_PROP_OVERFLOW}),

              '_sat':                  (RESULT_SAT,   {_PROP_SAT}),
              '_unsat':                (RESULT_UNSAT, {_PROP_SAT}),
              }

# Score values taken from http://sv-comp.sosy-lab.org/
# If different scores should be used depending on the checked property,
# change score_for_task() appropriately
# (use values 0 to disable scores completely for a given property).
_SCORE_CORRECT_TRUE = 2
_SCORE_CORRECT_FALSE = 1
_SCORE_UNKNOWN = 0
_SCORE_WRONG_FALSE = -16
_SCORE_WRONG_TRUE = -32


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


def properties_of_file(propertyfile):
    """
    Return a list of property names that should be checked according to the given property file.
    @param propertyfile: None or a file name of a property file.
    @return: A possibly empty list of property names.
    """
    assert os.path.isfile(propertyfile)

    with open(propertyfile) as f:
        content = f.read().strip()
    if not( 'CHECK' in content
            or content == 'OBSERVER AUTOMATON'
            or content == 'SATISFIABLE'
            ):
        sys.exit('File "{0}" is not a valid property file.'.format(propertyfile))

    properties = []
    # TODO: should we switch to regex or line-based reading?
    for substring, status in _PROPERTY_NAMES.items():
        if substring in content:
            properties.append(status)

    if not properties:
        sys.exit('File "{0}" does not contain a known property.'.format(propertyfile))
    return properties


def satisfies_file_property(filename, properties):
    """
    Tell whether the given property is violated or satisfied in a given file.
    @param filename: The file name of the input file.
    @param properties: The list of properties to check (as returned by properties_of_file()).
    @return True if the property is satisfied; False if it is violated; None if it is unknown
    """
    expected_result = _expected_result(filename, properties)
    if not expected_result:
        return None
    expected_result_class = get_result_classification(expected_result)
    if expected_result_class == RESULT_CLASS_TRUE:
        return True
    if expected_result_class == RESULT_CLASS_FALSE:
        return False
    return None


def score_for_task(filename, properties, category):
    """
    Return the possible score of task, depending on whether the result is correct or not.
    """
    if category != CATEGORY_CORRECT and category != CATEGORY_WRONG:
        return 0
    if _PROP_SAT in properties:
        return 0
    correct = (category == CATEGORY_CORRECT)
    expected = satisfies_file_property(filename, properties)
    if expected is None:
        return 0
    elif expected == True:
        return _SCORE_CORRECT_TRUE if correct else _SCORE_WRONG_FALSE
    elif expected == False:
        return _SCORE_CORRECT_FALSE if correct else _SCORE_WRONG_TRUE
    else:
        assert False, "unexpected return value from satisfies_file_property: " + expected

def _file_is_java(filename):
    # Java benchmarks have as filename their main class, so we cannot check for '.java'
    return '_assert' in filename


def get_result_classification(result):
    '''
    Classify the given result into "true" (property holds),
    "false" (property does not hold), "unknown", and "error".
    @param result: The result given by the tool (needs to be one of the RESULT_* strings to be recognized).
    @return One of RESULT_CLASS_* strings
    '''
    if result not in RESULT_LIST:
        return RESULT_CLASS_ERROR

    if result == RESULT_UNKNOWN:
        return RESULT_CLASS_UNKNOWN

    if result == RESULT_TRUE_PROP or result == RESULT_SAT:
        return RESULT_CLASS_TRUE
    else:
        return RESULT_CLASS_FALSE


def get_result_category(filename, result, properties):
    '''
    This function determines the relation between actual result and expected result
    for the given file and properties.
    @param filename: The file name of the input file.
    @param result: The result given by the tool (needs to be one of the RESULT_* strings to be recognized).
    @param properties: The list of properties to check (as returned by properties_of_file()).
    @return One of the CATEGORY_* strings.
    '''
    if result not in RESULT_LIST:
        return CATEGORY_ERROR

    if result == RESULT_UNKNOWN:
        return CATEGORY_UNKNOWN

    if _file_is_java(filename) and not properties:
        # Currently, no property files for checking Java programs exist,
        # so we hard-code a check for _PROP_ASSERT for these
        properties = [_PROP_ASSERT]

    if not properties:
        # Without property we cannot return correct or wrong results.
        return CATEGORY_MISSING

    expected_result = _expected_result(filename, properties)
    if not expected_result:
        # filename gives no hint on the expected output
        return CATEGORY_MISSING
    else:
        if expected_result == result:
            return CATEGORY_CORRECT
        else:
            return CATEGORY_WRONG
