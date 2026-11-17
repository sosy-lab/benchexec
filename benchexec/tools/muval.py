# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """Tool-info for MuVal"""

    # Relative to the archive's root: the tools (bin), MuVal's configurations,
    # the wrapper scripts, the shared libraries, and Frama-C's share directory
    REQUIRED_PATHS = ["bin", "config", "helpers", "lib", "share"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("solver", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "MuVal"

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def cmdline(self, executable, options, task, rlimits):
        """
        Compose command line for MuVal.

        Args:
            executable: Path to solver script
            options: Tool options from benchmark definition
            task: Task to verify (includes property file and input file)
            rlimits: Resource limits
        """
        cmd = [executable]

        # Add property file
        if task.property_file:
            cmd.append(f"--property={task.property_file}")

        # The task's data model (ILP32 or LP64), from its task definition
        data_model = task.options.get("data_model") if task.options else None
        if data_model:
            cmd.append(f"--data-model={data_model}")

        # A witness for every answer (witness.yml in the run's directory)
        cmd.append("--witness")

        # Add timeout if specified
        if rlimits.cputime:
            cmd.append(f"--timeout={int(rlimits.cputime)}")

        # Add additional options from benchmark definition
        cmd.extend(options)

        # Add input file
        cmd.append(task.single_input_file)

        return cmd

    # The answers FALSE(<property>) of helpers/solver_llvm2lts.sh, by property.
    FALSE_RESULTS = {
        "unreach-call": result.RESULT_FALSE_REACH,
        "termination": result.RESULT_FALSE_TERMINATION,
        "no-overflow": result.RESULT_FALSE_OVERFLOW,
        "valid-deref": result.RESULT_FALSE_DEREF,
        "valid-free": result.RESULT_FALSE_FREE,
        "valid-memtrack": result.RESULT_FALSE_MEMTRACK,
        # some memory-safety check failed, which one not known: scored as
        # unknown unless the task's expected result has no subproperty
        "valid-memsafety": result.RESULT_FALSE_PROP,
        "valid-memcleanup": result.RESULT_FALSE_MEMCLEANUP,
        "no-data-race": result.RESULT_FALSE_DATARACE,
    }

    def determine_result(self, run):
        """
        Parse tool output to determine verification result.

        Returns:
            BenchExec result status
        """
        if run.exit_code.value != 0:
            return result.RESULT_ERROR

        for line in run.output:
            line = line.strip()

            if line.startswith("FALSE(") and line.endswith(")"):
                return self.FALSE_RESULTS.get(
                    line[len("FALSE(") : -1], result.RESULT_ERROR
                )

            if line == "YES":
                return result.RESULT_TRUE_PROP
            elif line == "NO":
                return result.RESULT_FALSE_TERMINATION

            elif line == "TRUE":
                return result.RESULT_TRUE_PROP
            elif line == "FALSE":
                return result.RESULT_FALSE_REACH

            elif line == "UNKNOWN" or line == "MAYBE":
                # MAYBE is CoAR's "no answer" for LTS problems, and the
                # wrapper's answer when the frontend declines the input.
                return result.RESULT_UNKNOWN
            elif line == "TIMEOUT":
                return result.RESULT_TIMEOUT

        return result.RESULT_ERROR

    def project_url(self):
        return "https://github.com/hiroshi-unno/coar"
