#!/usr/bin/env python3
"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
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

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import itertools
import sys
sys.dont_write_bytecode = True # prevent creation of .pyc files

import benchexec.result as result
import benchexec.tablegenerator as tablegenerator

Util = tablegenerator.Util


def extract_cputime(run_result):
    pos = None
    for i, column in enumerate(run_result.columns):
        if column.title == 'cputime':
            pos = i
            break
    if pos is None:
        sys.exit('CPU time missing for task {0}.'.format(run_result.task_id[0]))
    return Util.to_decimal(run_result.values[pos])


def main(args=None):
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(
        fromfile_prefix_chars='@',
        description=
        """Create CSV tables for quantile plots with the results of a benchmark execution.
           The CSV tables are similar to those produced with table-generator,
           but have an additional first column with the index for the quantile plot,
           and they are sorted.
           The output is written to stdout.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/"""
    )

    parser.add_argument("result",
        metavar="RESULT",
        type=str,
        help="XML file with result produced by benchexec"
    )
    parser.add_argument("--correct-only",
        action="store_true", dest="correct_only",
        help="only use correct results (recommended, implied if --score-based is used)"
    )
    parser.add_argument("--score-based",
        action="store_true", dest="score_based",
        help="create data for score-based quantile plot"
    )

    options = parser.parse_args(args[1:])

    # load results
    run_set_result = tablegenerator.RunSetResult.create_from_xml(
            options.result, tablegenerator.parse_results_file(options.result))
    run_set_result.collect_data(options.correct_only)

    # select appropriate results
    if options.score_based:
        start_index = 0
        index_increment = lambda run_result: run_result.score
        results = []
        for run_result in run_set_result.results:
            if run_result.score is None:
                sys.exit('No score available for task {0}, '
                         'cannot produce score-based quantile data.'
                         .format(run_result.task_id[0]))

            if run_result.category == result.CATEGORY_WRONG:
                start_index += run_result.score
            elif run_result.category == result.CATEGORY_MISSING:
                sys.exit('Property missing for task {0}, '
                         'cannot produce score-based quantile data.'
                         .format(run_result.task_id[0]))
            elif run_result.category == result.CATEGORY_CORRECT:
                results.append(run_result)
            else:
                assert run_result.category in {result.CATEGORY_ERROR, result.CATEGORY_UNKNOWN}
    else:
        start_index = 0
        index_increment = lambda run_result: 1
        if options.correct_only:
            results = [run_result for run_result in run_set_result.results
                       if run_result.category == result.CATEGORY_CORRECT]
        else:
            results = run_set_result.results

    # sort data for quantile plot
    results.sort(key=extract_cputime)

    # extract information which id columns should be shown
    for run_result in run_set_result.results:
        run_result.id = run_result.task_id
    relevant_id_columns = tablegenerator.select_relevant_id_columns(results)

    # write output
    index = start_index
    for run_result in results:
        index += index_increment(run_result)
        columns = itertools.chain(
                [index],
                (id for id, show in zip(run_result.id, relevant_id_columns) if show),
                map(Util.remove_unit, (value or '' for value in run_result.values)),
                )
        print(*columns, sep='\t')

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit('Script was interrupted by user.')
