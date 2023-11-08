# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2022 Marek Chalupa marek.chalupa@ista.ac.at
#
# SPDX-License-Identifier: Apache-2.0

import benchexec
import benchexec.result as result
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


def get_verdict(s: str):
    return s[17:].strip()


class Tool(benchexec.tools.template.BaseTool2):
    """
    Info object for the tool Bubaak.
    """

    REQUIRED_PATHS = ["."]

    def executable(self, tool_locator):
        return tool_locator.find_executable("bubaak")

    def version(self, executable):
        return self._version_from_tool(executable, arg="-version")

    def name(self):
        """The human-readable name of the tool."""
        return "Bubaak"

    def project_url(self):
        return "https://gitlab.com/mchalupa/bubaak"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += ["-prp", task.property_file]

        arch = get_data_model_from_task(task, {ILP32: "-32", LP64: "-64"})
        if arch is not None and arch not in options:
            options += [arch]

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        for line in run.output:
            if "SV-COMP verdict:" in line:
                return get_verdict(line)

        if run.exit_code.value != 0:
            return f"{result.RESULT_ERROR} (ret {run.exit_code.value})"
        if run.exit_code.signal != 0:
            return f"{result.RESULT_ERROR} (sig {run.exit_code.signal})"

        return result.RESULT_ERROR
