import benchexec.util as util
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool):

    def executable(self):
        return util.find_executable('ufo.sh')


    def name(self):
        return 'Ufo'


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if returnsignal == 9 or returnsignal == (128+9):
            if isTimeout:
                status = "TIMEOUT"
            else:
                status = "KILLED BY SIGNAL 9"
        elif returncode == 1 and "program correct: ERROR unreachable" in output:
            status = "SAFE"
        elif returncode != 0:
            status = "ERROR ({0})".format(returncode)
        elif "ERROR reachable" in output:
            status = "UNSAFE"
        elif "program correct: ERROR unreachable" in output:
            status = "SAFE"
        else:
            status = "FAILURE"
        return status