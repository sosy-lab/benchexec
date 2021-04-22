#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import itertools
import sys

from benchexec import result, tablegenerator
from benchexec.tablegenerator import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files


def get_extract_value_function(column_identifier):
    """
    returns a function that extracts the value for a column.
    """

    def extract_value(run_result):
        pos = None
        for i, column in enumerate(run_result.columns):
            if column.title == column_identifier:
                pos = i
                break
        if pos is None:
            sys.exit(f"CPU time missing for task {run_result.task_id}.")
        return util.to_decimal(run_result.values[pos])

    return extract_value


def main(args=None):
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description="""Create CSV tables for quantile plots with the results of a benchmark execution.
           The CSV tables are similar to those produced with table-generator,
           but have an additional first column with the index for the quantile plot,
           and they are sorted.
           The output is written to stdout.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "result",
        metavar="RESULT",
        type=str,
        nargs="+",
        help="XML files with result produced by benchexec",
    )
    parser.add_argument(
        "--correct-only",
        action="store_true",
        dest="correct_only",
        help="only use correct results (recommended, implied if --score-based is used)",
    )
    parser.add_argument(
        "--score-based",
        action="store_true",
        dest="score_based",
        help="create data for score-based quantile plot",
    )
    parser.add_argument(
        "--sort-by",
        metavar="SORT",
        default="cputime",
        dest="column_identifier",
        type=str,
        help="column identifier for sorting the values, e.g. 'cputime' or 'walltime'",
    )

    options = parser.parse_args(args[1:])

    # load results
    run_set_result = tablegenerator.RunSetResult.create_from_xml(
        options.result[0], tablegenerator.parse_results_file(options.result[0])
    )
    for results_file in options.result[1:]:
        run_set_result.append(
            results_file, tablegenerator.parse_results_file(results_file)
        )
    run_set_result.collect_data(options.correct_only or options.score_based)

    # select appropriate results
    if options.score_based:
        start_index = 0
        index_increment = lambda run_result: run_result.score  # noqa: E731
        results = []
        for run_result in run_set_result.results:
            if run_result.score is None:
                sys.exit(
                    f"No score available for task {run_result.task_id}, "
                    f"cannot produce score-based quantile data."
                )

            if run_result.category == result.CATEGORY_WRONG:
                start_index += run_result.score
            elif run_result.category == result.CATEGORY_MISSING:
                sys.exit(
                    f"Property missing for task {run_result.task_id}, "
                    f"cannot produce score-based quantile data."
                )
            elif run_result.category == result.CATEGORY_CORRECT:
                results.append(run_result)
            else:
                assert run_result.category in {
                    result.CATEGORY_ERROR,
                    result.CATEGORY_UNKNOWN,
                }
    else:
        start_index = 0
        index_increment = lambda run_result: 1  # noqa: E731
        if options.correct_only:
            results = [
                run_result
                for run_result in run_set_result.results
                if run_result.category == result.CATEGORY_CORRECT
            ]
        else:
            results = run_set_result.results

    # sort data for quantile plot
    results.sort(key=get_extract_value_function(options.column_identifier))

    # extract information which id columns should be shown
    for run_result in run_set_result.results:
        run_result.id = run_result.task_id
    relevant_id_columns = tablegenerator.select_relevant_id_columns(results)

    # write output
    index = start_index
    for run_result in results:
        index += index_increment(run_result)
        task_ids = (
            task_id for task_id, show in zip(run_result.id, relevant_id_columns) if show
        )
        result_values = (util.remove_unit(value or "") for value in run_result.values)
        print(*itertools.chain([index], task_ids, result_values), sep="\t")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("Script was interrupted by user.")
