# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from xml.etree import ElementTree

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for impara.
    It always adds --xml-ui to the command-line arguments for easier parsing of the output.
    """

    REQUIRED_PATHS = ["impara"]

    def executable(self):
        return util.find_executable("impara")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "impara"

    def project_url(self):
        return "https://github.com/bjowac/impara"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if "--xml-ui" not in options:
            options = options + ["--xml-ui"]

        self.options = options

        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        # an empty tag cannot be parsed into a tree
        def sanitizeXML(s):
            return s.replace("<>", "<emptyTag>").replace("</>", "</emptyTag>")

        if returnsignal == 0 and ((returncode == 0) or (returncode == 10)):
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
                        elif msg:
                            status = f"ERROR ({msg})"
                        else:
                            status = "ERROR"
                    else:
                        status = "INVALID OUTPUT"

                elif status == "FAILURE":
                    assert returncode == 10
                    reason = tree.find("goto_trace").find("failure").findtext("reason")
                    if not reason:
                        reason = tree.find("goto_trace").find("failure").get("reason")
                    if "unwinding assertion" in reason:
                        status = result.RESULT_UNKNOWN
                    else:
                        status = result.RESULT_FALSE_REACH

                elif status == "SUCCESS":
                    assert returncode == 0
                    if "--no-unwinding-assertions" in self.options:
                        status = result.RESULT_UNKNOWN
                    else:
                        status = result.RESULT_TRUE_PROP

            except Exception:
                if isTimeout:
                    # in this case an exception is expected as the XML is invalid
                    status = result.RESULT_TIMEOUT
                elif "Minisat::OutOfMemoryException" in output:
                    status = "OUT OF MEMORY"
                else:
                    status = "INVALID OUTPUT"
                    logging.exception(
                        "Error parsing impara output for returncode %d", returncode
                    )

        elif returncode == 64 and "Usage error!" in output:
            status = "INVALID ARGUMENTS"

        else:
            status = result.RESULT_ERROR

        return status
