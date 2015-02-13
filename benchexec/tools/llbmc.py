import os
import subprocess

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for LLBMC
    """

    def executable(self):
        return util.find_executable('lib/native/x86_64-linux/llbmc')


    def version(self, executable):
        return subprocess.Popen([executable, '--version'],
                                stdout=subprocess.PIPE).communicate()[0].splitlines()[2][8:18]


    def name(self):
        return 'LLBMC'


    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        sourcefile = sourcefiles[0]
        # compile sourcefile with clang
        self.prepSourcefile = self._prepareSourcefile(sourcefile)

        return [executable] + options + [self.prepSourcefile]


    def _prepareSourcefile(self, sourcefile):
        clangExecutable = util.find_executable('clang')
        newFilename     = sourcefile + ".o"

        subprocess.Popen([clangExecutable,
                            '-c',
                            '-emit-llvm',
                            '-std=gnu89',
                            '-m32',
                            sourcefile,
                            '-O0',
                            '-o',
                            newFilename,
                            '-w'],
                          stdout=subprocess.PIPE).wait()

        return newFilename


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.STATUS_UNKNOWN

        for line in output:
            if 'Error detected.' in line:
                status = result.STATUS_FALSE_REACH
            elif 'No error detected.' in line:
                status = result.STATUS_TRUE_PROP

        # delete tmp-files
        try:
          os.remove(self.prepSourcefile)
        except OSError, e:
            print "Could not remove file " + self.prepSourcefile + "! Maybe clang call failed"
            pass

        return status


    def add_column_values(self, output, columns):
        """
        This method adds the values that the user requested to the column objects.
        If a value is not found, it should be set to '-'.
        If not supported, this method does not need to get overridden.
        """
        pass
