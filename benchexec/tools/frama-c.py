# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 CEA <https://www.frama-c.com>
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result
from benchexec.tools.template import ToolNotFoundException


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Frama-C wrapper for SVCOMP.
    """

    REQUIRED_PATHS = ["bin", "lib", "share"]
    _TOOL_NAME = "frama-c"
    _WRAPPER_NAME = _TOOL_NAME + ".py"

    # has_wrapper indicates whether we are running a recent (>= 2026) frama-c
    # wrapper, or an old one (pre-2026).
    # It is set by function executable() to either True or False.
    # All other functions expect it to be set to something other than None.
    has_wrapper = None

    def executable(self, tool_locator):
        try:
            wrapper = tool_locator.find_executable(Tool._WRAPPER_NAME)
            # if new version (from 2026): use sv-comp wrapper
            self.has_wrapper = True
            return wrapper
        except ToolNotFoundException:
            # assume old version (pre-2026); return frama-c executable
            self.has_wrapper = False
            return tool_locator.find_executable("frama-c", subdir="bin/")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Frama-C"

    def project_url(self):
        return "https://frama-c.com/"

    def cmdline(self, executable, options, task, rlimits):
        if self.has_wrapper:
            # new version (from 2026 on): assume sv-comp wrapper is being used
            cmd = [executable, "--program"] + list(task.input_files)
            if task.options is not None and "data_model" in task.options:
                cmd += ["--data_model", task.options.get("data_model")]
            if task.property_file:
                cmd += ["--property", task.property_file]
            return cmd + list(options)
        # old version (pre-2026):
        # Always put task input files before first occurrence of '-then*' parameters
        # This will give task files to the first batch of operations,
        # and execute succeeding batches on the resulting frama-c 'projects'
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
        if self.has_wrapper:
            # assume sv-comp wrapper (from 2026 on) was used
            # get last non-empty line
            lastline = next(
                (line for line in reversed(run.output) if line.strip()), None
            )
            if lastline is None:
                return result.RESULT_ERROR + "(empty output)"
            if not lastline.startswith("frama-c-verdict:"):
                return result.RESULT_ERROR + "(no frama-c-verdict)"
            return lastline.split(":", maxsplit=1)[-1].strip()
        # assume old (pre-2026) version is used; determine_result did not exist then
        return result.RESULT_DONE
