import benchexec.tools.template
import benchexec.result as result
import benchexec.util as util


class Tool(benchexec.tools.template.BaseTool):

    def executable(self):
        return util.find_executable("goblint")

    def name(self):
        return "Goblint"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        for line in output:
            line = line.strip()
            if line == "SV-COMP (unreach-call): true":
                return result.RESULT_TRUE_PROP
            elif line == "SV-COMP (unreach-call): false":
                return result.RESULT_FALSE_PROP

        return result.RESULT_UNKNOWN
