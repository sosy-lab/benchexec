
import subprocess
import os
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for Threader (http://www.esbmc.org/)
    """

    def executable(self):
        return util.find_executable('threader.sh')


    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]


    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir


    def environment(self, executable):
        return {"additionalEnv" : {'PATH' :  ':.'}}


    def version(self, executable):
        exe = 'cream'
        return subprocess.Popen([exe, '--help'], stdout=subprocess.PIPE)\
                              .communicate()[0].splitlines()[2][34:42]


    def name(self):
        return 'Threader'


    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        sourcefile = sourcefiles[0]
        workingDir = self.working_directory(executable)
        return [os.path.relpath(executable, start=workingDir)] + options + [os.path.relpath(sourcefile, start=workingDir)]


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if 'SSSAFE' in output:
            status = result.STATUS_TRUE_PROP
        elif 'UNSAFE' in output:
            status = result.STATUS_FALSE_REACH
        else:
            status = result.STATUS_UNKNOWN

        if status == result.STATUS_UNKNOWN and isTimeout:
            status = 'TIMEOUT'

        return status
