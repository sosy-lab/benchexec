"""
    This module contains functions for miscellaneous utilities required by the pqos_wrapper CLI
"""

import argparse
import sys


def argument_parser(argv):
    """
        Create an argument parser for pqos_wrapper CLI and parse the given arguments.
            
            @argv: the command line arguments passed to the CLI
    """
    parser = argparse.ArgumentParser(
        description="Execute pqos library functions using command line"
    )
    parser.add_argument(
        "-I",
        "--interface",
        dest="interface",
        default="MSR",
        help="Initialise pqos library using the given interface",
    )
    return vars(parser.parse_args(argv))


def wrapper_handle_error(message, returncode, function, expected=0):
    """
        Raise error in the form of python dict and exit the CLI.

            @message: The error message to be printed.
            @returncode: The status code raised by the error.
            @function: The name of the function raising error.
            @expected: The expected return code from the function.
    """
    if returncode != expected:
        sys.exit(
            prepare_cmd_output(message, function, error=True, returncode=returncode)
        )


def prepare_cmd_output(message, function, error=False, returncode=0, **kwargs):
    """
        Prepare a cmd_output for given parameters in the form of a python dict.

            @message: The message to be printed on the CLI.
            @function: The name of the function whose output is being recorded.
            @error: Boolean value to check if output is an error message.
            @returncode: The value returned by the function.
    """
    cmd_output = {
        "function": function,
        "message": message,
        "returncode": returncode,
        "error": error,
        "function_output": kwargs,
    }
    return cmd_output
