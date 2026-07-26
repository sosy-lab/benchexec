# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import contextlib
import copy
import logging
import inspect
import os
import sys
import yaml

import benchexec
import benchexec.benchexec
from benchexec import model
from benchexec import tooladapter
from benchexec import util
from benchexec.tooladapter import CURRENT_BASETOOL
import benchexec.tools.template

sys.dont_write_bytecode = True  # prevent creation of .pyc files

COLOR_RED = "\033[31;1m"
COLOR_GREEN = "\033[32;1m"
COLOR_ORANGE = "\033[33;1m"
COLOR_MAGENTA = "\033[35;1m"

if util.should_color_output():
    COLOR_DEFAULT = "\033[m"
    COLOR_DESCRIPTION = COLOR_MAGENTA
    COLOR_VALUE = COLOR_GREEN
    COLOR_WARNING = COLOR_RED
else:
    COLOR_DEFAULT = ""
    COLOR_DESCRIPTION = ""
    COLOR_VALUE = ""
    COLOR_WARNING = ""


def print_value(description, value, extra_line=False):
    sep = "\n\t" if extra_line else " "
    print(
        f"{COLOR_DESCRIPTION}{description}{COLOR_DEFAULT}:{sep}"
        f"“{COLOR_VALUE}{value}{COLOR_DEFAULT}”",
        file=sys.stderr,
    )


def print_optional_value(description, value, *args, **kwargs):
    if value:
        print_value(description, value, *args, **kwargs)


def print_list(description, value):
    print_value(description, list(value), extra_line=True)


def print_multiline_list(description, values):
    print(f"{COLOR_DESCRIPTION}{description}{COLOR_DEFAULT}:", file=sys.stderr)
    for value in values:
        print(f"\t“{COLOR_VALUE}{value}{COLOR_DEFAULT}”", file=sys.stderr)


def print_multiline_text(description, value):
    if value is None:
        print(
            f"{COLOR_DESCRIPTION}{description}{COLOR_DEFAULT}: "
            f"{COLOR_WARNING}None{COLOR_DEFAULT}",
            file=sys.stderr,
        )
    elif not value.strip():
        print(
            f"{COLOR_DESCRIPTION}{description}{COLOR_DEFAULT}: "
            f"{COLOR_WARNING}“{value}”{COLOR_DEFAULT}",
            file=sys.stderr,
        )
    else:
        print(
            f"{COLOR_DESCRIPTION}{description}{COLOR_DEFAULT}:",
            file=sys.stderr,
        )
        for line in value.splitlines():
            print(f"\t{COLOR_VALUE}{line}{COLOR_DEFAULT}", file=sys.stderr)


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


def print_tool_info(tool, tool_locator):
    """Print standard info from tool-info module"""
    print_multiline_text("Documentation of tool module", inspect.getdoc(tool))

    print_value("Name of tool", tool.name())
    print_optional_value("Webpage", tool.project_url())

    executable = tool.executable(tool_locator)
    print_value("Executable", executable)
    if not os.path.isabs(executable):
        print_value("Executable (absolute path)", os.path.abspath(executable))
    else:
        logging.warning(
            "Path to executable is absolute, this might be problematic "
            "in scenarios where runs are distributed to other machines."
        )
    if os.path.isdir(executable):
        logging.warning("Designated executable is a directory.")
    elif not os.path.isfile(executable):
        logging.warning("Designated executable does not exist.")
    elif not os.access(executable, os.X_OK):
        logging.warning("Designated executable is not marked as executable.")
    if tool_locator.tool_directory:
        abs_directory = os.path.abspath(tool_locator.tool_directory)
        abs_executable = os.path.abspath(executable)
        if not os.path.commonpath((abs_directory, abs_executable)) == abs_directory:
            logging.warning("Executable is not within specified tool directory.")

    version = None
    try:
        version = tool.version(executable)
    except BaseException:
        logging.warning("Determining version failed:", exc_info=1)
    if version:
        print_value("Version", tool.version(executable))
        if version[0] < "0" or version[0] > "9":
            logging.warning(
                "Version does not start with a digit, please remove any prefixes like the tool name."
            )
        print_optional_value("URL for version", tool.url_for_version(version))

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
    keep_environment = environment.pop("keepEnv", None)
    if keep_environment is not None:
        print_list(
            "Run will start with fresh environment, except for these variables",
            keep_environment.keys(),
        )
    new_environment = environment.pop("newEnv", {})
    if new_environment:
        print_multiline_list(
            "Additional environment variables",
            (f"{variable}={value}" for (variable, value) in new_environment.items()),
        )
    append_environment = environment.pop("additionalEnv", {})
    if append_environment:
        print_multiline_list(
            "Appended environment variables",
            (
                f"{variable}=${{{variable}}}{value}"
                for (variable, value) in append_environment.items()
            ),
        )
    if environment:
        logging.warning(
            "Tool module returned invalid entries for environment, these will be ignored: “%s”",
            environment,
        )

    return executable


def print_standard_task_cmdlines(tool, executable):
    """Print command lines resulting from a few different dummy tasks"""
    no_limits = CURRENT_BASETOOL.ResourceLimits()

    with log_if_unsupported(
        "tasks without options, property file, and resource limits"
    ):
        cmdline = model.cmdline_for_run(
            tool, executable, [], ["INPUT.FILE"], None, None, None, no_limits
        )
        print_list("Minimal command line", cmdline)
        if "INPUT.FILE" not in " ".join(cmdline):
            logging.warning("Tool module ignores input file.")

    with log_if_unsupported("tasks with command-line options"):
        cmdline = model.cmdline_for_run(
            tool,
            executable,
            ["-SOME_OPTION"],
            ["INPUT.FILE"],
            None,
            None,
            None,
            no_limits,
        )
        print_list("Command line with parameter", cmdline)
        if "-SOME_OPTION" not in cmdline:
            logging.warning("Tool module ignores command-line options.")

    with log_if_unsupported("tasks with property file"):
        cmdline = model.cmdline_for_run(
            tool, executable, [], ["INPUT.FILE"], None, "PROPERTY.PRP", None, no_limits
        )
        print_list("Command line with property file", cmdline)
        if "PROPERTY.PRP" not in " ".join(cmdline):
            logging.warning("Tool module ignores property file.")

    with log_if_unsupported("tasks with multiple input files"):
        cmdline = model.cmdline_for_run(
            tool,
            executable,
            [],
            ["INPUT1.FILE", "INPUT2.FILE"],
            None,
            None,
            None,
            no_limits,
        )
        print_list("Command line with multiple input files", cmdline)
        if "INPUT1.FILE" in " ".join(cmdline) and "INPUT2.FILE" not in " ".join(
            cmdline
        ):
            logging.warning("Tool module ignores all but first input file.")

    with log_if_unsupported("tasks with CPU-time limit"):
        cmdline = model.cmdline_for_run(
            tool,
            executable,
            [],
            ["INPUT.FILE"],
            None,
            None,
            None,
            CURRENT_BASETOOL.ResourceLimits(cputime=123),
        )
        print_list("Command line CPU-time limit", cmdline)

    with log_if_unsupported("SV-Benchmarks task"):
        cmdline = model.cmdline_for_run(
            tool,
            executable,
            [],
            ["INPUT.FILE"],
            None,
            "PROPERTY.PRP",
            {"language": "C", "data_model": "ILP32"},
            CURRENT_BASETOOL.ResourceLimits(cputime=900, cputime_hard=1000),
        )
        print_list("Command line SV-Benchmarks task", cmdline)

    # This will return the last command line that did not trigger an exception
    return cmdline


def print_task_cmdline(tool, executable, task_def_file):
    """Print command lines resulting for tasks from the given task-definition file."""
    no_limits = CURRENT_BASETOOL.ResourceLimits()

    task = yaml.safe_load(task_def_file)
    input_files = model.handle_files_from_task_definition(
        task.get("input_files"), task_def_file.name
    )

    def print_cmdline(task_description, property_file):
        task_description = task_def_file.name + " " + task_description
        with log_if_unsupported("task from " + task_description):
            cmdline = model.cmdline_for_run(
                tool,
                executable,
                [],
                input_files,
                task_def_file.name,
                property_file,
                copy.deepcopy(task.get("options")),
                no_limits,
            )
            print_list("Command line for " + task_description, cmdline)

    print_cmdline("without property file", None)

    for prop in task.get("properties", []):
        property_file = prop.get("property_file")
        if property_file:
            property_file = util.expand_filename_pattern(
                property_file, os.path.dirname(task_def_file.name)
            )[0]
            print_cmdline("with property " + property_file, property_file)


def analyze_tool_output(tool, file, dummy_cmdline):
    try:
        output = file.readlines()
    except (OSError, UnicodeDecodeError) as e:
        logging.warning("Cannot read tool output from “%s”: %s", file.name, e)
        return

    try:
        exit_code = util.ProcessExitCode.create(value=0)
        output = CURRENT_BASETOOL.RunOutput(output)
        run = CURRENT_BASETOOL.Run(dummy_cmdline, exit_code, output, None)
        result = tool.determine_result(run)
        print_value(
            "Result of analyzing tool output in “" + file.name + "”",
            result,
            extra_line=True,
        )
    except BaseException:
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
        "--tool-directory",
        help="look for tool in given directory",
        metavar="DIR",
        type=benchexec.util.non_empty_str,
    )
    parser.add_argument(
        "--tool-output",
        metavar="OUTPUT_FILE",
        nargs="+",
        type=argparse.FileType("r"),
        help="optional names of text files with example outputs of a tool run",
    )
    parser.add_argument(
        "--task-definition",
        metavar="TASK_DEF_FILE",
        nargs="+",
        default=[],
        type=argparse.FileType("r"),
        help="optional name of task-definition files to test the module with",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug output",
    )
    benchexec.benchexec.add_container_args(parser)

    options = parser.parse_args(argv[1:])
    logging.basicConfig(
        format=COLOR_WARNING + "%(levelname)s: %(message)s" + COLOR_DEFAULT,
        level=logging.DEBUG if options.debug else logging.INFO,
    )
    tool_locator = tooladapter.create_tool_locator(options)

    print_value("Name of tool module", options.tool)
    try:
        tool_module, tool = model.load_tool_info(options.tool, options)
        try:
            print_value("Full name of tool module", tool_module)
            executable = print_tool_info(tool, tool_locator)
            dummy_cmdline = print_standard_task_cmdlines(tool, executable)
            for task_def_file in options.task_definition:
                print_task_cmdline(tool, executable, task_def_file)

            if options.tool_output:
                for file in options.tool_output:
                    analyze_tool_output(tool, file, dummy_cmdline)
        finally:
            tool.close()

    except benchexec.BenchExecException as e:
        sys.exit("Error: " + str(e))


if __name__ == "__main__":
    main()
