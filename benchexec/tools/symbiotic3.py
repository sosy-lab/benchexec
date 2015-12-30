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
from os.path import dirname
from os.path import join as joinpath

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    Symbiotic tool info object
    """

    REQUIRED_PATHS = [
                  "bin",
                  "build-fix.sh",
                  "include",
                  "lib",
                  "lib32",
                  "lib.c",
                  "path_to_ml.pl",
                  "symbiotic"
                  ]

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('symbiotic')

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return self._version_from_tool(executable)

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'symbiotic'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        # only one task is supported
        assert len(tasks) == 1

        if not propertyfile is None:
            options = options + ['--prp={0}'.format(propertyfile)]

        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'timeout'

        if output is None:
            return 'error (no output)'

        for line in output:
          line = line.strip()
          if line == 'TRUE':
            return result.RESULT_TRUE_PROP
          elif line == 'UNKNOWN':
            return result.RESULT_UNKNOWN
          elif line == 'FALSE':
            return result.RESULT_FALSE_REACH

        return result.RESULT_ERROR
