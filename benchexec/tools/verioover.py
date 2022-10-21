

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    VeriOover
    """

    def name(self):
        return "VeriOover"

    def executable(self, tool_locator):
        return tool_locator.find_executable("VeriOover")
    
    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        if "-file" not in options:
            options = options + ["-file"]

        options = options + list(task.input_files_or_identifier)

        if task.property_file:
            options = options + ["-spec", task.property_file]

        return [executable] + options


    def determine_result(self, run):
        # parse output
        status = result.RESULT_UNKNOWN
        print(run.output)
        for line in run.output:
            if "spec incorrect!" in line:
                status = result.RESULT_FALSE_PROP
            elif "spec unknow!" in line:
                status = result.RESULT_UNKNOWN
            elif "spec correct!" in line:
                status = result.RESULT_TRUE_PROP

        return status

