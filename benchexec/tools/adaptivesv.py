# SPDX-License-Identifier: MIT
"""BenchExec adapter for AdaptiveSV; C reachability only."""
import math
from benchexec import result
from benchexec.tools.template import BaseTool2, UnsupportedFeatureException

class Tool(BaseTool2):
    """CPAchecker-backed C reachability; forwards task architecture and CPU budget."""
    REQUIRED_PATHS = ['bin/adaptivesv', 'src', 'configs', 'vendor', 'third_party/CPAchecker-4.2.2-unix']

    def name(self):
        return 'AdaptiveSV'

    def executable(self, tool_locator):
        return tool_locator.find_executable('adaptivesv', subdir='bin')

    def version(self, executable):
        return self._version_from_tool(executable).removeprefix('AdaptiveSV ').split(' ', 1)[0]

    def program_files(self, executable):
        return self._program_files_from_executable(executable, self.REQUIRED_PATHS, parent_dir=True)

    def cmdline(self, executable, options, task, rlimits):
        if not task.property_file:
            raise UnsupportedFeatureException('A reachability property file is required')
        metadata = task.options or {}
        if not isinstance(metadata, dict) or metadata.get('language', 'C') != 'C':
            raise UnsupportedFeatureException('Only C tasks are supported')
        model = metadata.get('data_model', 'ILP32')
        if model not in ('ILP32', 'LP64'):
            raise UnsupportedFeatureException(f'Unsupported data model: {model}')
        reserved = ('--architecture', '--program', '--property', '--time-limit')
        if any(opt.split('=')[0] in reserved for opt in options):
            raise UnsupportedFeatureException('Task-dependent options are supplied by the adapter')
        args = [executable, *options, '--program', task.single_input_file, '--property', task.property_file, '--architecture', '64' if model == 'LP64' else '32']
        if rlimits.cputime:
            args += ['--time-limit', str(max(1, math.floor(rlimits.cputime)))]
        return args

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        if run.exit_code.value != 0 or run.exit_code.signal:
            return result.RESULT_ERROR
        answers = [line.strip() for line in run.output if line.strip() in ('TRUE', 'FALSE(unreach-call)', 'UNKNOWN')]
        if len(answers) != 1:
            return result.RESULT_UNKNOWN
        return {'TRUE': result.RESULT_TRUE_PROP, 'FALSE(unreach-call)': result.RESULT_FALSE_REACH, 'UNKNOWN': result.RESULT_UNKNOWN}[answers[0]]
