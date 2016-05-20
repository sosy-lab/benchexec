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

"""Main package of BenchExec.

The following modules are the public entry points:
- benchexec: for executing benchmark suites
- runexec: for executing single runs
- check_cgroups: for checking the availability of cgroups
- test_tool_info: for testing a tool-info module

Naming conventions used within BenchExec:

TOOL: a (verification) tool that should be executed
EXECUTABLE: the executable file that should be called for running a TOOL
INPUTFILE: one input file for the TOOL
SOURCEFILE: deprecated name for INPUTFILE
RUN: one execution of a TOOL on one INPUTFILE
RUNSET: a set of RUNs of one TOOL with at most one RUN per INPUTFILE
RUNDEFINITION: a template for the creation of a RUNSET with RUNS from one or more INPUTFILESETs
BENCHMARK: a list of RUNDEFINITIONs and INPUTFILESETs for one TOOL
OPTION: a user-specified option to add to the command-line of the TOOL when it its run
CONFIG: the configuration of this script consisting of the command-line arguments given by the user
EXECUTOR: a module for executing a BENCHMARK

"run" always denotes a job to do and is never used as a verb.
"execute" is only used as a verb (this is what is done with a run).
A benchmark or a run set can also be executed, which means to execute all contained runs.

Variables ending with "file" contain filenames.
Variables ending with "tag" contain references to XML tag objects created by the XML parser.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = '1.9'

class BenchExecException(Exception):
    pass