# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0
"""
This class serves as BenchExec tool adaptor for Sikraken for Test-Comp
See baseclass documentation at https://github.com/sosy-lab/benchexec/blob/main/benchexec/tools/template.py
"""
import os
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    BenchExec tool-info for Sikraken
    """

    def name(self):
        return "Sikraken" 
    
    def project_url(self):
        return "https://github.com/echancrure/Sikraken" 
        
    def executable(self, tool_locator):
        return tool_locator.find_executable("sikraken.sh", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable, "-v")  
    
    """
    #Assuming that the default working directory is the root of the project (i.e. sikraken/) we don't need this
    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir
    """

    #Sikraken is currently ignoring property files as we only support "coverage-branches.prp"
    #I am assuming more options come from the benchmark definition .xml file "The benchmark definition defines the categories that the tester is to be executed on, the parameters to be passed, and the resource limits."
    #the rlimits for testcomp are passed as options

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "-m32", LP64: "-m64"})
        options += [data_model_param]
        return [executable] + options + [task.single_input_file]
        
    #we are always DONE
    def determine_result(self, run):
        status = result.RESULT_DONE
        return status
