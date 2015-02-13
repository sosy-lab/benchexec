import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an imaginary tool that returns always UNSAFE.
    To use it you need a normal benchmark-xml-file
    with the tool and sourcefiles, however options are ignored.
    """

    def executable(self):
        return '/bin/false'

    def name(self):
        return 'AlwaysFalseReach'

    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        return [executable] + sourcefiles

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        return result.STATUS_FALSE_REACH