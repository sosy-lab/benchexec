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

import argparse
import contextlib
import logging
import inspect
import os
import sys

sys.dont_write_bytecode = True  # prevent creation of .pyc files

import benchexec.benchexec
from benchexec import model
import benchexec.tools.template

COLOR_RED = "\033[31;1m"
COLOR_GREEN = "\033[32;1m"
COLOR_ORANGE = "\033[33;1m"
COLOR_MAGENTA = "\033[35;1m"

COLOR_DEFAULT = "\033[m"
COLOR_DESCRIPTION = COLOR_MAGENTA
COLOR_VALUE = COLOR_GREEN
COLOR_WARNING = COLOR_RED

if not sys.stdout.isatty():
    COLOR_DEFAULT = ""
    COLOR_DESCRIPTION = ""
    COLOR_VALUE = ""
    COLOR_WARNING = ""


def print_value(description, value, extra_line=False):
    print(
        "{}{}{}:{}“{}{}{}”".format(
            COLOR_DESCRIPTION,
            description,
            COLOR_DEFAULT,
            "\n\t" if extra_line else " ",
            COLOR_VALUE,
            value,
            COLOR_DEFAULT,
        ),
        file=sys.stderr,
    )


def print_list(description, value):
    print_value(description, list(value), extra_line=True)


def print_multiline_list(description, values):
    print(
        "{}{}{}:".format(COLOR_DESCRIPTION, description, COLOR_DEFAULT), file=sys.stderr
    )
    for value in values:
        print("\t“{}{}{}”".format(COLOR_VALUE, value, COLOR_DEFAULT), file=sys.stderr)


def print_multiline_text(description, value):
    if value is None:
        print(
            "{}{}{}: {}None{}".format(
                COLOR_DESCRIPTION,
                description,
                COLOR_DEFAULT,
                COLOR_WARNING,
                COLOR_DEFAULT,
            ),
            file=sys.stderr,
        )
    elif not value.strip():
        print(
            "{}{}{}: {}“{}”{}".format(
                COLOR_DESCRIPTION,
                description,
                COLOR_DEFAULT,
                COLOR_WARNING,
                value,
                COLOR_DEFAULT,
            ),
            file=sys.stderr,
        )
    else:
        print(
            "{}{}{}:".format(COLOR_DESCRIPTION, description, COLOR_DEFAULT),
            file=sys.stderr,
        )
        for line in value.splitlines():
            print("\t{}{}{}".format(COLOR_VALUE, line, COLOR_DEFAULT), file=sys.stderr)


@contextlib.contextmanager
def log_if_unsupported(msg):
    """Catch any exception in block and log it with a message about an unsupported feature"""
    try:
        yield  # call code block to be executed
    except BaseException as e:
        logging.warning(
            "Tool-info module does not support %s: “%s”",
            msg,
            e,
            exc_info=not isinstance(
                e, benchexec.tools.template.UnsupportedFeatureException
            ),
        )


def print_tool_info(name, config):
    print_value("Name of tool module", name)
    tool_module, tool = model.load_tool_info(name, config)
    print_value("Full name of tool module", tool_module)
    print_multiline_text("Documentation of tool module", inspect.getdoc(tool))

    print_value("Name of tool", tool.name())

    executable = tool.executable()
    print_value("Executable", executable)
    if not os.path.isabs(executable):
        print_value("Executable (absolute path)", os.path.abspath(executable))
    else:
        logging.warning(
            "Path to executable is absolute, this might be problematic "
            "in scenarios where runs are distributed to other machines."
        )

    try:
        print_value("Version", tool.version(executable))
    except:
        logging.warning("Determining version failed:", exc_info=1)

    working_directory = tool.working_directory(executable)
    print_value("Working directory", working_directory)
    if not os.path.isabs(working_directory):
        print_value(
            "Working directory (absolute path)", os.path.abspath(working_directory)
        )

    program_files = list(tool.program_files(executable))
    if program_files:
        print_multiline_list("Program files", program_files)
        print_multiline_list(
            "Program files (absolute paths)", map(os.path.abspath, program_files)
        )
    else:
        logging.warning("Tool module specifies no program files.")

    environment = tool.environment(executable)
    new_environment = environment.pop("newEnv", {})
    if new_environment:
        print_multiline_list(
            "Additional environment variables",
            (
                "{}={}".format(variable, value)
                for (variable, value) in new_environment.items()
            ),
        )
    append_environment = environment.pop("additionalEnv", {})
    if append_environment:
        print_multiline_list(
            "Appended environment variables",
            (
                "{}=${{{}}}{}".format(variable, variable, value)
                for (variable, value) in append_environment.items()
            ),
        )
    if environment:
        logging.warning(
            "Tool module returned invalid entries for environment, these will be ignored: “%s”",
            environment,
        )

    with log_if_unsupported(
        "tasks without options, property file, and resource limits"
    ):
        cmdline = model.cmdline_for_run(tool, executable, [], ["INPUT.FILE"], None, {})
        print_list("Minimal command line", cmdline)
        if not "INPUT.FILE" in " ".join(cmdline):
            logging.warning("Tool module ignores input file.")

    with log_if_unsupported("tasks with command-line options"):
        cmdline = model.cmdline_for_run(
            tool, executable, ["-SOME_OPTION"], ["INPUT.FILE"], None, {}
        )
        print_list("Command line with parameter", cmdline)
        if not "-SOME_OPTION" in cmdline:
            logging.warning("Tool module ignores command-line options.")

    with log_if_unsupported("tasks with property file"):
        cmdline = model.cmdline_for_run(
            tool, executable, [], ["INPUT.FILE"], "PROPERTY.PRP", {}
        )
        print_list("Command line with property file", cmdline)
        if not "PROPERTY.PRP" in " ".join(cmdline):
            logging.warning("Tool module ignores property file.")

    with log_if_unsupported("tasks with multiple input files"):
        cmdline = model.cmdline_for_run(
            tool, executable, [], ["INPUT1.FILE", "INPUT2.FILE"], None, {}
        )
        print_list("Command line with multiple input files", cmdline)
        if "INPUT1.FILE" in " ".join(cmdline) and not "INPUT2.FILE" in " ".join(
            cmdline
        ):
            logging.warning("Tool module ignores all but first input file.")

    with log_if_unsupported("tasks with CPU-time limit"):
        cmdline = model.cmdline_for_run(
            tool, executable, [], ["INPUT.FILE"], None, {model.SOFTTIMELIMIT: 123}
        )
        print_list("Command line CPU-time limit", cmdline)

    return tool


def analyze_tool_output(tool, file):
    try:
        output = file.readlines()
    except (IOError, UnicodeDecodeError) as e:
        logging.warning("Cannot read tool output from “%s”: %s", file.name, e)
        return

    try:
        result = tool.determine_result(
            returncode=0, returnsignal=0, output=output, isTimeout=False
        )
        print_value(
            "Result of analyzing tool output in “" + file.name + "”",
            result,
            extra_line=True,
        )
    except:
        logging.warning(
            "Tool module failed to analyze result in “%s”:", file.name, exc_info=1
        )


def main(argv=None):
    """
    A simple command-line interface to print information provided by a tool info.
    """
    if sys.version_info < (3,):
        sys.exit("benchexec.test_tool_info needs Python 3 to run.")
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description="""Test a tool info for BenchExec and print out all relevant information this tool info provides.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""",
    )
    parser.add_argument("tool", metavar="TOOL", help="name of tool info to test")
    parser.add_argument(
        "--tool-output",
        metavar="OUTPUT_FILE",
        nargs="+",
        type=argparse.FileType("r"),
        help="optional names of text files with example outputs of a tool run",
    )
    benchexec.benchexec.add_container_args(parser)

    options = parser.parse_args(argv[1:])
    logging.basicConfig(
        format=COLOR_WARNING + "%(levelname)s: %(message)s" + COLOR_DEFAULT
    )

    tool = print_tool_info(options.tool, options)

    if options.tool_output:
        for file in options.tool_output:
            analyze_tool_output(tool, file)


if __name__ == "__main__":
    main()
