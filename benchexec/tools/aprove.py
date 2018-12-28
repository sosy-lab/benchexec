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

import tempfile
import re
import subprocess
import logging

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for AProVE.
    URL: http://aprove.informatik.rwth-aachen.de/
    Only the binary (jar) distribution of AProVE is supported.
    """

    REQUIRED_PATHS = [
                  "aprove.jar",
                  "AProVE.sh",
                  "bin",
                  "newstrategy.strategy"
                  ]

    def executable(self):
        return util.find_executable('AProVE.sh')

    def name(self):
        return 'AProVE'

    def version(self, executable):
        with tempfile.NamedTemporaryFile(suffix=".c") as trivial_example:
            trivial_example.write(b'int main() { return 0; }\n')
            trivial_example.flush()

            cmd = [executable, trivial_example.name]
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (stdout, stderr) = process.communicate()
            except OSError as e:
                logging.warning('Unable to determine AProVE version: {0}'.format(e.strerror))
                return ''

            version_aprove_match = re.search(
                r'^# AProVE Commit ID: (.*)', util.decode_to_string(stdout), re.MULTILINE)
            if not version_aprove_match:
                logging.warning('Unable to determine AProVE version: {0}'.format(util.decode_to_string(stdout)))
                return ''
            return version_aprove_match.group(1)[:10]

    def determine_result(self, returncode, returnsignal, output, is_timeout):
        if not output:
            return result.RESULT_ERROR
        elif "YES" in output[0]:
            return result.RESULT_TRUE_PROP
        elif "TRUE" in output[0]:
            return result.RESULT_TRUE_PROP
        elif "FALSE" in output[0]:
            return result.RESULT_FALSE_TERMINATION
        elif "NO" in output[0]:
            return result.RESULT_FALSE_TERMINATION
        else:
            return result.RESULT_UNKNOWN
