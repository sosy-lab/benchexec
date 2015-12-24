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
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

import os

class Tool(benchexec.tools.template.BaseTool):
    """
    SymDIVINE info object
    """

    BINS = ['symdivine', 'run_symdivine.py', 'compile_to_bitcode.py',
        'lart', 'libz3.so', 'libc.so.6', 'libgomp.so.1', 'libstdc++.so.6']

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable(self.BINS[0])

    def version(self, executable):
        return "0.2"

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'SymDIVINE'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            In most cases we we have only _one_ inputfile.
        @param propertyfile: contains a specification for the verifier.
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        """
        directory = os.path.dirname(executable)

        # Ignore propertyfile since we run only reachability
        return [os.path.join('.', directory, self.BINS[1]), directory] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """

        join_output = '\n'.join(output)

        if isTimeout:
            return 'TIMEOUT'

        if returncode == 2:
            return 'ERROR - Pre-run'

        if join_output is None:
            return 'ERROR - no output'
        elif 'Safe.'in join_output:
            return result.RESULT_TRUE_PROP
        elif 'Error state' in join_output:
            return result.RESULT_FALSE_REACH
        else:
            return result.RESULT_UNKNOWN

    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool.
        """
        directory = os.path.dirname(executable)
        return [os.path.join('.', directory, f) for f in self.BINS]
