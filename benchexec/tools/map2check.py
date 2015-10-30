import subprocess
import os
import re
import benchexec.util as Util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for Map2Check (https://github.com/hbgit/Map2Check)
    """

    def executable(self):
        #Relative path to map2check wrapper
        return Util.find_executable('wrapper_script_map2check.sh')


    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]


    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir


    def environment(self, executable):
        return {"additionalEnv" : {'PATH' :  ':.'}}


    def version(self, executable):
        workingDir = self.working_directory(executable)
        return str(subprocess.Popen([workingDir + '/map2check.py', '--version'],
                                stdout=subprocess.PIPE).communicate()[0]).strip()


    def name(self):
        return 'Map2Check'


    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        sourcefile = sourcefiles[0]
        workingDir = self.working_directory(executable)        
        return [os.path.relpath(executable, start=workingDir)] + options + ['-c', propertyfile, os.path.relpath(sourcefile, start=workingDir)]


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if len(output) <= 0:
          return        
        output = output[-1].strip()                
        status = result.RESULT_UNKNOWN
                
        if output.endswith('TRUE'):
            status = result.RESULT_TRUE_PROP
        elif 'FALSE' in output:
            if "FALSE(valid-memtrack)" in output:
                status = result.RESULT_FALSE_MEMTRACK
            elif "FALSE(valid-deref)" in output:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in output:
                status = result.RESULT_FALSE_FREE
        elif output.endswith('UNKNOWN'):
            status = result.RESULT_UNKNOWN
        elif isTimeout:
            status = 'TIMEOUT'
        else:
            status = 'ERROR'

        return status
