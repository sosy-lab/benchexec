import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = [
                  "pinaka-wrapper.sh",
                  "pinaka"
                  ]

    def executable(self):
        return util.find_executable('pinaka-wrapper.sh')

    def name(self):
        return "Pinaka"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = ''

        if returnsignal==0 and ((returncode ==0) or (returncode==10)):
            if 'VERIFICATION SUCCESSFUL\n' in output:
                status = result.RESULT_TRUE_PROP
            elif 'VERIFICATION FAILED\n' in output:
                status = result.RESULT_FALSE_REACH
            else:
                status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
