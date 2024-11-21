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
import tempfile
import threading
import time
import unittest
import shutil

from benchexec import container
from benchexec import containerexecutor
from benchexec import filehierarchylimit
from benchexec.runexecutor import RunExecutor
from benchexec.cgroups import Cgroups
from benchexec import runexecutor
from benchexec import util

here = os.path.dirname(__file__)
base_dir = os.path.join(here, "..")
bin_dir = os.path.join(base_dir, "bin")
runexec = os.path.join(bin_dir, "runexec")

trivial_run_grace_time = 0.2


class TestRunExecutor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, "assertRegex"):
            cls.assertRegex = cls.assertRegexpMatches

        cls.cgroups = Cgroups.initialize()

        cls.echo = shutil.which("echo") or "/bin/echo"
        cls.sleep = shutil.which("sleep") or "/bin/sleep"
        cls.cat = shutil.which("cat") or "/bin/cat"
        cls.dd = shutil.which("dd") or "/bin/dd"
        cls.grep = shutil.which("grep") or "/bin/grep"

    def setUp(self, *args, **kwargs):
        with self.skip_if_logs(
            "Cannot reliably kill sub-processes without freezer cgroup"
        ):
            self.runexecutor = RunExecutor(*args, use_namespaces=False, **kwargs)

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
            "pressure-cpu-some",
            "pressure-io-some",
            "pressure-memory-some",
        }
        expected_keys.update(additional_keys)
        for key in result.keys():
            if key.startswith("cputime-cpu"):
                self.assertRegex(
                    key,
                    "^cputime-cpu[0-9]+$",
                    f"unexpected result entry '{key}={result[key]}'",
                )
            elif key.startswith("cpuenergy-"):
                self.assertRegex(
                    key,
                    "^cpuenergy-pkg[0-9]+-(package|core|uncore|dram|psys)$",
                    f"unexpected result entry '{key}={result[key]}'",
                )
            else:
                self.assertIn(
                    key,
                    expected_keys,
                    f"unexpected result entry '{key}={result[key]}'",
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
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
        (_, output) = self.execute_run(self.echo, "TEST_TOKEN")
        self.check_command_in_output(output, f"{self.echo} TEST_TOKEN")
        self.assertEqual(output[-1], "TEST_TOKEN", "run output misses command output")
        for line in output[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_command_error_output(self):
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
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
            "/bin/sh", "-c", f"{self.echo} ERROR_TOKEN >&2"
        )
        self.assertEqual(
            error_lines[-1], "ERROR_TOKEN", "run error output misses command output"
        )
        for line in output_lines[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")
        for line in error_lines[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run error output")

        (output_lines, error_lines) = execute_Run_intern(self.echo, "OUT_TOKEN")
        self.check_command_in_output(output_lines, f"{self.echo} OUT_TOKEN")
        self.check_command_in_output(error_lines, f"{self.echo} OUT_TOKEN")
        self.assertEqual(
            output_lines[-1], "OUT_TOKEN", "run output misses command output"
        )
        for line in output_lines[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")
        for line in error_lines[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run error output")

    def test_command_result(self):
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
        (result, _) = self.execute_run(self.echo, "TEST_TOKEN")
        self.check_exitcode(result, 0, "exit code of echo is not zero")
        self.assertAlmostEqual(
            result["walltime"],
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg="walltime of echo not as expected",
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg="cputime of echo not as expected",
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
        if not os.path.exists(self.sleep):
            self.skipTest("missing sleep")
        (result, output) = self.execute_run(
            self.sleep, "10", walltimelimit=1, expect_terminationreason="walltime"
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
                msg="cputime of sleep is not approximately zero",
            )

        self.check_command_in_output(output, f"{self.sleep} 10")
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

    def test_memory_limit(self):
        if not os.path.exists(self.dd):
            self.skipTest("missing dd")
        memlimit = 100_000_000
        (result, output) = self.execute_run(
            self.dd,
            "if=/dev/zero",
            "of=/dev/null",
            f"bs={memlimit}",
            "count=1",
            memlimit=memlimit,
            expect_terminationreason="memory",
        )

        self.check_exitcode(result, 9, "exit code of killed process is not 9")
        self.assertAlmostEqual(
            result["memory"],
            memlimit,
            delta=memlimit // 100,
            msg="memory is not approximately the amount after which the process should have been killed",
        )

        self.check_command_in_output(
            output, f"{self.dd} if=/dev/zero of=/dev/null bs={memlimit} count=1"
        )
        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_input_is_redirected_from_devnull(self):
        if not os.path.exists(self.cat):
            self.skipTest("missing cat")
        (result, output) = self.execute_run(self.cat, walltimelimit=1)

        self.check_exitcode(result, 0, "exit code of process is not 0")
        self.assertAlmostEqual(
            result["walltime"],
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg='walltime of "cat < /dev/null" is not approximately zero',
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg='cputime of "cat < /dev/null" is not approximately zero',
            )
        self.check_result_keys(result)

        self.check_command_in_output(output, self.cat)
        for line in output[1:]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_input_is_redirected_from_file(self):
        if not os.path.exists(self.cat):
            self.skipTest("missing cat")
        with tempfile.TemporaryFile() as tmp:
            tmp.write(b"TEST_TOKEN")
            tmp.flush()
            tmp.seek(0)
            (result, output) = self.execute_run(self.cat, stdin=tmp, walltimelimit=1)

        self.check_exitcode(result, 0, "exit code of process is not 0")
        self.assertAlmostEqual(
            result["walltime"],
            trivial_run_grace_time,
            delta=trivial_run_grace_time,
            msg='walltime of "cat < /dev/null" is not approximately zero',
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                result["cputime"],
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg='cputime of "cat < /dev/null" is not approximately zero',
            )
        self.check_result_keys(result)

        self.check_command_in_output(output, self.cat)
        self.assertEqual(output[-1], "TEST_TOKEN", "run output misses command output")
        for line in output[1:-1]:
            self.assertRegex(line, "^-*$", "unexpected text in run output")

    def test_input_is_redirected_from_stdin(self):
        if not os.path.exists(self.cat):
            self.skipTest("missing cat")

        (output_fd, output_filename) = tempfile.mkstemp(".log", "output_", text=True)
        cmd = self.get_runexec_cmdline(
            "--input",
            "-",
            "--walltime",
            "1",
            self.cat,
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
            msg='walltime of "cat < /dev/null" is not approximately zero',
        )
        if "cputime" in result:  # not present without cpuacct cgroup
            self.assertAlmostEqual(
                float(result["cputime"].rstrip("s")),
                trivial_run_grace_time,
                delta=trivial_run_grace_time,
                msg='cputime of "cat < /dev/null" is not approximately zero',
            )
        self.check_result_keys(result, "returnvalue")

        self.check_command_in_output(output, self.cat)
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
        if not os.path.exists(self.sleep):
            self.skipTest("missing sleep")
        thread = _StopRunThread(1, self.runexecutor)
        thread.start()
        (result, output) = self.execute_run(
            self.sleep, "10", expect_terminationreason="killed"
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
                msg="cputime of sleep is not approximately zero",
            )

        self.check_command_in_output(output, f"{self.sleep} 10")
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
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
        (result, output) = self.execute_run_extern(self.echo, "TEST_TOKEN")
        self.check_exitcode_extern(result, 0, "exit code of echo is not zero")
        self.check_result_keys(result, "returnvalue")

        self.check_command_in_output(output, f"{self.echo} TEST_TOKEN")
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
            f"temporary home directory {home_dir} was not cleaned up",
        )
        self.assertFalse(
            os.path.exists(temp_dir),
            f"temporary temp directory {temp_dir} was not cleaned up",
        )

    def test_home_is_writable(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("missing /bin/sh")
        (result, output) = self.execute_run("/bin/sh", "-c", "touch $HOME/TEST_FILE")
        self.check_exitcode(
            result,
            0,
            f"Failed to write to $HOME/TEST_FILE, output was\n{output}",
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
        if not os.path.exists(self.cat):
            self.skipTest("missing cat")
        if self.cgroups.version != 1:
            self.skipTest("not relevant in unified hierarchy")
        (result, output) = self.execute_run(self.cat, "/proc/self/cgroup")
        self.check_exitcode(result, 0, "exit code of cat is not zero")
        for line in output:
            if re.match(r"^[0-9]*:([^:]*,)?cpu(,[^:]*)?:/(.*/)?benchmark_.*$", line):
                return  # Success
        self.fail("Not in expected cgroup for subsystem cpu:\n" + "\n".join(output))

    def test_set_cgroup_cpu_shares(self):
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
        try:
            if self.cgroups.version == 1:
                self.setUp(additional_cgroup_subsystems=["cpu"])
            else:
                self.setUp(additional_cgroup_subsystems=["memory"])
        except SystemExit as e:
            self.skipTest(e)
        if self.cgroups.version == 1:
            cgValues = {("cpu", "shares"): 42}
        else:
            cgValues = {("memory", "high"): 420000000}
        (result, _) = self.execute_run(self.echo, cgroupValues=cgValues)
        self.check_exitcode(result, 0, "exit code of echo is not zero")
        # Just assert that execution was successful,
        # testing that the value was actually set is much more difficult.

    def test_nested_runexec(self):
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
        self.setUp(
            dir_modes={
                # Do not mark /home hidden, would fail with python from virtualenv
                "/": containerexecutor.DIR_READ_ONLY,
                "/tmp": containerexecutor.DIR_FULL_ACCESS,  # for inner_output_file
                "/sys/fs/cgroup": containerexecutor.DIR_FULL_ACCESS,
            }
        )
        inner_args = ["--", self.echo, "TEST_TOKEN"]

        with tempfile.NamedTemporaryFile(
            mode="r", prefix="inner_output_", suffix=".log"
        ) as inner_output_file:
            inner_cmdline = self.get_runexec_cmdline(
                *inner_args, output_filename=inner_output_file.name
            )
            outer_result, outer_output = self.execute_run(*inner_cmdline)
            inner_output = inner_output_file.read().strip().splitlines()

        logging.info("Outer output:\n%s", "\n".join(outer_output))
        logging.info("Inner output:\n%s", "\n".join(inner_output))
        self.check_result_keys(outer_result, "returnvalue")
        self.check_exitcode(outer_result, 0, "exit code of inner runexec is not zero")
        self.check_command_in_output(inner_output, f"{self.echo} TEST_TOKEN")
        self.assertEqual(
            inner_output[-1], "TEST_TOKEN", "run output misses command output"
        )

    def test_starttime(self):
        if not os.path.exists(self.echo):
            self.skipTest("missing echo")
        before = util.read_local_time()
        (result, _) = self.execute_run(self.echo)
        after = util.read_local_time()
        self.check_result_keys(result)
        run_starttime = result["starttime"]
        self.assertIsNotNone(run_starttime.tzinfo, "start time is not a local time")
        self.assertLessEqual(before, run_starttime)
        self.assertLessEqual(run_starttime, after)

    def test_frozen_process(self):
        # https://github.com/sosy-lab/benchexec/issues/840
        if not os.path.exists(self.sleep):
            self.skipTest("missing sleep")
        if self.cgroups.version == 1 and not os.path.exists("/sys/fs/cgroup/freezer"):
            self.skipTest("missing freezer cgroup")
        self.setUp(
            dir_modes={
                "/": containerexecutor.DIR_READ_ONLY,
                "/home": containerexecutor.DIR_HIDDEN,
                "/tmp": containerexecutor.DIR_HIDDEN,
                "/sys/fs/cgroup": containerexecutor.DIR_FULL_ACCESS,
            }
        )
        script_v1 = """#!/bin/sh
# create process, move it to sub-cgroup, and freeze it
set -eu

cgroup="/sys/fs/cgroup/freezer/$(grep freezer /proc/self/cgroup | cut -f 3 -d :)"
mkdir "$cgroup/tmp"
mkdir "$cgroup/tmp/tmp"

sleep 10 &
child_pid=$!

echo $child_pid > "$cgroup/tmp/tasks"
echo FROZEN > "$cgroup/tmp/freezer.state"
# remove permissions in order to test our handling of this case
chmod 000 "$cgroup/tmp/freezer.state"
chmod 000 "$cgroup/tmp/tasks"
chmod 000 "$cgroup/tmp"
chmod 000 "$cgroup/freezer.state"
chmod 000 "$cgroup/tasks"
echo FROZEN
wait $child_pid
"""
        script_v2 = """#!/bin/sh
# create process, move it to sub-cgroup, and freeze it
set -eu

cgroup="/sys/fs/cgroup/$(cut -f 3 -d : /proc/self/cgroup)"
mkdir "$cgroup/tmp"
mkdir "$cgroup/tmp/tmp"

sleep 10 &
child_pid=$!

echo $child_pid > "$cgroup/tmp/cgroup.procs"
echo 1 > "$cgroup/tmp/cgroup.freeze"
# remove permissions in order to test our handling of this case
chmod 000 "$cgroup/tmp/cgroup.freeze"
chmod 000 "$cgroup/tmp/cgroup.procs"
chmod 000 "$cgroup/tmp"
chmod 000 "$cgroup/cgroup.freeze"
chmod 000 "$cgroup/cgroup.kill"
echo FROZEN
wait $child_pid
"""
        (result, output) = self.execute_run(
            "/bin/sh",
            "-c",
            script_v1 if self.cgroups.version == 1 else script_v2,
            walltimelimit=1,
            expect_terminationreason="walltime",
        )
        self.check_exitcode(result, 9, "exit code of killed process is not 9")
        self.assertAlmostEqual(
            result["walltime"],
            2,
            delta=0.5,
            msg="walltime is not approximately the time after which the process should have been killed",
        )
        self.assertEqual(
            output[-1],
            "FROZEN",
            "run output misses command output and was not executed properly",
        )


class TestRunExecutorWithContainer(TestRunExecutor):
    def setUp(self, *args, **kwargs):
        try:
            container.execute_in_namespace(lambda: 0)
        except OSError as e:
            self.skipTest(f"Namespaces not supported: {os.strerror(e.errno)}")

        dir_modes = kwargs.pop(
            "dir_modes",
            {
                "/": containerexecutor.DIR_READ_ONLY,
                "/home": containerexecutor.DIR_HIDDEN,
                "/tmp": containerexecutor.DIR_HIDDEN,
            },
        )

        self.runexecutor = RunExecutor(
            *args, use_namespaces=True, dir_modes=dir_modes, **kwargs
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
            output_str = "\n".join(output)
            self.assertEqual(
                result["exitcode"].value,
                0,
                f"exit code of {' '.join(shell_cmd)} is not zero,\n"
                f"result was {result!r},\noutput was\n{output_str}",
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
                f"\nList of retrieved result files differs from expected list,\n"
                f"result was {result!r},\noutput was\n{output_str}",
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

    def test_result_file_log_limit(self):
        file_count = containerexecutor._MAX_RESULT_FILE_LOG_COUNT + 10
        with self.assertLogs(level=logging.DEBUG) as log:
            # Check that all output files are transferred ...
            self.check_result_files(
                f"for i in $(seq 1 {file_count}); do touch $i; done",
                ["*"],
                list(map(str, range(1, file_count + 1))),
            )
        # ... but not all output files are logged ...
        self.assertEqual(
            len([msg for msg in log.output if "Transferring output file" in msg]),
            containerexecutor._MAX_RESULT_FILE_LOG_COUNT,
        )
        # ... and the final count is correct.
        count_msg = next(msg for msg in log.output if " output files matched" in msg)
        self.assertIn(f"{file_count} output files matched", count_msg)

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
                "/bin/sh", "-c", f"echo TEST_TOKEN > '{temp_file}'"
            )
            self.check_result_keys(result)
            self.check_exitcode(result, 0, "exit code of process is not 0")
            self.assertTrue(
                os.path.exists(temp_file),
                f"File '{temp_file}' not created, output was:\n" + "\n".join(output),
            )
            with open(temp_file, "r") as f:
                self.assertEqual(f.read().strip(), "TEST_TOKEN")
        finally:
            shutil.rmtree(temp_dir)

    def test_cpuinfo_with_lxcfs(self):
        if not os.path.exists("/var/lib/lxcfs/proc"):
            self.skipTest("missing lxcfs")
        result, output = self.execute_run(
            self.grep, "^processor", "/proc/cpuinfo", cores=[0]
        )
        self.check_result_keys(result)
        self.check_exitcode(result, 0, "exit code for reading cpuinfo is not zero")
        cpus = [int(line.split()[2]) for line in output if line.startswith("processor")]
        self.assertListEqual(cpus, [0], "Unexpected CPU cores visible in container")

    def test_sys_cpu_with_lxcfs(self):
        if not os.path.exists("/var/lib/lxcfs/proc"):
            self.skipTest("missing lxcfs")
        result, output = self.execute_run(
            self.cat, "/sys/devices/system/cpu/online", cores=[0]
        )
        self.check_result_keys(result)
        self.check_exitcode(result, 0, "exit code for reading online CPUs is not zero")
        cpus = util.parse_int_list(output[-1])
        self.assertListEqual(cpus, [0], "Unexpected CPU cores online in container")

    def test_uptime_with_lxcfs(self):
        if not os.path.exists("/var/lib/lxcfs/proc"):
            self.skipTest("missing lxcfs")
        result, output = self.execute_run(self.cat, "/proc/uptime")
        self.check_result_keys(result)
        self.check_exitcode(result, 0, "exit code for reading uptime is not zero")
        uptime = float(output[-1].split(" ")[0])
        self.assertLessEqual(
            uptime, 10, f"Uptime {uptime}s unexpectedly high in container"
        )

    def test_uptime_without_lxcfs(self):
        if not os.path.exists("/var/lib/lxcfs/proc"):
            self.skipTest("missing lxcfs")
        # create RunExecutor with desired parameter
        self.setUp(container_system_config=False)
        result, output = self.execute_run(self.cat, "/proc/uptime")
        self.check_result_keys(result)
        self.check_exitcode(result, 0, "exit code for reading uptime is not zero")
        uptime = float(output[-1].split(" ")[0])
        # If uptime was less than 10s, LXCFS probably was in use
        self.assertGreaterEqual(
            uptime, 10, f"Uptime {uptime}s unexpectedly low in container"
        )

    def test_fuse_overlay(self):
        if not container.get_fuse_overlayfs_executable():
            self.skipTest("fuse-overlayfs not available")
        with tempfile.TemporaryDirectory(prefix="BenchExec_test_") as temp_dir:
            test_file_path = os.path.join(temp_dir, "test_file")
            with open(test_file_path, "wb") as test_file:
                test_file.write(b"TEST_TOKEN")

            self.setUp(
                dir_modes={
                    "/": containerexecutor.DIR_READ_ONLY,
                    "/home": containerexecutor.DIR_HIDDEN,
                    "/tmp": containerexecutor.DIR_HIDDEN,
                    temp_dir: containerexecutor.DIR_OVERLAY,
                },
            )
            result, output = self.execute_run(
                "/bin/sh",
                "-c",
                f"if [ $({self.cat} {test_file_path}) != TEST_TOKEN ]; then exit 1; fi; \
                {self.echo} TOKEN_CHANGED >{test_file_path}",
            )
            self.check_result_keys(result, "returnvalue")
            self.check_exitcode(result, 0, "exit code of inner runexec is not zero")
            self.assertTrue(
                os.path.exists(test_file_path),
                f"File '{test_file_path}' removed, output was:\n" + "\n".join(output),
            )
            with open(test_file_path, "rb") as test_file:
                test_token = test_file.read()
            self.assertEqual(
                test_token.strip(),
                b"TEST_TOKEN",
                f"File '{test_file_path}' content is incorrect. Expected 'TEST_TOKEN', but got:\n{test_token}",
            )

    def test_triple_nested_runexec(self):
        if not container.get_fuse_overlayfs_executable():
            self.skipTest("missing fuse-overlayfs")

        # Check if COV_CORE_SOURCE environment variable is set and remove it.
        # This is necessary because the coverage tool will not work in the nested runexec.
        coverage_env_var = os.environ.pop("COV_CORE_SOURCE", None)

        with tempfile.TemporaryDirectory(prefix="BenchExec_test_") as temp_dir:
            overlay_dir = os.path.join(temp_dir, "overlay")
            os.makedirs(overlay_dir)
            test_file = os.path.join(overlay_dir, "TEST_FILE")
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir)
            mid_output_file = os.path.join(output_dir, "mid_output.log")
            inner_output_file = os.path.join(output_dir, "inner_output.log")
            with open(test_file, "w") as f:
                f.write("TEST_TOKEN")
                f.seek(0)

            outer_cmd = [
                "python3",
                runexec,
                "--full-access-dir",
                "/",
                "--overlay-dir",
                overlay_dir,
                "--full-access-dir",
                output_dir,
                "--hidden-dir",
                "/tmp",
                "--full-access-dir",
                os.getcwd(),
                "--output",
                mid_output_file,
                "--",
            ]
            mid_cmd = [
                "python3",
                runexec,
                "--full-access-dir",
                "/",
                "--overlay-dir",
                overlay_dir,
                "--full-access-dir",
                output_dir,
                "--hidden-dir",
                "/tmp",
                "--full-access-dir",
                os.getcwd(),
                "--output",
                inner_output_file,
                "--",
            ]
            inner_cmd = [
                "/bin/sh",
                "-c",
                f"if [ $({self.cat} {test_file}) != TEST_TOKEN ]; then exit 1; fi; {self.echo} TOKEN_CHANGED >{test_file}",
            ]
            combined_cmd = outer_cmd + mid_cmd + inner_cmd

            self.setUp(
                dir_modes={
                    "/": containerexecutor.DIR_FULL_ACCESS,
                    "/tmp": containerexecutor.DIR_HIDDEN,
                    overlay_dir: containerexecutor.DIR_OVERLAY,
                    output_dir: containerexecutor.DIR_FULL_ACCESS,
                    os.getcwd(): containerexecutor.DIR_FULL_ACCESS,
                },
            )
            outer_result, outer_output = self.execute_run(*combined_cmd)
            self.check_result_keys(outer_result, "returnvalue")
            self.check_exitcode(
                outer_result, 0, "exit code of outer runexec is not zero"
            )
            with open(mid_output_file, "r") as f:
                self.assertIn("returnvalue=0", f.read().strip().splitlines())
            self.assertTrue(
                os.path.exists(test_file),
                f"File '{test_file}' removed, output was:\n" + "\n".join(outer_output),
            )
            with open(test_file, "r") as f:
                test_token = f.read()
                self.assertEqual(
                    test_token.strip(),
                    "TEST_TOKEN",
                    f"File '{test_file}' content is incorrect. Expected 'TEST_TOKEN', but got:\n{test_token}",
                )

        # Restore COV_CORE_SOURCE environment variable
        if coverage_env_var is not None:
            os.environ["COV_CORE_SOURCE"] = coverage_env_var


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
                output_content = f"""Dummy output
# An error report file with more information is saved as:
# {report_file.name}
More output
""".encode()  # noqa: E800 false alarm
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
