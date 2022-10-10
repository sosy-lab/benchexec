# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2022 Raphaël Monat
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result

import re, json, subprocess


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Mopsa.
    URL: https://gitlab.com/mopsa/mopsa-analyzer/
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("mopsa-sv-comp", subdir="bin/")

    def version(self, executable):
        # the provided utility will fail due to return code 2 in Mopsa
        process = subprocess.run(
            ["mopsa-c", "-format=json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        output = json.loads(process.stdout)
        return output["mopsa_dev_version"]

    def name(self):
        return "Mopsa"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, "--program", *task.input_files]
        if task.options is not None and "data_model" in task.options:
            cmd += ["--data_model", task.options.get("data_model")]
        if task.property_file:
            cmd += ["--property", task.property_file]
        return cmd 

    def determine_result(self, run):
        if run.was_timeout:
            return "TIMEOUT"
        r = run.output.text
        last = r.split("\n")
        if last[-1] != '': last = last[-1]
        else: last = last[-2]
        if last.startswith("true"): return result.RESULT_TRUE_PROP
        elif last.startswith("unknown"): return result.RESULT_UNKNOWN
        elif last.startswith("ERROR"): return result.RESULT_ERROR + last[len("ERROR"):]
        else: raise ValueError(last)
