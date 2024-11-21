# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import decimal
from decimal import Decimal, InvalidOperation
import itertools

from benchexec import result
from benchexec.tablegenerator import util
from benchexec.tablegenerator.columns import ColumnType

# It's important to make sure on *all* entry points / methods which perform arithmetics that the correct
# rounding / context is used.
DECIMAL_CONTEXT = decimal.Context(rounding=decimal.ROUND_HALF_UP)

nan = Decimal("nan")
inf = Decimal("inf")


class ColumnStatistics(object):
    _fields = frozenset(
        (
            "total",
            "local",
            "correct",
            "correct_true",
            "correct_false",
            "correct_unconfirmed",
            "correct_unconfirmed_true",
            "correct_unconfirmed_false",
            "wrong",
            "wrong_true",
            "wrong_false",
            "score",
        )
    )

    def __getattr__(self, name):
        # This is called for fields that have not been set previously, default is None
        if name in ColumnStatistics._fields:
            return None  # noqa: R501 specifying None explicitly is clearer
        raise AttributeError("can't get attribute " + name)

    def __setattr__(self, name, value):
        if name in ColumnStatistics._fields:
            return super().__setattr__(name, value)
        raise AttributeError("can't set attribute")


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
        with decimal.localcontext(DECIMAL_CONTEXT):
            if any(v is not None and v.is_nan() for v in values):
                return StatValue(nan, nan, nan, nan, nan, nan)

            values = sorted(v for v in values if v is not None)
            if not values:
                return None

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

                # The scaling is just to avoid having too few decimal digits when printing,
                # the value is still just 0.
                stdev = Decimal(0).scaleb(-decimal.getcontext().prec)
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
    columns = runResults[0].columns
    status_list = [(runResult.category, runResult.status) for runResult in runResults]

    # collect some statistics
    stats = []
    for index, column in enumerate(columns):
        col_type = column.type.type
        if col_type == ColumnType.status:
            column_stats = _get_stats_of_status_column(runResults, index)

        elif col_type == ColumnType.text:
            column_stats = None

        else:
            assert column.is_numeric()
            values = (run_result.values[index] for run_result in runResults)
            column_stats = _get_stats_of_number_column(
                values, status_list, correct_only
            )

        stats.append(column_stats)

    return stats


def _get_stats_of_number_column(values, categoryList, correct_only):
    valueList = [util.to_decimal(v) for v in values]
    assert len(valueList) == len(categoryList)

    valuesPerCategory = collections.defaultdict(list)
    for value, (category, status) in zip(valueList, categoryList):
        if status is None:
            continue
        valuesPerCategory[category, result.get_result_classification(status)].append(
            value
        )

    stats = ColumnStatistics()
    stats.total = StatValue.from_list(valueList)

    def create_stat_value_for(*keys):
        all_values_for_keys = list(
            itertools.chain.from_iterable(valuesPerCategory[key] for key in keys)
        )
        return StatValue.from_list(all_values_for_keys)

    stats.correct = create_stat_value_for(
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE),
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE),
    )
    stats.correct_true = create_stat_value_for(
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE)
    )
    stats.correct_false = create_stat_value_for(
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE)
    )
    stats.correct_unconfirmed = create_stat_value_for(
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE),
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE),
    )
    stats.correct_unconfirmed_true = create_stat_value_for(
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE)
    )
    stats.correct_unconfirmed_false = create_stat_value_for(
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE)
    )
    if not correct_only:
        stats.wrong = create_stat_value_for(
            (result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE),
            (result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE),
        )
        stats.wrong_true = create_stat_value_for(
            (result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE)
        )
        stats.wrong_false = create_stat_value_for(
            (result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE)
        )
    return stats


def _get_stats_of_status_column(run_results, col_index):
    stats = ColumnStatistics()
    stats.score = StatValue(sum(run_result.score or 0 for run_result in run_results))

    stats.total = StatValue(
        sum(1 for run_result in run_results if run_result.values[col_index])
    )

    counts = collections.Counter(
        (
            run_result.category,
            result.get_result_classification(run_result.values[col_index]),
        )
        for run_result in run_results
    )

    def create_stat_value_for(*keys):
        return StatValue(sum(counts[key] for key in keys))

    stats.correct = create_stat_value_for(
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE),
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE),
    )
    stats.correct_true = create_stat_value_for(
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE)
    )
    stats.correct_false = create_stat_value_for(
        (result.CATEGORY_CORRECT, result.RESULT_CLASS_FALSE)
    )
    stats.correct_unconfirmed = create_stat_value_for(
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE),
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE),
    )
    stats.correct_unconfirmed_true = create_stat_value_for(
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_TRUE)
    )
    stats.correct_unconfirmed_false = create_stat_value_for(
        (result.CATEGORY_CORRECT_UNCONFIRMED, result.RESULT_CLASS_FALSE)
    )
    stats.wrong = create_stat_value_for(
        (result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE),
        (result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE),
    )
    stats.wrong_true = create_stat_value_for(
        (result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE)
    )
    stats.wrong_false = create_stat_value_for(
        (result.CATEGORY_WRONG, result.RESULT_CLASS_FALSE)
    )

    return stats


def add_local_summary_statistics(run_set_result, run_set_stats):
    """
    Fill in the "local" values of ColumnStatistics instances in result of
    get_stats_of_run_set
    """
    for column, column_stats in zip(run_set_result.columns, run_set_stats):
        if (
            column.is_numeric()
            and column.title in run_set_result.summary
            and run_set_result.summary[column.title] != ""
        ):
            try:
                column_stats.local = StatValue(
                    util.to_decimal(run_set_result.summary[column.title])
                )
            except InvalidOperation:
                pass
