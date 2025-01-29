# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
Utilities for adapting older tool-info modules to the currently expected API.

This is an internal module for BenchExec and not to be used by tool-info modules.
"""

import inspect
from typing import cast, Union

from benchexec.tools.template import BaseTool, BaseTool2, ToolNotFoundException

import benchexec.model


CURRENT_BASETOOL = BaseTool2
"""Alias for the latest base-tool class in benchexec.tools.template"""


# We do not let Tool1To2 actually inherit from BaseTool2 because we do not want to
# inherit any default implementations, but we still declare it as a subclass.
@BaseTool2.register
class Tool1To2:
    """
    Adapter for making subclasses of BaseTool confirm to the API of BaseTool2
    """

    _FORWARDED_METHODS = [
        "program_files",
        "version",
        "name",
        "working_directory",
        "environment",
    ]

    def __init__(self, wrapped: BaseTool):
        self._wrapped = wrapped
        for method in Tool1To2._FORWARDED_METHODS:
            # This binds wrapped to the first argument of the method
            # such that when the method is called it can properly access its instance.
            assert not hasattr(self, method)
            setattr(self, method, getattr(wrapped, method))

        self.__doc__ = inspect.getdoc(wrapped)

    def executable(self, tool_locator):
        if tool_locator.tool_directory:
            raise ToolNotFoundException(
                f"Tool-info module for {self._wrapped.name()} "
                f"does not support parameter --tool-directory. "
                f"Instead, you can add the tool to PATH, "
                f"execute benchexec from the tool directory, "
                f"or upgrade the tool-info module."
            )

        assert tool_locator.use_path and tool_locator.use_current
        # This is the behavior that old tool-info modules are expected to have.
        try:
            return self._wrapped.executable()
        except SystemExit as e:
            raise ToolNotFoundException(str(e)) from e

    def cmdline(self, executable, options, task, rlimits):
        return self._wrapped.cmdline(
            executable,
            options,
            list(task.input_files_or_identifier),
            task.property_file,
            convert_resource_limits_to_dict(rlimits),
        )

    def determine_result(self, run):
        return self._wrapped.determine_result(
            run.exit_code.value or 0,
            run.exit_code.signal or 0,
            run.output._lines,
            run.was_timeout,
        )

    def get_value_from_output(self, output, identifier):
        return self._wrapped.get_value_from_output(output._lines, identifier)

    def project_url(self):
        return None

    def url_for_version(self, version):
        return None

    def close(self):
        pass


def adapt_to_current_version(tool: Union[BaseTool, BaseTool2]) -> CURRENT_BASETOOL:
    """
    Given an instance of a tool-info module's class, return an instance that conforms to
    the current API. Might be either the same or a different instance.
    """
    if isinstance(tool, BaseTool2):
        return tool
    elif isinstance(tool, BaseTool):
        return cast(BaseTool2, Tool1To2(tool))  # ptype does not support @register yet
    else:
        raise TypeError(
            f"{tool.__class__} is not a subclass of one of the expected base classes "
            f"in benchexec.tools.template"
        )


def create_tool_locator(config) -> CURRENT_BASETOOL.ToolLocator:
    """
    Create an instance of ToolLocator with the standard behavior based on the given
    command-line options.
    """
    if config.tool_directory:
        return CURRENT_BASETOOL.ToolLocator(tool_directory=config.tool_directory)
    else:
        return CURRENT_BASETOOL.ToolLocator(use_path=True, use_current=True)


def convert_resource_limits_to_dict(rlimits):
    """
    Convert an instance of ResourceLimits to the equivalent dict as used previously.
    """
    rlimits_dict = {}

    def copy_limit_if_present(field, key):
        value = getattr(rlimits, field)
        if value:
            rlimits_dict[key] = value

    if rlimits.cputime != rlimits.cputime_hard:
        # in old API, soft time limit only exists if different from time limit
        copy_limit_if_present("cputime", benchexec.model.SOFTTIMELIMIT)
    copy_limit_if_present("cputime_hard", benchexec.model.TIMELIMIT)
    copy_limit_if_present("walltime", benchexec.model.WALLTIMELIMIT)
    copy_limit_if_present("memory", benchexec.model.MEMLIMIT)
    copy_limit_if_present("cpu_cores", benchexec.model.CORELIMIT)

    return rlimits_dict
