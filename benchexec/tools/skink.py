import logging
import subprocess

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    def executable(self):
        return util.find_executable('skink.sh')

    def version(self, executable):
        return "0.314"

    def name(self):
        return 'skink'

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "Program is correct" in output:
            status = result.RESULT_TRUE_PROP
        elif "Program is incorrect" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status