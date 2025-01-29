# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Frama-C.
    """

    REQUIRED_PATHS = ["bin", "lib", "share"]

    def executable(self):
        return util.find_executable("frama-c", "bin/frama-c")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Frama-C"

    def project_url(self):
        return "https://frama-c.com/"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        # Always put task input files before first occurrence of '-then*' parameters
        # This will give task files to the first batch of operations,
        # and execute succeeding batches on the resulting frama-c 'projects'
        try:
            first_then = next(i for i, v in enumerate(options) if v.startswith("-then"))
            return [executable] + options[:first_then] + tasks + options[first_then:]
        except StopIteration:
            return [executable] + options + tasks
