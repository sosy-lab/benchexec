# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 CEA <https://www.frama-c.com>
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Frama-C.
    """

    REQUIRED_PATHS = ["bin", "lib", "share"]
    _TOOL_NAME = "frama-c"
    _WRAPPER_NAME = _TOOL_NAME + ".py"

    def executable(self, tool_locator):
        wrapper = tool_locator.find_executable(Tool._WRAPPER_NAME)
        if wrapper:
            # new version (from 2026): use sv-comp wrapper
            return wrapper
        # assume old version (pre-2026); return frama-c executable
        return tool_locator.find_executable("frama-c", subdir="bin/")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Frama-C"

    def project_url(self):
        return "https://frama-c.com/"

    def cmdline(self, executable, options, task, rlimits):
        has_wrapper = executable.endswith(".py")
        if has_wrapper:
            # new version (from 2026 on): assume sv-comp wrapper is being used
            cmd = [executable, "--program"] + list(task.input_files)
            if task.options is not None and "data_model" in task.options:
                cmd += ["--data_model", task.options.get("data_model")]
            if task.property_file:
                cmd += ["--property", task.property_file]
            return cmd + list(options)
        # old version (pre-2026)
        try:
            first_then = next(i for i, v in enumerate(options) if v.startswith("-then"))
            return (
                [executable]
                + options[:first_then]
                + list(task.input_files)
                + options[first_then:]
            )
        except StopIteration:
            return [executable] + options + list(task.input_files)

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        lastline = run.output[-1] or run.output[-2]  # last non-empty line
        if "RESULT" in lastline:
            # assume sv-comp wrapper (from 2026 on) was used
            if lastline.startswith("INFO\tRESULT\t"):
                return lastline.split("\t", maxsplit=3)[-1]
            if lastline.startswith("INFO:RESULT:"):
                return lastline.split(":", maxsplit=2)[-1]
            return result.RESULT_ERROR
        # assume old (pre-2026) version is used; determine_result did not exist then
        return result.RESULT_DONE
