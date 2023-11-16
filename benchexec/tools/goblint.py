# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result

import re
import logging


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Goblint.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("goblint")

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="Goblint version: ")

    def url_for_version(self, version):
        m = re.fullmatch(r"(heads|tags)/(.+)-(\d+)-g([0-9a-f]{7,})(-dirty)?", version)
        if m:
            return f"https://github.com/goblint/analyzer/commit/{m.group(4)}"

        m = re.fullmatch(r"([0-9.]+) ([0-9a-f]{40})", version)
        if m:
            return f"https://github.com/goblint/analyzer/commit/{m.group(2)}"

        return None

    def name(self):
        return "Goblint"

    def project_url(self):
        return "https://goblint.in.tum.de/"

    _DATA_MODELS = {"ILP32": "32bit", "LP64": "64bit"}

    def cmdline(self, executable, options, task, rlimits):
        additional_options = []

        if task.property_file:
            additional_options += ["--sets", "ana.specification", task.property_file]

        if task.options:
            data_model = task.options.get("data_model")
            if data_model:
                data_model_option = self._DATA_MODELS.get(data_model)
                if data_model_option:
                    additional_options += [
                        "--sets",
                        "exp.architecture",
                        data_model_option,
                    ]
                else:
                    raise benchexec.tools.template.UnsupportedFeatureException(
                        f"Unsupported data_model '{data_model}'"
                    )

        return [
            executable,
            *options,
            *additional_options,
            *task.input_files,
        ]

    def determine_result(self, run):
        status = None

        for line in run.output:
            if "Fatal error" in line:
                if "Assertion failed" in line:
                    return "ASSERTION"
                else:
                    m = re.search(
                        r"Fatal error: exception (Stack overflow|Out of memory|[A-Za-z._]+)",
                        line,
                    )
                    if m:
                        return f"EXCEPTION ({m.group(1)})"
                    else:
                        return "EXCEPTION"
            else:
                m = re.match(r"SV-COMP result: (.*)", line)
                if m:
                    status = m.group(1)

        if status:
            return status

        if run.exit_code.value != 0:
            return result.RESULT_ERROR
        else:
            return result.RESULT_UNKNOWN

    def get_value_from_output(self, output, identifier):
        regex = re.compile(identifier)
        for line in output:
            match = regex.search(line)
            if match and len(match.groups()) > 0:
                return match.group(1)
        logging.debug("Did not find a match with regex %s", identifier)
        return None
