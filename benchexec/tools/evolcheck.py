import logging
import os
import platform
import tempfile
import subprocess
import hashlib
import xml.etree.ElementTree as ET

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    previousStatus = None

    def executable(self):
        return util.find_executable('evolcheck_wrapper')


    def version(self, executable):
        return subprocess.Popen([executable, '--version'],
                                stdout=subprocess.PIPE).communicate()[0].strip()

    def name(self):
        return 'eVolCheck'

    def preprocessSourcefile(self, sourcefile):
        gotoCcExecutable      = util.find_executable('goto-cc')
        # compile with goto-cc to same file, bith '.cc' appended
        self.preprocessedFile = sourcefile + ".cc"

        subprocess.Popen([gotoCcExecutable,
                            sourcefile,
                            '-o',
                            self.preprocessedFile],
                          stdout=subprocess.PIPE).wait()

        return self.preprocessedFile


    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        sourcefile = sourcefiles[0]
        sourcefile = self.preprocessSourcefile(sourcefile)

        # also append '.cc' to the predecessor-file
        if '--predecessor' in options :
            options[options.index('--predecessor') + 1] = options[options.index('--predecessor') + 1] + '.cc'

        return [executable] + [sourcefile] + options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if not os.path.isfile(self.preprocessedFile):
            return 'ERROR (goto-cc)'

        status = None

        assertionHoldsFound         = False
        verificationSuccessfulFound = False
        verificationFailedFound     = False

        for line in output:
            if 'A real bug found.' in line:
                status = result.STATUS_FALSE_REACH
            elif 'VERIFICATION SUCCESSFUL' in line:
                verificationSuccessfulFound = True
            elif 'VERIFICATION FAILED' in line:
                verificationFailedFound = True
            elif 'ASSERTION(S) HOLD(S)' in line:
                assertionHoldsFound = True
            elif 'The program models are identical' in line:
                status = self.previousStatus
            elif 'Assertion(s) hold trivially.' in line:
                status = result.STATUS_TRUE_PROP

        if status is None:
            if verificationSuccessfulFound and not verificationFailedFound:
                status = result.STATUS_TRUE_PROP
            else:
                status = result.STATUS_UNKNOWN

        self.previousStatus = status

        return status
