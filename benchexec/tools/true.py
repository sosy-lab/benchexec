import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an imaginary tool that returns always SAFE.
    To use it you need a normal benchmark-xml-file
    with the tool and sourcefiles, however options are ignored.
    """
    def executable(self):
        return '/bin/true'

    def name(self):
        return 'AlwaysTrue'

    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        return [executable] + sourcefiles

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        return result.STATUS_TRUE_PROP