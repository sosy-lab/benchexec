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
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import util

here = os.path.dirname(__file__)
base_dir = os.path.join(here, '..', '..', '..')
bin_dir = os.path.join(base_dir, 'bin')
tablegenerator = os.path.join(bin_dir, 'table-generator')

# Set to True to let tests overwrite the expected result with the actual result
# instead of letting them fail.
# Use this to update expected files if necessary. Do not commit this flag set to True!
OVERWRITE_MODE = False


def result_file(name):
    return os.path.join(here, 'results', name)


class TableGeneratorIntegrationTests(unittest.TestCase):

    # Tests compare the generated CSV files and ignore the HTML files
    # because we assume the HTML files change more often on purpose.

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def setUp(self):
        # We use a temporary directory inside the source tree to avoid mismatching
        # path names inside HTML tables.
        self.tmp = tempfile.mkdtemp(prefix="integration_test_tmp_",
                                    dir=os.path.dirname(__file__))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cmd(self, *args):
        try:
            output = subprocess.check_output(args=args, stderr=subprocess.STDOUT).decode()
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            raise e
        print(output)
        return output

    def generate_tables_and_check_produced_files(self, args, table_prefix,
                                                 diff_prefix=None,
                                                 formats=['html', 'csv'],
                                                 output_path=None):
        output = self.run_cmd(*[tablegenerator] + list(args) + ['--outputpath', output_path or self.tmp])
        generated_files = set(os.path.join(self.tmp, x) for x in os.listdir(self.tmp))

        csv_file = os.path.join(self.tmp, table_prefix + '.csv') if 'csv' in formats else None
        html_file = os.path.join(self.tmp, table_prefix + '.html') if 'html' in formats else None
        expected_files = {csv_file, html_file}
        if diff_prefix:
            csv_diff_file = os.path.join(self.tmp, diff_prefix + '.csv') if 'csv' in formats else None
            html_diff_file = os.path.join(self.tmp, diff_prefix + '.html') if 'html' in formats else None
            expected_files |= {csv_diff_file, html_diff_file}
        else:
            csv_diff_file = None
            html_diff_file = None

        expected_files.discard(None)
        self.assertSetEqual(generated_files, expected_files, 'Set of generated files differs from set of expected files')
        return output, html_file, html_diff_file, csv_file, csv_diff_file

    def generate_tables_and_compare_content(self, args, table_prefix, result_prefix=None,
                                        diff_prefix=None, result_diff_prefix=None,
                                        expected_counts=None):
        def expected_file_name(ending):
            return [here, 'expected', (result_prefix or table_prefix) + '.' + ending]
        def expected_diff_file_name(ending):
            return [here, 'expected', (result_diff_prefix or diff_prefix) + '.' + ending]

        output, html_file, html_diff_file, csv_file, csv_diff_file = \
            self.generate_tables_and_check_produced_files(args, table_prefix, diff_prefix)

        generated_csv = util.read_file(csv_file)
        self.assert_file_content_equals(generated_csv, expected_file_name('csv'))

        generated_html = self.read_table_from_html(html_file)
        self.assert_file_content_equals(generated_html, expected_file_name('html'))

        if diff_prefix:
            generated_csv_diff = util.read_file(csv_diff_file)
            self.assert_file_content_equals(generated_csv_diff, expected_diff_file_name('csv'))

            generated_html_diff = self.read_table_from_html(html_diff_file)
            self.assert_file_content_equals(generated_html_diff, expected_diff_file_name('html'))

        if expected_counts:
            # output of table-generator should end with statistics about regressions
            counts = output[output.find('REGRESSIONS'):].strip()
            self.assertMultiLineEqual(expected_counts, counts)
        else:
            self.assertNotIn('REGRESSIONS', output)
            self.assertNotIn('STATS', output)

    def assert_file_content_equals(self, content, file):
        if OVERWRITE_MODE:
            util.write_file(content, *file)
        else:
            self.assertMultiLineEqual(content, util.read_file(*file))

    def read_table_from_html(self, file):
        content = util.read_file(file)
        # only keep table
        content = content[content.index('<table id="dataTable">'):content.index('</table>') + 8]
        return content


    def test_simple_table(self):
        self.generate_tables_and_compare_content(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_simple_table_correct_only(self):
        self.generate_tables_and_compare_content(
            ['--correct-only', result_file('test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            'test.2015-03-03_1613.results.predicateAnalysis.correct-only',
            )

    def test_simple_table_all_columns(self):
        self.generate_tables_and_compare_content(
            ['--all-columns', result_file('test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            'test.2015-03-03_1613.results.predicateAnalysis.all-columns',
            )

    def test_simple_table_xml(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'simple-table.xml')],
            'simple-table.table',
            'test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_simple_table_xml_with_columns(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'simple-table-with-columns.xml')],
            'simple-table-with-columns.table',
            )

    def test_simple_table_xml_with_links(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'simple-table-with-links.xml')],
            'simple-table-with-links.table',
            )

    def test_simple_table_xml_with_numberOfDigits(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'simple-table-with-numberOfDigits.xml')],
            'simple-table-with-numberOfDigits.table',
            )

    def test_simple_table_xml_with_scaling(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'simple-table-with-scaling.xml')],
            'simple-table-with-scaling.table',
        )

    def test_multi_table(self):
        self.generate_tables_and_compare_content(
            ['--name', 'predicateAnalysis',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1815.results.predicateAnalysis.xml'),
            ],
            table_prefix='predicateAnalysis.table',
            )

    def test_multi_table_reverse(self):
        self.generate_tables_and_compare_content(
            ['--name', 'predicateAnalysis-reverse',
             result_file('test.2015-03-03_1815.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
            ],
            table_prefix='predicateAnalysis-reverse.table',
            )

    def test_multi_table_no_diff(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613', '--no-diff',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.table',
            )

    def test_multi_table_differing_files(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.table',
            diff_prefix='test.2015-03-03_1613.diff',
            )

    def test_multi_table_differing_files_common(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613-common', '--common',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613-common.table',
            diff_prefix='test.2015-03-03_1613-common.diff',
            )

    def test_multi_table_differing_files_reverse(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613-reverse',
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613-reverse.table',
            diff_prefix='test.2015-03-03_1613-reverse.diff',
            )

    def test_multi_table_differing_files_correct_only(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613-correct-only', '--correct-only',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613-correct-only.table',
            diff_prefix='test.2015-03-03_1613-correct-only.diff',
            )

    def test_big_table(self):
        self.generate_tables_and_compare_content(
            [result_file('integration-predicateAnalysis.2015-10-20_1355.results.xml.bz2'),
             result_file('integration-predicateAnalysis.2015-10-22_1113.results.xml.bz2'),
             result_file('integration-predicateAnalysis.2015-10-23_1348.results.xml.bz2'),
             '-n', 'big-table'],
            table_prefix='big-table.table',
            diff_prefix='big-table.diff',
            )

    def test_dump_count_single_table(self):
        self.generate_tables_and_compare_content(
            ['--dump',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            expected_counts='REGRESSIONS 0\nSTATS\n3 1 0', # 3 correct, 1 incorrect, 0 unknown (1 without property is ignored)
            )

    def test_dump_count_single_table2(self):
        self.generate_tables_and_compare_content(
            ['--dump',
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.results.valueAnalysis',
            expected_counts='REGRESSIONS 0\nSTATS\n2 0 1', # 2 correct, 0 incorrect, 1 unknown
            )

    def test_dump_count_multi_table(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613', '--dump',
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.table',
            diff_prefix='test.2015-03-03_1613.diff',
            expected_counts='REGRESSIONS 2\nSTATS\n3 1 0\n2 0 1',
            )

    def test_dump_count_multi_table_reverse(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613-reverse', '--dump',
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613-reverse.table',
            diff_prefix='test.2015-03-03_1613-reverse.diff',
            expected_counts='REGRESSIONS 1\nSTATS\n2 0 1\n3 1 0',
            )

    def test_dump_count2(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'smt.xml'), '--dump',
            ],
            table_prefix='smt.table',
            diff_prefix='smt.diff',
            expected_counts='REGRESSIONS 2\nSTATS\n1 0 2\n2 0 1',
            )

    def test_dump_count_big_table(self):
        self.generate_tables_and_compare_content(
            [result_file('integration-predicateAnalysis.2015-10-20_1355.results.xml.bz2'),
             result_file('integration-predicateAnalysis.2015-10-22_1113.results.xml.bz2'),
             result_file('integration-predicateAnalysis.2015-10-23_1348.results.xml.bz2'),
             '-n', 'big-table', '--dump'],
            table_prefix='big-table.table',
            diff_prefix='big-table.diff',
            expected_counts="REGRESSIONS 4\nSTATS\n338 8 136\n315 8 161\n321 8 155",
            )

    def test_dump_count_big_table_ignore_flapping_timeout_regressions(self):
        self.generate_tables_and_compare_content(
            [result_file('integration-predicateAnalysis.2015-10-20_1355.results.xml.bz2'),
             result_file('integration-predicateAnalysis.2015-10-22_1113.results.xml.bz2'),
             result_file('integration-predicateAnalysis.2015-10-23_1348.results.xml.bz2'),
             '-n', 'big-table', '--dump', '--ignore-flapping-timeout-regressions'],
            table_prefix='big-table.table',
            diff_prefix='big-table.diff',
            expected_counts="REGRESSIONS 3\nSTATS\n338 8 136\n315 8 161\n321 8 155",
            )

    def test_multi_table_xml(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'multi-table.xml')],
            table_prefix='multi-table.table',
            diff_prefix='multi-table.diff',
            )

    def test_multi_table_xml_with_columns(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'multi-table-with-columns.xml')],
            table_prefix='multi-table-with-columns.table',
            diff_prefix='multi-table-with-columns.diff',
            )

    def test_multi_table_xml_with_wildcards(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'multi-table-with-wildcards.xml')],
            table_prefix='multi-table-with-wildcards.table',
            diff_prefix='multi-table-with-wildcards.diff',
            )

    def test_union_table(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'union-table-predicateAnalysis.xml')],
            table_prefix='union-table-predicateAnalysis.table',
            )

    def test_union_table2(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'union-table-valueAnalysis.xml')],
            table_prefix='union-table-valueAnalysis.table',
            )

    def test_union_table_different_result_order(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'union-table.xml')],
            table_prefix='union-table.table',
            diff_prefix='union-table.diff',
            )

    def test_union_table_duplicate_results(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'union-table-duplicate-results.xml')],
            table_prefix='union-table-duplicate-results.table',
            diff_prefix='union-table-duplicate-results.diff',
            )

    def test_union_table_multiple_results(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'union-table-multiple-results.xml')],
            table_prefix='union-table-multiple-results.table',
            diff_prefix='union-table-multiple-results.diff',
            )

    def test_union_table_order_of_results(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'union-table-mixed.xml')],
            table_prefix='union-table-mixed.table',
            diff_prefix='union-table-mixed.diff',
            )

    def test_simple_table_legacy(self):
        self.generate_tables_and_compare_content(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis-legacy.xml')],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis-legacy',
            result_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_error_result(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test-error.2015-03-03_1613',
             result_file('test-error.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test-error.2015-03-03_1613.table',
            diff_prefix='test-error.2015-03-03_1613.diff',
            )

    def test_error_result_ignored(self):
        self.generate_tables_and_compare_content(
            ['--name', 'test.2015-03-03_1613.results.valueAnalysis',
             '--ignore-erroneous-benchmarks',
             result_file('test-error.2015-03-03_1613.results.predicateAnalysis.xml'),
             result_file('test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.results.valueAnalysis.table',
            )

    def test_compressed_table_gzip(self):
        self.generate_tables_and_compare_content(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml.gz')],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_compressed_table_bzip2(self):
        self.generate_tables_and_compare_content(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml.bz2')],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_output_stdout(self):
        output, _, _, _, _ = self.generate_tables_and_check_produced_files(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             '-f', 'csv', '-q'],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            formats=[],
            output_path='-',
            )
        expected = util.read_file(here, 'expected', 'test.2015-03-03_1613.results.predicateAnalysis' + '.csv')
        self.assertMultiLineEqual(output.strip(), expected)

    def test_format_csv(self):
        self.generate_tables_and_check_produced_files(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             '-f', 'csv'],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            formats=['csv'],
            )

    def test_format_html(self):
        self.generate_tables_and_check_produced_files(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             '-f', 'html'],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            formats=['html'],
            )

    def test_format_csv_html(self):
        self.generate_tables_and_check_produced_files(
            [result_file('test.2015-03-03_1613.results.predicateAnalysis.xml'),
             '-f', 'csv', '-f', 'html'],
            table_prefix='test.2015-03-03_1613.results.predicateAnalysis',
            formats=['csv', 'html'],
            )

    def test_smt_results(self):
        self.generate_tables_and_compare_content(
            ['-x', os.path.join(here, 'smt.xml'),
            ],
            table_prefix='smt.table',
            diff_prefix='smt.diff',
            )

    def test_results_via_url(self):
        try:
            self.generate_tables_and_compare_content(
                ["https://sosy-lab.github.io/benchexec/example-table/cbmc.2015-12-11_1211.results.Simple.xml"],
                table_prefix="cbmc.2015-12-11_1211.results.Simple",
                )
        except subprocess.CalledProcessError as e:
            if "HTTP Error" or "urlopen error" in e.output.decode():
                self.skipTest("HTTP access to GitHub failed")
            else:
                raise
