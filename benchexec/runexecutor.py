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

# THIS MODULE HAS TO WORK WITH PYTHON 2.7!

import argparse
import errno
import logging
import multiprocessing
import os
import resource
import signal
import subprocess
import sys
import threading
import time
import tempfile
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import baseexecutor
from benchexec import BenchExecException
from benchexec import containerexecutor
from benchexec.cgroups import *
from benchexec import oomhandler
from benchexec import systeminfo
from benchexec import util

_WALLTIME_LIMIT_DEFAULT_OVERHEAD = 30 # seconds more than cputime limit
_ULIMIT_DEFAULT_OVERHEAD = 30 # seconds after cgroups cputime limit
_BYTE_FACTOR = 1000 # byte in kilobyte
_LOG_SHRINK_MARKER = "\n\n\nWARNING: YOUR LOGFILE WAS TOO LONG, SOME LINES IN THE MIDDLE WERE REMOVED.\n\n\n\n"
_SUDO_ARGS = ['sudo', '--non-interactive', '-u']

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'rb')


def main(argv=None):
    """
    A simple command-line interface for the runexecutor module of BenchExec.
    """
    if argv is None:
        argv = sys.argv

    # parse options
    parser = argparse.ArgumentParser(
        fromfile_prefix_chars='@',
        description=
        """Execute a command with resource limits and measurements.
           Command-line parameters can additionally be read from a file if file name prefixed with '@' is given as argument.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""")

    resource_args = parser.add_argument_group("optional arguments for resource limits")
    resource_args.add_argument("--memlimit", type=util.parse_memory_value, metavar="BYTES",
        help="memory limit in bytes")
    resource_args.add_argument("--timelimit", type=util.parse_timespan_value, metavar="SECONDS",
        help="CPU time limit in seconds")
    resource_args.add_argument("--softtimelimit", type=util.parse_timespan_value, metavar="SECONDS",
        help='"soft" CPU time limit in seconds (command will be send the TERM signal at this time)')
    resource_args.add_argument("--walltimelimit", type=util.parse_timespan_value, metavar="SECONDS",
        help='wall time limit in seconds (default is CPU time limit plus a few seconds)')
    resource_args.add_argument("--cores", type=util.parse_int_list, metavar="N,M-K",
        help="list of CPU cores to use")
    resource_args.add_argument("--memoryNodes", type=util.parse_int_list, metavar="N,M-K",
        help="list of memory nodes to use")

    io_args = parser.add_argument_group("optional arguments for run I/O")
    io_args.add_argument("--input", metavar="FILE",
        help="name of file used as stdin for command "
            "(default: /dev/null; use - for stdin passthrough)")
    io_args.add_argument("--output", default="output.log", metavar="FILE",
        help="name of file where command output is written")
    io_args.add_argument("--maxOutputSize", type=util.parse_memory_value, metavar="BYTES",
        help="shrink output file to approximately this size if necessary "
            "(by removing lines from the middle of the output)")
    io_args.add_argument("--skip-cleanup", action="store_false", dest="cleanup",
        help="do not delete files created by the tool in temp directory")

    container_args = parser.add_argument_group("optional arguments for run container")
    container_on_args = container_args.add_mutually_exclusive_group()
    container_on_args.add_argument("--container", action='store_true',
        help="force isolation of run in container (future default starting with BenchExec 2.0)")
    container_on_args.add_argument("--no-container", action='store_true',
        help="disable use of containers for isolation of runs (current default)")
    containerexecutor.add_basic_container_args(container_args)
    containerexecutor.add_container_output_args(container_args)

    environment_args = parser.add_argument_group("optional arguments for run environment")
    environment_args.add_argument("--require-cgroup-subsystem", action="append", default=[], metavar="SUBSYSTEM",
        help="additional cgroup system that should be enabled for runs "
            "(may be specified multiple times)")
    environment_args.add_argument("--set-cgroup-value", action="append", dest="cgroup_values", default=[],
        metavar="SUBSYSTEM.OPTION=VALUE",
        help="additional cgroup values that should be set for runs (e.g., 'cpu.shares=1000')")
    environment_args.add_argument("--dir", metavar="DIR",
        help="working directory for executing the command (default is current directory)")
    environment_args.add_argument("--user", metavar="USER",
        help="execute tool under given user account (needs password-less sudo setup, "
            "not supported in combination with --container)")

    baseexecutor.add_basic_executor_options(parser)

    options = parser.parse_args(argv[1:])
    baseexecutor.handle_basic_executor_options(options, parser)

    if options.container:
        if options.user is not None:
            sys.exit("Cannot use --user in combination with --container.")
        container_options = containerexecutor.handle_basic_container_args(options, parser)
        container_output_options = containerexecutor.handle_container_output_args(options, parser)
    else:
        container_options = {}
        container_output_options = {}
        if not options.no_container:
            logging.warning(
                "Neither --container or --no-container was specified, "
                "not using containers for isolation of runs. "
                "Either specify --no-container to silence this warning, "
                "or specify --container to use containers for better isolation of runs "
                "(this will be the default starting with BenchExec 2.0). "
                "Please read https://github.com/sosy-lab/benchexec/blob/master/doc/container.md "
                "for more information.")

    # For integrating into some benchmarking frameworks,
    # there is a DEPRECATED special mode
    # where the first and only command-line argument is a serialized dict
    # with additional options
    env = {}
    if len(options.args) == 1 and options.args[0].startswith("{"):
        data = eval(options.args[0])
        options.args = data["args"]
        env = data.get("env", {})
        options.debug = data.get("debug", options.debug)
        if "maxLogfileSize" in data:
            try:
                options.maxOutputSize = int(data["maxLogfileSize"]) * _BYTE_FACTOR * _BYTE_FACTOR # MB to bytes
            except ValueError:
                options.maxOutputSize = util.parse_memory_value(data["maxLogfileSize"])

    if options.input == '-':
        stdin = sys.stdin
    elif options.input is not None:
        if options.input == options.output:
            parser.error("Input and output files cannot be the same.")
        try:
            stdin = open(options.input, 'rt')
        except IOError as e:
            parser.error(e)
    else:
        stdin = None

    cgroup_subsystems = set(options.require_cgroup_subsystem)
    cgroup_values = {}
    for arg in options.cgroup_values:
        try:
            key, value = arg.split("=", 1)
            subsystem, option = key.split(".", 1)
            if not subsystem or not option:
                raise ValueError()
        except ValueError:
            parser.error(
                'Cgroup value "{}" has invalid format, needs to be "subsystem.option=value".'
                    .format(arg))
        cgroup_values[(subsystem, option)] = value
        cgroup_subsystems.add(subsystem)

    executor = RunExecutor(user=options.user, cleanup_temp_dir=options.cleanup,
                           additional_cgroup_subsystems=list(cgroup_subsystems),
                           use_namespaces=options.container, **container_options)

    # ensure that process gets killed on interrupt/kill signal
    def signal_handler_kill(signum, frame):
        executor.stop()
    signal.signal(signal.SIGTERM, signal_handler_kill)
    signal.signal(signal.SIGINT,  signal_handler_kill)

    formatted_args = " ".join(map(util.escape_string_shell, options.args))
    logging.info('Starting command %s', formatted_args)
    if options.container and options.output_directory and options.result_files:
        logging.info('Writing output to %s and result files to %s',
                     util.escape_string_shell(options.output),
                     util.escape_string_shell(options.output_directory))
    else:
        logging.info('Writing output to %s', util.escape_string_shell(options.output))

    # actual run execution
    try:
        result = executor.execute_run(
                            args=options.args,
                            output_filename=options.output,
                            stdin=stdin,
                            hardtimelimit=options.timelimit,
                            softtimelimit=options.softtimelimit,
                            walltimelimit=options.walltimelimit,
                            cores=options.cores,
                            memlimit=options.memlimit,
                            memory_nodes=options.memoryNodes,
                            cgroupValues=cgroup_values,
                            environments=env,
                            workingDir=options.dir,
                            maxLogfileSize=options.maxOutputSize,
                            **container_output_options)
    finally:
        if stdin:
            stdin.close()

    executor.check_for_new_files_in_home()

    # exit_code is a special number:
    exit_code = util.ProcessExitCode.from_raw(result['exitcode'])

    def print_optional_result(key):
        if key in result:
            # avoid unicode literals such that the string can be parsed by Python 3.2
            print(key + "=" + str(result[key]).replace("'u", ''))

    # output results
    print_optional_result('terminationreason')
    print("exitcode=" + str(exit_code.raw))
    if exit_code.value is not None:
        print("returnvalue=" + str(exit_code.value))
    if exit_code.signal is not None:
        print("exitsignal=" + str(exit_code.signal))
    print("walltime=" + str(result['walltime']) + "s")
    print("cputime=" + str(result['cputime']) + "s")
    for key in sorted(result.keys()):
        if key.startswith('cputime-'):
            print("{}={:.9f}s".format(key, result[key]))
    print_optional_result('memory')
    if 'energy' in result:
        for key, value in result['energy'].items():
            print("energy-{0}={1}".format(key, value))

class RunExecutor(containerexecutor.ContainerExecutor):

    # --- object initialization ---

    def __init__(self, user=None, cleanup_temp_dir=True, additional_cgroup_subsystems=[],
                 use_namespaces=False, *args, **kwargs):
        """
        Create an instance of of RunExecutor.
        @param user None or an OS user as which the benchmarked process should be executed (via sudo).
        @param cleanup_temp_dir Whether to remove the temporary directories created for the run.
        @param additional_cgroup_subsystems List of additional cgroup subsystems that should be required and used for runs.
        """
        super(RunExecutor, self).__init__(use_namespaces=use_namespaces, *args, **kwargs)
        if use_namespaces and user:
            raise ValueError("Combination of sudo mode of RunExecutor and namespaces is not supported")
        self._termination_reason = None
        self._user = user
        self._should_cleanup_temp_dir = cleanup_temp_dir
        self._cgroup_subsystems = additional_cgroup_subsystems

        if user is not None:
            # Check if we are allowed to execute 'kill' with dummy signal.
            sudo_check = self._build_cmdline(['kill', '-0', '0'])
            logging.debug('Checking for capability to run with sudo as user %s.', user)
            p = subprocess.Popen(sudo_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                if p.wait():
                    logging.error(
                        'Calling "%s" failed with error code %s and the following output: %s\n%s',
                        ' '.join(sudo_check),
                        p.returncode,
                        p.stdout.read().decode().strip(),
                        p.stderr.read().decode().strip())
                    sys.exit('Cannot execute benchmark as user "{0}", please fix your sudo setup.'.format(user))
            finally:
                p.stdout.close()
                p.stderr.close()

            # Check home directory of user
            try:
                self._home_dir = _get_user_account_info(user).pw_dir
            except (KeyError, ValueError) as e:
                sys.exit('Unknown user {}: {}'.format(user, e))
            try:
                self._home_dir_content = set(self._listdir(self._home_dir))
            except (subprocess.CalledProcessError, IOError):
                # Probably directory does not exist
                self._home_dir_content = []
            if self._home_dir_content:
                logging.warning(
                    'Home directory %s of user %s contains files and/or directories, it is '
                    'recommended to do benchmarks with empty home to prevent undesired influences.',
                    self._home_dir, user)

        self._init_cgroups()

    def _init_cgroups(self):
        """
        This function initializes the cgroups for the limitations and measurements.
        """
        self.cgroups = find_my_cgroups()

        for subsystem in self._cgroup_subsystems:
            self.cgroups.require_subsystem(subsystem)
            if subsystem not in self.cgroups:
                sys.exit('Required cgroup subsystem "{}" is missing.'.format(subsystem))

        self.cgroups.require_subsystem(CPUACCT)
        if CPUACCT not in self.cgroups:
            logging.warning('Without cpuacct cgroups, cputime measurement and limit '
                            'might not work correctly if subprocesses are started.')

        self.cgroups.require_subsystem(FREEZER)
        if FREEZER not in self.cgroups:
            if self._user is not None:
                # In sudo mode, we absolutely need at least one cgroup subsystem
                # to be able to find the process where we need to send signals to
                sys.exit('Cannot reliably kill sub-processes without freezer cgroup,'
                         + ' this is necessary if --user is specified.'
                         + ' Please enable this cgroup or do not specify --user.')
            else:
                logging.warning('Cannot reliably kill sub-processes without freezer cgroup.')

        self.cgroups.require_subsystem(MEMORY)
        if MEMORY not in self.cgroups:
            logging.warning('Cannot measure memory consumption without memory cgroup.')
        else:
            if systeminfo.has_swap() and (
                    not self.cgroups.has_value(MEMORY, 'memsw.max_usage_in_bytes')):
                logging.warning(
                    'Kernel misses feature for accounting swap memory, but machine has swap. '
                    'Memory usage may be measured inaccurately. '
                    'Please set swapaccount=1 on your kernel command line or disable swap with '
                    '"sudo swapoff -a".')

        self.cgroups.require_subsystem(CPUSET)
        self.cpus = None # to indicate that we cannot limit cores
        self.memory_nodes = None # to indicate that we cannot limit cores
        if CPUSET in self.cgroups:
            # Read available cpus/memory nodes:
            try:
                self.cpus = util.parse_int_list(self.cgroups.get_value(CPUSET, 'cpus'))
            except ValueError as e:
                logging.warning("Could not read available CPU cores from kernel: %s", e.strerror)
            logging.debug("List of available CPU cores is %s.", self.cpus)

            try:
                self.memory_nodes = util.parse_int_list(self.cgroups.get_value(CPUSET, 'mems'))
            except ValueError as e:
                logging.warning("Could not read available memory nodes from kernel: %s",
                                e.strerror)
            logging.debug("List of available memory nodes is %s.", self.memory_nodes)


    # --- utility functions ---

    def _build_cmdline(self, args, env={}):
        """
        Build the final command line for executing the given command,
        using sudo if necessary.
        """
        if self._user is None:
            return super(RunExecutor, self)._build_cmdline(args, env)
        result = _SUDO_ARGS + [self._user]
        for var, value in env.items():
            result.append(var + '=' + value)
        return result + ['--'] + args

    def _kill_process(self, pid, cgroups=None, sig=signal.SIGKILL):
        """
        Try to send signal to given process, either directly of with sudo.
        Because we cannot send signals to the sudo process itself,
        this method checks whether the target is the sudo process
        and redirects the signal to sudo's child in this case.
        """
        if self._user is not None:
            if not cgroups:
                cgroups = find_cgroups_of_process(pid)
            # In case we started a tool with sudo, we cannot kill the started
            # process itself, because sudo always runs as root.
            # So if we are asked to kill the started process itself (the first
            # process in the cgroup), we instead kill the child of sudo
            # (the second process in the cgroup).
            pids = cgroups.get_all_tasks(FREEZER)
            try:
                if pid == next(pids):
                    pid = next(pids)
            except StopIteration:
                # pids seems to not have enough values
                pass
            finally:
                pids.close()
        self._kill_process0(pid, sig)

    def _kill_process0(self, pid, sig=signal.SIGKILL):
        """
        Send signal to given process, either directly or with sudo.
        If the target is the sudo process itself, the signal will be lost,
        because we do not have the rights to send signals to sudo.
        Use _kill_process() because of this.
        """
        if self._user is None:
            super(RunExecutor, self)._kill_process(pid, sig)
        else:
            logging.debug('Sending signal %s to %s with sudo.', sig, pid)
            try:
                # Cast sig to int, under Python 3.5 the signal.SIG* constants are nums, not ints.
                subprocess.check_call(args=self._build_cmdline(['kill', '-'+str(int(sig)), str(pid)]))
            except subprocess.CalledProcessError as e:
                # may happen for example if process no longer exists
                logging.debug(e)

    def _listdir(self, path):
        """Return the list of files in a directory, assuming that our user can read it."""
        if self._user is None:
            return os.listdir(path)
        else:
            args = self._build_cmdline(['/bin/ls', '-1', path])
            return subprocess.check_output(args, stderr=DEVNULL).decode('utf-8', errors='ignore').split('\n')

    def _set_termination_reason(self, reason):
        if not self._termination_reason:
            self._termination_reason = reason


    # --- setup and cleanup for a single run ---

    def _setup_cgroups(self, my_cpus, memlimit, memory_nodes, cgroup_values):
        """
        This method creates the CGroups for the following execution.
        @param my_cpus: None or a list of the CPU cores to use
        @param memlimit: None or memory limit in bytes
        @param memory_nodes: None or a list of memory nodes of a NUMA system to use
        @param cgroup_values: dict of additional values to set
        @return cgroups: a map of all the necessary cgroups for the following execution.
                         Please add the process of the following execution to all those cgroups!
        """
        logging.debug("Setting up cgroups for run.")

        # Setup cgroups, need a single call to create_cgroup() for all subsystems
        subsystems = [CPUACCT, FREEZER, MEMORY] + self._cgroup_subsystems
        if my_cpus is not None:
            subsystems.append(CPUSET)
        subsystems = [s for s in subsystems if s in self.cgroups]

        cgroups = self.cgroups.create_fresh_child_cgroup(*subsystems)

        logging.debug("Created cgroups %s.", cgroups)

        # First, set user-specified values such that they get overridden by our settings if necessary.
        for ((subsystem, option), value) in cgroup_values.items():
            try:
                cgroups.set_value(subsystem, option, value)
            except EnvironmentError as e:
                cgroups.remove()
                sys.exit('{} for setting cgroup option {}.{} to "{}" (error code {}).'
                         .format(e.strerror, subsystem, option, value, e.errno))
            logging.debug('Cgroup value %s.%s was set to "%s", new value is now "%s".',
                          subsystem, option, value, cgroups.get_value(subsystem, option))

        # Setup cpuset cgroup if necessary to limit the CPU cores/memory nodes to be used.
        if my_cpus is not None:
            my_cpus_str = ','.join(map(str, my_cpus))
            cgroups.set_value(CPUSET, 'cpus', my_cpus_str)
            my_cpus_str = cgroups.get_value(CPUSET, 'cpus')
            logging.debug('Using cpu cores [%s].', my_cpus_str)

        if memory_nodes is not None:
            cgroups.set_value(CPUSET, 'mems', ','.join(map(str, memory_nodes)))
            memory_nodesStr = cgroups.get_value(CPUSET, 'mems')
            logging.debug('Using memory nodes [%s].', memory_nodesStr)


        # Setup memory limit
        if memlimit is not None:
            limit = 'limit_in_bytes'
            cgroups.set_value(MEMORY, limit, memlimit)

            swap_limit = 'memsw.limit_in_bytes'
            # We need swap limit because otherwise the kernel just starts swapping
            # out our process if the limit is reached.
            # Some kernels might not have this feature,
            # which is ok if there is actually no swap.
            if not cgroups.has_value(MEMORY, swap_limit):
                if systeminfo.has_swap():
                    sys.exit('Kernel misses feature for accounting swap memory, but machine has swap. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')
            else:
                try:
                    cgroups.set_value(MEMORY, swap_limit, memlimit)
                except IOError as e:
                    if e.errno == errno.ENOTSUP: # kernel responds with operation unsupported if this is disabled
                        sys.exit('Memory limit specified, but kernel does not allow limiting swap memory. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')
                    raise e

            memlimit = cgroups.get_value(MEMORY, limit)
            logging.debug('Effective memory limit is %s bytes.', memlimit)

        if MEMORY in cgroups:
            try:
                # Note that this disables swapping completely according to
                # https://www.kernel.org/doc/Documentation/cgroups/memory.txt
                # (unlike setting the global swappiness to 0).
                # Our process might get killed because of this.
                cgroups.set_value(MEMORY, 'swappiness', '0')
            except IOError as e:
                logging.warning('Could not disable swapping for benchmarked process: %s', e)

        return cgroups


    def _create_temp_dir(self):
        """Create a temporary directory for the run."""
        if self._user is None:
            base_dir = tempfile.mkdtemp(prefix="BenchExec_run_")
        else:
            create_temp_dir = self._build_cmdline([
                'python', '-c',
                'import tempfile;'
                'print(tempfile.mkdtemp(prefix="BenchExec_run_"))'
                ])
            base_dir = subprocess.check_output(create_temp_dir).decode().strip()
        return base_dir

    def _create_dirs_in_temp_dir(self, *paths):
        if self._user is None:
            super(RunExecutor, self)._create_dirs_in_temp_dir(*paths)
        elif paths:
            subprocess.check_call(self._build_cmdline(["mkdir", "--mode=700"] + list(paths)))

    def _cleanup_temp_dir(self, base_dir):
        """Delete given temporary directory and all its contents."""
        if self._should_cleanup_temp_dir:
            logging.debug('Cleaning up temporary directory.')
            if self._user is None:
                util.rmtree(base_dir, onerror=util.log_rmtree_error)
            else:
                rm = subprocess.Popen(self._build_cmdline(['rm', '-rf', '--', base_dir]),
                                      stderr=subprocess.PIPE)
                rm_output = rm.stderr.read().decode()
                rm.stderr.close()
                if rm.wait() != 0 or rm_output:
                    logging.warning("Failed to clean up temp directory %s: %s.",
                                    base_dir, rm_output)
        else:
            logging.info("Skipping cleanup of temporary directory %s.", base_dir)


    def _setup_environment(self, environments):
        """Return map with desired environment variables for run."""
        # If keepEnv is set or sudo is used, start from a fresh environment,
        # otherwise with the current one.
        # keepEnv specifies variables to copy from the current environment,
        # newEnv specifies variables to set to a new value,
        # additionalEnv specifies variables where some value should be appended, and
        # clearEnv specifies variables to delete.
        if self._user is not None or environments.get("keepEnv", None) is not None:
            run_environment = {}
        else:
            run_environment = os.environ.copy()
        for key, value in environments.get("keepEnv", {}).items():
            if key in os.environ:
                run_environment[key] = os.environ[key]
        for key, value in environments.get("newEnv", {}).items():
            run_environment[key] = value
        for key, value in environments.get("additionalEnv", {}).items():
            run_environment[key] = os.environ.get(key, "") + value
        for key in environments.get("clearEnv", {}).items():
            run_environment.pop(key, None)

        logging.debug("Using additional environment %s.", environments)
        return run_environment


    def _setup_output_file(self, output_filename, args):
        """Open and prepare output file."""
        # write command line into outputFile
        # (without environment variables, they are documented by benchexec)
        try:
            output_file = open(output_filename, 'w') # override existing file
        except IOError as e:
            sys.exit(e)
        output_file.write(' '.join(map(util.escape_string_shell, self._build_cmdline(args)))
                          + '\n\n\n' + '-' * 80 + '\n\n\n')
        output_file.flush()
        return output_file


    def _setup_cgroup_time_limit(self, hardtimelimit, softtimelimit, walltimelimit,
                                 cgroups, cores, pid_to_kill):
        """Start time-limit handler.
        @return None or the time-limit handler for calling cancel()
        """
        # hard time limit with cgroups is optional (additionally enforce by ulimit)
        cgroup_hardtimelimit = hardtimelimit if CPUACCT in cgroups else None

        if any([cgroup_hardtimelimit, softtimelimit, walltimelimit]):
            # Start a timer to periodically check timelimit
            timelimitThread = _TimelimitThread(cgroups=cgroups,
                                               hardtimelimit=cgroup_hardtimelimit,
                                               softtimelimit=softtimelimit,
                                               walltimelimit=walltimelimit,
                                               pid_to_kill=pid_to_kill,
                                               cores=cores,
                                               callbackFn=self._set_termination_reason,
                                               kill_process_fn=self._kill_process)
            timelimitThread.start()
            return timelimitThread
        return None

    def _setup_cgroup_memory_limit(self, memlimit, cgroups, pid_to_kill):
        """Start memory-limit handler.
        @return None or the memory-limit handler for calling cancel()
        """
        if memlimit is not None:
            try:
                oomThread = oomhandler.KillProcessOnOomThread(
                    cgroups=cgroups, pid_to_kill=pid_to_kill,
                    callbackFn=self._set_termination_reason,
                    kill_process_fn=self._kill_process)
                oomThread.start()
                return oomThread
            except OSError as e:
                logging.critical("OSError %s during setup of OomEventListenerThread: %s.",
                                 e.errno, e.strerror)
        return None

    def _setup_ulimit_time_limit(self, hardtimelimit, cgroups):
        """Setup time limit with ulimit for the current process."""
        if hardtimelimit is not None:
            # Also use ulimit for CPU time limit as a fallback if cgroups don't work.
            if CPUACCT in cgroups:
                # Use a slightly higher limit to ensure cgroups get used
                # (otherwise we cannot detect the timeout properly).
                ulimit = hardtimelimit + _ULIMIT_DEFAULT_OVERHEAD
            else:
                ulimit = hardtimelimit
            resource.setrlimit(resource.RLIMIT_CPU, (ulimit, ulimit))


    # --- run execution ---

    def execute_run(self, args, output_filename, stdin=None,
                   hardtimelimit=None, softtimelimit=None, walltimelimit=None,
                   cores=None, memlimit=None, memory_nodes=None,
                   environments={}, workingDir=None, maxLogfileSize=None,
                   cgroupValues={},
                   **kwargs):
        """
        This function executes a given command with resource limits,
        and writes the output to a file.
        @param args: the command line to run
        @param output_filename: the file where the output should be written to
        @param stdin: What to uses as stdin for the process (None: /dev/null, a file descriptor, or a file object)
        @param hardtimelimit: None or the CPU time in seconds after which the tool is forcefully killed.
        @param softtimelimit: None or the CPU time in seconds after which the tool is sent a kill signal.
        @param walltimelimit: None or the wall time in seconds after which the tool is forcefully killed (default: hardtimelimit + a few seconds)
        @param cores: None or a list of the CPU cores to use
        @param memlimit: None or memory limit in bytes
        @param memory_nodes: None or a list of memory nodes in a NUMA system to use
        @param environments: special environments for running the command
        @param workingDir: None or a directory which the execution should use as working directory
        @param maxLogfileSize: None or a number of bytes to which the output of the tool should be truncated approximately if there is too much output.
        @param cgroupValues: dict of additional cgroup values to set (key is tuple of subsystem and option, respective subsystem needs to be enabled in RunExecutor; cannot be used to override values set by BenchExec)
        @param **kwargs: further arguments for ContainerExecutor.execute_run()
        @return: dict with result of run (measurement results and process exitcode)
        """
        # Check argument values and call the actual method _execute()

        if stdin == subprocess.PIPE:
            sys.exit('Illegal value subprocess.PIPE for stdin')
        elif stdin is None:
            stdin = DEVNULL

        if hardtimelimit is not None:
            if hardtimelimit <= 0:
                sys.exit("Invalid time limit {0}.".format(hardtimelimit))
        if softtimelimit is not None:
            if softtimelimit <= 0:
                sys.exit("Invalid soft time limit {0}.".format(softtimelimit))
            if hardtimelimit and (softtimelimit > hardtimelimit):
                sys.exit("Soft time limit cannot be larger than the hard time limit.")
            if not CPUACCT in self.cgroups:
                sys.exit("Soft time limit cannot be specified without cpuacct cgroup.")

        if walltimelimit is None:
            if hardtimelimit is not None:
                walltimelimit = hardtimelimit + _WALLTIME_LIMIT_DEFAULT_OVERHEAD
            elif softtimelimit is not None:
                walltimelimit = softtimelimit + _WALLTIME_LIMIT_DEFAULT_OVERHEAD
        else:
            if walltimelimit <= 0:
                sys.exit("Invalid wall time limit {0}.".format(walltimelimit))

        if cores is not None:
            if self.cpus is None:
                sys.exit("Cannot limit CPU cores without cpuset cgroup.")
            if not cores:
                sys.exit("Cannot execute run without any CPU core.")
            if not set(cores).issubset(self.cpus):
                sys.exit("Cores {0} are not allowed to be used".format(list(set(cores).difference(self.cpus))))

        if memlimit is not None:
            if memlimit <= 0:
                sys.exit("Invalid memory limit {0}.".format(memlimit))
            if not MEMORY in self.cgroups:
                sys.exit("Memory limit specified, but cannot be implemented without cgroup support.")

        if memory_nodes is not None:
            if self.memory_nodes is None:
                sys.exit("Cannot restrict memory nodes without cpuset cgroup.")
            if len(memory_nodes) == 0:
                sys.exit("Cannot execute run without any memory node.")
            if not set(memory_nodes).issubset(self.memory_nodes):
                sys.exit("Memory nodes {0} are not allowed to be used".format(list(set(memory_nodes).difference(self.memory_nodes))))

        if workingDir:
            if not os.path.exists(workingDir):
                sys.exit("Working directory {0} does not exist.".format(workingDir))
            if not os.path.isdir(workingDir):
                sys.exit("Working directory {0} is not a directory.".format(workingDir))
            if not os.access(workingDir, os.X_OK):
                sys.exit("Permission denied for working directory {0}.".format(workingDir))

        for ((subsystem, option), _) in cgroupValues.items():
            if not subsystem in self._cgroup_subsystems:
                sys.exit('Cannot set option "{option}" for subsystem "{subsystem}" that is not enabled. '
                         'Please specify "--require-cgroup-subsystem {subsystem}".'.format(
                            option=option, subsystem=subsystem))
            if not self.cgroups.has_value(subsystem, option):
                sys.exit('Cannot set option "{option}" for subsystem "{subsystem}", it does not exist.'
                         .format(option=option, subsystem=subsystem))

        try:
            return self._execute(args, output_filename, stdin,
                                 hardtimelimit, softtimelimit, walltimelimit, memlimit,
                                 cores, memory_nodes,
                                 cgroupValues,
                                 environments, workingDir, maxLogfileSize,
                                 **kwargs)

        except BenchExecException as e:
            logging.critical("Cannot execute '%s': %s.",
                util.escape_string_shell(args[0]), e)
            return {'terminationreason': 'failed', 'exitcode': 0,
                    'cputime': 0, 'walltime': 0}
        except OSError as e:
            logging.critical("OSError %s while starting '%s' in '%s': %s.",
                e.errno, util.escape_string_shell(args[0]), workingDir or '.', e.strerror)
            return {'terminationreason': 'failed', 'exitcode': 0,
                    'cputime': 0, 'walltime': 0}


    def _execute(self, args, output_filename, stdin,
                 hardtimelimit, softtimelimit, walltimelimit, memlimit,
                 cores, memory_nodes,
                 cgroup_values,
                 environments, workingDir, max_output_size,
                 **kwargs):
        """
        This method executes the command line and waits for the termination of it,
        handling all setup and cleanup, but does not check whether arguments are valid.
        """

        def preParent():
            """Setup that is executed in the parent process immediately before the actual tool is started."""
            # start measurements
            energy_before = util.measure_energy()
            walltime_before = util.read_monotonic_time()
            return (walltime_before, energy_before)

        def postParent(preParent_result):
            """Cleanup that is executed in the parent process immediately after the actual tool terminated."""
            # finish measurements
            walltime_before, energy_before = preParent_result
            walltime = util.read_monotonic_time() - walltime_before
            energy = util.measure_energy(energy_before)
            return (walltime, energy)

        def preSubprocess():
            """Setup that is executed in the forked process before the actual tool is started."""
            os.setpgrp() # make subprocess to group-leader
            os.nice(5) # increase niceness of subprocess
            self._setup_ulimit_time_limit(hardtimelimit, cgroups)

        # preparations that are not time critical
        cgroups = self._setup_cgroups(cores, memlimit, memory_nodes, cgroup_values)
        temp_dir = self._create_temp_dir()
        run_environment = self._setup_environment(environments)
        outputFile = self._setup_output_file(output_filename, args)

        timelimitThread = None
        oomThread = None
        pid = None
        returnvalue = 0
        ru_child = None
        self._termination_reason = None

        throttle_check = systeminfo.CPUThrottleCheck(cores)
        swap_check = systeminfo.SwapCheck()

        logging.debug('Starting process.')

        try:
            pid, result_fn = self._start_execution(args=args,
                stdin=stdin, stdout=outputFile, stderr=outputFile,
                env=run_environment, cwd=workingDir, temp_dir=temp_dir,
                cgroups=cgroups,
                parent_setup_fn=preParent, child_setup_fn=preSubprocess,
                parent_cleanup_fn=postParent,
                **kwargs)

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.add(pid)

            timelimitThread = self._setup_cgroup_time_limit(
                hardtimelimit, softtimelimit, walltimelimit, cgroups, cores, pid)
            oomThread = self._setup_cgroup_memory_limit(memlimit, cgroups, pid)

            returnvalue, ru_child, (walltime, energy) = result_fn() # blocks until process has terminated

            result = {}
            result['walltime'] = walltime
            if energy:
                result['energy'] = energy

            # needs to come before cgroups.remove()
            self._get_cgroup_measurements(cgroups, ru_child, result)

        finally:
            # cleanup steps that need to get executed even in case of failure
            logging.debug('Process terminated, exit code %s.', returnvalue)

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.discard(pid)

            if timelimitThread:
                timelimitThread.cancel()

            if oomThread:
                oomThread.cancel()

            # Kill all remaining processes if some managed to survive.
            # Because we send signals to all processes anyway we use the
            # internal function.
            cgroups.kill_all_tasks(self._kill_process0)

            # normally subprocess closes file, we do this again after all tasks terminated
            outputFile.close()

            logging.debug("Cleaning up cgroups.")
            cgroups.remove()

            self._cleanup_temp_dir(temp_dir)

        # cleanup steps that are only relevant in case of success
        if throttle_check.has_throttled():
            logging.warning('CPU throttled itself during benchmarking due to overheating. '
                            'Benchmark results are unreliable!')
        if swap_check.has_swapped():
            logging.warning('System has swapped during benchmarking. '
                            'Benchmark results are unreliable!')

        _reduce_file_size_if_necessary(output_filename, max_output_size)

        if returnvalue not in [0,1]:
            _get_debug_output_after_crash(output_filename)

        result['exitcode'] = returnvalue
        if self._termination_reason:
            result['terminationreason'] = self._termination_reason
        elif memlimit and 'memory' in result and result['memory'] >= memlimit:
            # The kernel does not always issue OOM notifications and thus the OOMHandler
            # does not always run even in case of OOM. We detect this there and report OOM.
            result['terminationreason'] = 'memory'

        return result


    def _get_cgroup_measurements(self, cgroups, ru_child, result):
        """
        This method calculates the exact results for time and memory measurements.
        It is not important to call this method as soon as possible after the run.
        """
        logging.debug("Getting cgroup measurements.")

        cputime_wait = ru_child.ru_utime + ru_child.ru_stime if ru_child else 0
        cputime_cgroups = None
        if CPUACCT in cgroups:
            # We want to read the value from the cgroup.
            # The documentation warns about outdated values.
            # So we read twice with 0.1s time difference,
            # and continue reading as long as the values differ.
            # This has never happened except when interrupting the script with Ctrl+C,
            # but just try to be on the safe side here.
            tmp = cgroups.read_cputime()
            tmp2 = None
            while tmp != tmp2:
                time.sleep(0.1)
                tmp2 = tmp
                tmp = cgroups.read_cputime()
            cputime_cgroups = tmp

            # Usually cputime_cgroups seems to be 0.01s greater than cputime_wait.
            # Furthermore, cputime_wait might miss some subprocesses,
            # therefore we expect cputime_cgroups to be always greater (and more correct).
            # However, sometimes cputime_wait is a little bit bigger than cputime2.
            # For small values, this is probably because cputime_wait counts since fork,
            # whereas cputime_cgroups counts only after cgroups.add_task()
            # (so overhead from runexecutor is correctly excluded in cputime_cgroups).
            # For large values, a difference may also indicate a problem with cgroups,
            # for example another process moving our benchmarked process between cgroups,
            # thus we warn if the difference is substantial and take the larger cputime_wait value.
            if cputime_wait > 0.5 and (cputime_wait * 0.95) > cputime_cgroups:
                logging.warning(
                    'Cputime measured by wait was %s, cputime measured by cgroup was only %s, '
                    'perhaps measurement is flawed.',
                    cputime_wait, cputime_cgroups)
                result['cputime'] = cputime_wait
            else:
                result['cputime'] = cputime_cgroups

            for (core, coretime) in enumerate(cgroups.get_value(CPUACCT, 'usage_percpu').split(" ")):
                try:
                    coretime = int(coretime)
                    if coretime != 0:
                        result['cputime-cpu'+str(core)] = coretime/1000000000 # nano-seconds to seconds
                except (OSError, ValueError) as e:
                    logging.debug("Could not read CPU time for core %s from kernel: %s", core, e)
        else:
            # For backwards compatibility, we report cputime_wait on systems without cpuacct cgroup.
            # TOOD We might remove this for BenchExec 2.0.
            result['cputime'] = cputime_wait

        if MEMORY in cgroups:
            # This measurement reads the maximum number of bytes of RAM+Swap the process used.
            # For more details, c.f. the kernel documentation:
            # https://www.kernel.org/doc/Documentation/cgroups/memory.txt
            memUsageFile = 'memsw.max_usage_in_bytes'
            if not cgroups.has_value(MEMORY, memUsageFile):
                memUsageFile = 'max_usage_in_bytes'
            if not cgroups.has_value(MEMORY, memUsageFile):
                logging.warning('Memory-usage is not available due to missing files.')
            else:
                try:
                    result['memory'] = int(cgroups.get_value(MEMORY, memUsageFile))
                except IOError as e:
                    if e.errno == errno.ENOTSUP: # kernel responds with operation unsupported if this is disabled
                        logging.critical(
                            "Kernel does not track swap memory usage, cannot measure memory usage."
                            " Please set swapaccount=1 on your kernel command line.")
                    else:
                        raise e

        logging.debug(
            'Resource usage of run: walltime=%s, cputime=%s, cgroup-cputime=%s, memory=%s',
            result['walltime'], cputime_wait, cputime_cgroups, result.get('memory', None))


    # --- other public functions ---

    def stop(self):
        self._set_termination_reason('killed')
        super(RunExecutor, self).stop()

    def check_for_new_files_in_home(self):
        """Check that the user account's home directory now does not contain more files than
        when this instance was created, and warn otherwise.
        Does nothing if no user account was given to RunExecutor.
        @return set of newly created files
        """
        if not self._user:
            return None
        try:
            created_files = set(self._listdir(self._home_dir)).difference(self._home_dir_content)
        except (subprocess.CalledProcessError, IOError):
            # Probably home directory does not exist
            created_files = []
        if created_files:
            logging.warning('The tool created the following files in %s, '
                            'this may influence later runs:\n\t%s',
                            self._home_dir, '\n\t'.join(created_files))
        return created_files


def _get_user_account_info(user):
    """Get the user account info from the passwd database. Only works on Linux.
    @param user The name of a user account or a numeric uid prefixed with '#'
    @return a tuple that corresponds to the members of the passwd structure
    @raise KeyError: If user account is unknown
    @raise ValueError: If uid is not a valid number
    """
    import pwd # Import here to avoid problems on other platforms
    if user[0] == '#':
        return pwd.getpwuid(int(user[1:]))
    else:
        return pwd.getpwnam(user)


def _reduce_file_size_if_necessary(fileName, maxSize):
    """
    This function shrinks a file.
    We remove only the middle part of a file,
    the file-start and the file-end remain unchanged.
    """
    fileSize = os.path.getsize(fileName)

    if maxSize is None:
        logging.debug("Size of logfile '%s' is %s bytes, size limit disabled.", fileName, fileSize)
        return # disabled, nothing to do

    if fileSize < (maxSize + 500):
        logging.debug("Size of logfile '%s' is %s bytes, nothing to do.", fileName, fileSize)
        return

    logging.warning("Logfile '%s' is too big (size %s bytes). Removing lines.", fileName, fileSize)
    util.shrink_text_file(fileName, maxSize, _LOG_SHRINK_MARKER)


def _get_debug_output_after_crash(output_filename):
    """
    Segmentation faults and some memory failures reference a file
    with more information (hs_err_pid_*). We append this file to the log.
    The format that we expect is a line
    "# An error report file with more information is saved as:"
    and the file name of the dump file on the next line.
    """
    logging.debug("Analysing output for crash info.")
    foundDumpFile = False
    with open(output_filename, 'r+') as outputFile:
        for line in outputFile:
            if foundDumpFile:
                try:
                    dumpFileName = line.strip(' #\n')
                    outputFile.seek(0, os.SEEK_END) # jump to end of log file
                    with open(dumpFileName, 'r') as dumpFile:
                        util.copy_all_lines_from_to(dumpFile, outputFile)
                    os.remove(dumpFileName)
                except IOError as e:
                    logging.warning('Could not append additional segmentation fault information '
                                    'from %s (%s)',
                                    dumpFile, e.strerror)
                break
            try:
                if util.decode_to_string(line).startswith('# An error report file with more information is saved as:'):
                    logging.debug('Going to append error report file')
                    foundDumpFile = True
            except UnicodeDecodeError:
                pass
                # ignore invalid chars from logfile


class _TimelimitThread(threading.Thread):
    """
    Thread that periodically checks whether the given process has already
    reached its timelimit. After this happens, the process is terminated.
    """
    def __init__(self, cgroups, kill_process_fn, hardtimelimit, softtimelimit, walltimelimit, pid_to_kill, cores,
                 callbackFn=lambda reason: None):
        super(_TimelimitThread, self).__init__()

        if hardtimelimit or softtimelimit:
            assert CPUACCT in cgroups
        assert walltimelimit is not None

        if cores:
            self.cpuCount = len(cores)
        else:
            try:
                self.cpuCount = multiprocessing.cpu_count()
            except NotImplementedError:
                self.cpuCount = 1

        self.daemon = True
        self.cgroups = cgroups
        self.timelimit = hardtimelimit or (60*60*24*365*100) # large dummy value
        self.softtimelimit = softtimelimit or (60*60*24*365*100) # large dummy value
        self.latestKillTime = util.read_monotonic_time() + walltimelimit
        self.pid_to_kill = pid_to_kill
        self.callback = callbackFn
        self.kill_process = kill_process_fn
        self.finished = threading.Event()

    def read_cputime(self):
        while True:
            try:
                return self.cgroups.read_cputime()
            except ValueError:
                # Sometimes the kernel produces strange values with linebreaks in them
                time.sleep(1)

    def run(self):
        while not self.finished.is_set():
            usedCpuTime = self.read_cputime() if CPUACCT in self.cgroups else 0
            remainingCpuTime = self.timelimit - usedCpuTime
            remainingSoftCpuTime = self.softtimelimit - usedCpuTime
            remainingWallTime = self.latestKillTime - util.read_monotonic_time()
            logging.debug(
                "TimelimitThread for process %s: used CPU time: %s, remaining CPU time: %s, "
                "remaining soft CPU time: %s, remaining wall time: %s.",
                self.pid_to_kill, usedCpuTime, remainingCpuTime,
                remainingSoftCpuTime, remainingWallTime)
            if remainingCpuTime <= 0:
                self.callback('cputime')
                logging.debug('Killing process %s due to CPU time timeout.', self.pid_to_kill)
                self.kill_process(self.pid_to_kill, self.cgroups)
                self.finished.set()
                return
            if remainingWallTime <= 0:
                self.callback('walltime')
                logging.warning('Killing process %s due to wall time timeout.', self.pid_to_kill)
                self.kill_process(self.pid_to_kill, self.cgroups)
                self.finished.set()
                return

            if remainingSoftCpuTime <= 0:
                self.callback('cputime-soft')
                # soft time limit violated, ask process to terminate
                self.kill_process(self.pid_to_kill, self.cgroups, signal.SIGTERM)
                self.softtimelimit = self.timelimit

            remainingTime = min(remainingCpuTime/self.cpuCount,
                                remainingSoftCpuTime/self.cpuCount,
                                remainingWallTime)
            self.finished.wait(remainingTime + 1)

    def cancel(self):
        self.finished.set()


if __name__ == '__main__':
    main()
