# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2019  Dirk Beyer
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

import collections
from decimal import Decimal, InvalidOperation
import logging
import math

from benchexec import result
from benchexec.tablegenerator import util
from benchexec.tablegenerator.columns import ColumnType


nan = float("nan")
inf = float("inf")


class StatValue(object):
    def __init__(
        self, sum, min=None, max=None, avg=None, median=None, stdev=None  # noqa: A002
    ):  # @ReservedAssignment
        self.sum = sum
        self.min = min
        self.max = max
        self.avg = avg
        self.median = median
        self.stdev = stdev

    def __str__(self):
        return str(self.sum)

    @classmethod
    def from_list(cls, values):
        if any(math.isnan(v) for v in values if v is not None):
            return StatValue(nan, nan, nan, nan, nan, nan)

        values = sorted(v for v in values if v is not None)
        if not values:
            return StatValue(0)

        values_len = len(values)
        min_value = values[0]
        max_value = values[-1]

        if min_value == -inf and max_value == +inf:
            values_sum = nan
            mean = nan
            stdev = nan
        elif max_value == inf:
            values_sum = inf
            mean = inf
            stdev = inf
        elif min_value == -inf:
            values_sum = -inf
            mean = -inf
            stdev = inf
        else:
            values_sum = sum(values)
            mean = values_sum / values_len

            stdev = Decimal(0)
            for v in values:
                diff = v - mean
                stdev += diff * diff
            stdev = (stdev / values_len).sqrt()

        half, len_is_odd = divmod(values_len, 2)
        if len_is_odd:
            median = values[half]
        else:
            median = (values[half - 1] + values[half]) / Decimal(2)

        return StatValue(
            values_sum,
            min=min_value,
            max=max_value,
            avg=mean,
            median=median,
            stdev=stdev,
        )


def get_stats_of_run_set(runResults, correct_only):
    """
    This function returns the numbers of the statistics.
    @param runResults: All the results of the execution of one run set (as list of RunResult objects)
    """

    # convert:
    # [['TRUE', 0,1], ['FALSE', 0,2]] -->  [['TRUE', 'FALSE'], [0,1, 0,2]]
    listsOfValues = zip(*[runResult.values for runResult in runResults])

    columns = runResults[0].columns
    status_list = [(runResult.category, runResult.status) for runResult in runResults]

    # collect some statistics
    totalRow = []
    correctRow = []
    correctTrueRow = []
    correctFalseRow = []
    correctUnconfirmedRow = []
    correctUnconfirmedTrueRow = []
    correctUnconfirmedFalseRow = []
    incorrectRow = []
    wrongTrueRow = []
    wrongFalseRow = []
    scoreRow = []

    status_col_index = 0  # index of 'status' column
    for index, (column, values) in enumerate(zip(columns, listsOfValues)):
        col_type = column.type.type
        if col_type != ColumnType.text:
            if col_type == ColumnType.status:
                status_col_index = index
                score = StatValue(
                    sum(run_result.score or 0 for run_result in runResults)
                )

                total = StatValue(
                    len(
                        [
                            runResult.values[index]
                            for runResult in runResults
                            if runResult.status
                        ]
                    )
                )

                curr_status_list = [
                    (runResult.category, runResult.values[index])
                    for runResult in runResults
                ]

                counts = collections.Counter(
                    (category, result.get_result_classification(status))
                    for category, status in curr_status_list
                )
                countCorrectTrue = counts[
                    result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE
                ]
                countCorrectFalse = counts[
                    result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE
                ]
                countCorrectUnconfirmedTrue = counts[
                    result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE
                ]
                countCorrectUnconfirmedFalse = counts[
                    result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE
                ]
                countWrongTrue = counts[result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE]
                countWrongFalse = counts[
                    result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE
                ]

                correct = StatValue(countCorrectTrue + countCorrectFalse)
                correctTrue = StatValue(countCorrectTrue)
                correctFalse = StatValue(countCorrectFalse)
                correctUnconfirmed = StatValue(
                    countCorrectUnconfirmedTrue + countCorrectUnconfirmedFalse
                )
                correctUnconfirmedTrue = StatValue(countCorrectUnconfirmedTrue)
                correctUnconfirmedFalse = StatValue(countCorrectUnconfirmedFalse)
                incorrect = StatValue(countWrongTrue + countWrongFalse)
                wrongTrue = StatValue(countWrongTrue)
                wrongFalse = StatValue(countWrongFalse)

            else:
                assert column.is_numeric()
                (
                    total,
                    correct,
                    correctTrue,
                    correctFalse,
                    correctUnconfirmed,
                    correctUnconfirmedTrue,
                    correctUnconfirmedFalse,
                    incorrect,
                    wrongTrue,
                    wrongFalse,
                ) = get_stats_of_number_column(
                    values, status_list, column.title, correct_only
                )

                score = None

        else:
            (
                total,
                correct,
                correctTrue,
                correctFalse,
                correctUnconfirmed,
                correctUnconfirmedTrue,
                correctUnconfirmedFalse,
                incorrect,
                wrongTrue,
                wrongFalse,
            ) = (
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
            score = None

        totalRow.append(total)
        correctRow.append(correct)
        correctTrueRow.append(correctTrue)
        correctFalseRow.append(correctFalse)
        correctUnconfirmedRow.append(correctUnconfirmed)
        correctUnconfirmedTrueRow.append(correctUnconfirmedTrue)
        correctUnconfirmedFalseRow.append(correctUnconfirmedFalse)
        incorrectRow.append(incorrect)
        wrongTrueRow.append(wrongTrue)
        wrongFalseRow.append(wrongFalse)
        scoreRow.append(score)

    def replace_irrelevant(row):
        if not row:
            return
        count = row[status_col_index]
        if not count or not count.sum:
            for i in range(1, len(row)):
                row[i] = None

    replace_irrelevant(totalRow)
    replace_irrelevant(correctRow)
    replace_irrelevant(correctTrueRow)
    replace_irrelevant(correctFalseRow)
    replace_irrelevant(correctUnconfirmedRow)
    replace_irrelevant(correctUnconfirmedTrueRow)
    replace_irrelevant(correctUnconfirmedFalseRow)
    replace_irrelevant(incorrectRow)
    replace_irrelevant(wrongTrueRow)
    replace_irrelevant(wrongFalseRow)
    replace_irrelevant(scoreRow)

    stats = (
        totalRow,
        correctRow,
        correctTrueRow,
        correctFalseRow,
        correctUnconfirmedRow,
        correctUnconfirmedTrueRow,
        correctUnconfirmedFalseRow,
        incorrectRow,
        wrongTrueRow,
        wrongFalseRow,
        scoreRow,
    )
    return stats


def get_stats_of_number_column(values, categoryList, columnTitle, correct_only):
    assert len(values) == len(categoryList)
    try:
        valueList = [util.to_decimal(v) for v in values]
    except InvalidOperation as e:
        if columnTitle != "host" and not columnTitle.endswith("status"):
            # We ignore values of columns 'host' and 'status'.
            logging.warning("%s. Statistics may be wrong.", e)
        return (
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
            StatValue(0),
        )

    valuesPerCategory = collections.defaultdict(list)
    for value, catStat in zip(valueList, categoryList):
        category, status = catStat
        if status is None:
            continue
        valuesPerCategory[category, result.get_result_classification(status)].append(
            value
        )

    return (
        StatValue.from_list(valueList),
        StatValue.from_list(
            valuesPerCategory[result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE]
            + valuesPerCategory[result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE]
        ),
        StatValue.from_list(
            valuesPerCategory[result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE]
        ),
        StatValue.from_list(
            valuesPerCategory[result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE]
        ),
        StatValue.from_list(
            valuesPerCategory[
                result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE
            ]
            + valuesPerCategory[
                result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE
            ]
        ),
        StatValue.from_list(
            valuesPerCategory[
                result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE
            ]
        ),
        StatValue.from_list(
            valuesPerCategory[
                result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE
            ]
        ),
        StatValue.from_list(
            valuesPerCategory[result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE]
            + valuesPerCategory[result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE]
        )
        if not correct_only
        else None,
        StatValue.from_list(
            valuesPerCategory[result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE]
        )
        if not correct_only
        else None,
        StatValue.from_list(
            valuesPerCategory[result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE]
        )
        if not correct_only
        else None,
    )


def get_summary(runSetResults):
    summaryStats = []
    available = False
    for runSetResult in runSetResults:
        for column in runSetResult.columns:
            if (
                column.is_numeric()
                and column.title in runSetResult.summary
                and runSetResult.summary[column.title] != ""
            ):

                available = True
                try:
                    value = StatValue(
                        util.to_decimal(runSetResult.summary[column.title])
                    )
                except InvalidOperation:
                    value = None
            else:
                value = None
            summaryStats.append(value)

    return summaryStats if available else None
