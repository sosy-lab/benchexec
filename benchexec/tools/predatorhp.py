import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

import subprocess
import os
import sys

class Tool(benchexec.tools.template.BaseTool):
    """
    Wrapper for a Predator - Hunting Party
    http://www.fit.vutbr.cz/research/groups/verifit/tools/predator-hp/
    """

    def executable(self):
        executable = util.find_executable('predatorHP.py')
        executableDir = os.path.dirname(executable)
        if not os.path.isfile(os.path.join(executableDir, "predator-build-ok")):
            self._buildPredatorHp(executableDir)
        return executable

    def _buildPredatorHp(self, executableDir):
        proc = subprocess.Popen([os.path.join(executableDir, 'build-all.sh')], cwd=executableDir)
        proc.communicate()
        if proc.returncode:
            sys.exit('Failed to build Predator-HP, please fix the build first.')

    def name(self):
        return 'Predator-HP'
        
    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):        
        spec = ["--propertyfile", propertyfile] if propertyfile is not None else []
        return [executable] + options + spec + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        status = "UNKNOWN"
        if "UNKNOWN" in output:
            status = result.RESULT_UNKNOWN
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE(valid-memtrack)" in output:
            status = result.RESULT_FALSE_MEMTRACK
        elif "FALSE(valid-deref)" in output:
            status = result.RESULT_FALSE_DEREF
        elif "FALSE(valid-free)" in output:
            status = result.RESULT_FALSE_FREE
        elif "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        if (status == "UNKNOWN" and isTimeout):
            status = "TIMEOUT"
        return status

    def program_files(self, executable):
        """
        Returns a list of files or directories that are necessary to run the tool.
        """
        return [executable]
        
        
    def working_directory(self, executable):
        return os.path.dirname(executable)
        