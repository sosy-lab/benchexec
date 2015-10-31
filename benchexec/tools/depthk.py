
import subprocess
import os
import re
import benchexec.util as Util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):

    """
    This class serves as tool adaptor for DepthK (www.esbmc.org)
    Autor: Williame Rocha - williame.rocha10@gmail.com
    	   Herbert Rocha - herberthb12@gmail.com
    """

    def executable(self):

        # Relative path to depthk wrapper

        return Util.find_executable('depthk-wrapper.sh')

    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]

    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def environment(self, executable):
        return {'additionalEnv': {'PATH': ':.'}}

    def version(self, executable):
        workingDir = self.working_directory(executable)
        return subprocess.Popen([workingDir + '/depthk.py', '--version'],
                                stdout=subprocess.PIPE).communicate()[0].strip()

    def name(self):
        return 'DepthK'

    def cmdline(
        self,
        executable,
        options,
        tasks,
        propertyfile,
        rlimits,
        ):
        assert len(tasks) == 1, 'only one sourcefile supported'
        sourcefile = tasks[0]
        workingDir = self.working_directory(executable)
        return [os.path.relpath(executable, start=workingDir)] \
            + options + ['-c', propertyfile, os.path.relpath(sourcefile, start=workingDir)]

    def determine_result(
        self,
        returncode,
        returnsignal,
        output,
        isTimeout,
        ):

        if len(output) <= 0:
            return

        output = output[-1].strip()
        status = ''

        if 'TRUE' in output:
            status = result.RESULT_TRUE_PROP
        elif 'FALSE' in output:
            if 'FALSE(valid-memtrack)' in output:
                status = result.RESULT_FALSE_MEMTRACK
            elif 'FALSE(valid-deref)' in output:
                status = result.RESULT_FALSE_DEREF
            elif 'FALSE(no-overflow)' in output:
                status = result.RESULT_FALSE_OVERFLOW
            else:
                status = result.RESULT_FALSE_REACH
        elif 'UNKNOWN' in output:
            status = result.RESULT_UNKNOWN
        elif isTimeout:
            status = 'TIMEOUT'
        else:
            status = 'ERROR'

        return status

    

			
