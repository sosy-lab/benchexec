# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import shutil
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import container
from benchexec import containerexecutor
from benchexec.runexecutor import RunExecutor
from benchexec import runexecutor

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

try:
    unichr(0)
except NameError:
    unichr = chr

here = os.path.dirname(__file__)
base_dir = os.path.join(here, '..')
bin_dir = os.path.join(base_dir, 'bin')
runexec = os.path.join(bin_dir, 'runexec')
python = 'python2' if sys.version_info[0] == 2 else 'python3'

class TestRunExecutor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None
        logging.disable(logging.CRITICAL)
        if not hasattr(cls, 'assertRegex'):
            cls.assertRegex = cls.assertRegexpMatches
        if not hasattr(cls, 'assertRaisesRegex'):
            cls.assertRaisesRegex = cls.assertRaisesRegexp

    def setUp(self, *args, **kwargs):
        self.runexecutor = RunExecutor(*args, **kwargs)

    def execute_run(self, *args, **kwargs):
        (output_fd, output_filename) = tempfile.mkstemp('.log', 'output_', text=True)
        try:
            result = self.runexecutor.execute_run(list(args), output_filename, **kwargs)
            output_lines = os.read(output_fd, 4096).decode().splitlines()
            return (result, output_lines)
        finally:
            os.close(output_fd)
            os.remove(output_filename)

    def execute_run_extern(self, *args, **kwargs):
        (output_fd, output_filename) = tempfile.mkstemp('.log', 'output_', text=True)
        try:
            runexec_output = subprocess.check_output(
                    args=[python, runexec] + list(args) + ['--output', output_filename],
                    stderr=DEVNULL,
                    **kwargs
                    ).decode()
            output_lines = os.read(output_fd, 4096).decode().splitlines()
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            raise e
        finally:
            os.close(output_fd)
            os.remove(output_filename)

        result={key.strip(): value.strip() for (key, _, value) in (line.partition('=') for line in runexec_output.splitlines())}
        return (result, output_lines)

    def check_command_in_output(self, output, cmd):
        self.assertEqual(output[0], cmd, 'run output misses executed command')

    def check_result_keys(self, result, *additional_keys):
        expected_keys = {'cputime', 'walltime', 'memory', 'exitcode',
                         'energy', 'energy-cpu', 'energy-core', 'energy-uncore'}
        expected_keys.update(additional_keys)
        for key in result.keys():
            if key.startswith('cputime-cpu'):
                self.assertRegex(key, '^cputime-cpu[0-9]+$',
                                 "unexpected result entry '{}={}'".format(key, result[key]))
            else:
                self.assertIn(key, expected_keys,
                              "unexpected result entry '{}={}'".format(key, result[key]))

    def test_command_output(self):
        if not os.path.exists('/bin/echo'):
            self.skipTest('missing /bin/echo')
        (_, output) = self.execute_run('/bin/echo', 'TEST_TOKEN')
        self.check_command_in_output(output, '/bin/echo TEST_TOKEN')
        self.assertEqual(output[-1], 'TEST_TOKEN', 'run output misses command output')
        for line in output[1:-1]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_command_result(self):
        if not os.path.exists('/bin/echo'):
            self.skipTest('missing /bin/echo')
        (result, _) = self.execute_run('/bin/echo', 'TEST_TOKEN')
        self.assertEqual(result['exitcode'], 0, 'exit code of /bin/echo is not zero')
        self.assertAlmostEqual(result['walltime'], 0.2, delta=0.2, msg='walltime of /bin/echo not as expected')
        self.assertAlmostEqual(result['cputime'], 0.2, delta=0.2, msg='cputime of /bin/echo not as expected')
        self.check_result_keys(result)

    def test_cputime_hardlimit(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        (result, output) = self.execute_run('/bin/sh', '-c', 'i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i',
                                            hardtimelimit=1)
        self.assertEqual(result['exitcode'], 9, 'exit code of killed process is not 9')
        if 'terminationreason' in result:
            # not produced currently if killed by ulimit
            self.assertEqual(result['terminationreason'], 'cputime', 'termination reason is not "cputime"')
        self.assertAlmostEqual(result['walltime'], 1.4, delta=0.5, msg='walltime is not approximately the time after which the process should have been killed')
        self.assertAlmostEqual(result['cputime'], 1.4, delta=0.5, msg='cputime is not approximately the time after which the process should have been killed')
        self.check_result_keys(result, 'terminationreason')

        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_cputime_softlimit(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        try:
            (result, output) = self.execute_run('/bin/sh', '-c', 'i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i',
                                                softtimelimit=1)
        except SystemExit as e:
            self.assertEqual(str(e), 'Soft time limit cannot be specified without cpuacct cgroup.')
            self.skipTest(e)

        self.assertEqual(result['exitcode'], 15, 'exit code of killed process is not 15')
        self.assertEqual(result['terminationreason'], 'cputime-soft', 'termination reason is not "cputime-soft"')
        self.assertAlmostEqual(result['walltime'], 4, delta=3, msg='walltime is not approximately the time after which the process should have been killed')
        self.assertAlmostEqual(result['cputime'], 4, delta=3, msg='cputime is not approximately the time after which the process should have been killed')
        self.check_result_keys(result, 'terminationreason')

        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_walltime_limit(self):
        if not os.path.exists('/bin/sleep'):
            self.skipTest('missing /bin/sleep')
        try:
            (result, output) = self.execute_run('/bin/sleep', '10', walltimelimit=1)
        except SystemExit as e:
            self.assertEqual(str(e), 'Wall time limit is not implemented for systems without cpuacct cgroup.')
            self.skipTest(e)

        self.assertEqual(result['exitcode'], 9, 'exit code of killed process is not 9')
        self.assertEqual(result['terminationreason'], 'walltime', 'termination reason is not "walltime"')
        self.assertAlmostEqual(result['walltime'], 4, delta=3, msg='walltime is not approximately the time after which the process should have been killed')
        self.assertAlmostEqual(result['cputime'], 0.2, delta=0.2, msg='cputime of /bin/sleep is not approximately zero')
        self.check_result_keys(result, 'terminationreason')

        self.check_command_in_output(output, '/bin/sleep 10')
        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_cputime_walltime_limit(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        (result, output) = self.execute_run('/bin/sh', '-c', 'i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i',
                                            hardtimelimit=1, walltimelimit=5)

        self.assertEqual(result['exitcode'], 9, 'exit code of killed process is not 9')
        if 'terminationreason' in result:
            # not produced currently if killed by ulimit
            self.assertEqual(result['terminationreason'], 'cputime', 'termination reason is not "cputime"')
        self.assertAlmostEqual(result['walltime'], 1.4, delta=0.5, msg='walltime is not approximately the time after which the process should have been killed')
        self.assertAlmostEqual(result['cputime'], 1.4, delta=0.5, msg='cputime is not approximately the time after which the process should have been killed')
        self.check_result_keys(result, 'terminationreason')

        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_all_timelimits(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        try:
            (result, output) = self.execute_run('/bin/sh', '-c', 'i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i',
                                                softtimelimit=1, hardtimelimit=2, walltimelimit=5)
        except SystemExit as e:
            self.assertEqual(str(e), 'Soft time limit cannot be specified without cpuacct cgroup.')
            self.skipTest(e)

        self.assertEqual(result['exitcode'], 15, 'exit code of killed process is not 15')
        self.assertEqual(result['terminationreason'], 'cputime-soft', 'termination reason is not "cputime-soft"')
        self.assertAlmostEqual(result['walltime'], 1.4, delta=0.5, msg='walltime is not approximately the time after which the process should have been killed')
        self.assertAlmostEqual(result['cputime'], 1.4, delta=0.5, msg='cputime is not approximately the time after which the process should have been killed')
        self.check_result_keys(result, 'terminationreason')

        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_input_is_redirected_from_devnull(self):
        if not os.path.exists('/bin/cat'):
            self.skipTest('missing /bin/cat')
        try:
            (result, output) = self.execute_run('/bin/cat', walltimelimit=1)
        except SystemExit as e:
            self.assertEqual(str(e), 'Wall time limit is not implemented for systems without cpuacct cgroup.')
            self.skipTest(e)

        self.assertEqual(result['exitcode'], 0, 'exit code of process is not 0')
        self.assertAlmostEqual(result['walltime'], 0.2, delta=0.2, msg='walltime of "/bin/cat < /dev/null" is not approximately zero')
        self.assertAlmostEqual(result['cputime'], 0.2, delta=0.2, msg='cputime of "/bin/cat < /dev/null" is not approximately zero')
        self.check_result_keys(result)

        self.check_command_in_output(output, '/bin/cat')
        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_input_is_redirected_from_file(self):
        if not os.path.exists('/bin/cat'):
            self.skipTest('missing /bin/cat')
        with tempfile.TemporaryFile() as tmp:
            tmp.write(b'TEST_TOKEN')
            tmp.flush()
            tmp.seek(0)
            try:
                (result, output) = self.execute_run('/bin/cat', stdin=tmp, walltimelimit=1)
            except SystemExit as e:
                self.assertEqual(str(e), 'Wall time limit is not implemented for systems without cpuacct cgroup.')
                self.skipTest(e)

        self.assertEqual(result['exitcode'], 0, 'exit code of process is not 0')
        self.assertAlmostEqual(result['walltime'], 0.2, delta=0.2, msg='walltime of "/bin/cat < /dev/null" is not approximately zero')
        self.assertAlmostEqual(result['cputime'], 0.2, delta=0.2, msg='cputime of "/bin/cat < /dev/null" is not approximately zero')
        self.check_result_keys(result)

        self.check_command_in_output(output, '/bin/cat')
        self.assertEqual(output[-1], 'TEST_TOKEN', 'run output misses command output')
        for line in output[1:-1]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_input_is_redirected_from_stdin(self):
        if not os.path.exists('/bin/cat'):
            self.skipTest('missing /bin/cat')

        (output_fd, output_filename) = tempfile.mkstemp('.log', 'output_', text=True)
        cmd = [runexec, '--input', '-', '--output', output_filename, '--walltime', '1', '/bin/cat']
        try:
            process = subprocess.Popen(args=cmd, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=DEVNULL)
            try:
                runexec_output, unused_err = process.communicate(b'TEST_TOKEN')
            except:
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if retcode:
                print(runexec_output.decode())
                raise subprocess.CalledProcessError(retcode, cmd, output=runexec_output)

            output = os.read(output_fd, 4096).decode().splitlines()
        finally:
            os.close(output_fd)
            os.remove(output_filename)

        result={key.strip(): value.strip() for (key, _, value) in (line.partition('=') for line in runexec_output.decode().splitlines())}
        self.assertEqual(int(result['exitcode']), 0, 'exit code of process is not 0')
        self.assertAlmostEqual(float(result['walltime'].rstrip('s')), 0.2, delta=0.2, msg='walltime of "/bin/cat < /dev/null" is not approximately zero')
        self.assertAlmostEqual(float(result['cputime'].rstrip('s')), 0.2, delta=0.2, msg='cputime of "/bin/cat < /dev/null" is not approximately zero')
        self.check_result_keys(result, 'returnvalue')

        self.check_command_in_output(output, '/bin/cat')
        self.assertEqual(output[-1], 'TEST_TOKEN', 'run output misses command output')
        for line in output[1:-1]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_stop_run(self):
        if not os.path.exists('/bin/sleep'):
            self.skipTest('missing /bin/sleep')
        thread = _StopRunThread(1, self.runexecutor)
        thread.start()
        (result, output) = self.execute_run('/bin/sleep', '10')
        thread.join()

        self.assertEqual(result['exitcode'], 9, 'exit code of killed process is not 9')
        self.assertEqual(result['terminationreason'], 'killed', 'termination reason is not "killed"')
        self.assertAlmostEqual(result['walltime'], 1, delta=0.5, msg='walltime is not approximately the time after which the process should have been killed')
        self.assertAlmostEqual(result['cputime'], 0.2, delta=0.2, msg='cputime of /bin/sleep is not approximately zero')
        self.check_result_keys(result, 'terminationreason')

        self.check_command_in_output(output, '/bin/sleep 10')
        for line in output[1:]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')


    def test_reduce_file_size_empty_file(self):
        with tempfile.NamedTemporaryFile() as tmp:
            runexecutor._reduce_file_size_if_necessary(tmp.name, 0)
            self.assertEqual(os.path.getsize(tmp.name), 0)

    def test_reduce_file_size_empty_file2(self):
        with tempfile.NamedTemporaryFile() as tmp:
            runexecutor._reduce_file_size_if_necessary(tmp.name, 500)
            self.assertEqual(os.path.getsize(tmp.name), 0)

    def test_reduce_file_size_long_line_not_truncated(self):
        with tempfile.NamedTemporaryFile(mode='wt') as tmp:
            content = 'Long line ' * 500
            tmp.write(content)
            tmp.flush()
            runexecutor._reduce_file_size_if_necessary(tmp.name, 500)
            with open(tmp.name, 'rt') as tmp2:
                self.assertMultiLineEqual(tmp2.read(), content)

    REDUCE_WARNING_MSG = "WARNING: YOUR LOGFILE WAS TOO LONG, SOME LINES IN THE MIDDLE WERE REMOVED."
    REDUCE_OVERHEAD = 100

    def test_reduce_file_size(self):
        with tempfile.NamedTemporaryFile(mode='wt') as tmp:
            line = 'Some text\n'
            tmp.write(line * 500)
            tmp.flush()
            limit = 500
            runexecutor._reduce_file_size_if_necessary(tmp.name, limit)
            self.assertLessEqual(os.path.getsize(tmp.name), limit + self.REDUCE_OVERHEAD)
            with open(tmp.name, 'rt') as tmp2:
                new_content = tmp2.read()
        self.assertIn(self.REDUCE_WARNING_MSG, new_content)
        self.assertTrue(new_content.startswith(line))
        self.assertTrue(new_content.endswith(line))

    def test_reduce_file_size_limit_zero(self):
        with tempfile.NamedTemporaryFile(mode='wt') as tmp:
            line = 'Some text\n'
            tmp.write(line * 500)
            tmp.flush()
            runexecutor._reduce_file_size_if_necessary(tmp.name, 0)
            self.assertLessEqual(os.path.getsize(tmp.name), self.REDUCE_OVERHEAD)
            with open(tmp.name, 'rt') as tmp2:
                new_content = tmp2.read()
        self.assertIn(self.REDUCE_WARNING_MSG, new_content)
        self.assertTrue(new_content.startswith(line))

    def test_integration(self):
        if not os.path.exists('/bin/echo'):
            self.skipTest('missing /bin/echo')
        (result, output) = self.execute_run_extern('/bin/echo', 'TEST_TOKEN')
        self.assertEqual(int(result['exitcode']), 0, 'exit code of /bin/echo is not zero')
        self.check_result_keys(result, 'returnvalue')

        self.check_command_in_output(output, '/bin/echo TEST_TOKEN')
        self.assertEqual(output[-1], 'TEST_TOKEN', 'run output misses command output')
        for line in output[1:-1]:
            self.assertRegex(line, '^-*$', 'unexpected text in run output')

    def test_home_and_tmp_is_separate(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        (result, output) = self.execute_run('/bin/sh', '-c', 'echo $HOME $TMPDIR')
        self.assertEqual(int(result['exitcode']), 0, 'exit code of /bin/sh is not zero')
        self.assertRegex(output[-1], '/BenchExec_run_[^/]*/home .*/BenchExec_run_[^/]*/tmp',
                         'HOME or TMPDIR variable does not contain expected temporary directory')

    def test_temp_dirs_are_removed(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        (result, output) = self.execute_run('/bin/sh', '-c', 'echo $HOME $TMPDIR')
        self.assertEqual(int(result['exitcode']), 0, 'exit code of /bin/sh is not zero')
        home_dir = output[-1].split(' ')[0]
        temp_dir = output[-1].split(' ')[1]
        self.assertFalse(os.path.exists(home_dir),
                         'temporary home directory {} was not cleaned up'.format(home_dir))
        self.assertFalse(os.path.exists(temp_dir),
                         'temporary temp directory {} was not cleaned up'.format(temp_dir))

    def test_no_cleanup_temp(self):
        if not os.path.exists('/bin/sh'):
            self.skipTest('missing /bin/sh')
        self.setUp(cleanup_temp_dir=False)  # create RunExecutor with desired parameter
        (result, output) = self.execute_run('/bin/sh', '-c', 'echo "$TMPDIR"; echo "" > "$TMPDIR/test"')
        self.assertEqual(int(result['exitcode']), 0, 'exit code of /bin/sh is not zero')
        temp_dir = output[-1]
        test_file = os.path.join(temp_dir, 'test')
        subprocess.check_call(self.runexecutor._build_cmdline(['test', '-f', test_file]))
        self.assertEqual('tmp', os.path.basename(temp_dir), 'unexpected name of temp dir')
        self.assertNotEqual('/tmp', temp_dir, 'temp dir should not be the global temp dir')
        subprocess.check_call(self.runexecutor._build_cmdline(['rm', '-r', os.path.dirname(temp_dir)]))

    def test_require_cgroup_invalid(self):
        self.assertRaisesRegex(SystemExit, '.*invalid.*',
                               lambda: RunExecutor(additional_cgroup_subsystems=['invalid']))

    def test_require_cgroup_cpu(self):
        try:
            self.setUp(additional_cgroup_subsystems=['cpu'])
        except SystemExit as e:
            self.skipTest(e)
        if not os.path.exists('/bin/cat'):
            self.skipTest('missing /bin/cat')
        (result, output) = self.execute_run('/bin/cat', '/proc/self/cgroup')
        self.assertEqual(int(result['exitcode']), 0, 'exit code of /bin/cat is not zero')
        for line in output:
            if re.match('^[0-9]*:cpu:/(.*/)?benchmark_.*$',line):
                return # Success
        self.fail('Not in expected cgroup for subsystem cpu:\n' + '\n'.join(output))

    def test_set_cgroup_cpu_shares(self):
        if not os.path.exists('/bin/echo'):
            self.skipTest('missing /bin/echo')
        try:
            self.setUp(additional_cgroup_subsystems=['cpu'])
        except SystemExit as e:
            self.skipTest(e)
        (result, _) = self.execute_run('/bin/echo',
                                            cgroupValues={('cpu', 'shares'): 42})
        self.assertEqual(int(result['exitcode']), 0, 'exit code of /bin/echo is not zero')
        # Just assert that execution was successful,
        # testing that the value was actually set is much more difficult.


class TestRunExecutorWithSudo(TestRunExecutor):
    """
    Run tests using the sudo mode of RunExecutor, if possible.
    sudo is typically set up to allow executing as our own user,
    so we try that. Note that this will not catch all problems,
    for example if we forget to use "sudo kill" to send a signal
    and instead send it directly, but requiring a second user for tests
    would not be good, either.
    """

    # Use user name defined in environment variable if present,
    # or fall back to current user (sudo always allows this).
    # sudo allows refering to numerical uids with '#'.
    user = os.environ.get('BENCHEXEC_TEST_USER', '#' + str(os.getuid()))

    def setUp(self, *args, **kwargs):
        try:
            self.runexecutor = RunExecutor(user=self.user, *args, **kwargs)
        except SystemExit as e:
            # sudo seems not to be available
            self.skipTest(e)

    def execute_run(self, *args, **kwargs):
        result, output = super(TestRunExecutorWithSudo, self).execute_run(*args, **kwargs)
        self.fix_exitcode(result)
        return (result, output)

    def execute_run_extern(self, *args, **kwargs):
        result, output = super(TestRunExecutorWithSudo, self) \
            .execute_run_extern('--user', self.user, *args, **kwargs)
        self.fix_exitcode(result)
        return (result, output)

    def fix_exitcode(self, result):
        # Using sudo may affect the exit code:
        # what was the returnsignal is now the returnvalue.
        # The distinction between returnsignal and returnvalue of the actual
        # process is lost.
        # If the returnsignal (of the sudo process) is 0,
        # we replace the exit code with the mixed returnsignal/returnvalue of
        # the actual process (with bit for core dump cleared).
        exitcode = int(result['exitcode'])
        returnsignal = exitcode & 0x7F
        returnvalue = (exitcode >> 8) & 0x7F
        if returnsignal == 0:
            result['exitcode'] = returnvalue

    def check_command_in_output(self, output, cmd):
        self.assertTrue(output[0].endswith(cmd), 'run output misses executed command')

    def test_detect_new_files_in_home(self):
        if not os.path.exists('/usr/bin/mktemp'):
            self.skipTest('missing /usr/bin/mktemp')
        home_dir = runexecutor._get_user_account_info(self.user).pw_dir
        tmp_file_pattern = '.BenchExec_test_runexecutor_'+unichr(0xe4)+unichr(0xf6)+unichr(0xfc)+'_XXXXXXXXXX'
        (result, output) = self.execute_run(
            '/usr/bin/mktemp', '--tmpdir=' + home_dir, tmp_file_pattern)
        try:
            self.assertEqual(int(result['exitcode']), 0, 'exit code of /usr/bin/mktemp is not zero')
            tmp_file = output[-1]
            self.assertIn(tmp_file, self.runexecutor.check_for_new_files_in_home(),
                          'runexecutor failed to detect new temporary file in home directory')
        finally:
            subprocess.check_call(self.runexecutor._build_cmdline(['rm', tmp_file]))


class TestRunExecutorWithContainer(TestRunExecutor):

    def setUp(self, *args, **kwargs):
        try:
            container.execute_in_namespace(lambda: 0)
        except OSError as e:
            self.skipTest("Namespaces not supported: {}".format(os.strerror(e.errno)))

        self.runexecutor = RunExecutor(
            use_namespaces=True,
            dir_modes={"/": containerexecutor.DIR_READ_ONLY,
                       "/tmp": containerexecutor.DIR_HIDDEN},
            container_system_config=False,
            *args, **kwargs)

    def execute_run(self, *args, **kwargs):
        return super(TestRunExecutorWithContainer, self).execute_run(workingDir="/tmp", *args, **kwargs)

    def test_home_and_tmp_is_separate(self):
        self.skipTest("not relevant in container")

    def test_temp_dirs_are_removed(self):
        self.skipTest("not relevant in container")

    def test_no_cleanup_temp(self):
        self.skipTest("not relevant in container")

    def check_result_files(self, shell_cmd, result_files_patterns, expected_result_files):
        output_dir = tempfile.mkdtemp("", "output_")
        try:
            result, output = self.execute_run("/bin/sh", "-c", shell_cmd,
                                              output_dir=output_dir,
                                              result_files_patterns=result_files_patterns)
            self.assertNotIn("terminationreason", result)
            self.assertEqual(result["exitcode"], 0,
                "exit code of {} is not zero,\nresult was {!r},\noutput was\n{}"
                    .format(" ".join(shell_cmd), result, "\n".join(output)))
            result_files = []
            for root, unused_dirs, files in os.walk(output_dir):
                for file in files:
                    result_files.append(os.path.relpath(os.path.join(root, file), output_dir))
            expected_result_files.sort()
            result_files.sort()
            self.assertListEqual(result_files, expected_result_files,
                "\nList of retrieved result files differs from expected list,\n"
                "result was {!r},\noutput was\n{}".format(result, "\n".join(output)))
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_result_file_simple(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["."], ["TEST_FILE"])

    def test_result_file_recursive(self):
        self.check_result_files("mkdir TEST_DIR; echo TEST_TOKEN > TEST_DIR/TEST_FILE", ["."],
                               ["TEST_DIR/TEST_FILE"])

    def test_result_file_multiple(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE; echo TEST_TOKEN > TEST_FILE2", ["."],
                               ["TEST_FILE", "TEST_FILE2"])

    def test_result_file_symlink(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE; ln -s TEST_FILE TEST_LINK", ["."],
                               ["TEST_FILE"])

    def test_result_file_no_match(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["NO_MATCH"], [])

    def test_result_file_no_pattern(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", [], [])

    def test_result_file_empty_pattern(self):
        self.assertRaises(ValueError,
            lambda: self.check_result_files("echo TEST_TOKEN > TEST_FILE", [""], []))

    def test_result_file_partial_match(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; mkdir TEST_DIR; echo TEST_TOKEN > TEST_DIR/TEST_FILE",
            ["TEST_DIR"], ["TEST_DIR/TEST_FILE"])

    def test_result_file_multiple_patterns(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; "
            "echo TEST_TOKEN > TEST_FILE2; "
            "mkdir TEST_DIR; "
            "echo TEST_TOKEN > TEST_DIR/TEST_FILE; ",
            ["TEST_FILE", "TEST_DIR/TEST_FILE"], ["TEST_FILE", "TEST_DIR/TEST_FILE"])

    def test_result_file_wildcard(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; "
            "echo TEST_TOKEN > TEST_FILE2; "
            "echo TEST_TOKEN > TEST_NOFILE; ",
            ["TEST_FILE*"], ["TEST_FILE", "TEST_FILE2"])

    def test_result_file_absolute_pattern(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["/"], ["tmp/TEST_FILE"])

    def test_result_file_absolute_and_pattern(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; mkdir TEST_DIR; echo TEST_TOKEN > TEST_DIR/TEST_FILE",
            ["TEST_FILE", "/tmp/TEST_DIR", ], ["tmp/TEST_FILE", "tmp/TEST_DIR/TEST_FILE"])

    def test_result_file_relative_traversal(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["foo/../TEST_FILE"], ["TEST_FILE"])

    def test_result_file_illegal_relative_traversal(self):
        self.assertRaises(ValueError,
            lambda: self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["foo/../../bar"], []))


class _StopRunThread(threading.Thread):
    def __init__(self, delay, runexecutor):
        super(_StopRunThread, self).__init__()
        self.daemon = True
        self.delay = delay
        self.runexecutor = runexecutor

    def run(self):
        time.sleep(self.delay)
        self.runexecutor.stop()
