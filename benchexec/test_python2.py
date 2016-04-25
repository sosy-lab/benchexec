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

import sys
import unittest
sys.dont_write_bytecode = True # prevent creation of .pyc files

class Python2Tests(unittest.TestSuite):
    """
    Test suite aggregating all tests that should be executed when using Python 2
    (runexecutor supports Python 2, the rest does not).
    """

    def __init__(self):
        loader = unittest.TestLoader()
        super(Python2Tests, self).__init__([
            loader.loadTestsFromName('benchexec.test_cgroups'),
            loader.loadTestsFromName('benchexec.test_runexecutor'),
            loader.loadTestsFromName('benchexec.test_util'),
            ])
