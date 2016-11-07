
import logging
import xml.etree.ElementTree as ET

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
	ConSequence for SV-COMP 2017
    """
    REQUIRED_PATHS = [
                  "consequence.pl"
                  ]
    def executable(self):
        return util.find_executable('consequence.pl')


    def version(self, executable):
        return "Version 1.0"


    def name(self):
        return 'ConSequence SV-COMP 2017'

    """
    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options += ['--property-file', propertyfile]
        self.options = options
        return [executable] + options + tasks
    """



    def determine_result(self, returncode, returnsignal, output, isTimeout):
        lines = " ".join(output[-10:])
        print(lines)

        if isTimeout:
            return 'TIMEOUT' 

        if "success" in lines:
            return result.RESULT_TRUE_PROP
        elif "failed" in lines:
            return result.RESULT_FALSE_REACH
        elif "unknown" in lines:
            return result.RESULT_UNKNOWN
        else:
            return result.RESULT_ERROR

