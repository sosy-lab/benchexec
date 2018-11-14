#!/usr/bin/env python3
"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2017  Dirk Beyer
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

import argparse
import collections
import itertools
import re
import string
import sys
import multiprocessing
from functools import partial
sys.dont_write_bytecode = True # prevent creation of .pyc files

import benchexec.tablegenerator as tablegenerator

Util = tablegenerator.Util

HEADER = (
r"""% The following definition defines a command for each value.
% The command name is the concatenation of the first six arguments.
% To override this definition, define \StoreBenchExecResult with \newcommand before including this file.
% Arguments: benchmark name, run-set name, category, status, column name, statistic, value
\providecommand\StoreBenchExecResult[7]{\expandafter\newcommand\csname#1#2#3#4#5#6\endcsname{#7}}%""")

def extract_time(column_title, time_name, run_result):
    pos = None
    for i, column in enumerate(run_result.columns):
        if column.title == column_title:
            pos = i
            break
    if pos is None:
        sys.exit("{0} time missing for task {1}.".format(time_name, run_result.task_id[0]))
    return Util.to_decimal(run_result.values[pos])

def extract_cputime(run_result):
    return extract_time("cputime", "CPU", run_result)

def extract_walltime(run_result):
    return extract_time("walltime", "Wall", run_result)

def format_command_part(name):
    name = re.sub("[^a-zA-Z]", "-", name)
    name = string.capwords(name, "-")
    name = name.replace("-", "")
    return name


class StatAccumulator(object):
    def __init__(self):
        self.count = 0
        self.cputime_values = []
        self.walltime_values = []

    def add(self, result):
        self.count += 1
        self.cputime_values.append(extract_cputime(result))
        self.walltime_values.append(extract_walltime(result))

    def to_latex(self, name_parts):
        cputime_stats = tablegenerator.StatValue.from_list(self.cputime_values)
        walltime_stats = tablegenerator.StatValue.from_list(self.walltime_values)
        assert len(name_parts) <= 4
        name_parts += [""] * (4 - len(name_parts)) # ensure length 4
        name = r"}{".join(map(format_command_part, name_parts))
        return "\n".join(itertools.chain.from_iterable(
            [["\StoreBenchExecResult{%s}{Count}{}{%s}%%" % (name, self.count)]]
          + [[
                r"\StoreBenchExecResult{%s}{%s}{}{%s}%%" % (name, time_name, time_stats.sum),
                r"\StoreBenchExecResult{%s}{%s}{Avg}{%s}%%" % (name, time_name, time_stats.avg),
                r"\StoreBenchExecResult{%s}{%s}{Median}{%s}%%" % (name, time_name, time_stats.median),
                r"\StoreBenchExecResult{%s}{%s}{Min}{%s}%%" % (name, time_name, time_stats.min),
                r"\StoreBenchExecResult{%s}{%s}{Max}{%s}%%" % (name, time_name, time_stats.max),
                r"\StoreBenchExecResult{%s}{%s}{Stdev}{%s}%%" % (name, time_name, time_stats.stdev)
              ] for (time_name, time_stats) in [
                  ("Cputime", cputime_stats),
                  ("Walltime", walltime_stats)
                ]]
            ))


class StatsCollection(object):
    def __init__(self, prefix_list, total_stats, category_stats, status_stats):
        self.prefix_list = prefix_list
        self.total_stats = total_stats
        self.category_stats = category_stats
        self.status_stats = status_stats


def load_results(result_file, status_print):
    run_set_result = tablegenerator.RunSetResult.create_from_xml(
            result_file, tablegenerator.parse_results_file(result_file))
    run_set_result.collect_data(False)

    total_stats = StatAccumulator()
    category_stats = collections.defaultdict(StatAccumulator)
    status_stats = collections.defaultdict(lambda: collections.defaultdict(StatAccumulator))
    for run_result in run_set_result.results:
        total_stats.add(run_result)
        category_stats[run_result.category].add(run_result)
        if status_print == "full":
            status_stats[run_result.category][run_result.status].add(run_result)
        elif status_print == "short":
            short_status = re.sub(r" *\(.*", "", run_result.status)
            status_stats[run_result.category][short_status].add(run_result)
    assert len(run_set_result.results) == total_stats.count

    basenames = [Util.prettylist(run_set_result.attributes.get("benchmarkname")),
                 Util.prettylist(run_set_result.attributes.get("name"))]

    # status_stats must be transformed to a dictionary to get rid of the lambda-factory used above (can't be pickled)
    return StatsCollection(basenames, total_stats, category_stats, dict(status_stats))


def main(args=None):
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description=
        """Dump LaTeX commands with summary values of the table.
           All the information from the footer of HTML tables is available.
           The output is written to stdout.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/"""
        )

    parser.add_argument("result",
        metavar="RESULT",
        type=str,
        nargs='+',
        help="XML file(s) with result produced by benchexec"
        )
    parser.add_argument("--status",
        action="store",
        choices=["none", "short", "full"],
        default="short",
        help="whether to output statistics aggregated for each different status value, "
             "for each abbreviated status value, or not",
        )

    options = parser.parse_args(args[1:])

    pool = multiprocessing.Pool()
    stats = pool.map(partial(load_results, status_print=options.status), options.result)

    print(HEADER)
    for curr_stats in stats:
        basenames = curr_stats.prefix_list
        total_stats = curr_stats.total_stats
        category_stats = curr_stats.category_stats
        status_stats = curr_stats.status_stats

        print(total_stats.to_latex(basenames + ["total"]))

        for (category, counts) in sorted(category_stats.items()):
            print(counts.to_latex(basenames + [category]))
            categories = [(s, c) for (s, c) in status_stats.get(category, {}).items() if s]
            for (status, counts2) in sorted(categories):
                print(counts2.to_latex(basenames + [category, status]))
                if category == "correct" and status_stats.get("wrong", {}).get(status) is None:
                    print(StatAccumulator().to_latex(basenames + ["wrong", status]))
                elif category == "wrong" and status_stats.get("correct", {}).get(status) is None:
                    print(StatAccumulator().to_latex(basenames + ["correct", status]))

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("Script was interrupted by user.")
