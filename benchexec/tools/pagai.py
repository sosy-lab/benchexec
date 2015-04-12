import benchmark.util as Util
import benchmark.tools.template
import benchmark.result as result

class Tool(benchmark.tools.template.BaseTool):
    """
    Wrapper for a PAGAI tool (http://pagai.forge.imag.fr/).
    """

    def getExecutable(self):
        return Util.findExecutable('pagai')

    def getName(self):
        return 'PAGAI'

    def getStatus(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if returnsignal == 9 or returnsignal == (128+9):
            if isTimeout:
                status = "TIMEOUT"
            else:
                status = "KILLED BY SIGNAL 9"
        elif "RESULT: TRUE" in output:
            status = result.STATUS_TRUE_PROP
        elif returncode != 0:
            status = "ERROR ({0})".format(returncode)
        elif "RESULT: UNKNOWN" in output:
            status = result.STATUS_UNKNOWN
        else:
            status = result.STATUS_UNKNOWN
        return status

