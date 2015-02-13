import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    def executable(self):
        return util.find_executable('ecaverifier')


    def name(self):
        return 'EcaVerifier'


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.STATUS_UNKNOWN
        for line in output:
            if line.startswith('0 safe, 1 unsafe'):
                status = result.STATUS_FALSE_REACH
            elif line.startswith('1 safe, 0 unsafe'):
                status = result.STATUS_TRUE_PROP
            elif returnsignal == 9:
                if isTimeout:
                    status = 'TIMEOUT'
                else:
                    status = "KILLED BY SIGNAL 9"

        return status