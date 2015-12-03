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

import sys
sys.dont_write_bytecode = True # prevent creation of .pyc files


if __name__ == '__main__':
    def showwarning(message, *args, **kwargs):
        if sys.stderr.isatty():
            sys.stderr.write("\033[31;1mWarning: " + str(message) + "\033[m\n")
        else:
            sys.stderr.write("Warning: " + str(message) + "\n")

    import warnings
    warnings.showwarning = showwarning
    warnings.warn('Using benchexec.test_tool_wrapper is deprecated, please call benchexec.test_tool_info.')

    from benchexec import test_tool_info
    sys.exit(test_tool_info.main())
