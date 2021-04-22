# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
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

from benchexec import container
from benchexec import containerexecutor
from benchexec import filehierarchylimit
from benchexec.runexecutor import RunExecutor
from benchexec import runexecutor
from benchexec import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files

here = os.path.dirname(__file__)
base_dir = os.path.join(here, "..")
bin_dir = os.path.join(base_dir, "bin")
runexec = os.path.join(bin_dir, "runexec")

trivial_run_grace_time = 0.2


class TestRunExecutor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None
        logging.disable(logging.NOTSET)  # need to make sure to get all messages
        if not hasattr(cls, "assertRegex"):
            cls.assertRegex = cls.assertRegexpMatches

    def setUp(self, *args, **kwargs):
        with self.skip_if_logs(
            "Cannot reliably kill sub-processes without freezer cgroup"
        ):
            self.runexecutor = RunExecutor(use_namespaces=False, *args, **kwargs)

    @contextlib.contextmanager
    def skip_if_logs(self, error_msg):
        """A context manager that automatically marks the test as skipped if SystemExit
        is thrown and the given error message had been logged with level ERROR."""
        # Note: assertLogs checks that there is at least one log message of given level.
        # This is not what we want, so we just rely on one debug message being present.
        try:
            with self.assertLogs(level=logging.DEBUG) as log:
                yield
        except SystemExit as e:
            if any(
                record.levelno == logging.ERROR and record.msg.startswith(error_msg)
                for record in log.records
            ):
                self.skipTest(e)
            raise e

    def execute_run(self, *args, expect_terminationreason=None, **kwargs):
        (output_fd, output_filename) = tempfile.mkstemp(".log", "output_", text=True)
        try:
            result = self.runexecutor.execute_run(list(args), output_filename, **kwargs)
            output = os.read(output_fd, 4096).decode()
        finally:
            os.close(output_fd)
            os.remove(output_filename)

        self.check_result_keys(result, "terminationreason")
        if isinstance(expect_terminationreason, list):
            self.assertIn(
                result.get("terminationreason"),
                expect_terminationreason,
                "Unexpected terminationreason, output is \n" + output,
            )
        else:
            self.assertEqual(
                result.get("terminationreason"),
                expect_terminationreason,
                "Unexpected terminationreason, output is \n" + output,
            )
        return (result, output.splitlines())

    def get_runexec_cmdline(self, *args, **kwargs):
        return [
            "python3",
            runexec,
            "--no-container",
            "--output",
            kwargs["output_filename"],
        ] + list(args)

    def execute_run_extern(self, *args, expect_terminationreason=None, **kwargs):
        (output_fd, output_filename) = tempfile.mkstemp(".log", "output_", text=True)
        try:
            runexec_output = subprocess.check_output(
                args=self.get_runexec_cmdline(*args, output_filename=output_filename),
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                **kwargs,
            )
            output = os.read(output_fd, 4096).decode()
        except subprocess.CalledProcessError as e:
            print(e.output)
            raise e
        finally:
            os.close(output_fd)
            os.remove(output_filename)

        result = {
            key.strip(): value.strip()
            for (key, _, value) in (
                line.partition("=") for line in runexec_output.splitlines()
            )
        }
        self.check_result_keys(result, "terminationreason", "returnvalue")
        if isinstance(expect_terminationreason, list):
            self.assertIn(
                result.get("terminationreason"),
                expect_terminationreason,
                "Unexpected terminationreason, output is \n" + output,
            )
        else:
            self.assertEqual(
                result.get("terminationreason"),
                expect_terminationreason,
                "Unexpected terminationreason, output is \n" + output,
            )
        return (result, output.splitlines())

    def check_command_in_output(self, output, cmd):
        self.assertEqual(output[0], cmd, "run output misses executed command")

    def check_result_keys(self, result, *additional_keys):
        expected_keys = {
            "cputime",
            "walltime",
            "memory",
            "exitcode",
            "cpuenergy",
            "blkio-read",
            "blkio-write",
            "starttime",
        }
        expected_keys.update(additional_keys)
        for key in result.keys():
            if key.startswith("cputime-cpu"):
                self.assertRegex(
                    key,
                    "^cputime-cpu[0-9]+$",
                    "unexpected result entry '{}={}'".format(key, result[key]),
                )
            elif key.startswith("cpuenergy-"):
                self.assertRegex(
                    key,
                    "^cpuenergy-pkg[0-9]+-(package|core|uncore|dram|psys)$",
                    "unexpected result entry '{}={}'".format(key, result[key]),
                )
            else:
                self.assertIn(
                    key,
                    expected_keys,
                    "unexpected result entry '{}={}'".format(key, result[key]),
                )

    def check_exitcode(self, result, exitcode, msg=None):
        self.assertEqual(result["exitcode"].raw, exitcode, msg)

    def check_exitcode_extern(self, result, exitcode, msg=None):
        exitcode = util.ProcessExitCode.from_raw(exitcode)
        if exitcode.value is not None:
            self.assertEqual(int(result["returnvalue"]), exitcode.value, msg)
        else:
            self.assertEqual(int(result["exitsignal"]), exitcode.signal, msg)

    def test_command_output(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        (_, output) = self.execute_run("/bin/echo", "TEST_TOKEN")
        self.check_command_in_output(output, "/bin/echo TEST_TOKEN")
        self.assertEqual(output[-1], "TEST_TOKEN", "run output misses command output")
        for line in output[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_command_error_output(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")

        def execute_Run_intern(*args, **kwargs):
            (error_fd, error_filename) = tempfile.mkstemp(".log", "error_", text=True)
            try:
                (_, output_lines) = self.execute_run(
                    *args, error_filename=error_filename, **kwargs
                )
                error_lines = os.read(error_fd, 4096).decode().splitlines()
                return (output_lines, error_lines)
            finally:
                os.close(error_fd)
                os.remove(error_filename)

        (output_lines, error_lines) = execute_Run_intern(
            "/bin/sh", "-c", "/bin/echo ERROR_TOKEN >&2"
        )
        self.assertEqual(
            error_lines[-1], "ERROR_TOKEN", "run error output misses command output"
        )
        for line in output_lines[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")
        for line in error_lines[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run error output")

        (output_lines, error_lines) = execute_Run_intern("/bin/echo", "OUT_TOKEN")
        self.check_command_in_output(output_lines, "/bin/echo OUT_TOKEN")
        self.check_command_in_output(error_lines, "/bin/echo OUT_TOKEN")
        self.assertEqual(
            output_lines[-1], "OUT_TOKEN", "run output misses command output"
        )
        for line in output_lines[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")
        for line in error_lines[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run error output")

    def test_command_result(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        (result, _) = self.execute_run("/bin/echo", "TEST_TOKEN")
        self.check_exitcode(result, 0, "exit code of /bin/echo is not zero")
        self.assertAlmostEqual(
            result["walltime"],
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg="walltime of /bin/echo not as expected",
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg="cputime of /bin/echo not as expected",
            )
        self.check_result_keys(result)

    def test_wrong_command(self):
        (result, _) = self.execute_run(
            "/does/not/exist", expect_terminationreason="failed"
        )

    def test_wrong_command_extern(self):
        (result, _) = self.execute_run(
            "/does/not/exist", expect_terminationreason="failed"
        )

    def test_cputime_hardlimit(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        with self.skip_if_logs("Time limit cannot be specified without cpuacct cgroup"):
            (result, output) = self.execute_run(
                "/bin/sh",
                "-c",
                "i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i",
                hardtimelimit=1,
                expect_terminationreason="cputime",
            )
        self.check_exitcode(result, 9, "exit code of killed process is not 9")
        self.assertAlmostEqual(
            result["walltime"],
            1.4,
            delta=0.5,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        self.assertAlmostEqual(
            result["cputime"],
            1.4,
            delta=0.5,
            msg="cputime is not approximately the time after which the process should have been killed",
        )

        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_cputime_softlimit(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        with self.skip_if_logs(
            "Soft time limit cannot be specified without cpuacct cgroup"
        ):
            (result, output) = self.execute_run(
                "/bin/sh",
                "-c",
                "i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i",
                softtimelimit=1,
                expect_terminationreason="cputime-soft",
            )
        self.check_exitcode(result, 15, "exit code of killed process is not 15")
        self.assertAlmostEqual(
            result["walltime"],
            4,
            delta=3,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        self.assertAlmostEqual(
            result["cputime"],
            4,
            delta=3,
            msg="cputime is not approximately the time after which the process should have been killed",
        )

        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_walltime_limit(self):
        if not os.path.exists("/bin/sleep"):
            self.skipTest("missing /bin/sleep")
        (result, output) = self.execute_run(
            "/bin/sleep", "10", walltimelimit=1, expect_terminationreason="walltime"
        )

        self.check_exitcode(result, 9, "exit code of killed process is not 9")
        self.assertAlmostEqual(
            result["walltime"],
            4,
            delta=3,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg="cputime of /bin/sleep is not approximately zero",
            )

        self.check_command_in_output(output, "/bin/sleep 10")
        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_cputime_walltime_limit(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        with self.skip_if_logs("Time limit cannot be specified without cpuacct cgroup"):
            (result, output) = self.execute_run(
                "/bin/sh",
                "-c",
                "i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i",
                hardtimelimit=1,
                walltimelimit=5,
                expect_terminationreason="cputime",
            )

        self.check_exitcode(result, 9, "exit code of killed process is not 9")
        self.assertAlmostEqual(
            result["walltime"],
            1.4,
            delta=0.5,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        self.assertAlmostEqual(
            result["cputime"],
            1.4,
            delta=0.5,
            msg="cputime is not approximately the time after which the process should have been killed",
        )

        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_all_timelimits(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        with self.skip_if_logs("Time limit cannot be specified without cpuacct cgroup"):
            (result, output) = self.execute_run(
                "/bin/sh",
                "-c",
                "i=0; while [ $i -lt 10000000 ]; do i=$(($i+1)); done; echo $i",
                softtimelimit=1,
                hardtimelimit=2,
                walltimelimit=5,
                expect_terminationreason="cputime-soft",
            )

        self.check_exitcode(result, 15, "exit code of killed process is not 15")
        self.assertAlmostEqual(
            result["walltime"],
            1.4,
            delta=0.5,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        self.assertAlmostEqual(
            result["cputime"],
            1.4,
            delta=0.5,
            msg="cputime is not approximately the time after which the process should have been killed",
        )

        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_input_is_redirected_from_devnull(self):
        if not os.path.exists("/bin/cat"):
            self.skipTest("missing /bin/cat")
        (result, output) = self.execute_run("/bin/cat", walltimelimit=1)

        self.check_exitcode(result, 0, "exit code of process is not 0")
        self.assertAlmostEqual(
            result["walltime"],
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg='walltime of "/bin/cat < /dev/null" is not approximately zero',
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg='cputime of "/bin/cat < /dev/null" is not approximately zero',
            )
        self.check_result_keys(result)

        self.check_command_in_output(output, "/bin/cat")
        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_input_is_redirected_from_file(self):
        if not os.path.exists("/bin/cat"):
            self.skipTest("missing /bin/cat")
        with tempfile.TemporaryFile() as tmp:
            tmp.write(b"TEST_TOKEN")
            tmp.flush()
            tmp.seek(0)
            (result, output) = self.execute_run("/bin/cat", stdin=tmp, walltimelimit=1)

        self.check_exitcode(result, 0, "exit code of process is not 0")
        self.assertAlmostEqual(
            result["walltime"],
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg='walltime of "/bin/cat < /dev/null" is not approximately zero',
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg='cputime of "/bin/cat < /dev/null" is not approximately zero',
            )
        self.check_result_keys(result)

        self.check_command_in_output(output, "/bin/cat")
        self.assertEqual(output[-1], "TEST_TOKEN", "run output misses command output")
        for line in output[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_input_is_redirected_from_stdin(self):
        if not os.path.exists("/bin/cat"):
            self.skipTest("missing /bin/cat")

        (output_fd, output_filename) = tempfile.mkstemp(".log", "output_", text=True)
        cmd = self.get_runexec_cmdline(
            "--input",
            "-",
            "--walltime",
            "1",
            "/bin/cat",
            output_filename=output_filename,
        )
        try:
            process = subprocess.Popen(
                args=cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            try:
                runexec_output, unused_err = process.communicate("TEST_TOKEN")
            except BaseException:
                # catch everything, we re-raise
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if retcode:
                print(runexec_output)
                raise subprocess.CalledProcessError(retcode, cmd, output=runexec_output)

            output = os.read(output_fd, 4096).decode().splitlines()
        finally:
            os.close(output_fd)
            os.remove(output_filename)

        result = {
            key.strip(): value.strip()
            for (key, _, value) in (
                line.partition("=") for line in runexec_output.splitlines()
            )
        }
        self.check_exitcode_extern(result, 0, "exit code of process is not 0")
        self.assertAlmostEqual(
            float(result["walltime"].rstrip("s")),
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg='walltime of "/bin/cat < /dev/null" is not approximately zero',
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                float(result["cputime"].rstrip("s")),
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg='cputime of "/bin/cat < /dev/null" is not approximately zero',
            )
        self.check_result_keys(result, "returnvalue")

        self.check_command_in_output(output, "/bin/cat")
        self.assertEqual(output[-1], "TEST_TOKEN", "run output misses command output")
        for line in output[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_append_environment_variable(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (_, output) = self.execute_run("/bin/sh", "-c", "echo $PATH")
        path = output[-1]
        (_, output) = self.execute_run(
            "/bin/sh",
            "-c",
            "echo $PATH",
            environments={"additionalEnv": {"PATH": ":TEST_TOKEN"}},
        )
        self.assertEqual(output[-1], path + ":TEST_TOKEN")

    def test_new_environment_variable(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (_, output) = self.execute_run(
            "/bin/sh", "-c", "echo $PATH", environments={"newEnv": {"PATH": "/usr/bin"}}
        )
        self.assertEqual(output[-1], "/usr/bin")

    def test_stop_run(self):
        if not os.path.exists("/bin/sleep"):
            self.skipTest("missing /bin/sleep")
        thread = _StopRunThread(1, self.runexecutor)
        thread.start()
        (result, output) = self.execute_run(
            "/bin/sleep", "10", expect_terminationreason="killed"
        )
        thread.join()

        self.check_exitcode(result, 9, "exit code of killed process is not 9")
        self.assertAlmostEqual(
            result["walltime"],
            1,
            delta=0.5,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg="cputime of /bin/sleep is not approximately zero",
            )

        self.check_command_in_output(output, "/bin/sleep 10")
        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_reduce_file_size_empty_file(self):
        with tempfile.NamedTemporaryFile() as tmp:
            runexecutor._reduce_file_size_if_necessary(tmp.name, 0)
            self.assertEqual(os.path.getsize(tmp.name), 0)

    def test_reduce_file_size_empty_file2(self):
        with tempfile.NamedTemporaryFile() as tmp:
            runexecutor._reduce_file_size_if_necessary(tmp.name, 500)
            self.assertEqual(os.path.getsize(tmp.name), 0)

    def test_reduce_file_size_long_line_not_truncated(self):
        with tempfile.NamedTemporaryFile(mode="wt") as tmp:
            content = "Long line " * 500
            tmp.write(content)
            tmp.flush()
            runexecutor._reduce_file_size_if_necessary(tmp.name, 500)
            with open(tmp.name, "rt") as tmp2:
                self.assertMultiLineEqual(tmp2.read(), content)

    REDUCE_WARNING_MSG = (
        "WARNING: YOUR LOGFILE WAS TOO LONG, SOME LINES IN THE MIDDLE WERE REMOVED."
    )
    REDUCE_OVERHEAD = 100

    def test_reduce_file_size(self):
        with tempfile.NamedTemporaryFile(mode="wt") as tmp:
            line = "Some text\n"
            tmp.write(line * 500)
            tmp.flush()
            limit = 500
            runexecutor._reduce_file_size_if_necessary(tmp.name, limit)
            self.assertLessEqual(
                os.path.getsize(tmp.name), limit + self.REDUCE_OVERHEAD
            )
            with open(tmp.name, "rt") as tmp2:
                new_content = tmp2.read()
        self.assertIn(self.REDUCE_WARNING_MSG, new_content)
        self.assertTrue(new_content.startswith(line))
        self.assertTrue(new_content.endswith(line))

    def test_reduce_file_size_limit_zero(self):
        with tempfile.NamedTemporaryFile(mode="wt") as tmp:
            line = "Some text\n"
            tmp.write(line * 500)
            tmp.flush()
            runexecutor._reduce_file_size_if_necessary(tmp.name, 0)
            self.assertLessEqual(os.path.getsize(tmp.name), self.REDUCE_OVERHEAD)
            with open(tmp.name, "rt") as tmp2:
                new_content = tmp2.read()
        self.assertIn(self.REDUCE_WARNING_MSG, new_content)
        self.assertTrue(new_content.startswith(line))

    def test_append_crash_dump_info(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (result, output) = self.execute_run(
            "/bin/sh",
            "-c",
            'echo "# An error report file with more information is saved as:";'
            'echo "# $(pwd)/hs_err_pid_1234.txt";'
            "echo TEST_TOKEN > hs_err_pid_1234.txt;"
            "exit 2",
        )
        self.assertEqual(
            output[-1], "TEST_TOKEN", "log file misses content from crash dump file"
        )

    def test_integration(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        (result, output) = self.execute_run_extern("/bin/echo", "TEST_TOKEN")
        self.check_exitcode_extern(result, 0, "exit code of /bin/echo is not zero")
        self.check_result_keys(result, "returnvalue")

        self.check_command_in_output(output, "/bin/echo TEST_TOKEN")
        self.assertEqual(output[-1], "TEST_TOKEN", "run output misses command output")
        for line in output[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_home_and_tmp_is_separate(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (result, output) = self.execute_run("/bin/sh", "-c", "echo $HOME $TMPDIR")
        self.check_exitcode(result, 0, "exit code of /bin/sh is not zero")
        self.assertRegex(
            output[-1],
            "/BenchExec_run_[^/]*/home .*/BenchExec_run_[^/]*/tmp",
            "HOME or TMPDIR variable does not contain expected temporary directory",
        )

    def test_temp_dirs_are_removed(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (result, output) = self.execute_run("/bin/sh", "-c", "echo $HOME $TMPDIR")
        self.check_exitcode(result, 0, "exit code of /bin/sh is not zero")
        home_dir = output[-1].split(" ")[0]
        temp_dir = output[-1].split(" ")[1]
        self.assertFalse(
            os.path.exists(home_dir),
            "temporary home directory {} was not cleaned up".format(home_dir),
        )
        self.assertFalse(
            os.path.exists(temp_dir),
            "temporary temp directory {} was not cleaned up".format(temp_dir),
        )

    def test_home_is_writable(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (result, output) = self.execute_run("/bin/sh", "-c", "touch $HOME/TEST_FILE")
        self.check_exitcode(
            result,
            0,
            "Failed to write to $HOME/TEST_FILE, output was\n{}".format(output),
        )

    def test_no_cleanup_temp(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        self.setUp(cleanup_temp_dir=False)  # create RunExecutor with desired parameter
        (result, output) = self.execute_run(
            "/bin/sh", "-c", 'echo "$TMPDIR"; echo "" > "$TMPDIR/test"'
        )
        self.check_exitcode(result, 0, "exit code of /bin/sh is not zero")
        temp_dir = output[-1]
        test_file = os.path.join(temp_dir, "test")
        subprocess.run(["test", "-f", test_file], check=True)
        self.assertEqual(
            "tmp", os.path.basename(temp_dir), "unexpected name of temp dir"
        )
        self.assertNotEqual(
            "/tmp", temp_dir, "temp dir should not be the global temp dir"
        )
        subprocess.run(["rm", "-r", os.path.dirname(temp_dir)], check=True)

    def test_require_cgroup_invalid(self):
        with self.assertLogs(level=logging.ERROR) as log:
            with self.assertRaises(SystemExit):
                RunExecutor(additional_cgroup_subsystems=["invalid"])

        self.assertIn(
            'Cgroup subsystem "invalid" was required but is not available',
            "\n".join(log.output),
        )

    def test_require_cgroup_cpu(self):
        try:
            self.setUp(additional_cgroup_subsystems=["cpu"])
        except SystemExit as e:
            self.skipTest(e)
        if not os.path.exists("/bin/cat"):
            self.skipTest("missing /bin/cat")
        (result, output) = self.execute_run("/bin/cat", "/proc/self/cgroup")
        self.check_exitcode(result, 0, "exit code of /bin/cat is not zero")
        for line in output:
            if re.match(r"^[0-9]*:([^:]*,)?cpu(,[^:]*)?:/(.*/)?benchmark_.*$", line):
                return  # Success
        self.fail("Not in expected cgroup for subsystem cpu:\n" + "\n".join(output))

    def test_set_cgroup_cpu_shares(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        try:
            self.setUp(additional_cgroup_subsystems=["cpu"])
        except SystemExit as e:
            self.skipTest(e)
        (result, _) = self.execute_run(
            "/bin/echo", cgroupValues={("cpu", "shares"): 42}
        )
        self.check_exitcode(result, 0, "exit code of /bin/echo is not zero")
        # Just assert that execution was successful,
        # testing that the value was actually set is much more difficult.

    def test_nested_runexec(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        self.setUp(
            dir_modes={
                # Do not mark /home hidden, would fail with python from virtualenv
                "/": containerexecutor.DIR_READ_ONLY,
                "/tmp": containerexecutor.DIR_FULL_ACCESS,  # for inner_output_file
                "/sys/fs/cgroup": containerexecutor.DIR_FULL_ACCESS,
            }
        )
        inner_args = ["--", "/bin/echo", "TEST_TOKEN"]

        with tempfile.NamedTemporaryFile(
            mode="r", prefix="inner_output_", suffix=".log"
        ) as inner_output_file:
            inner_cmdline = self.get_runexec_cmdline(
                *inner_args, output_filename=inner_output_file.name
            )
            outer_result, outer_output = self.execute_run(*inner_cmdline)
            inner_output = inner_output_file.read().strip().splitlines()

        logging.info("Outer output:\n" + "\n".join(outer_output))
        logging.info("Inner output:\n" + "\n".join(inner_output))
        self.check_result_keys(outer_result, "returnvalue")
        self.check_exitcode(outer_result, 0, "exit code of inner runexec is not zero")
        self.check_command_in_output(inner_output, "/bin/echo TEST_TOKEN")
        self.assertEqual(
            inner_output[-1], "TEST_TOKEN", "run output misses command output"
        )

    def test_starttime(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("missing /bin/echo")
        before = util.read_local_time()
        (result, _) = self.execute_run("/bin/echo")
        after = util.read_local_time()
        self.check_result_keys(result)
        run_starttime = result["starttime"]
        self.assertIsNotNone(run_starttime.tzinfo, "start time is not a local time")
        self.assertLessEqual(before, run_starttime)
        self.assertLessEqual(run_starttime, after)


class TestRunExecutorWithContainer(TestRunExecutor):
    def setUp(self, *args, **kwargs):
        try:
            container.execute_in_namespace(lambda: 0)
        except OSError as e:
            self.skipTest("Namespaces not supported: {}".format(os.strerror(e.errno)))

        dir_modes = kwargs.pop(
            "dir_modes",
            {
                "/": containerexecutor.DIR_READ_ONLY,
                "/home": containerexecutor.DIR_HIDDEN,
                "/tmp": containerexecutor.DIR_HIDDEN,
            },
        )

        self.runexecutor = RunExecutor(
            use_namespaces=True, dir_modes=dir_modes, *args, **kwargs
        )

    def get_runexec_cmdline(self, *args, **kwargs):
        return [
            "python3",
            runexec,
            "--container",
            "--read-only-dir",
            "/",
            "--hidden-dir",
            "/home",
            "--hidden-dir",
            "/tmp",
            "--dir",
            "/tmp",
            "--output",
            kwargs["output_filename"],
        ] + list(args)

    def execute_run(self, *args, **kwargs):
        return super(TestRunExecutorWithContainer, self).execute_run(
            workingDir="/tmp", *args, **kwargs
        )

    def test_home_and_tmp_is_separate(self):
        self.skipTest("not relevant in container")

    def test_temp_dirs_are_removed(self):
        self.skipTest("not relevant in container")

    def test_no_cleanup_temp(self):
        self.skipTest("not relevant in container")

    def check_result_files(
        self, shell_cmd, result_files_patterns, expected_result_files
    ):
        output_dir = tempfile.mkdtemp("", "output_")
        try:
            result, output = self.execute_run(
                "/bin/sh",
                "-c",
                shell_cmd,
                output_dir=output_dir,
                result_files_patterns=result_files_patterns,
            )
            self.assertEqual(
                result["exitcode"].value,
                0,
                "exit code of {} is not zero,\nresult was {!r},\noutput was\n{}".format(
                    " ".join(shell_cmd), result, "\n".join(output)
                ),
            )
            result_files = []
            for root, _unused_dirs, files in os.walk(output_dir):
                for file in files:
                    result_files.append(
                        os.path.relpath(os.path.join(root, file), output_dir)
                    )
            expected_result_files.sort()
            result_files.sort()
            self.assertListEqual(
                result_files,
                expected_result_files,
                "\nList of retrieved result files differs from expected list,\n"
                "result was {!r},\noutput was\n{}".format(result, "\n".join(output)),
            )
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_result_file_simple(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["."], ["TEST_FILE"])

    def test_result_file_recursive(self):
        self.check_result_files(
            "mkdir TEST_DIR; echo TEST_TOKEN > TEST_DIR/TEST_FILE",
            ["."],
            ["TEST_DIR/TEST_FILE"],
        )

    def test_result_file_multiple(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; echo TEST_TOKEN > TEST_FILE2",
            ["."],
            ["TEST_FILE", "TEST_FILE2"],
        )

    def test_result_file_symlink(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; ln -s TEST_FILE TEST_LINK",
            ["."],
            ["TEST_FILE"],
        )

    def test_result_file_no_match(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["NO_MATCH"], [])

    def test_result_file_no_pattern(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", [], [])

    def test_result_file_empty_pattern(self):
        self.assertRaises(
            ValueError,
            lambda: self.check_result_files("echo TEST_TOKEN > TEST_FILE", [""], []),
        )

    def test_result_file_partial_match(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; mkdir TEST_DIR; echo TEST_TOKEN > TEST_DIR/TEST_FILE",
            ["TEST_DIR"],
            ["TEST_DIR/TEST_FILE"],
        )

    def test_result_file_multiple_patterns(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; "
            "echo TEST_TOKEN > TEST_FILE2; "
            "mkdir TEST_DIR; "
            "echo TEST_TOKEN > TEST_DIR/TEST_FILE; ",
            ["TEST_FILE", "TEST_DIR/TEST_FILE"],
            ["TEST_FILE", "TEST_DIR/TEST_FILE"],
        )

    def test_result_file_wildcard(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; "
            "echo TEST_TOKEN > TEST_FILE2; "
            "echo TEST_TOKEN > TEST_NOFILE; ",
            ["TEST_FILE*"],
            ["TEST_FILE", "TEST_FILE2"],
        )

    def test_result_file_absolute_pattern(self):
        self.check_result_files("echo TEST_TOKEN > TEST_FILE", ["/"], ["tmp/TEST_FILE"])

    def test_result_file_absolute_and_pattern(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE; mkdir TEST_DIR; echo TEST_TOKEN > TEST_DIR/TEST_FILE",
            ["TEST_FILE", "/tmp/TEST_DIR"],
            ["tmp/TEST_FILE", "tmp/TEST_DIR/TEST_FILE"],
        )

    def test_result_file_relative_traversal(self):
        self.check_result_files(
            "echo TEST_TOKEN > TEST_FILE", ["foo/../TEST_FILE"], ["TEST_FILE"]
        )

    def test_result_file_illegal_relative_traversal(self):
        self.assertRaises(
            ValueError,
            lambda: self.check_result_files(
                "echo TEST_TOKEN > TEST_FILE", ["foo/../../bar"], []
            ),
        )

    def test_result_file_recursive_pattern(self):
        self.check_result_files(
            "mkdir -p TEST_DIR/TEST_DIR; "
            "echo TEST_TOKEN > TEST_FILE.txt; "
            "echo TEST_TOKEN > TEST_DIR/TEST_FILE.txt; "
            "echo TEST_TOKEN > TEST_DIR/TEST_DIR/TEST_FILE.txt; ",
            ["**/*.txt"],
            [
                "TEST_FILE.txt",
                "TEST_DIR/TEST_FILE.txt",
                "TEST_DIR/TEST_DIR/TEST_FILE.txt",
            ],
        )

    def test_file_count_limit(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        self.setUp(container_tmpfs=False)  # create RunExecutor with desired parameter
        filehierarchylimit._CHECK_INTERVAL_SECONDS = 0.1
        (result, output) = self.execute_run(
            "/bin/sh",
            "-c",
            "for i in $(seq 1 10000); do touch $i; done",
            files_count_limit=100,
            result_files_patterns=None,
            expect_terminationreason="files-count",
        )

        self.check_exitcode(result, 9, "exit code of killed process is not 15")

        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_file_size_limit(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        self.setUp(container_tmpfs=False)  # create RunExecutor with desired parameter
        filehierarchylimit._CHECK_INTERVAL_SECONDS = 0.1
        (result, output) = self.execute_run(
            "/bin/sh",
            "-c",
            "for i in $(seq 1 100000); do echo $i >> TEST_FILE; done",
            files_size_limit=100,
            result_files_patterns=None,
            expect_terminationreason="files-size",
        )

        self.check_exitcode(result, 9, "exit code of killed process is not 15")

        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_path_with_space(self):
        temp_dir = tempfile.mkdtemp(prefix="BenchExec test")
        try:
            # create RunExecutor with desired parameter
            self.setUp(
                dir_modes={
                    "/": containerexecutor.DIR_READ_ONLY,
                    "/home": containerexecutor.DIR_HIDDEN,
                    "/tmp": containerexecutor.DIR_HIDDEN,
                    temp_dir: containerexecutor.DIR_FULL_ACCESS,
                }
            )
            temp_file = os.path.join(temp_dir, "TEST_FILE")
            result, output = self.execute_run(
                "/bin/sh", "-c", "echo TEST_TOKEN > '{}'".format(temp_file)
            )
            self.check_result_keys(result)
            self.check_exitcode(result, 0, "exit code of process is not 0")
            self.assertTrue(
                os.path.exists(temp_file),
                "File '{}' not created, output was:{}\n".format(
                    temp_file, "\n".join(output)
                ),
            )
            with open(temp_file, "r") as f:
                self.assertEqual(f.read().strip(), "TEST_TOKEN")
        finally:
            shutil.rmtree(temp_dir)

    def test_uptime_with_lxcfs(self):
        if not os.path.exists("/var/lib/lxcfs/proc"):
            self.skipTest("missing lxcfs")
        result, output = self.execute_run("cat", "/proc/uptime")
        self.check_result_keys(result)
        self.check_exitcode(result, 0, "exit code for reading uptime is not zero")
        uptime = float(output[-1].split(" ")[0])
        self.assertLessEqual(
            uptime, 10, "Uptime %ss unexpectedly high in container" % uptime
        )

    def test_uptime_without_lxcfs(self):
        if not os.path.exists("/var/lib/lxcfs/proc"):
            self.skipTest("missing lxcfs")
        # create RunExecutor with desired parameter
        self.setUp(container_system_config=False)
        result, output = self.execute_run("cat", "/proc/uptime")
        self.check_result_keys(result)
        self.check_exitcode(result, 0, "exit code for reading uptime is not zero")
        uptime = float(output[-1].split(" ")[0])
        # If uptime was less than 10s, LXCFS probably was in use
        self.assertGreaterEqual(
            uptime, 10, "Uptime %ss unexpectedly low in container" % uptime
        )


class _StopRunThread(threading.Thread):
    def __init__(self, delay, runexecutor):
        super(_StopRunThread, self).__init__()
        self.daemon = True
        self.delay = delay
        self.runexecutor = runexecutor

    def run(self):
        time.sleep(self.delay)
        self.runexecutor.stop()


class TestRunExecutorUnits(unittest.TestCase):
    """unit tests for parts of RunExecutor"""

    def test_get_debug_output_with_error_report_and_invalid_utf8(self):
        invalid_utf8 = b"\xFF"
        with tempfile.NamedTemporaryFile(mode="w+b", delete=False) as report_file:
            with tempfile.NamedTemporaryFile(mode="w+b") as output:
                output_content = """Dummy output
# An error report file with more information is saved as:
# {}
More output
"""
                output_content = output_content.format(report_file.name).encode()
                report_content = b"Report output\nMore lines"
                output_content += invalid_utf8
                report_content += invalid_utf8

                output.write(output_content)
                output.flush()
                output.seek(0)
                report_file.write(report_content)
                report_file.flush()

                runexecutor._get_debug_output_after_crash(output.name, "")

                self.assertFalse(os.path.exists(report_file.name))
                self.assertEqual(output.read(), output_content + report_content)