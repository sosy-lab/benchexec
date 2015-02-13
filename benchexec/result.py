"""
CPAchecker is a tool for configurable software verification.
This file is part of CPAchecker.

Copyright (C) 2007-2014  Dirk Beyer
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


CPAchecker web page:
  http://cpachecker.sosy-lab.org
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals
from . import util
import os


# CONSTANTS

CATEGORY_CORRECT = 'correct'
CATEGORY_WRONG   = 'wrong'
CATEGORY_UNKNOWN = 'unknown'
CATEGORY_ERROR   = 'error'
CATEGORY_MISSING = 'missing'

STR_TRUE = 'true'
STATUS_UNKNOWN = 'unknown'
STR_FALSE = 'false' # only for special cases. STR_FALSE is no official result, because property is missing

PROP_REACH =        'reach'
PROP_TERMINATION =  'termination'
PROP_DEREF =        'valid-deref'
PROP_FREE =         'valid-free'
PROP_MEMTRACK =     'valid-memtrack'

# next lines are for public usage in tool-wrappers or in the scripts
STATUS_TRUE_PROP =          STR_TRUE
STATUS_FALSE_REACH =        STR_FALSE + '(' + PROP_REACH       + ')'
STATUS_FALSE_TERMINATION =  STR_FALSE + '(' + PROP_TERMINATION + ')'
STATUS_FALSE_DEREF =        STR_FALSE + '(' + PROP_DEREF       + ')'
STATUS_FALSE_FREE =         STR_FALSE + '(' + PROP_FREE        + ')'
STATUS_FALSE_MEMTRACK =     STR_FALSE + '(' + PROP_MEMTRACK    + ')'


# list of all public constants,
# if a tool-result is not in this list, it is handled as CATEGORY_ERROR
STATUS_LIST = [STATUS_TRUE_PROP, STATUS_UNKNOWN,
            STATUS_FALSE_REACH, STATUS_FALSE_TERMINATION, 
            STATUS_FALSE_DEREF, STATUS_FALSE_FREE, STATUS_FALSE_MEMTRACK]

# string used to recognize java programs
JAVA_CHECK_SUBSTRING = '_assert'

# strings searched in filenames to determine correct or incorrect status.
# use lower case! the dict contains assignments 'substring' --> 'partial statuses'
SUBSTRINGS = {
              '_true-unreach-label':   (STR_TRUE, [PROP_REACH]),
              '_true-unreach-call':    (STR_TRUE, [PROP_REACH]),
              '_true_assert':          (STR_TRUE, [PROP_REACH]),
              '_true-termination':     (STR_TRUE, [PROP_TERMINATION]),
              '_true-valid-deref':     (STR_TRUE, [PROP_DEREF]),
              '_true-valid-free':      (STR_TRUE, [PROP_FREE]),
              '_true-valid-memtrack':  (STR_TRUE, [PROP_MEMTRACK]),
              '_true-valid-memsafety': (STR_TRUE, [PROP_DEREF, PROP_FREE, PROP_MEMTRACK]),

              '_false-unreach-label':  (STR_FALSE, [PROP_REACH]),
              '_false-unreach-call':   (STR_FALSE, [PROP_REACH]),
              '_false_assert':         (STR_FALSE, [PROP_REACH]),
              '_false-termination':    (STR_FALSE, [PROP_TERMINATION]),
              '_false-valid-deref':    (STR_FALSE, [PROP_DEREF]),
              '_false-valid-free':     (STR_FALSE, [PROP_FREE]),
              '_false-valid-memtrack': (STR_FALSE, [PROP_MEMTRACK])
              }


# this map contains substring of property-files with their status
PROPERTY_MATCHER = {'LTL(G ! label(':                    PROP_REACH,
                    'LTL(G ! call(__VERIFIER_error()))': PROP_REACH,
                    'LTL(F end)':                        PROP_TERMINATION,
                    'LTL(G valid-free)':                 PROP_FREE,
                    'LTL(G valid-deref)':                PROP_DEREF,
                    'LTL(G valid-memtrack)':             PROP_MEMTRACK,
                    'OBSERVER AUTOMATON':                PROP_REACH
                   }


# Score values taken from http://sv-comp.sosy-lab.org/
SCORE_CORRECT_TRUE = 2
SCORE_CORRECT_FALSE = 1
SCORE_UNKNOWN = 0
SCORE_WRONG_FALSE = -6
SCORE_WRONG_TRUE = -12


def _statuses_of_file(filename):
    """
    This function returns a list of all properties in the filename.
    """
    statuses = []
    for (substr, props) in SUBSTRINGS.items():
        if substr in filename:
            statuses.extend((props[0], prop) for prop in props[1])
    return statuses


def _statuses_of_property_file(propertyFile):
    assert os.path.isfile(propertyFile)

    statuses = []
    with open(propertyFile) as f:
        content = f.read()
        assert 'CHECK' in content or 'OBSERVER' in content, "Invalid property {0}".format(content)

        # TODO: should we switch to regex or line-based reading?
        for substring, status in PROPERTY_MATCHER.items():
            if substring in content:
                statuses.append(status)

        assert statuses, "Unkown property {0}".format(content)
    return statuses

def _file_is_java(filename):
  return JAVA_CHECK_SUBSTRING in filename

def get_result_category(filename, status, propertyFile=None):
    '''
    This function return a string
    that shows the relation between status and file.
    '''

    if status == STATUS_UNKNOWN:
        category = CATEGORY_UNKNOWN
    elif status in STATUS_LIST:
        
        # Currently, no properties for checking Java programs exist, so we only check for PROP_REACH for these
        if _file_is_java(filename):
          fileStatuses = _statuses_of_file(filename)

          if not fileStatuses:
            category = CATEGORY_MISSING
          elif all(prop is not PROP_REACH or s in status for (s, prop) in fileStatuses):
            category = CATEGORY_CORRECT
          else:
            category = CATEGORY_WRONG

        # Without propertyfile we do not return correct or wrong results, but always UNKNOWN.
        elif propertyFile is None:
            category = CATEGORY_MISSING
        else:
            fileStatuses = _statuses_of_file(filename)
            propertiesToCheck = _statuses_of_property_file(propertyFile)

            searchedProperties = []
            for (flag,prop) in fileStatuses:
                if prop in propertiesToCheck:
                    searchedProperties.append(flag + '(' + prop + ')') # format must match with above!

            if not searchedProperties:
                # filename gives no hint on the searched bug or
                # we are searching for a property, that has nothing to do with the file
                category = CATEGORY_MISSING

            elif status is STR_TRUE:
                if all(prop.startswith(STR_TRUE) for prop in searchedProperties):
                    category = CATEGORY_CORRECT
                else:
                    category = CATEGORY_WRONG

            elif status in searchedProperties:
                category = CATEGORY_CORRECT
            else:
                category = CATEGORY_WRONG

    else:
        category = CATEGORY_ERROR
    return category


def calculate_score(category, status):
    if category == CATEGORY_CORRECT:
        return SCORE_CORRECT_TRUE if status == STATUS_TRUE_PROP else SCORE_CORRECT_FALSE
    elif category == CATEGORY_WRONG:
        return SCORE_WRONG_TRUE if status == STATUS_TRUE_PROP else SCORE_WRONG_FALSE
    elif category in [CATEGORY_UNKNOWN, CATEGORY_ERROR, CATEGORY_MISSING]:
        return SCORE_UNKNOWN
    else:
        assert False, 'impossible category {0}'.format(category)
