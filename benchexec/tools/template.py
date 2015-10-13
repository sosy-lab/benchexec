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

import logging
import subprocess

import benchexec.util as util

class BaseTool(object):
    """
    This class serves both as a template for tool adaptor implementations,
    and as an abstract super class for them.
    For writing a new tool adaptor, inherit from this class and override
    the necessary methods (usually only executable(), name(), and determine_result(),
    maybe version() and cmdline(), too).
    The classes for each specific tool need to be named "Tool"
    and be located in a module named "benchmark.tools.<tool>",
    where "<tool>" is the string specified by the user in the benchmark definition.
    """

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('tool')


    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return ''

    def _version_from_tool(self, executable, arg='--version'):
        """
        Get version of a tool by executing it with argument "--version"
        and returning stdout.
        """
        try:
            process = subprocess.Popen([executable, arg],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run {0} to determine version: {1}'.
                            format(executable, e.strerror))
            return ''
        if stderr:
            logging.warning('Cannot determine {0} version, error output: {1}'.
                            format(executable, util.decode_to_string(stderr)))
            return ''
        if process.returncode:
            logging.warning('Cannot determine {0} version, exit code {1}'.
                            format(executable, process.returncode))
            return ''
        return util.decode_to_string(stdout).strip()


    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'UNKOWN'


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
                            In most cases we we have only _one_ inputfile.
        @param propertyfile: contains a specification for the verifier.
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        """
        return [executable] + options + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        return 'UNKNOWN'


    def get_value_from_output(self, lines, identifier):
        """
        OPTIONAL, extract a statistic value from the output of the tool.
        This value will be added to the resulting tables.
        It may contain HTML code, which will be rendered appropriately in the HTML tables.
        @param lines The output of the tool as list of lines.
        @param identifier The user-specified identifier for the statistic item.
        """


    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool.
        """
        return [executable]


    def working_directory(self, executable):
        """
        OPTIONAL, this method is only necessary for situations
        when the tool needs a separate working directory.
        """
        return "."


    def environment(self, executable):
        """
        OPTIONAL, this method is only necessary for tools
        that needs special environment variable.
        Returns a map, that contains identifiers for several submaps.
        All keys and values have to be Strings!

        Currently we support 2 identifiers:

        "newEnv": Before the execution, the values are assigned to the real environment-identifiers.
                  This will override existing values.
        "additionalEnv": Before the execution, the values are appended to the real environment-identifiers.
                  The seperator for the appending must be given in this method,
                  so that the operation "realValue + additionalValue" is a valid value.
                  For example in the PATH-variable the additionalValue starts with a ":".
        """
        return {}
