# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """
    BenchExec tool-info for Sikraken
    """

    def name(self):
        return "Sikraken"

    def project_url(self):
        return "https://github.com/echancrure/Sikraken"

    def executable(self, tool_locator):
        return tool_locator.find_executable("sikraken.sh", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable, "-v")

    def _coverage_options(self, property_file):
        try:
            with open(property_file) as f:
                prp = f.read()
        except OSError as e:
            raise benchexec.tools.template.UnsupportedFeatureException(
                f"Cannot read property file {property_file}: {e.strerror}"
            ) from e
        match = re.search(r"@CALL\(\s*([A-Za-z_]\w*)\s*\)", prp)
        if match:
            options = ["--coverage", "reach"]
            if match.group(1) != "reach_error":
                options += ["--reach", match.group(1)]
            return options
        if "@DECISIONEDGE" in prp:
            return ["--coverage", "branch"]
        raise benchexec.tools.template.UnsupportedFeatureException(
            f"Sikraken does not support property file {property_file}"
        )

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "-m32", LP64: "-m64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]
        # --coverage/--reach are only understood from Sikraken 2.0.0 on
        version = tuple(int(p) for p in re.findall(r"\d+", self.version(executable)))
        if task.property_file and version >= (2, 0, 0):
            options += self._coverage_options(task.property_file)
        return [executable] + options + [task.single_input_file]
