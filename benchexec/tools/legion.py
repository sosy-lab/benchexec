import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Legion (https://github.com/Alan32Liu/Principes).
    """

    REQUIRED_PATHS = [
        "legion-sv",
        "Legion.py",
        "__VERIFIER.c",
        "__trace_jump.s",
        "tracejump.py",
        "lib",
    ]

    def executable(self):
        return util.find_executable('legion-sv')

    def name(self):
        return 'Legion'
