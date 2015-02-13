"""
CPAchecker is a tool for configurable software verification.
This file is part of CPAchecker.

Copyright (C) 2007-2014  Dirk Beyer
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


CPAchecker web page:
  http://cpachecker.sosy-lab.org
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import multiprocessing
import os
import resource
import signal
import subprocess
import sys
import threading
import time

from . import util as util
from .cgroups import *
from . import oomhandler

read_file = util.read_file
write_file = util.write_file

CPUACCT = 'cpuacct'
CPUSET = 'cpuset'
MEMORY = 'memory'

_WALLTIME_LIMIT_DEFAULT_OVERHEAD = 30 # seconds more than cputime limit
_BYTE_FACTOR = 1000 # byte in kilobyte


def main(argv=None):
    """
    A simple command-line interface for the runexecutor module of BenchExec.
    """
    if argv is None:
        argv = sys.argv

    # parse options
    parser = argparse.ArgumentParser(description=
        "Run a command with resource limits and measurements.")
    parser.add_argument("args", nargs="+", metavar="ARG",
                        help='command line to run (prefix with "--" to ensure all arguments are treated correctly)')
    parser.add_argument("--output", default="output.log", metavar="FILE",
                        help="file name for file with command output")
    parser.add_argument("--maxOutputSize", type=int, metavar="BYTES",
                        help="approximate size of command output after which it will be truncated")
    parser.add_argument("--memlimit", type=int, metavar="BYTES",
                        help="memory limit in bytes")
    parser.add_argument("--timelimit", type=int, metavar="SECONDS",
                        help="CPU time limit in seconds")
    parser.add_argument("--softtimelimit", type=int, metavar="SECONDS",
                        help='"soft" CPU time limit in seconds')
    parser.add_argument("--walltimelimit", type=int, metavar="SECONDS",
                        help='wall time limit in seconds (default is CPU time plus a few seconds)')
    parser.add_argument("--cores", type=util.parse_int_list, metavar="N,M-K",
                        help="the list of CPU cores to use")
    parser.add_argument("--memoryNodes", type=util.parse_int_list, metavar="N,M-K",
                        help="the list of memory nodes to use")
    parser.add_argument("--dir", metavar="DIR",
                        help="working directory for executing the command (default is current directory)")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--debug", action="store_true",
                           help="Show debug output")
    verbosity.add_argument("--quiet", action="store_true",
                           help="Show only warnings")
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

    executor = RunExecutor()

    # ensure that process gets killed on interrupt/kill signal
    def signal_handler_kill(signum, frame):
        executor.stop()
    signal.signal(signal.SIGTERM, signal_handler_kill)
    signal.signal(signal.SIGINT,  signal_handler_kill)

    logging.info('Starting command ' + ' '.join(options.args))
    logging.info('Writing output to ' + options.output)

    # actual run execution
    result = \
        executor.execute_run(args=options.args,
                            output_filename=options.output,
                            hardtimelimit=options.timelimit,
                            softtimelimit=options.softtimelimit,
                            walltimelimit=options.walltimelimit,
                            cores=options.cores,
                            memlimit=options.memlimit,
                            memory_nodes=options.memoryNodes,
                            environments=env,
                            workingDir=options.dir,
                            maxLogfileSize=options.maxOutputSize)

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
        This function initializes the cgroups for the limitations.
        Please call it before any calls to execute_run(),
        if you want to separate initialization from actual run execution
        (e.g., for better error message handling).
        """
        self.cgroupsParents = {} # contains the roots of all cgroup-subsystems

        init_cgroup(self.cgroupsParents, CPUACCT)
        if not self.cgroupsParents[CPUACCT]:
            logging.warning('Without cpuacct cgroups, cputime measurement and limit might not work correctly if subprocesses are started.')

        init_cgroup(self.cgroupsParents, MEMORY)
        if not self.cgroupsParents[MEMORY]:
            logging.warning('Cannot measure memory consumption without memory cgroup.')

        init_cgroup(self.cgroupsParents, CPUSET)

        self.cpus = None # to indicate that we cannot limit cores
        self.memory_nodes = None # to indicate that we cannot limit cores
        cgroupCpuset = self.cgroupsParents[CPUSET]
        if cgroupCpuset:
            # Read available cpus/memory nodes:
            cpuStr = read_file(cgroupCpuset, 'cpuset.cpus')
            try:
                self.cpus = util.parse_int_list(cpuStr)
            except ValueError as e:
                logging.warning("Could not read available CPU cores from kernel: {0}".format(e.strerror))
            logging.debug("List of available CPU cores is {0}.".format(self.cpus))

            memsStr = read_file(cgroupCpuset, 'cpuset.mems')
            try:
                self.memory_nodes = util.parse_int_list(memsStr)
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
        subsystems = [CPUACCT, MEMORY]
        if my_cpus is not None:
            subsystems.append(CPUSET)

        cgroups = create_cgroup(self.cgroupsParents, *subsystems)

        logging.debug("Executing {0} in cgroups {1}.".format(args, cgroups.values()))

        # Setup cpuset cgroup if necessary to limit the CPU cores/memory nodes to be used.
        if my_cpus is not None:
            cgroupCpuset = cgroups[CPUSET]
            my_cpus_str = ','.join(map(str, my_cpus))
            write_file(my_cpus_str, cgroupCpuset, 'cpuset.cpus')
            my_cpus_str = read_file(cgroupCpuset, 'cpuset.cpus')
            logging.debug('Executing {0} with cpu cores [{1}].'.format(args, my_cpus_str))

        if memory_nodes is not None:
            cgroupCpuset = cgroups[CPUSET]
            write_file(','.join(map(str, memory_nodes)), cgroupCpuset, 'cpuset.mems')
            memory_nodesStr = read_file(cgroupCpuset, 'cpuset.mems')
            logging.debug('Executing {0} with memory nodes [{1}].'.format(args, memory_nodesStr))


        # Setup memory limit
        if memlimit is not None:
            cgroupMemory = cgroups[MEMORY]

            limitFile = 'memory.limit_in_bytes'
            write_file(str(memlimit), cgroupMemory, limitFile)

            swapLimitFile = 'memory.memsw.limit_in_bytes'
            # We need swap limit because otherwise the kernel just starts swapping
            # out our process if the limit is reached.
            # Some kernels might not have this feature,
            # which is ok if there is actually no swap.
            if not os.path.exists(os.path.join(cgroupMemory, swapLimitFile)):
                if _has_swap():
                    sys.exit('Kernel misses feature for accounting swap memory, but machine has swap. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')
            else:
                try:
                    write_file(str(memlimit), cgroupMemory, swapLimitFile)
                except IOError as e:
                    if e.errno == 95: # kernel responds with error 95 (operation unsupported) if this is disabled
                        sys.exit('Memory limit specified, but kernel does not allow limiting swap memory. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')
                    raise e

            memlimit = read_file(cgroupMemory, limitFile)
            logging.debug('Executing {0} with memory limit {1} bytes.'.format(args, memlimit))

        if not os.path.exists(os.path.join(cgroups[MEMORY], 'memory.memsw.max_usage_in_bytes')) and _has_swap():
            logging.warning('Kernel misses feature for accounting swap memory, but machine has swap. Memory usage may be measured inaccurately. Please set swapaccount=1 on your kernel command line or disable swap with "sudo swapoff -a".')

        return cgroups


    def _execute(self, args, output_filename, cgroups, hardtimelimit, softtimelimit, walltimelimit, myCpuCount, memlimit, environments, workingDir):
        """
        This method executes the command line and waits for the termination of it. 
        """

        def preSubprocess():
            os.setpgrp() # make subprocess to group-leader
            os.nice(5) # increase niceness of subprocess

            if hardtimelimit is not None:
                # Also use ulimit for CPU time limit as a fallback if cgroups are not available
                resource.setrlimit(resource.RLIMIT_CPU, (hardtimelimit, hardtimelimit))
                # TODO: using ulimit allows the tool to be killed because of timelimit
                # without the termination reason to be properly set

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
            except OSError as e:
                pass
                #print('libcgroup is not available: {}'.format(e.strerror))

            for cgroup in set(cgroups.values()):
                add_task_to_cgroup(cgroup, pid)


        # copy parent-environment and set needed values, either override or append
        runningEnv = os.environ.copy()
        for key, value in environments.get("newEnv", {}).items():
            runningEnv[key] = value
        for key, value in environments.get("additionalEnv", {}).items():
            runningEnv[key] = runningEnv.get(key, "") + value

        logging.debug("Using additional environment {0}.".format(str(environments)))

        # write command line into outputFile
        outputFile = open(output_filename, 'w') # override existing file
        outputFile.write(' '.join(args) + '\n\n\n' + '-' * 80 + '\n\n\n')
        outputFile.flush()

        timelimitThread = None
        oomThread = None
        energyBefore = util.measure_energy()
        walltime_before = time.time()

        p = None
        try:
            p = subprocess.Popen(args,
                                 stdout=outputFile, stderr=outputFile,
                                 env=runningEnv, cwd=workingDir,
                                 preexec_fn=preSubprocess)

        except OSError as e:
            logging.critical("OSError {0} while starting {1}: {2}. "
                             + "Assure that the directory containing the tool to be benchmarked is included "
                             + "in the PATH environment variable or an alias is set."
                             .format(e.errno, args[0], e.strerror))
            return (0, 0, 0, None)

        try:
            with self.SUB_PROCESSES_LOCK:
                self.SUB_PROCESSES.add(p)

            if hardtimelimit is not None and CPUACCT in cgroups:
                # Start a timer to periodically check timelimit with cgroup
                # if the tool uses subprocesses and ulimit does not work.
                timelimitThread = _TimelimitThread(cgroups[CPUACCT], hardtimelimit, softtimelimit, walltimelimit, p, myCpuCount, self._set_termination_reason)
                timelimitThread.start()

            if memlimit is not None:
                try:
                    oomThread = oomhandler.KillProcessOnOomThread(cgroups[MEMORY], p,
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
            for cgroup in set(cgroups.values()):
                kill_all_tasks_in_cgroup(cgroup)

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
            cgroupCpuacct = cgroups[CPUACCT]
            tmp = _read_cputime(cgroupCpuacct)
            tmp2 = None
            while tmp != tmp2:
                time.sleep(0.1)
                tmp2 = tmp
                tmp = _read_cputime(cgroupCpuacct)
            cputime2 = tmp

        memUsage = None
        if MEMORY in cgroups:
            # This measurement reads the maximum number of bytes of RAM+Swap the process used.
            # For more details, c.f. the kernel documentation:
            # https://www.kernel.org/doc/Documentation/cgroups/memory.txt
            memUsageFile = 'memory.memsw.max_usage_in_bytes'
            if not os.path.exists(os.path.join(cgroups[MEMORY], memUsageFile)):
                memUsageFile = 'memory.max_usage_in_bytes'
            if not os.path.exists(os.path.join(cgroups[MEMORY], memUsageFile)):
                logging.warning('Memory-usage is not available due to missing files.')
            else:
                try:
                    memUsage = read_file(cgroups[MEMORY], memUsageFile)
                    memUsage = int(memUsage)
                except IOError as e:
                    if e.errno == 95: # kernel responds with error 95 (operation unsupported) if this is disabled
                        logging.critical("Kernel does not track swap memory usage, cannot measure memory usage. "
                              + "Please set swapaccount=1 on your kernel command line.")
                    else:
                        raise e

        logging.debug('Run exited with code {0}, walltime={1}, cputime={2}, cgroup-cputime={3}, memory={4}'
                      .format(returnvalue, walltime, cputime, cputime2, memUsage))

        # Usually cputime2 seems to be 0.01s greater than cputime.
        # Furthermore, cputime might miss some subprocesses,
        # therefore we expect cputime2 to be always greater (and more correct).
        # However, sometimes cputime is a little bit bigger than cputime2.
        # This may indicate a problem with cgroups, for example another process
        # moving our benchmarked process between cgroups.
        if cputime2 is not None:
            if (cputime * 0.9) > cputime2:
                logging.warning('Cputime measured by wait was {0}, cputime measured by cgroup was only {1}, perhaps measurement is flawed.'.format(cputime, cputime2))
            else:
                cputime = cputime2

        return (cputime, memUsage)


    def execute_run(self, args, output_filename,
                   hardtimelimit=None, softtimelimit=None, walltimelimit=None,
                   cores=None, memlimit=None, memory_nodes=None,
                   environments={}, workingDir=None, maxLogfileSize=None):
        """
        This function executes a given command with resource limits,
        and writes the output to a file.
        @param args: the command line to run
        @param output_filename: the file where the output should be written to
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

        if hardtimelimit is not None:
            if hardtimelimit <= 0:
                sys.exit("Invalid time limit {0}.".format(hardtimelimit))
        if softtimelimit is not None:
            if softtimelimit <= 0:
                sys.exit("Invalid soft time limit {0}.".format(softtimelimit))
            if hardtimelimit is None:
                sys.exit("Soft time limit without hard time limit is not implemented.")
            if softtimelimit > hardtimelimit:
                sys.exit("Soft time limit cannot be larger than the hard time limit.")

        if walltimelimit is None:
            if hardtimelimit is not None:
                walltimelimit = hardtimelimit + _WALLTIME_LIMIT_DEFAULT_OVERHEAD
        else:
            if walltimelimit <= 0:
                sys.exit("Invalid wall time limit {0}.".format(walltimelimit))
            if hardtimelimit is None:
                sys.exit("Wall time limit without hard time limit is not implemented.")

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
            if not self.cgroupsParents[MEMORY]:
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

        try:
            logging.debug("execute_run: executing tool.")
            (exitcode, walltime, cputime, energy) = \
                self._execute(args, output_filename, cgroups,
                              hardtimelimit, softtimelimit, walltimelimit,
                              coreCount, memlimit,
                              environments, workingDir)

            logging.debug("execute_run: getting exact measures.")
            (cputime, memUsage) = self._get_exact_measures(cgroups, exitcode, walltime, cputime)

        finally: # always try to cleanup cgroups, even on sys.exit()
            logging.debug("execute_run: cleaning up CGroups.")
            for cgroup in set(cgroups.values()):
                # Need the set here to delete each cgroup only once.
                remove_cgroup(cgroup)

        # if exception is thrown, skip the rest, otherwise perform normally

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
                logging.warn('Killing process {0} forcefully.'.format(process.pid))
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

    with open(fileName, 'r+') as outputFile:
        with open(fileName, 'r') as inputFile:
            # Position outputFile between A and B
            outputFile.seek(maxSize // 2)
            outputFile.readline() # jump to end of current line so that we truncate at line boundaries

            outputFile.write("\n\n\nWARNING: YOUR LOGFILE WAS TOO LONG, SOME LINES IN THE MIDDLE WERE REMOVED.\n\n\n\n")

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
                    logging.warn('Could not append additional segmentation fault information from {0} ({1})'.format(dumpFile, e.strerror))
                break
            if unicode(line, errors='ignore').startswith('# An error report file with more information is saved as:'):
                logging.debug('Going to append error report file')
                foundDumpFile = True


def _read_cputime(cgroupCpuacct):
    cputimeFile = os.path.join(cgroupCpuacct, 'cpuacct.usage')
    if not os.path.exists(cputimeFile):
        logging.warning('Could not read cputime. File {0} does not exist.'.format(cputimeFile))
        return 0 # dummy value, if cputime is not available
    return float(read_file(cputimeFile))/1000000000 # nano-seconds to seconds


class _TimelimitThread(threading.Thread):
    """
    Thread that periodically checks whether the given process has already
    reached its timelimit. After this happens, the process is terminated.
    """
    def __init__(self, cgroupCpuacct, hardtimelimit, softtimelimit, walltimelimit, process, cpuCount=1,
                 callbackFn=lambda reason: None):
        super(_TimelimitThread, self).__init__()
        self.daemon = True
        self.cgroupCpuacct = cgroupCpuacct
        self.timelimit = hardtimelimit
        self.softtimelimit = softtimelimit or hardtimelimit
        self.latestKillTime = time.time() + walltimelimit
        self.cpuCount = cpuCount
        self.process = process
        self.callback = callbackFn
        self.finished = threading.Event()

    def run(self):
        while not self.finished.is_set():
            read = False
            while not read:
                try:
                    usedCpuTime = _read_cputime(self.cgroupCpuacct)
                    read = True
                except ValueError:
                    # Sometimes the kernel produces strange values with linebreaks in them
                    time.sleep(1)
                    pass
            remainingCpuTime = self.timelimit - usedCpuTime
            remainingWallTime = self.latestKillTime - time.time()
            logging.debug("TimelimitThread for process {0}: used CPU time: {1}, remaining CPU time: {2}, remaining wall time: {3}."
                          .format(self.process.pid, usedCpuTime, remainingCpuTime, remainingWallTime))
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

            if (self.softtimelimit - usedCpuTime) <= 0:
                self.callback('cputime-soft')
                # soft time limit violated, ask process to terminate
                util.kill_process(self.process.pid, signal.SIGTERM)
                self.softtimelimit = self.timelimit

            remainingTime = min(remainingCpuTime/self.cpuCount, remainingWallTime)
            self.finished.wait(remainingTime + 1)

    def cancel(self):
        self.finished.set()


def _has_swap():
    with open('/proc/meminfo', 'r') as meminfo:
        for line in meminfo:
            if line.startswith('SwapTotal:'):
                swap = line.split()[1]
                if int(swap) == 0:
                    return False
    return True
