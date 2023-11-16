# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import os
import re

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for CPAchecker, the Configurable Software-Verification Platform.

    Both binary and source distributions of CPAchecker are supported.
    If the source of CPAchecker is present, it is checked wether the compiled binaries
    are outdated and need to be regenerated.
    Additional statistics can be extracted from the output of CPAchecker
    and added to the result tables.
    For this reason, the parameter -stats is always added to the command line.
    Furthermore, if a CPU-time limit is specified for BenchExec,
    it is passed to CPAchecker using the parameter -timelimit.
    This allows for proper termination of CPAchecker and statistics output
    even in cases of a timeout.
    """

    REQUIRED_PATHS = [
        "lib/java/runtime",
        "lib/*.jar",
        "lib/native/x86_64-linux",
        "scripts",
        "cpachecker.jar",
        "config",
    ]

    def executable(self, tool_locator):
        executable = tool_locator.find_executable("cpa.sh", subdir="scripts")
        base_dir = os.path.join(os.path.dirname(executable), os.path.pardir)
        jar_file = os.path.join(base_dir, "cpachecker.jar")
        bin_dir = os.path.join(base_dir, "bin")
        src_dir = os.path.join(base_dir, "src")

        # If this is a source checkout of CPAchecker, we heuristically check that
        # sources are not newer than binaries (cpachecker.jar or files in bin/).
        if os.path.isdir(src_dir):
            src_mtime = self._find_newest_mtime(src_dir)

            if os.path.isfile(jar_file):
                if src_mtime > os.stat(jar_file).st_mtime:
                    sys.exit("CPAchecker JAR is not uptodate, run 'ant jar'!")

            elif os.path.isdir(bin_dir):
                if src_mtime > self._find_newest_mtime(bin_dir):
                    sys.exit("CPAchecker build is not uptodate, run 'ant'!")

        return executable

    def _find_newest_mtime(self, path):
        mtime = 0
        for _root, _dirs, files, rootfd in os.fwalk(path):
            for f in files:
                mtime = max(mtime, os.stat(f, dir_fd=rootfd).st_mtime)

        return mtime

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        version = self._version_from_tool(executable, "-help", line_prefix="CPAchecker")
        return version.split("(")[0].strip()

    def url_for_version(self, version):
        if ":" in version:
            # Revision from VerifierCloud WebClient like "trunk:44918"
            branch, revision = version.split(":", maxsplit=1)
            if branch != "trunk":
                branch = f"branches/{branch}"
            return f"https://svn.sosy-lab.org/trac/cpachecker/browser/CPAchecker/{branch}/?rev={revision}"

        elif re.fullmatch("[0-9.]+", version):
            # Release version like "2.2.1"
            return f"https://svn.sosy-lab.org/trac/cpachecker/browser/CPAchecker/tags/cpachecker-{version}/"

        elif re.fullmatch("[0-9.]+-svn [0-9]{1,5}", version):
            # Old development version like "1.7-svn 20000"
            # Could end in "M", but then has local changes and we do not want a link.
            version = version.rsplit(" ", maxsplit=1)[-1]
            return f"https://svn.sosy-lab.org/trac/cpachecker/browser/CPAchecker/trunk/?rev={version}"

        elif re.fullmatch("[0-9.]+-svn-[0-9]{5}", version):
            # Recent development version like "2.0-svn-30000"
            # Could end in "M", but then has local changes and we do not want a link.
            version = version.rsplit("-", maxsplit=1)[-1]
            return f"https://svn.sosy-lab.org/trac/cpachecker/browser/CPAchecker/trunk/?rev={version}"

        elif re.fullmatch("[0-9.]+-svn-[0-9a-f]{6,}", version):
            # Development version with git commit like "2.2.1-svn-9743f6eae7"
            # Could end in "+", but then has local changes and we do not want a link.
            version = version.rsplit("-", maxsplit=1)[-1]
            return f"https://gitlab.com/sosy-lab/software/cpachecker/-/tree/{version}"

        elif re.fullmatch("[0-9a-f]{40}", version):
            # Full git hash produced by VerifierCloud WebClient
            return f"https://gitlab.com/sosy-lab/software/cpachecker/-/tree/{version}"

        return None

    def name(self):
        return "CPAchecker"

    def project_url(self):
        return "https://cpachecker.sosy-lab.org/"

    def _get_additional_options(self, existing_options, task, rlimits):
        options = []
        if rlimits.cputime and "-timelimit" not in existing_options:
            options += ["-timelimit", f"{rlimits.cputime}s"]

        if "-stats" not in existing_options:
            options += ["-stats"]

        if task.property_file:
            options += ["-spec", task.property_file]

        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model:
                data_model_option = {"ILP32": "-32", "LP64": "-64"}.get(data_model)
                if data_model_option:
                    if data_model_option not in existing_options:
                        options += [data_model_option]
                else:
                    raise benchexec.tools.template.UnsupportedFeatureException(
                        f"Unsupported data_model '{data_model}' defined for task '{task}'"
                    )

        return options

    def cmdline(self, executable, options, task, rlimits):
        additional_options = self._get_additional_options(options, task, rlimits)
        return (
            [executable]
            + options
            + additional_options
            + list(task.input_files_or_identifier)
        )

    def determine_result(self, run):
        """
        @return: status of CPAchecker after executing a run
        """

        def isOutOfNativeMemory(line):
            return (
                "std::bad_alloc" in line  # C++ out of memory exception (MathSAT)
                or "Cannot allocate memory" in line
                or "Native memory allocation (malloc) failed to allocate" in line  # JNI
                or line.startswith("out of memory")  # CuDD
            )

        status = None

        for line in run.output:
            if "java.lang.OutOfMemoryError" in line:
                status = "OUT OF JAVA MEMORY"
            elif isOutOfNativeMemory(line):
                status = "OUT OF NATIVE MEMORY"
            elif (
                "There is insufficient memory for the Java Runtime Environment to continue."
                in line
                or "cannot allocate memory for thread-local data: ABORT" in line
            ):
                status = "OUT OF MEMORY"
            elif "SIGSEGV" in line:
                status = "SEGMENTATION FAULT"
            elif "java.lang.AssertionError" in line:
                status = "ASSERTION"
            elif (
                ("Exception:" in line or line.startswith("Exception in thread"))
                # ignore "cbmc error output: ... Minisat::OutOfMemoryException"
                and not line.startswith("cbmc")
            ):
                status = "EXCEPTION"
            elif "Could not reserve enough space for object heap" in line:
                status = "JAVA HEAP ERROR"
            elif line.startswith("Error: ") and not status:
                status = result.RESULT_ERROR
                if "Cannot parse witness" in line:
                    status += " (invalid witness file)"
                elif "Unsupported" in line:
                    if "recursion" in line:
                        status += " (recursion)"
                    elif "threads" in line:
                        status += " (threads)"
                elif "Parsing failed" in line:
                    status += " (parsing failed)"
                elif "Interpolation failed" in line:
                    status += " (interpolation failed)"
            elif line.startswith("Invalid configuration: ") and not status:
                if "Cannot parse witness" in line:
                    status = result.RESULT_ERROR
                    status += " (invalid witness file)"
            elif (
                line.startswith(
                    "For your information: CPAchecker is currently hanging at"
                )
                and not status
                and run.was_timeout
            ):
                status = result.RESULT_TIMEOUT

            elif line.startswith("Verification result: "):
                line = line[21:].strip()
                if line.startswith("TRUE"):
                    newStatus = result.RESULT_TRUE_PROP
                elif line.startswith("FALSE"):
                    newStatus = result.RESULT_FALSE_PROP
                    match = re.match(
                        r".* Property violation \(([a-zA-Z0-9_-]+)(:.*)?\) found by chosen configuration.*",
                        line,
                    )
                    if match:
                        newStatus += f"({match.group(1)})"
                else:
                    newStatus = result.RESULT_UNKNOWN

                if not status:
                    status = newStatus
                elif newStatus != result.RESULT_UNKNOWN and status != newStatus:
                    status = f"{status} ({newStatus})"
            elif line == "Finished." and not status:
                status = result.RESULT_DONE

        if (
            (not status or status == result.RESULT_UNKNOWN)
            and run.was_timeout
            and run.exit_code.value in [15, 143]
        ):
            # The JVM sets such an returncode if it receives signal 15 (143 is 15+128)
            status = result.RESULT_TIMEOUT

        if not status:
            status = result.RESULT_ERROR
        return status

    def get_value_from_output(self, output, identifier):
        # search for the text in output and get its value,
        # search the first line, that starts with the searched text
        # warn if there are more lines (multiple statistics from sequential analysis?)
        match = None
        for line in output:
            if line.lstrip().startswith(identifier):
                startPosition = line.find(":") + 1
                endPosition = line.find("(", startPosition)
                if endPosition == -1:
                    endPosition = len(line)
                if match is None:
                    match = line[startPosition:endPosition].strip()
                else:
                    logging.warning(
                        "skipping repeated match for identifier '%s': '%s'",
                        identifier,
                        line,
                    )
        return match
