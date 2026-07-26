# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import unittest

import benchexec.model

here = os.path.dirname(__file__)


class ToolInfoModuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def test_load_tool_info_module(self):
        """Test whether all tool-info modules can be loaded"""
        files = os.listdir(here)
        for file_name in files:
            tool_info_name = os.path.splitext(file_name)
            if tool_info_name[1] != ".py" or file_name == os.path.basename(__file__):
                continue

            try:
                benchexec.model.load_tool_info(tool_info_name[0], Config())
            except SystemExit as e:
                logging.warning(
                    "Cannot load tool-info module %s: %s", tool_info_name, e
                )
            except BaseException as e:
                self.fail(f"Loading tool-info module {tool_info_name} failed: {e}")


class Config(object):
    """Dummy config object for test"""

    container = False
