# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from xml.etree import ElementTree

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for CBMC.
    It always adds --xml-ui to the command-line arguments for easier parsing of
    the output, unless a propertyfile is passed -- in which case running under
    SV-COMP conditions is assumed.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("cbmc")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "CBMC"

    def project_url(self):
        return "http://www.cprover.org/cbmc/"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyfile", task.property_file]
        elif "--xml-ui" not in options:
            options = options + ["--xml-ui"]

        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        self.options = options

        return [executable] + options + list(task.input_files_or_identifier)

    def parse_XML(self, output, exit_code, isTimeout):
        # an empty tag cannot be parsed into a tree
        def sanitizeXML(s):
            return s.replace("<>", "<emptyTag>").replace("</>", "</emptyTag>")

        try:
            tree = ElementTree.fromstringlist(list(map(sanitizeXML, output)))
            status = tree.findtext("cprover-status")

            if status is None:

                def isErrorMessage(msg):
                    return msg.get("type", None) == "ERROR"

                messages = list(filter(isErrorMessage, tree.getiterator("message")))
                if messages:
                    # for now, use only the first error message if there are several
                    msg = messages[0].findtext("text")
                    if msg == "Out of memory":
                        status = "OUT OF MEMORY"
                    elif msg == "SAT checker ran out of memory":
                        status = "OUT OF MEMORY"
                    elif msg:
                        status = f"ERROR ({msg})"
                    else:
                        status = "ERROR"
                else:
                    status = "INVALID OUTPUT"

            elif status == "FAILURE":
                assert exit_code.value == 10
                reason = tree.find("goto_trace").find("failure").findtext("reason")
                if not reason:
                    reason = tree.find("goto_trace").find("failure").get("reason")
                if "unwinding assertion" in reason:
                    status = result.RESULT_UNKNOWN
                else:
                    status = result.RESULT_FALSE_REACH

            elif status == "SUCCESS":
                assert exit_code.value == 0
                if "--unwinding-assertions" in self.options:
                    status = result.RESULT_TRUE_PROP
                else:
                    status = result.RESULT_UNKNOWN

        except Exception:
            if isTimeout:
                # in this case an exception is expected as the XML is invalid
                status = result.RESULT_TIMEOUT
            elif "Minisat::OutOfMemoryException" in output:
                status = "OUT OF MEMORY"
            else:
                status = "INVALID OUTPUT"
                logging.exception(
                    "Error parsing CBMC output for exit_code.value %d", exit_code.value
                )

        return status

    def determine_result(self, run):
        output = run.output

        if run.exit_code.value in [0, 10]:
            status = result.RESULT_ERROR
            if "--xml-ui" in self.options:
                status = self.parse_XML(output, run.exit_code, run.was_timeout)
            elif len(output) > 0:
                # SV-COMP mode
                result_str = output[-1].strip()

                if result_str == "TRUE":
                    status = result.RESULT_TRUE_PROP
                elif "FALSE" in result_str:
                    if result_str == "FALSE(valid-memtrack)":
                        status = result.RESULT_FALSE_MEMTRACK
                    elif result_str == "FALSE(valid-deref)":
                        status = result.RESULT_FALSE_DEREF
                    elif result_str == "FALSE(valid-free)":
                        status = result.RESULT_FALSE_FREE
                    elif result_str == "FALSE(no-overflow)":
                        status = result.RESULT_FALSE_OVERFLOW
                    elif result_str == "FALSE(valid-memcleanup)":
                        status = result.RESULT_FALSE_MEMCLEANUP
                    else:
                        status = result.RESULT_FALSE_REACH
                elif "UNKNOWN" in output:
                    status = result.RESULT_UNKNOWN

        elif run.exit_code.value == 64 and "Usage error!" in output:
            status = "INVALID ARGUMENTS"

        elif run.exit_code.value == 6 and "Out of memory" in output:
            status = "OUT OF MEMORY"

        elif run.exit_code.value == 6 and "SAT checker ran out of memory" in output:
            status = "OUT OF MEMORY"

        else:
            status = result.RESULT_ERROR

        return status
