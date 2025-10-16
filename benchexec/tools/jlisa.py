import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

import sys

class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for JLiSA
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("jlisa")
    
    def version(self, executable):
        return self._version_from_tool(executable, arg="version")

    def name(self):
        return "JLiSA"

    def project_url(self):
        return "https://github.com/lisa-analyzer/jlisa"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, "check", "--inputs", " ".join(task.input_files_or_empty)]
        if task.property_file:
            cmd += ["--property", task.property_file]
        return cmd

    def determine_result(self, run):
        try:
            jlisa_output = run.output[-1]
            ### ASSERT ###
            if jlisa_output == "ASSERT HOLDS FOR SOME CASES BUT NOT FOR OTHERS":
                return result.RESULT_UNKNOWN
            if jlisa_output == "ASSERT DOES HOLD":
                return result.RESULT_TRUE_PROP
            if jlisa_output == "ASSERT DOES NOT HOLD":
                return result.RESULT_UNKNOWN
            if jlisa_output == "ASSERT POSSIBLY HOLDS":
                return result.RESULT_UNKNOWN
            if jlisa_output == "NO ASSERT WARNING":
                return result.RESULT_UNKNOWN

            ### RUNTIME ###
            if jlisa_output == "RUNTIME HOLDS FOR SOME CASES BUT NOT FOR OTHERS": 
                return result.RESULT_UNKNOWN
            if jlisa_output == "RUNTIME DOES HOLD":
                return result.RESULT_TRUE_PROP
            if jlisa_output == "RUNTIME DOES NOT HOLD":
                return result.RESULT_FALSE_PROP
            if jlisa_output == "RUNTIME POSSIBLY HOLDS":
                return result.RESULT_UNKNOWN
            if jlisa_output == "NO RUNTIME WARNING":
                return result.RESULT_TRUE_PROP
            
            # UNKNOWN otherwise.
            return result.RESULT_UNKNOWN
        except:
            return result.RESULT_UNKNOWN
