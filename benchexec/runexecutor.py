# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import collections
import datetime
import decimal
import logging
import multiprocessing
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import tempfile
from typing import cast, Any, Dict, Optional

from benchexec import __version__
from benchexec import baseexecutor
from benchexec import BenchExecException
from benchexec import containerexecutor
from benchexec.cgroups import Cgroups
from benchexec.filehierarchylimit import FileHierarchyLimitThread
from benchexec import intel_cpu_energy
from benchexec import oomhandler
from benchexec.util import print_decimal
from benchexec import resources
from benchexec import systeminfo
from benchexec import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files

_WALLTIME_LIMIT_DEFAULT_OVERHEAD = 30  # seconds more than cputime limit
_BYTE_FACTOR = 1000  # byte in kilobyte
_LOG_SHRINK_MARKER = "\n\n\nWARNING: YOUR LOGFILE WAS TOO LONG, SOME LINES IN THE MIDDLE WERE REMOVED.\n\n\n\n"


def main(argv=None):
    """
    A simple command-line interface for the runexecutor module of BenchExec.
    """
    if argv is None:
        argv = sys.argv

    # parse options
    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description="""Execute a command with resource limits and measurements.
           Command-line parameters can additionally be read from a file if file name prefixed with '@' is given as argument.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""",
    )

    resource_args = parser.add_argument_group("optional arguments for resource limits")
    resource_args.add_argument(
        "--memlimit",
        type=util.parse_memory_value,
        metavar="BYTES",
        help="memory limit in bytes",
    )
    resource_args.add_argument(
        "--timelimit",
        type=util.parse_timespan_value,
        metavar="SECONDS",
        help="CPU time limit in seconds",
    )
    resource_args.add_argument(
        "--softtimelimit",
        type=util.parse_timespan_value,
        metavar="SECONDS",
        help='"soft" CPU time limit in seconds (command will be send the TERM signal at this time)',
    )
    resource_args.add_argument(
        "--walltimelimit",
        type=util.parse_timespan_value,
        metavar="SECONDS",
        help="wall time limit in seconds (default is CPU time limit plus a few seconds)",
    )
    resource_args.add_argument(
        "--cores",
        type=util.parse_int_list,
        metavar="N,M-K",
        help="list of CPU cores to use",
    )
    resource_args.add_argument(
        "--memoryNodes",
        type=util.parse_int_list,
        metavar="N,M-K",
        help="list of memory nodes to use",
    )

    io_args = parser.add_argument_group("optional arguments for run I/O")
    io_args.add_argument(
        "--input",
        metavar="FILE",
        help="name of file used as stdin for command "
        "(default: /dev/null; use - for stdin passthrough)",
    )
    io_args.add_argument(
        "--output",
        default="output.log",
        metavar="FILE",
        help="name of file where command output (stdout and stderr) is written",
    )
    io_args.add_argument(
        "--maxOutputSize",
        type=util.parse_memory_value,
        metavar="BYTES",
        help="shrink output file to approximately this size if necessary "
        "(by removing lines from the middle of the output)",
    )
    io_args.add_argument(
        "--filesCountLimit",
        type=int,
        metavar="COUNT",
        help="maximum number of files the tool may write to (checked periodically, counts only files written in container mode or to temporary directories, only supported with --no-tmpfs)",
    )
    io_args.add_argument(
        "--filesSizeLimit",
        type=util.parse_memory_value,
        metavar="BYTES",
        help="maximum size of files the tool may write (checked periodically, counts only files written in container mode or to temporary directories, only supported with --no-tmpfs)",
    )
    io_args.add_argument(
        "--skip-cleanup",
        action="store_false",
        dest="cleanup",
        help="do not delete files created by the tool in temp directory",
    )

    container_args = parser.add_argument_group("optional arguments for run container")
    container_on_args = container_args.add_mutually_exclusive_group()
    container_on_args.add_argument(
        "--container",
        action="store_true",
        dest="_ignored_container",
        help="force isolation of run in container (default)",
    )
    container_on_args.add_argument(
        "--no-container",
        action="store_false",
        dest="container",
        help="disable use of containers for isolation of runs",
    )
    containerexecutor.add_basic_container_args(container_args)
    containerexecutor.add_container_output_args(container_args)

    environment_args = parser.add_argument_group(
        "optional arguments for run environment"
    )
    environment_args.add_argument(
        "--require-cgroup-subsystem",
        action="append",
        default=[],
        metavar="SUBSYSTEM",
        help="additional cgroup system that should be enabled for runs "
        "(may be specified multiple times)",
    )
    environment_args.add_argument(
        "--set-cgroup-value",
        action="append",
        dest="cgroup_values",
        default=[],
        metavar="SUBSYSTEM.OPTION=VALUE",
        help="additional cgroup values that should be set for runs (e.g., 'cpu.shares=1000')",
    )
    environment_args.add_argument(
        "--dir",
        metavar="DIR",
        help="working directory for executing the command (default is current directory)",
    )

    baseexecutor.add_basic_executor_options(parser)

    options = parser.parse_args(argv[1:])
    baseexecutor.handle_basic_executor_options(options)
    logging.debug("This is runexec %s.", __version__)

    if options.container:
        container_options = containerexecutor.handle_basic_container_args(
            options, parser
        )
        container_output_options = containerexecutor.handle_container_output_args(
            options, parser
        )
        if container_options["container_tmpfs"] and (
            options.filesCountLimit or options.filesSizeLimit
        ):
            parser.error(
                "Files-count limit and files-size limit are not supported if tmpfs is used in container. Use --no-tmpfs to make these limits work or disable them (typically they are unnecessary if a tmpfs is used)."
            )
    else:
        container_options = {}
        container_output_options = {}

    if options.input == "-":
        stdin = sys.stdin
    elif options.input is not None:
        if options.input == options.output:
            parser.error("Input and output files cannot be the same.")
        try:
            stdin = open(options.input, "rt")
        except OSError as e:
            parser.error(str(e))
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
                f'Cgroup value "{arg}" has invalid format, '
                f'needs to be "subsystem.option=value".'
            )
        cgroup_values[(subsystem, option)] = value
        cgroup_subsystems.add(subsystem)

    executor = RunExecutor(
        cleanup_temp_dir=options.cleanup,
        additional_cgroup_subsystems=list(cgroup_subsystems),
        use_namespaces=options.container,
        **container_options,
    )

    # Ensure that process gets killed on interrupt/kill signal,
    # and avoid KeyboardInterrupt because it could occur anywhere.
    def signal_handler_kill(signum, frame):
        executor.stop()

    signal.signal(signal.SIGTERM, signal_handler_kill)
    signal.signal(signal.SIGQUIT, signal_handler_kill)
    signal.signal(signal.SIGINT, signal_handler_kill)

    logging.info("Starting command %s", shlex.join(options.args))
    if options.container and options.output_directory and options.result_files:
        logging.info(
            "Writing output to %s and result files to %s",
            shlex.quote(options.output),
            shlex.quote(options.output_directory),
        )
    else:
        logging.info("Writing output to %s", shlex.quote(options.output))

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
            workingDir=options.dir,
            maxLogfileSize=options.maxOutputSize,
            files_count_limit=options.filesCountLimit,
            files_size_limit=options.filesSizeLimit,
            **container_output_options,
        )
    finally:
        if stdin:
            stdin.close()

    # exit_code is a util.ProcessExitCode instance
    exit_code = cast(Optional[util.ProcessExitCode], result.pop("exitcode", None))

    def print_optional_result(key, unit=""):
        if key in result:
            value = result[key]
            if isinstance(value, decimal.Decimal):
                format_fn = print_decimal
            elif isinstance(value, datetime.datetime):
                format_fn = datetime.datetime.isoformat
            else:
                format_fn = str
            print(f"{key}={format_fn(value)}{unit}")

    # output results
    print_optional_result("starttime", unit="")
    print_optional_result("terminationreason")
    if exit_code is not None and exit_code.value is not None:
        print(f"returnvalue={exit_code.value}")
    if exit_code is not None and exit_code.signal is not None:
        print(f"exitsignal={exit_code.signal}")
    print_optional_result("walltime", "s")
    print_optional_result("cputime", "s")
    for key in sorted(result.keys()):
        if key.startswith("cputime-"):
            print(f"{key}={result[key]:.9f}s")
    print_optional_result("memory", "B")
    print_optional_result("blkio-read", "B")
    print_optional_result("blkio-write", "B")
    print_optional_result("pressure-cpu-some", "s")
    print_optional_result("pressure-io-some", "s")
    print_optional_result("pressure-memory-some", "s")
    energy = intel_cpu_energy.format_energy_results(result.get("cpuenergy"))
    for energy_key, energy_value in energy.items():
        print(f"{energy_key}={energy_value}J")


class RunExecutor(containerexecutor.ContainerExecutor):
    # --- object initialization ---

    def __init__(
        self, cleanup_temp_dir=True, additional_cgroup_subsystems=[], *args, **kwargs
    ):
        """
        Create an instance of of RunExecutor.
        @param cleanup_temp_dir Whether to remove the temporary directories created for the run.
        @param additional_cgroup_subsystems List of additional cgroup subsystems that should be required and used for runs.
        """
        super(RunExecutor, self).__init__(*args, **kwargs)
        self._termination_reason = None
        self._should_cleanup_temp_dir = cleanup_temp_dir
        self._cgroup_subsystems = additional_cgroup_subsystems

        self._energy_measurement = (
            intel_cpu_energy.EnergyMeasurement.create_if_supported()
        )

        self._init_cgroups()

    def _init_cgroups(self):
        """
        This function initializes the cgroups for the limitations and measurements.
        """
        self.cgroups = Cgroups.initialize()
        critical_cgroups = set()

        for subsystem in self._cgroup_subsystems:
            self.cgroups.require_subsystem(subsystem)
            if subsystem not in self.cgroups:
                critical_cgroups.add(subsystem)
                logging.error(
                    'Cgroup subsystem "%s" was required but is not available.',
                    subsystem,
                )

        # Feature is still experimental, do not warn loudly
        self.cgroups.require_subsystem(self.cgroups.IO, log_method=logging.debug)
        if self.cgroups.IO not in self.cgroups:
            logging.debug("Cannot measure I/O without blkio cgroup.")

        self.cgroups.require_subsystem(self.cgroups.CPU)
        if self.cgroups.CPU not in self.cgroups:
            logging.warning("Cannot measure CPU time without cpuacct cgroup.")

        self.cgroups.require_subsystem(self.cgroups.FREEZE)
        if self.cgroups.FREEZE not in self.cgroups and not self._use_namespaces:
            critical_cgroups.add(self.cgroups.FREEZE)
            logging.error(
                "Cannot reliably kill sub-processes without freezer cgroup "
                "or container mode. Please enable at least one of them."
            )

        self.cgroups.require_subsystem(self.cgroups.MEMORY)
        if self.cgroups.MEMORY not in self.cgroups:
            logging.warning("Cannot measure memory consumption without memory cgroup.")
        else:
            if systeminfo.has_swap() and not self.cgroups.can_limit_swap():
                logging.warning(
                    "Kernel misses feature for accounting swap memory, but machine has swap. "
                    "Memory usage may be measured inaccurately. "
                    "Please set swapaccount=1 on your kernel command line or disable swap with "
                    '"sudo swapoff -a".'
                )

        # Do not warn about missing CPUSET here, it is only useful for core limits
        # and if one is set we terminate with a better error message later.
        self.cgroups.require_subsystem(self.cgroups.CPUSET, log_method=logging.debug)
        self.cpus = None  # to indicate that we cannot limit cores
        self.memory_nodes = None  # to indicate that we cannot limit cores
        if self.cgroups.CPUSET in self.cgroups:
            # Read available cpus/memory nodes:
            try:
                self.cpus = self.cgroups.read_allowed_cpus()
            except ValueError as e:
                logging.warning("Could not read available CPU cores from kernel: %s", e)
            logging.debug("List of available CPU cores is %s.", self.cpus)

            try:
                self.memory_nodes = self.cgroups.read_allowed_memory_banks()
            except ValueError as e:
                logging.warning(
                    "Could not read available memory nodes from kernel: %s", str(e)
                )
            logging.debug("List of available memory nodes is %s.", self.memory_nodes)

        self.cgroups.handle_errors(critical_cgroups)

    # --- utility functions ---

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
        subsystems = [
            self.cgroups.IO,
            self.cgroups.CPU,
            self.cgroups.FREEZE,
            self.cgroups.MEMORY,
        ] + self._cgroup_subsystems
        if my_cpus is not None or memory_nodes is not None:
            subsystems.append(self.cgroups.CPUSET)
        subsystems = [s for s in subsystems if s in self.cgroups]

        cgroups = self.cgroups.create_fresh_child_cgroup(subsystems)

        logging.debug("Created cgroups %s.", cgroups)

        # First, set user-specified values such that they get overridden by our settings if necessary.
        for (subsystem, option), value in cgroup_values.items():
            try:
                cgroups.set_value(subsystem, option, value)
            except OSError as e:
                cgroups.remove()
                sys.exit(
                    f"{e.strerror} for setting cgroup option {subsystem}.{option} "
                    f'to "{value}" (error code {e.errno}).'
                )
            logging.debug(
                'Cgroup value %s.%s was set to "%s", new value is now "%s".',
                subsystem,
                option,
                value,
                cgroups.get_value(subsystem, option),
            )

        # Setup cpuset cgroup if necessary to limit the CPU cores/memory nodes to be used.
        if my_cpus is not None:
            my_cpus_str = ",".join(map(str, my_cpus))
            cgroups.set_value(self.cgroups.CPUSET, "cpus", my_cpus_str)
            my_cpus_str = cgroups.get_value(self.cgroups.CPUSET, "cpus")
            logging.debug("Using cpu cores [%s].", my_cpus_str)

        if memory_nodes is not None:
            cgroups.set_value(
                self.cgroups.CPUSET, "mems", ",".join(map(str, memory_nodes))
            )
            memory_nodesStr = cgroups.get_value(self.cgroups.CPUSET, "mems")
            logging.debug("Using memory nodes [%s].", memory_nodesStr)

        # Setup memory limit
        if memlimit is not None:
            cgroups.write_memory_limit(memlimit)

            memlimit = cgroups.read_memory_limit()
            logging.debug("Effective memory limit is %s bytes.", memlimit)

        if cgroups.MEMORY in cgroups:
            try:
                cgroups.disable_swap()
            except OSError as e:
                logging.warning(
                    "Could not disable swapping for benchmarked process: %s", e
                )

        return cgroups

    def _cleanup_temp_dir(self, base_dir):
        """Delete given temporary directory and all its contents."""
        if self._should_cleanup_temp_dir:
            logging.debug("Cleaning up temporary directory %s.", base_dir)
            util.rmtree(base_dir, onerror=util.log_rmtree_error)
        else:
            logging.info("Skipping cleanup of temporary directory %s.", base_dir)

    def _setup_environment(self, environments):
        """Return map with desired environment variables for run."""
        # If keepEnv is set, start from a fresh environment,
        # otherwise with the current one.
        # keepEnv specifies variables to copy from the current environment,
        # newEnv specifies variables to set to a new value,
        # additionalEnv specifies variables where some value should be appended, and
        if environments.get("keepEnv", None) is not None:
            run_environment = {}
        else:
            run_environment = os.environ.copy()
        for key in environments.get("keepEnv", {}).keys():
            if key in os.environ:
                run_environment[key] = os.environ[key]
        for key, value in environments.get("newEnv", {}).items():
            run_environment[key] = value
        for key, value in environments.get("additionalEnv", {}).items():
            run_environment[key] = os.environ.get(key, "") + value

        logging.debug("Using additional environment %s.", environments)
        return run_environment

    def _setup_output_file(self, output_filename, args, write_header=True):
        """Open and prepare output file."""
        # write command line into outputFile
        # (without environment variables, they are documented by benchexec)
        try:
            parent_dir = os.path.dirname(output_filename)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            output_file = open(output_filename, "w")  # override existing file
        except OSError as e:
            sys.exit("Could not write to output file: " + str(e))

        if write_header:
            output_file.write(shlex.join(args) + "\n\n\n" + "-" * 80 + "\n\n\n")
            output_file.flush()

        return output_file

    def _setup_cgroup_time_limit(
        self, hardtimelimit, softtimelimit, walltimelimit, cgroups, cores, pid_to_kill
    ):
        """Start time-limit handler.
        @return None or the time-limit handler for calling cancel()
        """
        if any([hardtimelimit, softtimelimit, walltimelimit]):
            # Start a timer to periodically check timelimit
            timelimitThread = _TimelimitThread(
                cgroups=cgroups,
                hardtimelimit=hardtimelimit,
                softtimelimit=softtimelimit,
                walltimelimit=walltimelimit,
                pid_to_kill=pid_to_kill,
                cores=cores,
                callbackFn=self._set_termination_reason,
            )
            timelimitThread.start()
            return timelimitThread
        return None

    def _setup_cgroup_memory_limit_thread(self, memlimit, cgroups, pid_to_kill):
        """Start memory-limit handler.
        @return None or the memory-limit handler for calling cancel()
        """
        # On CgroupsV2, the kernel kills the whole cgroup for us on OOM
        # and we can detect OOMs reliably after the fact. So no need to do anything.
        if memlimit is not None and cgroups.version == 1:
            try:
                oomThread = oomhandler.KillProcessOnOomThread(
                    cgroups=cgroups,
                    pid_to_kill=pid_to_kill,
                    callbackFn=self._set_termination_reason,
                )
                oomThread.start()
                return oomThread
            except OSError as e:
                logging.critical(
                    "OSError %s during setup of OomEventListenerThread: %s.",
                    e.errno,
                    e.strerror,
                )
        return None

    def _setup_file_hierarchy_limit(
        self, files_count_limit, files_size_limit, temp_dir, cgroups, pid_to_kill
    ):
        """Start thread that enforces any file-hiearchy limits."""
        if files_count_limit is not None or files_size_limit is not None:
            file_hierarchy_limit_thread = FileHierarchyLimitThread(
                self._get_result_files_base(temp_dir),
                files_count_limit=files_count_limit,
                files_size_limit=files_size_limit,
                pid_to_kill=pid_to_kill,
                callbackFn=self._set_termination_reason,
            )
            file_hierarchy_limit_thread.start()
            return file_hierarchy_limit_thread
        return None

    # --- run execution ---

    def execute_run(
        self,
        args,
        output_filename,
        stdin=None,
        hardtimelimit=None,
        softtimelimit=None,
        walltimelimit=None,
        cores=None,
        memlimit=None,
        memory_nodes=None,
        environments={},
        workingDir=None,
        maxLogfileSize=None,
        cgroupValues={},
        files_count_limit=None,
        files_size_limit=None,
        error_filename=None,
        write_header=True,
        **kwargs,
    ) -> Dict[str, Any]:  # pytype: disable=signature-mismatch
        """
        This function executes a given command with resource limits,
        and writes the output to a file.

        Note that this method does not expect to be interrupted by KeyboardInterrupt
        and does not guarantee proper cleanup if KeyboardInterrupt is raised!
        If this method runs on the main thread of your program,
        make sure to set a signal handler for signal.SIGINT that calls stop() instead.

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
        @param files_count_limit: None or maximum number of files that may be written.
        @param files_size_limit: None or maximum size of files that may be written.
        @param error_filename: the file where the error output should be written to (default: same as output_filename)
        @param write_headers: Write informational headers to the output and the error file if separate (default: True)
        @param **kwargs: further arguments for ContainerExecutor.execute_run()
        @return: dict with result of run (measurement results and process exitcode)
        """
        # Check argument values and call the actual method _execute()

        if stdin == subprocess.PIPE:
            sys.exit("Illegal value subprocess.PIPE for stdin")
        elif stdin is None:
            stdin = subprocess.DEVNULL

        critical_cgroups = set()

        if hardtimelimit is not None:
            if hardtimelimit <= 0:
                sys.exit(f"Invalid time limit {hardtimelimit}.")
            if self.cgroups.CPU not in self.cgroups:
                logging.error("Time limit cannot be specified without cpuacct cgroup.")
                critical_cgroups.add(self.cgroups.CPU)
        if softtimelimit is not None:
            if softtimelimit <= 0:
                sys.exit(f"Invalid soft time limit {softtimelimit}.")
            if hardtimelimit and (softtimelimit > hardtimelimit):
                sys.exit("Soft time limit cannot be larger than the hard time limit.")
            if self.cgroups.CPU not in self.cgroups:
                logging.error(
                    "Soft time limit cannot be specified without cpuacct cgroup."
                )
                critical_cgroups.add(self.cgroups.CPU)

        if walltimelimit is None:
            if hardtimelimit is not None:
                walltimelimit = hardtimelimit + _WALLTIME_LIMIT_DEFAULT_OVERHEAD
            elif softtimelimit is not None:
                walltimelimit = softtimelimit + _WALLTIME_LIMIT_DEFAULT_OVERHEAD
        else:
            if walltimelimit <= 0:
                sys.exit(f"Invalid wall time limit {walltimelimit}.")

        if cores is not None:
            if self.cpus is None:
                logging.error("Cannot limit CPU cores without cpuset cgroup.")
                critical_cgroups.add(self.cgroups.CPUSET)
            elif not cores:
                sys.exit("Cannot execute run without any CPU core.")
            elif not set(cores).issubset(self.cpus):
                forbidden_cores = list(set(cores).difference(self.cpus))
                sys.exit(f"Cores {forbidden_cores} are not allowed to be used")

        if memlimit is not None:
            if memlimit <= 0:
                sys.exit(f"Invalid memory limit {memlimit}.")
            if self.cgroups.MEMORY not in self.cgroups:
                logging.error(
                    "Memory limit specified, but cannot be implemented without cgroup support."
                )
                critical_cgroups.add(self.cgroups.MEMORY)

        if memory_nodes is not None:
            if self.memory_nodes is None:
                logging.error("Cannot restrict memory nodes without cpuset cgroup.")
                critical_cgroups.add(self.cgroups.CPUSET)
            elif len(memory_nodes) == 0:
                sys.exit("Cannot execute run without any memory node.")
            elif not set(memory_nodes).issubset(self.memory_nodes):
                forbidden_nodes = list(set(memory_nodes).difference(self.memory_nodes))
                sys.exit(f"Memory nodes {forbidden_nodes} are not allowed to be used")

        if workingDir:
            if not os.path.exists(workingDir):
                sys.exit(f"Working directory {workingDir} does not exist.")
            if not os.path.isdir(workingDir):
                sys.exit(f"Working directory {workingDir} is not a directory.")
            if not os.access(workingDir, os.X_OK):
                sys.exit(f"Permission denied for working directory {workingDir}.")

        self.cgroups.handle_errors(critical_cgroups)

        for (subsystem, option), _ in cgroupValues.items():
            if subsystem not in self._cgroup_subsystems:
                sys.exit(
                    f'Cannot set option "{option}" for subsystem "{subsystem}" '
                    f"that is not enabled. "
                    f'Please specify "--require-cgroup-subsystem {subsystem}".'
                )
            if not self.cgroups.has_value(subsystem, option):
                sys.exit(
                    f'Cannot set option "{option}" for subsystem "{subsystem}", '
                    f"it does not exist."
                )

        if files_count_limit is not None:
            if files_count_limit < 0:
                sys.exit(f"Invalid files-count limit {files_count_limit}.")
        if files_size_limit is not None:
            if files_size_limit < 0:
                sys.exit(f"Invalid files-size limit {files_size_limit}.")

        try:
            return self._execute(
                args,
                output_filename,
                error_filename,
                stdin,
                write_header,
                hardtimelimit,
                softtimelimit,
                walltimelimit,
                memlimit,
                cores,
                memory_nodes,
                cgroupValues,
                environments,
                workingDir,
                maxLogfileSize,
                files_count_limit,
                files_size_limit,
                **kwargs,
            )

        except BenchExecException as e:
            logging.critical("Cannot execute '%s': %s.", shlex.quote(args[0]), e)
            return {"terminationreason": "failed"}
        except OSError as e:
            logging.critical(
                "Error while starting '%s' in '%s': %s.",
                shlex.quote(args[0]),
                workingDir or ".",
                e,
            )
            logging.debug("Source of this OSError is:", exc_info=True)
            return {"terminationreason": "failed"}

    def _execute(
        self,
        args,
        output_filename,
        error_filename,
        stdin,
        write_header,
        hardtimelimit,
        softtimelimit,
        walltimelimit,
        memlimit,
        cores,
        memory_nodes,
        cgroup_values,
        environments,
        workingDir,
        max_output_size,
        files_count_limit,
        files_size_limit,
        **kwargs,
    ):
        """
        This method executes the command line and waits for the termination of it,
        handling all setup and cleanup, but does not check whether arguments are valid.
        """
        timelimitThread = None
        oomThread = None
        file_hierarchy_limit_thread = None

        if self._energy_measurement is not None:
            # Calculate which packages we should use for energy measurements
            if cores is None:
                packages = True  # We use all cores and thus all packages
            else:
                all_siblings = set(
                    util.flatten(
                        resources.get_cores_of_same_package_as(core) for core in cores
                    )
                )
                if all_siblings == set(cores):
                    packages = {
                        resources.get_cpu_package_for_core(core) for core in cores
                    }
                else:
                    # Disable energy measurements because we use only parts of a CPU
                    packages = None

        def preParent():
            """Setup that is executed in the parent process immediately before the actual tool is started."""
            # start measurements
            if self._energy_measurement is not None and packages:
                self._energy_measurement.start()
            starttime = util.read_local_time()
            walltime_before = time.monotonic()
            return starttime, walltime_before

        def postParent(preParent_result, exit_code, base_path, tool_cgroups):
            """Cleanup that is executed in the parent process immediately after the actual tool terminated."""
            # finish measurements
            starttime, walltime_before = preParent_result
            walltime = time.monotonic() - walltime_before
            energy = (
                self._energy_measurement.stop() if self._energy_measurement else None
            )

            # Because of https://github.com/sosy-lab/benchexec/issues/433, we want to
            # kill all processes here. Furthermore, we have experienced cases where the
            # container would just hang instead of killing all processes when its init
            # process existed, and killing via cgroups prevents this.
            # But if we do not have freezer, it is safer to just let all processes run
            # until the container is killed.
            if tool_cgroups.FREEZE in tool_cgroups:
                tool_cgroups.kill_all_tasks()

            # For a similar reason, we cancel all limits. Otherwise a run could have
            # terminationreason=walltime because copying output files took a long time.
            # Can be removed if #433 gets implemented properly.
            if timelimitThread:
                timelimitThread.cancel()
            if oomThread:
                oomThread.cancel()
            if file_hierarchy_limit_thread:
                file_hierarchy_limit_thread.cancel()

            if exit_code.value not in [0, 1]:
                _get_debug_output_after_crash(output_filename, base_path)

            return starttime, walltime, energy

        def preSubprocess():
            """Setup that is executed in the forked process before the actual tool is started."""
            os.setpgrp()  # make subprocess to group-leader

        # preparations that are not time critical
        cgroups = self._setup_cgroups(cores, memlimit, memory_nodes, cgroup_values)
        temp_dir = tempfile.mkdtemp(prefix="BenchExec_run_")
        run_environment = self._setup_environment(environments)
        outputFile = self._setup_output_file(
            output_filename, args, write_header=write_header
        )
        if error_filename is None:
            errorFile = outputFile
        else:
            errorFile = self._setup_output_file(
                error_filename, args, write_header=write_header
            )

        tool_pid = None
        tool_cgroups = None
        returnvalue = 0
        ru_child = None
        self._termination_reason = None
        result = collections.OrderedDict()

        throttle_check = systeminfo.CPUThrottleCheck(cores)
        swap_check = systeminfo.SwapCheck()

        logging.debug("Starting process.")

        try:
            tool_pid, tool_cgroups, result_fn = self._start_execution(
                args=args,
                stdin=stdin,
                stdout=outputFile,
                stderr=errorFile,
                env=run_environment,
                cwd=workingDir,
                temp_dir=temp_dir,
                memlimit=memlimit,
                memory_nodes=memory_nodes,
                cgroups=cgroups,
                parent_setup_fn=preParent,
                child_setup_fn=preSubprocess,
                parent_cleanup_fn=postParent,
                **kwargs,
            )

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.add(tool_pid)

            timelimitThread = self._setup_cgroup_time_limit(
                hardtimelimit,
                softtimelimit,
                walltimelimit,
                tool_cgroups,
                cores,
                tool_pid,
            )
            oomThread = self._setup_cgroup_memory_limit_thread(
                memlimit, tool_cgroups, tool_pid
            )
            file_hierarchy_limit_thread = self._setup_file_hierarchy_limit(
                files_count_limit, files_size_limit, temp_dir, tool_cgroups, tool_pid
            )

            # wait until process has terminated
            returnvalue, ru_child, (starttime, walltime, energy) = result_fn()
            if starttime:
                result["starttime"] = starttime
            result["walltime"] = walltime
        finally:
            # cleanup steps that need to get executed even in case of failure
            logging.debug("Process terminated, exit code %s.", returnvalue)

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.discard(tool_pid)

            if timelimitThread:
                timelimitThread.cancel()

            if oomThread:
                oomThread.cancel()

            if file_hierarchy_limit_thread:
                file_hierarchy_limit_thread.cancel()

            # Make sure to kill all processes if there are still some
            # (needs to come early to avoid accumulating more CPU time)
            if tool_cgroups:
                tool_cgroups.kill_all_tasks()

            # normally subprocess closes file, we do this again after all tasks terminated
            outputFile.close()
            if errorFile is not outputFile:
                errorFile.close()

            # measurements are not relevant in case of failure, but need to come before cgroup cleanup
            if tool_cgroups:
                self._get_cgroup_measurements(tool_cgroups, ru_child, result)
            logging.debug("Cleaning up cgroups.")
            cgroups.kill_all_tasks()  # currently necessary for removing child cgroups
            cgroups.remove()

            self._cleanup_temp_dir(temp_dir)

            if timelimitThread:
                _try_join_cancelled_thread(timelimitThread)
            if oomThread:
                _try_join_cancelled_thread(oomThread)
            if file_hierarchy_limit_thread:
                _try_join_cancelled_thread(file_hierarchy_limit_thread)

            if self._energy_measurement:
                self._energy_measurement.stop()

        # cleanup steps that are only relevant in case of success
        if throttle_check.has_throttled():
            logging.warning(
                "CPU throttled itself during benchmarking due to overheating. "
                "Benchmark results are unreliable!"
            )
        if swap_check.has_swapped():
            logging.warning(
                "System has swapped during benchmarking. "
                "Benchmark results are unreliable!"
            )

        if error_filename is not None:
            _reduce_file_size_if_necessary(error_filename, max_output_size)

        _reduce_file_size_if_necessary(output_filename, max_output_size)

        result["exitcode"] = util.ProcessExitCode.from_raw(returnvalue)
        if energy:
            if packages is True:
                result["cpuenergy"] = energy
            else:
                result["cpuenergy"] = {
                    pkg: energy[pkg] for pkg in energy if pkg in packages
                }
        if self._termination_reason:
            result["terminationreason"] = self._termination_reason
        elif self.cgroups.version == 2 and (oom_kills := result.get("oom_kill_count")):
            # At least one process was killed by the kernel due to OOM.
            logging.debug("Kernel killed %s processes due to OOM.", oom_kills)
            result["terminationreason"] = "memory"
        elif self.cgroups.version == 1 and (
            memlimit and result.get("memory", 0) >= memlimit
        ):
            # The kernel does not always issue OOM notifications and thus the OOMHandler
            # does not always run even in case of OOM. We detect this there and report OOM.
            result["terminationreason"] = "memory"

        # Cleanup
        result.pop("oom_kill_count", None)

        return result

    def _get_cgroup_measurements(self, cgroups, ru_child, result):
        """
        This method calculates the exact results for time and memory measurements.
        It is not important to call this method as soon as possible after the run.
        """
        logging.debug("Getting cgroup measurements.")

        cputime_wait = ru_child.ru_utime + ru_child.ru_stime if ru_child else 0
        cputime_cgroups = None

        def store_result(key, value):
            if value is not None:
                result[key] = value

        if cgroups.CPU in cgroups:
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
                    "Cputime measured by wait was %s, cputime measured by cgroup was only %s, "
                    "perhaps measurement is flawed.",
                    cputime_wait,
                    cputime_cgroups,
                )
                result["cputime"] = cputime_wait
            else:
                result["cputime"] = cputime_cgroups

            for core, coretime in cgroups.read_usage_per_cpu().items():
                result[f"cputime-cpu{core}"] = coretime

        if cgroups.MEMORY in cgroups:
            store_result("memory", cgroups.read_max_mem_usage())
            store_result("oom_kill_count", cgroups.read_oom_kill_count())

        if cgroups.IO in cgroups:
            result["blkio-read"], result["blkio-write"] = cgroups.read_io_stat()

        # Pressure information does not depend on enabled controllers:
        # https://docs.kernel.org/accounting/psi.html
        store_result("pressure-cpu-some", cgroups.read_cpu_pressure())
        store_result("pressure-memory-some", cgroups.read_mem_pressure())
        store_result("pressure-io-some", cgroups.read_io_pressure())

        logging.debug(
            "Resource usage of run: walltime=%s, cputime=%s, cgroup-cputime=%s, memory=%s",
            result.get("walltime"),
            cputime_wait,
            cputime_cgroups,
            result.get("memory", None),
        )

    # --- other public functions ---

    def stop(self):
        self._set_termination_reason("killed")
        super(RunExecutor, self).stop()


def _reduce_file_size_if_necessary(fileName, maxSize):
    """
    This function shrinks a file.
    We remove only the middle part of a file,
    the file-start and the file-end remain unchanged.
    """
    fileSize = os.path.getsize(fileName)

    if maxSize is None:
        logging.debug(
            "Size of logfile '%s' is %s bytes, size limit disabled.", fileName, fileSize
        )
        return  # disabled, nothing to do

    if fileSize < (maxSize + 500):
        logging.debug(
            "Size of logfile '%s' is %s bytes, nothing to do.", fileName, fileSize
        )
        return

    logging.warning(
        "Logfile '%s' is too big (size %s bytes). Removing lines.", fileName, fileSize
    )
    util.shrink_text_file(fileName, maxSize, _LOG_SHRINK_MARKER)


def _get_debug_output_after_crash(output_filename, base_path):
    """
    Segmentation faults and some memory failures reference a file
    with more information (hs_err_pid_*). We append this file to the log.
    The format that we expect is a line
    "# An error report file with more information is saved as:"
    and the file name of the dump file on the next line.
    @param output_filename name of log file with tool output
    @param base_path string that needs to be preprended to paths for lookup of files
    """
    logging.debug("Analysing output for crash info.")
    foundDumpFile = False
    try:
        with open(output_filename, "r+b") as outputFile:
            for line in outputFile:
                if foundDumpFile:
                    dumpFileName = base_path.encode() + line.strip(b" #\n")
                    outputFile.seek(0, os.SEEK_END)  # jump to end of log file
                    try:
                        with open(dumpFileName, "rb") as dumpFile:
                            util.copy_all_lines_from_to(dumpFile, outputFile)
                        os.remove(dumpFileName)
                    except OSError as e:
                        logging.warning(
                            "Could not append additional segmentation fault information "
                            "from %s (%s)",
                            dumpFileName,
                            e.strerror,
                        )
                    break
                try:
                    if line.startswith(
                        b"# An error report file with more information is saved as:"
                    ):
                        logging.debug("Going to append error report file")
                        foundDumpFile = True
                except UnicodeDecodeError:
                    pass
                    # ignore invalid chars from logfile
    except OSError as e:
        logging.warning(
            "Could not analyze tool output for crash information (%s)", e.strerror
        )


def _try_join_cancelled_thread(thread):
    """Join a thread, but if the thread doesn't terminate for some time, ignore it
    instead of waiting infinitely."""
    thread.join(10)
    if thread.is_alive():
        logging.warning(
            "Thread %s did not terminate within grace period after cancellation",
            thread.name,
        )


class _TimelimitThread(threading.Thread):
    """
    Thread that periodically checks whether the given process has already
    reached its timelimit. After this happens, the process is terminated.
    """

    def __init__(
        self,
        cgroups,
        hardtimelimit,
        softtimelimit,
        walltimelimit,
        pid_to_kill,
        cores,
        callbackFn=lambda reason: None,
    ):
        super(_TimelimitThread, self).__init__()
        self.name = "TimelimitThread-" + self.name
        self.finished = threading.Event()

        if hardtimelimit or softtimelimit:
            assert cgroups.CPU in cgroups
        assert walltimelimit is not None

        if cores:
            self.cpuCount = len(cores)
        else:
            try:
                self.cpuCount = multiprocessing.cpu_count()
            except NotImplementedError:
                self.cpuCount = 1

        self.cgroups = cgroups
        # set timelimits to large dummy value if no limit is given
        self.timelimit = hardtimelimit or (60 * 60 * 24 * 365 * 100)
        self.softtimelimit = softtimelimit or (60 * 60 * 24 * 365 * 100)
        self.latestKillTime = time.monotonic() + walltimelimit
        self.pid_to_kill = pid_to_kill
        self.callback = callbackFn

    def read_cputime(self):
        while True:
            try:
                return self.cgroups.read_cputime()
            except ValueError:
                # Sometimes the kernel produces strange values with linebreaks in them
                time.sleep(1)

    def run(self):
        while not self.finished.is_set():
            usedCpuTime = self.read_cputime() if self.cgroups.CPU in self.cgroups else 0
            remainingCpuTime = self.timelimit - usedCpuTime
            remainingSoftCpuTime = self.softtimelimit - usedCpuTime
            remainingWallTime = self.latestKillTime - time.monotonic()
            logging.debug(
                "TimelimitThread for process %s: used CPU time: %s, remaining CPU time: %s, "
                "remaining soft CPU time: %s, remaining wall time: %s.",
                self.pid_to_kill,
                usedCpuTime,
                remainingCpuTime,
                remainingSoftCpuTime,
                remainingWallTime,
            )
            if remainingCpuTime <= 0:
                self.callback("cputime")
                logging.debug(
                    "Killing process %s due to CPU time timeout.", self.pid_to_kill
                )
                util.kill_process(self.pid_to_kill)
                self.finished.set()
                return
            if remainingWallTime <= 0:
                self.callback("walltime")
                logging.warning(
                    "Killing process %s due to wall time timeout.", self.pid_to_kill
                )
                util.kill_process(self.pid_to_kill)
                self.finished.set()
                return

            if remainingSoftCpuTime <= 0:
                self.callback("cputime-soft")
                # soft time limit violated, ask process to terminate
                util.kill_process(self.pid_to_kill, signal.SIGTERM)
                self.softtimelimit = self.timelimit

            remainingTime = min(
                remainingCpuTime / self.cpuCount,
                remainingSoftCpuTime / self.cpuCount,
                remainingWallTime,
            )
            self.finished.wait(remainingTime + 1)

    def cancel(self):
        self.finished.set()


if __name__ == "__main__":
    main()
