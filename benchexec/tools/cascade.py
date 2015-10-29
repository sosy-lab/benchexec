"""
Cascade Verification Tool
Copyright (c) 2015 New York University
All Rights Reserved
"""

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool wrapper for Cascade (http://cascade.cims.nyu.edu/).
    """

    def executable(self):
        return util.find_executable('run_cascade')

    def name(self):
        return 'Cascade'

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one sourcefile supported"
        inputfile = tasks[0]
        assert propertyfile is not None
        spec = ['-spec', propertyfile]
        return [executable] + options + spec + [inputfile]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "FALSE" in output:
            if "FALSE(valid-deref)" in output:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in output:
                status = result.RESULT_FALSE_FREE
            elif "FALSE(valid-memtrack)" in output:
                status = result.RESULT_FALSE_MEMTRACK
            else:
                status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        else:
            status = result.RESULT_UNKNOWN

        return status
