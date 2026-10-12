# Derived from the BenchExec Deagle adapter.
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-License-Identifier: Apache-2.0
"""BenchExec adapter for the witness-enabled Chyra entrypoint."""

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """Tool info for Chyra's concurrent C verifier with YAML witness export."""

    REQUIRED_PATHS = [
        "chyra-verifier",
        "chyra",
        "graphml_correctness_to_yaml.py",
        "loop_create_filter.awk",
        "multi_create_loop_filter.awk",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("chyra-wrapper")

    def name(self):
        return "Chyra"

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def project_url(self):
        return "https://gitlab.com/Lapulatos/chyra"

    def cmdline(self, executable, options, task, rlimits) -> list[str]:
        if not task.property_file:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "Chyra requires a property file"
            )
        task_model = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        arguments = list(options)
        selected = {value for value in arguments if value in ("--32", "--64")}
        if len(selected) > 1:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "Chyra received conflicting --32 and --64 options"
            )
        option_model = next(iter(selected), None)
        if task_model and option_model and task_model != option_model:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "command-line model disagrees with task model"
            )
        model = task_model or option_model or "--32"
        arguments = [value for value in arguments if value not in ("--32", "--64")]
        return [
            executable,
            task.property_file,
            task.single_input_file,
            model,
        ] + arguments

    def determine_result(self, run):
        if run.was_timeout or run.exit_code.signal or run.exit_code.value != 0:
            return result.RESULT_UNKNOWN
        lines = [line.strip() for line in run.output if line.strip()]
        terminal = lines[-1] if lines else ""
        if terminal == "SUCCESSFUL":
            return result.RESULT_TRUE_PROP
        if terminal != "FAILED":
            return result.RESULT_UNKNOWN
        failures = [line for line in lines if "FAILURE" in line]
        categories = set()
        for line in failures:
            if "nodatarace.assertion." in line:
                categories.add(result.RESULT_FALSE_DATARACE)
            if "overflow." in line:
                categories.add(result.RESULT_FALSE_OVERFLOW)
            if "memory-leak." in line:
                categories.add(result.RESULT_FALSE_MEMTRACK)
            if "pointer_dereference." in line or "alloc.assertion." in line:
                categories.add(result.RESULT_FALSE_DEREF)
            if any(
                value in line
                for value in ("double free", "free argument", "free called for")
            ):
                categories.add(result.RESULT_FALSE_FREE)
        # Multiple memory-safety obligations may fail in one trace. Keep the
        # real sub-property without matching benchmark names or labels.
        for category in (
            result.RESULT_FALSE_FREE,
            result.RESULT_FALSE_DEREF,
            result.RESULT_FALSE_MEMTRACK,
            result.RESULT_FALSE_DATARACE,
            result.RESULT_FALSE_OVERFLOW,
        ):
            if category in categories:
                return category
        return result.RESULT_FALSE_REACH
