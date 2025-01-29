# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.fizzer as fizzer


class Tool(fizzer.Tool):
    """
    Tool info for rizzer.
    """

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        This method always needs to be overriden, and typically just contains
        return "My Toolname"
        @return a non-empty string
        """
        return "Rizzer"

    def project_url(self):
        return "https://github.com/staticafi/sbt-fizzer/tree/rizzer"
