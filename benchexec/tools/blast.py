import subprocess
import os

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    def executable(self):
        return util.find_executable('pblast.opt')


    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]


    def working_directory(self, executable):
        return os.curdir


    def environment(self, executable):
        executableDir = os.path.dirname(executable)
        workingDir = self.working_directory(executable)
        return {"additionalEnv" : {'PATH' :  ':' + (os.path.relpath(executableDir, start=workingDir))}}


    def version(self, executable):
        return subprocess.Popen([executable],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT).communicate()[0][6:11]


    def cmdline(self, blastExe, options, sourcefiles, propertyfile, rlimits):
        workingDir = self.working_directory(blastExe)
        ocamlExe = util.find_executable('ocamltune')
        return [os.path.relpath(ocamlExe, start=workingDir), os.path.relpath(blastExe, start=workingDir)] + options + sourcefiles


    def name(self):
        return 'BLAST'


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.STATUS_UNKNOWN
        for line in output:
            if line.startswith('Error found! The system is unsafe :-('):
                status = result.STATUS_FALSE_REACH
            elif line.startswith('No error found.  The system is safe :-)'):
                status = result.STATUS_TRUE_PROP
            elif line.startswith('Fatal error: exception Out_of_memory'):
                status = 'OUT OF MEMORY'
            elif line.startswith('Error: label \'ERROR\' appears multiple times'):
                status = 'ERROR'
            elif (returnsignal == 9):
                status = 'TIMEOUT'
            elif 'Ack! The gremlins again!' in line:
                status = 'EXCEPTION (Gremlins)'
        return status
