# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class CSeqTool(benchexec.tools.template.BaseTool):
    """
    Abstract tool info for CSeq-based tools (http://users.ecs.soton.ac.uk/gp4/cseq/cseq.html).
    """

    def version(self, executable):
        output = self._version_from_tool(executable, arg="--version")
        first_line = output.splitlines()[0]
        return first_line.strip()

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.
        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            In most cases we we have only _one_ inputfile.
        @param propertyfile: contains a specification for the verifier.
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        """
        assert len(tasks) == 1, "only one inputfile supported"
        inputfile = ["--input", tasks[0]]
        spec = ["--spec", propertyfile] if propertyfile is not None else []
        return [executable] + options + spec + inputfile

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        status = result.RESULT_UNKNOWN
        if "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        else:
            status = result.RESULT_UNKNOWN
        return status
