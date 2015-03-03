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

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import benchexec.util as util
sys.dont_write_bytecode = True # prevent creation of .pyc files

here = os.path.dirname(__file__)
base_dir = os.path.join(here, '..', '..', '..')
bin_dir = os.path.join(base_dir, 'bin')
tablegenerator = os.path.join(bin_dir, 'table-generator')

class TableGeneratorIntegrationTests(unittest.TestCase):

    # Tests compare the generated CSV files and ignore the HTML files
    # because we assume the HTML files change more often on purpose.

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="BenchExec.tablegenerator.integration_test")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cmd(self, *args):
        print(subprocess.check_output(args=args).decode())

    def generate_tables_and_compare_csv(self, args, table_prefix, result_prefix=None):
        self.run_cmd(*[tablegenerator] + list(args) + ['--outputpath', self.tmp])
        print('table-generator produced files: ' + '\n'.join(os.listdir(self.tmp)))
        csv_file = os.path.join(self.tmp, table_prefix + '.csv')
        html_file = os.path.join(self.tmp, table_prefix + '.html')
        self.assertTrue(os.path.exists(html_file), 'Missing file for HTML table')
        self.assertTrue(os.path.exists(csv_file), 'Missing file for CSV table')

        generated = util.read_file(csv_file)
        expected = util.read_file(here, 'expected', (result_prefix or table_prefix) + '.csv')
        self.assertMultiLineEqual(generated, expected)

    def test_simple_table(self):
        self.generate_tables_and_compare_csv(
            [os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_simple_table_correct_only(self):
        self.generate_tables_and_compare_csv(
            ['--correct-only', os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            'test.2015-03-03_1613.results.predicateAnalysis.correct-only',
            )

    def test_simple_table_all_columns(self):
        self.generate_tables_and_compare_csv(
            ['--all-columns', os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            'test.2015-03-03_1613.results.predicateAnalysis.all-columns',
            )

    def test_simple_table_xml(self):
        self.generate_tables_and_compare_csv(
            ['-x', os.path.join(here, 'simple-table.xml')],
            'simple-table.table',
            'test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_simple_table_xml_with_columns(self):
        self.generate_tables_and_compare_csv(
            ['-x', os.path.join(here, 'simple-table-with-columns.xml')],
            'simple-table-with-columns.table',
            )
