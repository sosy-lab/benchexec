"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import glob
import logging
import multiprocessing
import os
import resource
import signal
import subprocess
import sys
import threading
import time

from . import __version__
from . import util as util
from .cgroups import *
from . import oomhandler
from benchexec import systeminfo

read_file = util.read_file
write_file = util.write_file

_WALLTIME_LIMIT_DEFAULT_OVERHEAD = 30 # seconds more than cputime limit
_ULIMIT_DEFAULT_OVERHEAD = 30 # seconds after cgroups cputime limit
_BYTE_FACTOR = 1000 # byte in kilobyte

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
           Part of BenchExec: https://github.com/dbeyer/benchexec/""")
    parser.add_argument("args", nargs="+", metavar="ARG",
                        help='command line to run (prefix with "--" to ensure all arguments are treated correctly)')
    parser.add_argument("--input", metavar="FILE",
                        help="name of file used as stdin for command (default: /dev/null; use - for stdin passthrough)")
    parser.add_argument("--output", default="output.log", metavar="FILE",
                        help="name of file where command output is written")
    parser.add_argument("--maxOutputSize", type=int, metavar="BYTES",
                        help="shrink output file to approximately this size if necessary (by removing lines from the middle of the output)")
    parser.add_argument("--memlimit", type=int, metavar="BYTES",
                        help="memory limit in bytes")
    parser.add_argument("--timelimit", type=int, metavar="SECONDS",
                        help="CPU time limit in seconds")
    parser.add_argument("--softtimelimit", type=int, metavar="SECONDS",
                        help='"soft" CPU time limit in seconds (command will be send the TERM signal at this time)')
    parser.add_argument("--walltimelimit", type=int, metavar="SECONDS",
                        help='wall time limit in seconds (default is CPU time limit plus a few seconds)')
    parser.add_argument("--cores", type=util.parse_int_list, metavar="N,M-K",
                        help="list of CPU cores to use")
    parser.add_argument("--memoryNodes", type=util.parse_int_list, metavar="N,M-K",
                        help="list of memory nodes to use")
    parser.add_argument("--dir", metavar="DIR",
                        help="working directory for executing the command (default is current directory)")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--debug", action="store_true",
                           help="show debug output")
    verbosity.add_argument("--quiet", action="store_true",
                           help="show only warnings")
    options = parser.parse_args(argv[1:])

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
            options.maxOutputSize = data["maxLogfileSize"] * _BYTE_FACTOR * _BYTE_FACTOR # MB to bytes

    # setup logging
    logLevel = logging.INFO
    if options.debug:
        logLevel = logging.DEBUG
    elif options.quiet:
        logLevel = logging.WARNING
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        level=logLevel)

    if options.input == '-':
        stdin = sys.stdin
    elif options.input is not None:
        if options.input == options.output:
            sys.exit("Input and output files cannot be the same.")
        try:
            stdin = open(options.input, 'rt')
        except IOError as e:
            sys.exit(e)
    else:
        stdin = None

    executor = RunExecutor()

    # ensure that process gets killed on interrupt/kill signal
    def signal_handler_kill(signum, frame):
        executor.stop()
    signal.signal(signal.SIGTERM, signal_handler_kill)
    signal.signal(signal.SIGINT,  signal_handler_kill)

    logging.info('Starting command ' + ' '.join(options.args))
    logging.info('Writing output to ' + options.output)

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
                            environments=env,
                            workingDir=options.dir,
                            maxLogfileSize=options.maxOutputSize)
    finally:
        if stdin:
            stdin.close()

    # exit_code is a special number:
    # It is a 16bit int of which the lowest 7 bit are the signal number,
    # and the high byte is the real exit code of the process (here 0).
    exit_code = result['exitcode']
    return_value = exit_code // 256
    exitSignal = exit_code % 128

    def print_optional_result(key):
        if key in result:
            # avoid unicode literals such that the string can be parsed by Python 3.2
            print(key + "=" + str(result[key]).replace("'u", ''))

    # output results
    print_optional_result('terminationreason')
    print("exitcode=" + str(exit_code))
    if (exitSignal == 0) or (return_value != 0):
        print("returnvalue=" + str(return_value))
    if exitSignal != 0 :
        print("exitsignal=" + str(exitSignal))
    print("walltime=" + str(result['walltime']) + "s")
    print("cputime=" + str(result['cputime']) + "s")
    print_optional_result('memory')
    if 'energy' in result:
        for key, value in result['energy'].items():
            print("energy-{0}={1}".format(key, value))

class RunExecutor():

    def __init__(self):
        self.PROCESS_KILLED = False
        self.SUB_PROCESSES_LOCK = threading.Lock() # needed, because we kill the process asynchronous
        self.SUB_PROCESSES = set()
        self._termination_reason = None

        self._init_cgroups()


    def _init_cgroups(self):
        """
        This function initializes the cgroups for the limitations and measurements.
        """
        self.cgroups = find_my_cgroups()

        self.cgroups.require_subsystem(CPUACCT)
        if CPUACCT not in self.cgroups:
            logging.warning('Without cpuacct cgroups, cputime measurement and limit might not work correctly if subprocesses are started.')

        self.cgroups.require_subsystem(FREEZER)
        if FREEZER not in self.cgroups:
            logging.warning('Cannot reliably kill sub-processes without freezer cgroup.')

        self.cgroups.require_subsystem(MEMORY)
        if MEMORY not in self.cgroups:
            logging.warning('Cannot measure memory consumption without memory cgroup.')

        self.cgroups.require_subsystem(CPUSET)

        self.cpus = None # to indicate that we cannot limit cores
        self.memory_nodes = None # to indicate that we cannot limit cores
        if CPUSET in self.cgroups:
            # Read available cpus/memory nodes:
            try:
                self.cpus = util.parse_int_list(self.cgroups.get_value(CPUSET, 'cpus'))
            except ValueError as e:
                logging.warning("Could not read available CPU cores from kernel: {0}".format(e.strerror))
            logging.debug("List of available CPU cores is {0}.".format(self.cpus))

            try:
                self.memory_nodes = util.parse_int_list(self.cgroups.get_value(CPUSET, 'mems'))
            except ValueError as e:
                logging.warning("Could not read available memory nodes from kernel: {0}".format(e.strerror))
            logging.debug("List of available memory nodes is {0}.".format(self.memory_nodes))


    def _setup_cgroups(self, args, my_cpus, memlimit, memory_nodes):
        """
        This method creates the CGroups for the following execution.
        @param args: the command line to run, used only for logging
        @param my_cpus: None or a list of the CPU cores to use
        @param memlimit: None or memory limit in bytes
        @param memory_nodes: None or a list of memory nodes of a NUMA system to use
        @return cgroups: a map of all the necessary cgroups for the following execution.
                         Please add the process of the following execution to all those cgroups!
        """

        # Setup cgroups, need a single call to create_cgroup() for all subsystems
        subsystems = [CPUACCT, FREEZER, MEMORY]
        if my_cpus is not None:
            subsystems.append(CPUSET)
        subsystems = [s for s in subsystems if s in self.cgroups]

        cgroups = self.cgroups.create_fresh_child_cgroup(*subsystems)

        logging.debug("Executing {0} in cgroups {1}.".format(args, cgroups))

        # Setup cpuset cgroup if necessary to limit the CPU cores/memory nodes to be used.
        if my_cpus is not None:
            my_cpus_str = ','.join(map(str, my_cpus))
            cgroups.set_value(CPUSET, 'cpus', my_cpus_str)
            my_cpus_str = cgroups.get_value(CPUSET, 'cpus')
            logging.debug('Executing {0} with cpu cores [{1}].'.format(args, my_cpus_str))

        if memory_nodes is not None:
            cgroups.set_value(CPUSET, 'mems', ','.join(map(str, memory_nodes)))
            memory_nodesStr = cgroups.get_value(CPUSET, 'mems')
            logging.debug('Executing {0} with memory nodes [{1}].'.format(args, memory_nodesStr))


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
                    if e.errno == 95: # kernel responds with error 95 (operation unsupported) if this is disabled
                        sys.exit('Memory limit specified, but kernel does not allow limiting swap memory. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')
                    raise e

            memlimit = cgroups.get_value(MEMORY, limit)
            logging.debug('Executing {0} with memory limit {1} bytes.'.format(args, memlimit))

        if MEMORY in cgroups \
                and not cgroups.has_value(MEMORY, 'memsw.max_usage_in_bytes') \
                and systeminfo.has_swap():
            logging.warning('Kernel misses feature for accounting swap memory, but machine has swap. Memory usage may be measured inaccurately. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')

        if MEMORY in cgroups:
            try:
                # Note that this disables swapping completely according to
                # https://www.kernel.org/doc/Documentation/cgroups/memory.txt
                # (unlike setting the global swappiness to 0).
                # Our process might get killed because of this.
                cgroups.set_value(MEMORY, 'swappiness', '0')
            except IOError as e:
                logging.warning('Could not disable swapping for benchmarked process: ' + str(e))

        return cgroups


    def _execute(self, args, output_filename, stdin, cgroups, hardtimelimit, softtimelimit, walltimelimit, myCpuCount, memlimit, environments, workingDir):
        """
        This method executes the command line and waits for the termination of it.
        """

        def preSubprocess():
            os.setpgrp() # make subprocess to group-leader
            os.nice(5) # increase niceness of subprocess

            if hardtimelimit is not None:
                # Also use ulimit for CPU time limit as a fallback if cgroups don't work.
                if CPUACCT in cgroups:
                    # Use a slightly higher limit to ensure cgroups get used
                    # (otherwise we cannot detect the timeout properly).
                    ulimit = hardtimelimit + _ULIMIT_DEFAULT_OVERHEAD
                else:
                    ulimit = hardtimelimit
                resource.setrlimit(resource.RLIMIT_CPU, (ulimit, ulimit))

            # put us into the cgroup(s)
            pid = os.getpid()
            # On some systems, cgrulesengd would move our process into other cgroups.
            # We disable this behavior via libcgroup if available.
            # Unfortunately, logging/printing does not seem to work here.
            from ctypes import cdll
            try:
                libcgroup = cdll.LoadLibrary('libcgroup.so.1')
                failure = libcgroup.cgroup_init()
                if failure:
                    pass
                    #print('Could not initialize libcgroup, error {}'.format(success))
                else:
                    CGROUP_DAEMON_UNCHANGE_CHILDREN = 0x1
                    failure = libcgroup.cgroup_register_unchanged_process(pid, CGROUP_DAEMON_UNCHANGE_CHILDREN)
                    if failure:
                        pass
                        #print('Could not register process to cgrulesndg, error {}. Probably the daemon will mess up our cgroups.'.format(success))
            except OSError:
                pass
                #print('libcgroup is not available: {}'.format(e.strerror))

            cgroups.add_task(pid)


        # Setup environment:
        # If keepEnv is set, start from a fresh environment, otherwise with the current one.
        # keepEnv specifies variables to copy from the current environment,
        # newEnv specifies variables to set to a new value,
        # additionalEnv specifies variables where some value should be appended, and
        # clearEnv specifies variables to delete.
        runningEnv = os.environ.copy() if not environments.get("keepEnv", {}) else {}
        for key, value in environments.get("keepEnv", {}).items():
            if key in os.environ:
                runningEnv[key] = os.environ[key]
        for key, value in environments.get("newEnv", {}).items():
            runningEnv[key] = value
        for key, value in environments.get("additionalEnv", {}).items():
            runningEnv[key] = os.environ.get(key, "") + value
        for key in environments.get("clearEnv", {}).items():
            runningEnv.pop(key, None)

        logging.debug("Using additional environment {0}.".format(str(environments)))

        # write command line into outputFile
        try:
            outputFile = open(output_filename, 'w') # override existing file
        except IOError as e:
            sys.exit(e)
        outputFile.write(' '.join(args) + '\n\n\n' + '-' * 80 + '\n\n\n')
        outputFile.flush()

        timelimitThread = None
        oomThread = None
        energyBefore = util.measure_energy()
        walltime_before = time.time()

        p = None
        try:
            p = subprocess.Popen(args,
                                 stdin=stdin,
                                 stdout=outputFile, stderr=outputFile,
                                 env=runningEnv, cwd=workingDir,
                                 close_fds=True,
                                 preexec_fn=preSubprocess)

        except OSError as e:
            logging.critical("OSError {0} while starting '{1}' in '{2}': {3}."
                             .format(e.errno, args[0], workingDir or '.', e.strerror))
            return (0, 0, 0, None)

        try:
            with self.SUB_PROCESSES_LOCK:
                self.SUB_PROCESSES.add(p)

            # hard time limit with cgroups is optional (additionally enforce by ulimit)
            cgroup_hardtimelimit = hardtimelimit if CPUACCT in cgroups else None

            if any([cgroup_hardtimelimit, softtimelimit, walltimelimit]):
                # Start a timer to periodically check timelimit
                timelimitThread = _TimelimitThread(cgroups, cgroup_hardtimelimit, softtimelimit, walltimelimit, p, myCpuCount, self._set_termination_reason)
                timelimitThread.start()

            if memlimit is not None:
                try:
                    oomThread = oomhandler.KillProcessOnOomThread(cgroups, p,
                                                                  self._set_termination_reason)
                    oomThread.start()
                except OSError as e:
                    logging.critical("OSError {0} during setup of OomEventListenerThread: {1}.".format(e.errno, e.strerror))

            try:
                logging.debug("waiting for: pid:{0}".format(p.pid))
                pid, returnvalue, ru_child = os.wait4(p.pid, 0)
                logging.debug("waiting finished: pid:{0}, retVal:{1}".format(pid, returnvalue))

            except OSError as e:
                returnvalue = 0
                ru_child = None
                if self.PROCESS_KILLED:
                    # OSError 4 (interrupted system call) seems always to happen if we killed the process ourselves after Ctrl+C was pressed
                    logging.debug("OSError {0} while waiting for termination of {1} ({2}): {3}.".format(e.errno, args[0], p.pid, e.strerror))
                else:
                    logging.critical("OSError {0} while waiting for termination of {1} ({2}): {3}.".format(e.errno, args[0], p.pid, e.strerror))

        finally:
            walltime_after = time.time()


            with self.SUB_PROCESSES_LOCK:
                self.SUB_PROCESSES.discard(p)

            if timelimitThread:
                timelimitThread.cancel()

            if oomThread:
                oomThread.cancel()

            outputFile.close() # normally subprocess closes file, we do this again

            logging.debug("size of logfile '{0}': {1}".format(output_filename, str(os.path.getsize(output_filename))))

            # kill all remaining processes if some managed to survive
            cgroups.kill_all_tasks()

        energy = util.measure_energy(energyBefore)
        walltime = walltime_after - walltime_before
        cputime = ru_child.ru_utime + ru_child.ru_stime if ru_child else 0
        return (returnvalue, walltime, cputime, energy)



    def _get_exact_measures(self, cgroups, returnvalue, walltime, cputime):
        """
        This method tries to extract better measures from cgroups.
        """

        cputime2 = None
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
            cputime2 = tmp

        memUsage = None
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
                    memUsage = int(cgroups.get_value(MEMORY, memUsageFile))
                except IOError as e:
                    if e.errno == 95: # kernel responds with error 95 (operation unsupported) if this is disabled
                        logging.critical("Kernel does not track swap memory usage, cannot measure memory usage. "
                              + "Please set swapaccount=1 on your kernel command line.")
                    else:
                        raise e

        logging.debug('Run exited with code {0}, walltime={1}, cputime={2}, cgroup-cputime={3}, memory={4}'
                      .format(returnvalue, walltime, cputime, cputime2, memUsage))

        # Usually cputime2 (measured with cgroups) seems to be 0.01s greater
        # than cputime (measured with ulimit).
        # Furthermore, cputime might miss some subprocesses,
        # therefore we expect cputime2 to be always greater (and more correct).
        # However, sometimes cputime is a little bit bigger than cputime2.
        # For small values, this is probably because cputime counts since fork,
        # whereas cputime2 counts only after cgroups.add_task()
        # (so overhead from runexecutor is correctly excluded in cputime2).
        # For large values, a difference may also indicate a problem with cgroups,
        # for example another process moving our benchmarked process between cgroups,
        # thus we warn if the difference is substantial and take the larger ulimit value.
        if cputime2 is not None:
            if cputime > 0.5 and (cputime * 0.95) > cputime2:
                logging.warning('Cputime measured by wait was {0}, cputime measured by cgroup was only {1}, perhaps measurement is flawed.'.format(cputime, cputime2))
            else:
                cputime = cputime2

        return (cputime, memUsage)


    def execute_run(self, args, output_filename, stdin=None,
                   hardtimelimit=None, softtimelimit=None, walltimelimit=None,
                   cores=None, memlimit=None, memory_nodes=None,
                   environments={}, workingDir=None, maxLogfileSize=None):
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
        @return: a tuple with walltime in seconds, cputime in seconds, memory usage in bytes, returnvalue, and process output
        """

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
            coreCount = len(cores)
            if coreCount == 0:
                sys.exit("Cannot execute run without any CPU core.")
            if not set(cores).issubset(self.cpus):
                sys.exit("Cores {0} are not allowed to be used".format(list(set(cores).difference(self.cpus))))
        else:
            try:
                coreCount = multiprocessing.cpu_count()
            except NotImplementedError:
                coreCount = 1

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

        self._termination_reason = None

        logging.debug("execute_run: setting up Cgroups.")
        cgroups = self._setup_cgroups(args, cores, memlimit, memory_nodes)

        throttle_check = _CPUThrottleCheck(cores)
        swap_check = _SwapCheck()

        try:
            logging.debug("execute_run: executing tool.")
            (exitcode, walltime, cputime, energy) = \
                self._execute(args, output_filename, stdin, cgroups,
                              hardtimelimit, softtimelimit, walltimelimit,
                              coreCount, memlimit,
                              environments, workingDir)

            logging.debug("execute_run: getting exact measures.")
            (cputime, memUsage) = self._get_exact_measures(cgroups, exitcode, walltime, cputime)

        finally: # always try to cleanup cgroups, even on sys.exit()
            logging.debug("execute_run: cleaning up CGroups.")
            cgroups.remove()

        # if exception is thrown, skip the rest, otherwise perform normally

        if throttle_check.has_throttled():
            logging.warning('CPU throttled itself during benchmarking due to overheating. Benchmark results are unreliable!')
        if swap_check.has_swapped():
            logging.warning('System has swapped during benchmarking. Benchmark results are unreliable!')

        _reduce_file_size_if_necessary(output_filename, maxLogfileSize)

        if exitcode not in [0,1]:
            logging.debug("execute_run: analysing output for crash-info.")
            _get_debug_output_after_crash(output_filename)

        logging.debug("execute_run: Run execution returns with code {0}, walltime={1}, cputime={2}, memory={3}, energy={4}"
                      .format(exitcode, walltime, cputime, memUsage, energy))

        result = {'walltime': walltime,
                  'cputime':  cputime,
                  'exitcode': exitcode,
                  }
        if memUsage:
            result['memory'] = memUsage
        if self._termination_reason:
            result['terminationreason'] = self._termination_reason
        if energy:
            result['energy'] = energy
        return result

    def _set_termination_reason(self, reason):
        self._termination_reason = reason

    def stop(self):
        self._set_termination_reason('killed')
        self.PROCESS_KILLED = True
        with self.SUB_PROCESSES_LOCK:
            for process in self.SUB_PROCESSES:
                logging.warning('Killing process {0} forcefully.'.format(process.pid))
                util.kill_process(process.pid)


def _reduce_file_size_if_necessary(fileName, maxSize):
    """
    This function shrinks a file.
    We remove only the middle part of a file,
    the file-start and the file-end remain unchanged.
    """
    if maxSize is None: return # disabled, nothing to do

    fileSize = os.path.getsize(fileName)
    if fileSize < (maxSize + 500): return # not necessary

    logging.warning("Logfile '{0}' is too big (size {1} bytes). Removing lines.".format(fileName, fileSize))

    # We partition the file into 3 parts:
    # A) start: maxSize/2 bytes we want to keep
    # B) middle: part we want to remove
    # C) end: maxSize/2 bytes we want to keep

    # Trick taken from StackOverflow:
    # https://stackoverflow.com/questions/2329417/fastest-way-to-delete-a-line-from-large-file-in-python
    # We open the file twice at the same time, once for reading and once for writing.
    # We position the one file object at the beginning of B
    # and the other at the beginning of C.
    # Then we copy the content of C into B, overwriting what is there.
    # Afterwards we truncate the file after A+C.

    with open(fileName, 'r+b') as outputFile:
        with open(fileName, 'rb') as inputFile:
            # Position outputFile between A and B
            outputFile.seek(maxSize // 2)
            outputFile.readline() # jump to end of current line so that we truncate at line boundaries
            if outputFile.tell() == fileSize:
                # readline jumped to end of file because of a long line
                return

            outputFile.write("\n\n\nWARNING: YOUR LOGFILE WAS TOO LONG, SOME LINES IN THE MIDDLE WERE REMOVED.\n\n\n\n".encode())

            # Position inputFile between B and C
            inputFile.seek(-maxSize // 2, os.SEEK_END) # jump to beginning of second part we want to keep from end of file
            inputFile.readline() # jump to end of current line so that we truncate at line boundaries

            # Copy C over B
            _copy_all_lines_from_to(inputFile, outputFile)

            outputFile.truncate()


def _copy_all_lines_from_to(inputFile, outputFile):
    """
    Copy all lines from an input file object to an output file object.
    """
    currentLine = inputFile.readline()
    while currentLine:
        outputFile.write(currentLine)
        currentLine = inputFile.readline()


def _get_debug_output_after_crash(output_filename):
    """
    Segmentation faults and some memory failures reference a file
    with more information (hs_err_pid_*). We append this file to the log.
    The format that we expect is a line
    "# An error report file with more information is saved as:"
    and the file name of the dump file on the next line.
    """
    foundDumpFile = False
    with open(output_filename, 'r+') as outputFile:
        for line in outputFile:
            if foundDumpFile:
                try:
                    dumpFileName = line.strip(' #\n')
                    outputFile.seek(0, os.SEEK_END) # jump to end of log file
                    with open(dumpFileName, 'r') as dumpFile:
                        _copy_all_lines_from_to(dumpFile, outputFile)
                    os.remove(dumpFileName)
                except IOError as e:
                    logging.warning('Could not append additional segmentation fault information from {0} ({1})'.format(dumpFile, e.strerror))
                break
            if util.decode_to_string(line).startswith('# An error report file with more information is saved as:'):
                logging.debug('Going to append error report file')
                foundDumpFile = True


class _TimelimitThread(threading.Thread):
    """
    Thread that periodically checks whether the given process has already
    reached its timelimit. After this happens, the process is terminated.
    """
    def __init__(self, cgroups, hardtimelimit, softtimelimit, walltimelimit, process, cpuCount=1,
                 callbackFn=lambda reason: None):
        super(_TimelimitThread, self).__init__()

        if hardtimelimit or softtimelimit:
            assert CPUACCT in cgroups
        assert walltimelimit is not None

        self.daemon = True
        self.cgroups = cgroups
        self.timelimit = hardtimelimit or (60*60*24*365*100) # large dummy value
        self.softtimelimit = softtimelimit or (60*60*24*365*100) # large dummy value
        self.latestKillTime = time.time() + walltimelimit
        self.cpuCount = cpuCount
        self.process = process
        self.callback = callbackFn
        self.finished = threading.Event()

    def read_cputime(self):
        while True:
            try:
                return self.cgroups.read_cputime()
            except ValueError:
                # Sometimes the kernel produces strange values with linebreaks in them
                time.sleep(1)
                pass

    def run(self):
        while not self.finished.is_set():
            usedCpuTime = self.read_cputime() if CPUACCT in self.cgroups else 0
            remainingCpuTime = self.timelimit - usedCpuTime
            remainingSoftCpuTime = self.softtimelimit - usedCpuTime
            remainingWallTime = self.latestKillTime - time.time()
            logging.debug("TimelimitThread for process {0}: used CPU time: {1}, remaining CPU time: {2}, remaining soft CPU time: {3}, remaining wall time: {4}."
                          .format(self.process.pid, usedCpuTime, remainingCpuTime, remainingSoftCpuTime, remainingWallTime))
            if remainingCpuTime <= 0:
                self.callback('cputime')
                logging.debug('Killing process {0} due to CPU time timeout.'.format(self.process.pid))
                util.kill_process(self.process.pid)
                self.finished.set()
                return
            if remainingWallTime <= 0:
                self.callback('walltime')
                logging.warning('Killing process {0} due to wall time timeout.'.format(self.process.pid))
                util.kill_process(self.process.pid)
                self.finished.set()
                return

            if remainingSoftCpuTime <= 0:
                self.callback('cputime-soft')
                # soft time limit violated, ask process to terminate
                util.kill_process(self.process.pid, signal.SIGTERM)
                self.softtimelimit = self.timelimit

            remainingTime = min(remainingCpuTime/self.cpuCount,
                                remainingSoftCpuTime/self.cpuCount,
                                remainingWallTime)
            self.finished.wait(remainingTime + 1)

    def cancel(self):
        self.finished.set()


class _CPUThrottleCheck(object):
    """
    Class for checking whether the CPU has throttled during some time period.
    """
    def __init__(self, cores=None):
        """
        Create an instance that monitors the given list of cores (or all CPUs).
        """
        self.cpu_throttle_count = {}
        cpu_pattern = '[{0}]'.format(','.join(map(str, cores))) if cores else '*'
        for file in glob.glob('/sys/devices/system/cpu/cpu{}/thermal_throttle/*_throttle_count'.format(cpu_pattern)):
            try:
                self.cpu_throttle_count[file] = int(util.read_file(file))
            except Exception as e:
                logging.warning('Cannot read throttling count of CPU from kernel: ' + str(e))

    def has_throttled(self):
        """
        Check whether any of the CPU cores monitored by this instance has
        throttled since this instance was created.
        @return a boolean value
        """
        for file, value in self.cpu_throttle_count.items():
            try:
                new_value = int(util.read_file(file))
                if new_value > value:
                    return True
            except Exception as e:
                logging.warning('Cannot read throttling count of CPU from kernel: ' + str(e))
        return False


class _SwapCheck(object):
    """
    Class for checking whether the system has swapped during some period.
    """
    def __init__(self):
        self.swap_count = self._read_swap_count()

    def _read_swap_count(self):
        try:
            return dict((k, int(v)) for k, v
                                    in util.read_key_value_pairs_from_file('/proc/vmstat')
                                    if k in ['pswpin', 'pswpout'])
        except Exception as e:
                logging.warning('Cannot read swap count from kernel: ' + str(e))

    def has_swapped(self):
        """
        Check whether any swapping occured on this system since this instance was created.
        @return a boolean value
        """
        new_values = self._read_swap_count()
        for key, new_value in new_values.items():
            old_value = self.swap_count.get(key, 0)
            if new_value > old_value:
                return True
        return False


if __name__ == '__main__':
    main()
