# coding=utf-8
from benchexec import util, result
from benchexec.tools.template import BaseTool

__author__ = 'guangchen'


class Tool(BaseTool):
    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'TIMEOUT'
        if returncode != 0:
            return 'CRASH'
        status = result.RESULT_UNKNOWN
        output = str(output)
        if 'TRUE' in output:
            return result.RESULT_TRUE_PROP
        if 'FALSE' in output and 'bb_VERIFY_ERROR' in output:
            return result.RESULT_FALSE_REACH
        return result.RESULT_UNKNOWN

    def name(self):
        return 'Ceagle AbsRef'

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return [executable, 'beagle-ir2elts', 'sv_absref', 'libz3.so']

    def executable(self):
        return util.find_executable('absref.sh')

