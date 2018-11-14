"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2015-2018  Vladimír Štill
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

This file contains tool support for DIVINE (divine.fi.muni.cz)
"""

import logging

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result
import subprocess

import os

class Tool(benchexec.tools.template.BaseTool):
    """
    DIVINE tool info object
    """

    BINS = ['divine', 'divine-svc']
    RESMAP = { 'true': result.RESULT_TRUE_PROP
             , 'false': result.RESULT_FALSE_REACH
             , 'false-deref': result.RESULT_FALSE_DEREF
             , 'false-free': result.RESULT_FALSE_FREE
             , 'false-memtrack': result.RESULT_FALSE_MEMTRACK
             , 'false-term': result.RESULT_FALSE_TERMINATION
             , 'false-deadlock': result.RESULT_FALSE_DEADLOCK
             , 'false-overflow': result.RESULT_FALSE_OVERFLOW
             }

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable(self.BINS[0])

    def version(self, executable):
        try:
            process = subprocess.Popen([executable, "--version"],
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            (stdout, _) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run {0} to determine version: {1}'.
                            format(executable, e.strerror))
            return ''
        if process.returncode:
            logging.warning('Cannot determine {0} version, exit code {1}'.
                            format(executable, process.returncode))
            return ''
        lns = {}
        for l in util.decode_to_string(stdout).strip().splitlines():
            k, v = l.split(':', maxsplit=1)
            lns[k] = v
        return lns['version']


    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'DIVINE'

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
        prp = propertyfile if propertyfile is not None else "-"

        run = [os.path.join('.', directory, self.BINS[1]), executable, prp] + options + tasks
        return run

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

        if not output:
            return 'ERROR - no output'

        last = output[-1]

        if isTimeout:
            return 'TIMEOUT'

        if returncode != 0:
            return 'ERROR - {0}'.format( last )

        if 'result:' in last:
            res = last.split(':', maxsplit=1)[1].strip()
            return self.RESMAP.get( res, result.RESULT_UNKNOWN );
        else:
            return ''.join( output )
            return result.RESULT_UNKNOWN

    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool.
        """
        directory = os.path.dirname(executable)
        libs = []
        for (dirpath, _, filenames) in os.walk(os.path.join('.', directory, "lib")):
            libs.extend( [os.path.join(dirpath, x) for x in filenames] )
        return [os.path.join('.', directory, x) for x in self.BINS] + libs
