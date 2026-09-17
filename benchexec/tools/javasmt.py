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
    https://github.com/sosy-lab/java-smt

    JavaSMT decides the satisfiability of a single SMT-LIB 2 formula, so tasks
    with more than one input file are not supported. If a memory limit is
    specified for BenchExec, it is passed to the JVM with the parameter -Xmx.

    The tool directory is the JavaSMT project directory. It needs to contain:
    - javasmt, the launcher script that assembles the classpath
    - the classes to run, either below bin/ or as a java-smt-<version>.jar
    - lib/java/core/ with the core JARs
    - lib/java/runtime-<solver>/ with the JARs of the individual solvers
    - lib/native/<architecture>/ with the JNI libraries of the native solvers
    """

    REQUIRED_PATHS = [
        "javasmt",
        "bin",
        "java-smt-*.jar",
        "lib/java/core",
        "lib/java/runtime-*",
        "lib/native",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("javasmt")

    def name(self):
        return "JavaSMT"

    def project_url(self):
        return "https://github.com/sosy-lab/java-smt"

    def version(self, executable):
        # The version is part of the name of the JAR that "ant jar" produces,
        # e.g. java-smt-5.0.1-1260-g7e5485a79.jar.
        jars = [
            jar
            for jar in glob.glob(
                os.path.join(os.path.dirname(executable), "java-smt-*.jar")
            )
            if not jar.endswith(("-sources.jar", "-javadoc.jar"))
        ]
        if len(jars) != 1:
            return ""
        return os.path.basename(jars[0])[len("java-smt-") : -len(".jar")]

    def program_files(self, executable):
        return self._program_files_from_executable(executable, self.REQUIRED_PATHS)

    def cmdline(self, executable, options, task, rlimits):
        heap = [f"-Xmx{rlimits.memory}"] if rlimits.memory else []
        return [executable, *heap, *options, task.single_input_file]

    def determine_result(self, run):
        # JavaSMT exits with code 1 after printing "unknown",
        # so the answer is checked before the exit code.
        for line in run.output:
            line = line.strip()
            if line == "sat":
                return result.RESULT_TRUE_PROP
            elif line == "unsat":
                return result.RESULT_FALSE_PROP
            elif line == "unknown":
                return result.RESULT_UNKNOWN

        # JavaSMT reports expected failures with a message on stderr (see JavaSMTMain).
        # Report the kind of failure, such that the reason is visible in the table.
        for line in run.output:
            line = line.strip()
            for message, reason in self._ERROR_REASONS.items():
                if message in line:
                    return f"ERROR ({reason})"

        # Unexpected failures, e.g., in a solver binding, terminate JavaSMT with an
        # uncaught Java exception. Report the exception class.
        for line in run.output:
            line = line.strip()
            if line.startswith("Exception in thread"):
                return f"ERROR ({self._exception_class(line)})"

        # An unspecific error lets BenchExec name the signal that killed the run,
        # such as "SEGMENTATION FAULT", or report the exit code of the tool.
        return result.RESULT_ERROR

    # Error messages of JavaSMTMain, mapped to the reason that is shown in the table.
    # The order matters: the more specific parsing messages come first.
    _ERROR_REASONS = {
        "does not support parsing SMT-LIB2 input": "no parser",
        "Could not parse SMT2 file": "parsing",
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
