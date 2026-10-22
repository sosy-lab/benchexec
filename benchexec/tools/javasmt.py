# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import glob
import os

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for JavaSMT, a unified interface for SMT solvers in Java.

    JavaSMT decides the satisfiability of a single SMT-LIB 2 formula, so tasks
    with more than one input file are not supported.

    The tool directory is the JavaSMT project directory. It needs to contain:
    - javasmt, the launcher script that assembles the classpath
    - java-smt-<version>.jar, the JAR of JavaSMT that "ant jar" produces
    - lib/java/core/ with the core JARs
    - lib/java/runtime-<solver>/ with the JARs of the individual solvers
    - lib/native/<architecture>-<os>/ with the JNI libraries of the native solvers
    """

    REQUIRED_PATHS = [
        "javasmt",
        "lib/java/core",
        "lib/java/runtime-*",
        "lib/native",
    ]

    def executable(self, tool_locator):
        executable = tool_locator.find_executable("javasmt")
        # Stop before the runs are started if it is unclear which JAR would be used.
        jars = self._jars(executable)
        if not jars:
            raise benchexec.tools.template.ToolNotFoundException(
                f"Found {executable}, but no JAR of JavaSMT next to it."
            )
        if len(jars) > 1:
            raise benchexec.tools.template.ToolNotFoundException(
                f"Found several JARs of JavaSMT next to {executable}: "
                f"{', '.join(jars)}. Keep only the JAR that should be benchmarked."
            )
        return executable

    @staticmethod
    def _jars(executable):
        """
        The names of the JARs of JavaSMT next to the launcher, without those that
        carry only the sources or the documentation.
        """
        return [
            os.path.basename(jar)
            for jar in glob.glob(
                os.path.join(os.path.dirname(executable), "java-smt-*.jar")
            )
            if not jar.endswith(("-sources.jar", "-javadoc.jar"))
        ]

    def name(self):
        return "JavaSMT"

    def project_url(self):
        return "https://github.com/sosy-lab/java-smt"

    def version(self, executable):
        # JavaSMT reads its version from the manifest of the JAR.
        return self._version_from_tool(executable, "--help", line_prefix="JavaSMT ")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS + self._jars(executable)
        )

    def cmdline(self, executable, options, task, rlimits):
        return [executable, *options, task.single_input_file]

    def determine_result(self, run):
        # JavaSMT exits with code 1 after printing "unknown",
        # so the answer is checked before the exit code.
        for line in run.output:
            if line == "sat":
                return result.RESULT_TRUE_PROP
            elif line == "unsat":
                return result.RESULT_FALSE_PROP
            elif line == "unknown":
                return result.RESULT_UNKNOWN

        # JavaSMT reports expected failures with a message on stderr (see JavaSMTMain).
        # Report the kind of failure, such that the reason is visible in the table.
        for line in run.output:
            for message, reason in self._ERROR_REASONS.items():
                if message in line:
                    return f"ERROR ({reason})"

        # Unexpected failures, e.g., in a solver binding, terminate JavaSMT with an
        # uncaught Java exception. Report the exception class.
        for line in run.output:
            if line.startswith("Exception in thread"):
                return f"ERROR ({self._exception_class(line)})"

        # An unspecific error lets BenchExec name the signal that killed the run,
        # such as "SEGMENTATION FAULT", or report the exit code of the tool.
        return result.RESULT_ERROR

    # Error messages of JavaSMTMain, mapped to the reason that is shown in the table.
    # The order matters: the more specific parsing messages come first.
    _ERROR_REASONS = {
        "does not support parsing SMT-LIB2 input": "no parser",
        "is not supported": "unsupported command",
        "Only one (check-sat)": "unsupported command",
        "only allowed as the last command": "unsupported command",
        "Could not parse SMT2 file": "parsing",
        "Unexpected input": "parsing",
        "contains no (check-sat) command": "no check-sat",
        "Could not read SMT2 file": "input file",
        "Invalid configuration": "configuration",
        "Could not process command line arguments": "arguments",
        "No SMT2 file given": "arguments",
    }

    @staticmethod
    def _exception_class(line):
        """
        Get the class of an uncaught Java exception from the line that reports it,
        e.g. "UnsupportedOperationException" for a line that starts with
        'Exception in thread "main" java.lang.UnsupportedOperationException:'.
        """
        qualified_name = line.split(":")[0].split()[-1]
        return qualified_name.rsplit(".", 1)[-1]
