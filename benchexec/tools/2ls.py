import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    Wrapper for 2LS (http://www.cprover.org/2LS).
    """

    def executable(self):
        return util.find_executable('2ls')

    def name(self):
        return '2LS'

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if ((returnsignal == 9) or (returnsignal == 15)) and isTimeout:
            status = 'TIMEOUT'
        elif returnsignal == 9:
            status = "KILLED BY SIGNAL 9"
        elif returncode == 0:
            status = result.RESULT_TRUE_PROP
        elif returncode == 10:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status


