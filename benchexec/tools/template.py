# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module provides base classes from which tool-info modules need to inherit.
New tool-info modules should inherit from the latest class (BaseTool2),
other base classes are provided for compatibility with older tool-info modules.
The class that a tool-info module provides always has to have the name "Tool".

For more information, please refer to
https://github.com/sosy-lab/benchexec/blob/main/doc/tool-integration.md
"""

from abc import ABCMeta, abstractmethod
from collections import namedtuple
import collections
import copy
import os
import logging
import subprocess

import benchexec
import benchexec.result as result
import benchexec.util as util


class ToolNotFoundException(benchexec.BenchExecException):
    """
    Raised when a tool's executable cannot be found.
    """

    pass


class UnsupportedFeatureException(benchexec.BenchExecException):
    """
    Raised when a tool or its tool-info module does not support a requested feature.
    """

    pass


class BaseTool2(object, metaclass=ABCMeta):
    """
    This class serves both as a template for tool-info implementations,
    and as an abstract super class for them.
    For writing a new tool info, inherit from this class and override
    the necessary methods (always executable() and name(),
    usually determine_result(), cmdline(), and version(),
    and maybe working_directory() and get_value_from_output(), too).

    BenchExec will then instantiate the tool-info module's class
    and call the methods that return general information about the tool first.
    In this phase, executable() will always be called, other methods may be called.
    Afterwards, the run-specific methods will be called,
    and for each run, cmdline() will always be called before determine_result().
    Apart from this, no guarantee is made about which methods are called
    and in which order. In particular, the class must not assume that determine_result()
    will be called for a run result immediately after cmdline() was called for that run.
    It is guaranteed, however, that one instance of the class will only be used for
    one instance of the tool (in one location), so for example executable() can store
    some information about the tool (e.g., its version) in an attribute
    and other methods can safely rely on this.

    In special circumstances, it can make sense to not inherit from this class.
    In such cases the tool-info module's class needs to implement all the methods
    defined here and BaseTool2.register needs to be called with the respective class
    (cf. documentation of abc.ABCMeta.register) to declare compatibility with BaseTool2.
    Note that we might add optional methods (with default implementations) to BaseTool2
    at any time.

    This class is supported since BenchExec 3.3.
    For older tool-info modules that still inherit from BaseTool we provide a
    [migration guide](https://github.com/sosy-lab/benchexec/blob/main/doc/tool-integration.md#migrating-tool-info-modules-to-new-api).
    """

    REQUIRED_PATHS = []
    """
    List of path patterns that is used by the default implementation of program_files().
    Not necessary if this method is overwritten.
    """  # noqa: B018"

    # Methods that provide general (run-independent) information about the tool

    @abstractmethod
    def name(self):
        """
        Return the name of the tool, formatted for humans.
        This method always needs to be overriden, and typically just contains

        return "My Toolname"

        @return a non-empty string
        """
        raise NotImplementedError()

    def project_url(self):
        """
        OPTIONAL, return the URL of the tool's webpage, if available.

        @return None or a string with a URL in valid syntax for links on webpages
        """
        return None  # noqa: R501

    @abstractmethod
    def executable(self, tool_locator):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and should typically delegate to our utility method find_executable. Example:

        return tool_locator.find_executable("mytool")

        The path returned should be relative to the current directory.
        @param tool_locator: an instance of class ToolLocator
        @return a string pointing to an executable file
        """
        raise NotImplementedError()

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        Do not hard-code a version in this function, either extract the version
        from the tool or do not return a version at all.
        There is a helper function `self._version_from_tool`
        that should work with most tools, you only need to extract the version number
        from the returned tool output.
        @return a (possibly empty) string
        """
        return ""

    @staticmethod
    def _version_from_tool(
        executable,
        arg="--version",
        use_stderr=False,
        ignore_stderr=False,
        line_prefix=None,
    ):
        """
        Get version of a tool by executing it with argument "--version"
        and returning stdout.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @param arg: an argument to pass to the tool to let it print its version
        @param use_stderr: True if the tool prints version on stderr, False for stdout
        @param line_prefix: if given, search line with this prefix and return only the rest of this line
        @return a (possibly empty) string of output of the tool
        """
        try:
            process = subprocess.run(
                [executable, arg],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                universal_newlines=True,
            )
        except OSError as e:
            logging.warning(
                "Cannot run %s to determine version: %s", executable, e.strerror
            )
            return ""
        if process.stderr and not use_stderr and not ignore_stderr:
            logging.warning(
                "Cannot determine %s version, error output: %s",
                executable,
                process.stderr,
            )
            return ""
        if process.returncode:
            logging.warning(
                "Cannot determine %s version, exit code %s",
                executable,
                process.returncode,
            )
            return ""

        output = (process.stderr if use_stderr else process.stdout).strip()
        if line_prefix:
            matches = (
                line[len(line_prefix) :].strip()
                for line in output.splitlines()
                if line.startswith(line_prefix)
            )
            output = next(matches, "")
        return output

    def url_for_version(self, version):
        """
        OPTIONAL, return a link to the specific version of the tool.
        This could be for example a link to a specific release page or even a revision
        in the project's repository if the version is fine-granular enough.
        BenchExec will use this link to make version numbers of the tool clickable.

        Note that this method may be called without any of the other methods
        being called before.
        The string that is passed as a parameter is guaranteed to have been returned
        by the version() method at some point, but not necessarily in the current
        execution of BenchExec and possibly by a previous implementation of this
        tool-info module.

        If no URL can be produced, the method may simply return None.

        @param version: a version string as returned by the version() method in the past
        @return None or a string with a URL in valid syntax for links on webpages
        """
        return None  # noqa: R501

    def environment(self, executable):
        """
        OPTIONAL, this method is only necessary for tools
        that needs special environment variable, such as a modified PATH.
        However, for usability of the tool it is in general not recommended to require
        additional variables (tool uses outside of BenchExec would need to have them specified
        manually), but instead change the tool such that it does not need additional variables.
        For example, instead of requiring the tool directory to be added to PATH,
        the tool can be changed to call binaries from its own directory directly.
        This also has the benefit of not confusing bundled binaries
        with existing binaries of the system.

        Note that when executing benchmarks under a separate user account (with flag --user),
        the environment of the tool is a fresh almost-empty one.
        This function can be used to set some variables.

        Note that runexec usually overrides the environment variable $HOME and sets it to a fresh
        directory. If your tool relies on $HOME pointing to the real home directory,
        you can use the result of this function to overwrite the value specified by runexec.
        This is not recommended, however, because it means that runs may be influenced
        by files in the home directory, which hinders reproducibility.

        This method returns a dict that contains several further dicts.
        All keys and values have to be strings.
        Currently we support 3 identifiers in the outer dict:

        "keepEnv": If specified, the run gets initialized with a fresh environment and only
                  variables listed in this dict are copied from the system environment
                  (the values in this dict are ignored).
        "newEnv": Before the execution, the values are assigned to the real environment-identifiers.
                  This will override existing values.
        "additionalEnv": Before the execution, the values are appended to the real environment-identifiers.
                  The seperator for the appending must be given in this method,
                  so that the operation "realValue + additionalValue" is a valid value.
                  For example in the PATH-variable the additionalValue starts with a ":".
        @param executable: the path to the executable of the tool (typically the result of executable())
        @return a possibly empty dict with three possibly empty dicts with environment variables in them
        """
        return {}

    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool,
        relative to the current directory.
        The default implementation returns a list with the executable itself
        and all paths that result from expanding patterns in self.REQUIRED_PATHS,
        interpreting the latter as relative to the directory of the executable.
        @return a list of paths as strings
        """
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS
        )

    @staticmethod
    def _program_files_from_executable(executable, required_paths, parent_dir=False):
        """
        Get a list of program files by expanding a list of path patterns
        and interpreting it as relative to the executable.
        This method can be used as helper for implementing the method program_files().
        Contrary to the default implementation of program_files(), this method does not explicitly
        add the executable to the list of returned files, it assumes that required_paths
        contains a path that covers the executable.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @param required_paths: a list of required path patterns
        @param parent_dir: whether required_paths are relative to the directory of executable or the parent directory
        @return a list of paths as strings, suitable for result of program_files()
        """
        base_dir = os.path.dirname(executable)
        if parent_dir:
            base_dir = os.path.join(base_dir, os.path.pardir)
        return util.flatten(
            util.expand_filename_pattern(path, base_dir) for path in required_paths
        )

    def working_directory(self, executable):
        """
        OPTIONAL, this method is only necessary for situations
        when the tool needs a separate working directory.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @return a string pointing to a directory
        """
        return os.curdir

    # Methods for handling individual runs and their results

    def cmdline(self, executable, options, task, rlimits):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        All paths passed to this method (executable and fields of task)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param task: An instance of of class Task, e.g., with the input files
        @param rlimits: An instance of class ResourceLimits with the limits for this run
        @return a list of strings that represent the command line to execute
        """
        return [executable, *options, *task.input_files_or_identifier]

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        For tools that do not output some true/false result, benchexec.result.RESULT_DONE
        can be returned (this is also the default implementation).
        BenchExec will then automatically add some more information
        if the tool was killed due to a timeout, segmentation fault, etc.
        @param run: information about the run as instanceof of class Run
        @return a non-empty string, usually one of the benchexec.result.RESULT_* constants
        """
        return result.RESULT_DONE

    def get_value_from_output(self, output, identifier):
        """
        OPTIONAL, extract a statistic value from the output of the tool.
        This value will be added to the resulting tables.
        It may contain HTML code, which will be rendered appropriately in the HTML tables.

        Note that this method may be called without any of the other methods called
        before it and without any existing installation of the tool on this machine
        (because table-generator uses this method).

        @param output: The output of the tool as instance of class RunOutput.
        @param identifier: The user-specified identifier for the statistic item.
        @return a (possibly empty) string, optional with HTML tags
        """

    def close(self):
        """
        OPTIONAL, called before tool-info module is no longer used,
        but no strict guarantee about this.
        """
        pass

    # Classes that are used in parameters above

    class ToolLocator(
        namedtuple("ToolLocator", ["tool_directory", "use_path", "use_current"])
    ):
        def find_executable(self, executable_name, subdir=""):
            assert (
                os.path.basename(executable_name) == executable_name
            ), "Executable needs to be a simple file name"
            dirs = []
            if self.tool_directory:
                # join automatically handles the case where subdir is the empty string
                dirs.append(os.path.join(self.tool_directory, subdir))
            if self.use_path:
                dirs.extend(benchexec.util.get_path())
            if self.use_current:
                dirs.append(os.curdir)
                if subdir:
                    dirs.append(subdir)

            executable = benchexec.util.find_executable2(executable_name, dirs)
            if executable:
                return executable

            other_file = benchexec.util.find_executable2(executable_name, dirs, os.F_OK)
            if other_file:
                raise ToolNotFoundException(
                    f"Could not find executable '{executable_name}', "
                    f"but found file '{other_file}' that is not executable."
                )

            msg = (
                f"Could not find executable '{executable_name}'. "
                f"The searched directories were: " + "".join("\n  " + d for d in dirs)
            )
            if not self.tool_directory:
                msg += "\nYou can specify the tool's directory with --tool-directory."

            raise ToolNotFoundException(msg)

        def __new__(cls, tool_directory=None, use_path=False, use_current=False):
            """
            Create instance. All parameters have default values that do nothing and
            at least one parameter needs to be given, otherwise the instance could not
            do anything.
            """
            assert tool_directory or use_path or use_current
            return super().__new__(cls, tool_directory, use_path, use_current)

    class Task(
        namedtuple(
            "Task", ["input_files_or_empty", "identifier", "property_file", "options"]
        )
    ):
        """
        Represent the task for which the tool should be executed in a run.
        While this class is technically a tuple,
        this should be seen as an implementation detail and the order of elements in the
        tuple should not be considered. New fields may be added in the future.

        Explanation of fields:
        input_files_or_empty: ordered sequence of paths to input files (or directories),
            each relative to the tool's working directory;
            guaranteed to be of type collections.abc.Sequence;
            it is recommended to access input_files or input_files_or_identifier instead
        identifier: name of task when <withoutfile> is used to define the task,
            i.e., when the list of input files is empty, None otherwise
        property_file: path to property file if one is used (relative to the tool's
            working directory) or None otherwise
        options: content of the "options" key in the task-definition file (if present)
        """

        def __new__(cls, input_files, identifier, property_file, options):
            input_files = tuple(input_files)  # make input_files immutable
            assert bool(input_files) != bool(identifier), (
                f"exactly one is required: " f"{input_files=!r} {identifier=!r}"
            )
            options = copy.deepcopy(options)  # defensive copy because not immutable
            return super().__new__(cls, input_files, identifier, property_file, options)

        @classmethod
        def with_files(cls, input_files, *, property_file=None, options=None):
            return cls(
                input_files=input_files,
                identifier=None,
                property_file=property_file,
                options=options,
            )

        @classmethod
        def without_files(cls, identifier, *, property_file=None, options=None):
            return cls(
                input_files=[],
                identifier=identifier,
                property_file=property_file,
                options=options,
            )

        @property
        def input_files(self):
            """
            Return sequence of input files or raise appropriate exception if the task
            has no input files.
            """
            self.require_input_files()
            return self.input_files_or_empty

        @property
        def single_input_file(self):
            """
            Return string with the single given input file, or raise appropriate
            exception if there is not exactly one input file.
            """
            self.require_input_files()
            self.require_single_input_file()
            return self.input_files_or_empty[0]

        @property
        def input_files_or_identifier(self):
            """
            Return either the sequence of input files or a one-element sequence with the
            identifier. Useful for adding either to the command line arguments.
            """
            return self.input_files_or_empty or (self.identifier,)

        def require_input_files(self):
            """
            Check that there is at least one path in input_files and raise appropriate
            exception otherwise
            """
            if not self.input_files_or_empty:
                raise UnsupportedFeatureException(
                    "Tool does not support tasks without input files"
                )

        def require_single_input_file(self):
            """
            Check that there is not more than one path in input_files and raise
            appropriate exception otherwise.
            """
            if len(self.input_files_or_empty) > 1:
                raise UnsupportedFeatureException(
                    "Tool does not support tasks with more than one input file"
                )

    class ResourceLimits(
        namedtuple(
            "ResourceLimits",
            ["cputime", "cputime_hard", "walltime", "memory", "cpu_cores"],
        )
    ):
        """
        Represent resource limits of a run. While this class is technically a tuple,
        this should be seen as an implementation detail and the order of elements in the
        tuple should not be considered. New fields may be added in the future.
        Each field contains a positive int or None, which means no limit.

        Explanation of fields:
        cputime: CPU-time limit in seconds after which the tool will receive
            a termination signal and the result will be counted as timeout
        cputime_hard: CPU-time limit in seconds after which the tool will be killed
            forcibly (always greater or equal than cputime)
        walltime: Wall-time limit in seconds after which the tool will be killed
        memory: Memory limit in bytes
        cpu_cores: Number of CPU cores allowed to be used

        The CPU-time limits will either both have a value of both be None.
        """

        def __new__(
            cls,
            cputime=None,
            cputime_hard=None,
            walltime=None,
            memory=None,
            cpu_cores=None,
        ):
            return super().__new__(
                cls, cputime, cputime_hard, walltime, memory, cpu_cores
            )

    class Run(
        namedtuple("Run", ["cmdline", "exit_code", "output", "termination_reason"])
    ):
        """
        Represent a run (one tool execution) and its result. While this class is
        technically a tuple, this should be seen as an implementation detail
        and the order of elements in the tuple should not be considered.
        New fields may be added in the future.

        Explanation of files:
        @param cmdline: command line as executed (as sequence of strings)
        @param exit_code: an instance of class benchexec.util.ProcessExitCode
            (contains return code or the signal that led to termination)
        @param output: the output of the tool as instance of class RunOutput
        @param termination_reason: reason why BenchExec terminated the run, if any
            (cf. https://github.com/sosy-lab/benchexec/blob/main/doc/run-results.md,
            useful to distinguish between program killed because of error and timeout)
        """

        def __new__(cls, cmdline, exit_code, output, termination_reason):
            cmdline = tuple(cmdline)  # make cmdline immutable
            return super().__new__(cls, cmdline, exit_code, output, termination_reason)

        @property
        def was_terminated(self):
            """
            Returns whether the tool was terminated by BenchExec due to a violation
            of a resource limit or some other reason.
            """
            return bool(self.termination_reason)

        @property
        def was_timeout(self):
            """
            Returns whether the tool was terminated by BenchExec due to a violation
            of some time limit.
            """
            return self.termination_reason in ["cputime", "cputime-soft", "walltime"]

    class RunOutput(collections.abc.Sequence):
        """
        Represent the output (stdin and stdout) of a run, separated into lines.
        This class is basically an immutable list of strings
        and supports all the usual list operations (indexing, iterating, etc.)
        as well as a few other utility methods.
        Each list entry is one line of the tool's output without line separator.
        """

        @property
        def text(self):
            """Return the full output as a single string (with line separators)."""
            if self._text is None:
                self._text = "".join(self._lines)
            return self._text

        def any_line_contains(self, substr):
            """Check whether at least one line in the output contains substr."""
            assert "\n" not in substr  # would never match
            return any(substr in line for line in self._lines)

        def __init__(self, lines):
            # We keep the original line separators in _lines because then we can
            # recreate _text exactly and it makes tooladapter.Tool1To2's job easier.
            self._lines = lines
            self._text = None

        def __getitem__(self, index):
            if isinstance(index, slice):
                # We wrap the result in an RunOutput instance again such that
                # all features also work on slices of the original instance.
                return self.__class__(self._lines[index])
            return self._lines[index].rstrip(os.linesep)

        def __len__(self):
            return len(self._lines)

        def __str__(self):
            return self.text


class BaseTool(object):
    """
    This class serves both as a template for tool-info implementations,
    and as an abstract super class for them.
    However, for writing a new tool info, it is recommended to inherit from the latest
    class in this module instead of this class.
    Classes that inherit from this class need to override
    the necessary methods (always executable() and name(),
    usually determine_result(), cmdline(), and version(),
    and maybe working_directory() and get_value_from_output(), too).

    Note that tool-info modules that inherit from this class cannot make use of all of
    BenchExec's features and that we may drop support for such modules in BenchExec 4.0.
    It is thus recommended to upgrade all such tool-info modules to BaseTool2, cf. our
    [migration guide](https://github.com/sosy-lab/benchexec/blob/main/doc/tool-integration.md#migrating-tool-info-modules-to-new-api).
    """

    REQUIRED_PATHS = []
    """
    List of path patterns that is used by the default implementation of program_files().
    Not necessary if this method is overwritten.
    """  # noqa: B018

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        @return a string pointing to an executable file
        """
        return util.find_executable("tool")

    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool,
        relative to the current directory.
        The default implementation returns a list with the executable itself
        and all paths that result from expanding patterns in self.REQUIRED_PATHS,
        interpreting the latter as relative to the directory of the executable.
        @return a list of paths as strings
        """
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS
        )

    def _program_files_from_executable(self, *args, **kwargs):
        # Just delegate to same method in BaseTool2 to avoid duplicate code.
        return BaseTool2._program_files_from_executable(*args, **kwargs)

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        Do not hard-code a version in this function, either extract the version
        from the tool or do not return a version at all.
        There is a helper function `self._version_from_tool`
        that should work with most tools, you only need to extract the version number
        from the returned tool output.
        @return a (possibly empty) string
        """
        return ""

    def _version_from_tool(self, *args, **kwargs):
        # Just delegate to same method in BaseTool2 to avoid duplicate code.
        return BaseTool2._version_from_tool(*args, **kwargs)

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        This function should always be overriden.
        @return a non-empty string
        """
        return "UNKOWN"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            A typical run has only one input file, but there can be more than one.
        @param propertyfile: contains a specification for the verifier (optional, not always present).
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        @return a list of strings that represent the command line to execute
        """
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        For tools that do not output some true/false result, benchexec.result.RESULT_DONE
        can be returned (this is also the default implementation).
        BenchExec will then automatically add some more information
        if the tool was killed due to a timeout, segmentation fault, etc.
        @param returncode: the exit code of the program, 0 if the program was killed
        @param returnsignal: the signal that killed the program, 0 if program exited itself
        @param output: a list of strings of output lines of the tool (both stdout and stderr)
        @param isTimeout: whether the result is a timeout
        (useful to distinguish between program killed because of error and timeout)
        @return a non-empty string, usually one of the benchexec.result.RESULT_* constants
        """
        return result.RESULT_DONE

    def get_value_from_output(self, lines, identifier):
        """
        OPTIONAL, extract a statistic value from the output of the tool.
        This value will be added to the resulting tables.
        It may contain HTML code, which will be rendered appropriately in the HTML tables.
        It can also be a numeric value, e.g., int, float, or decimal.Decimal.
        @param lines: The output of the tool as list of lines.
        @param identifier: The user-specified identifier for the statistic item.
        @return a (possibly empty) string, optional with HTML tags, or a numeric value
        """

    def working_directory(self, executable):
        """
        OPTIONAL, this method is only necessary for situations
        when the tool needs a separate working directory.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @return a string pointing to a directory
        """
        return os.curdir

    def environment(self, executable):
        """
        OPTIONAL, this method is only necessary for tools
        that needs special environment variable, such as a modified PATH.
        However, for usability of the tool it is in general not recommended to require
        additional variables (tool uses outside of BenchExec would need to have them specified
        manually), but instead change the tool such that it does not need additional variables.
        For example, instead of requiring the tool directory to be added to PATH,
        the tool can be changed to call binaries from its own directory directly.
        This also has the benefit of not confusing bundled binaries
        with existing binaries of the system.

        Note that when executing benchmarks under a separate user account (with flag --user),
        the environment of the tool is a fresh almost-empty one.
        This function can be used to set some variables.

        Note that runexec usually overrides the environment variable $HOME and sets it to a fresh
        directory. If your tool relies on $HOME pointing to the real home directory,
        you can use the result of this function to overwrite the value specified by runexec.
        This is not recommended, however, because it means that runs may be influenced
        by files in the home directory, which hinders reproducibility.

        This method returns a dict that contains several further dicts.
        All keys and values have to be strings.
        Currently we support 3 identifiers in the outer dict:

        "keepEnv": If specified, the run gets initialized with a fresh environment and only
                  variables listed in this dict are copied from the system environment
                  (the values in this dict are ignored).
        "newEnv": Before the execution, the values are assigned to the real environment-identifiers.
                  This will override existing values.
        "additionalEnv": Before the execution, the values are appended to the real environment-identifiers.
                  The seperator for the appending must be given in this method,
                  so that the operation "realValue + additionalValue" is a valid value.
                  For example in the PATH-variable the additionalValue starts with a ":".
        @param executable: the path to the executable of the tool (typically the result of executable())
        @return a possibly empty dict with three possibly empty dicts with environment variables in them
        """
        return {}
