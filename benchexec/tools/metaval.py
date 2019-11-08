"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2019  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result
import os


class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = ["CPAchecker", "esbmc"]
    TOOL_TO_PATH_MAP = {"cpachecker": ["CPAchecker"], "esbmc": ["esbmc"]}

    def executable(self):
        return util.find_executable("metaval.sh")

    def name(self):
        return "metaval"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if not hasattr(self, "wrappedTool"):
            return "METAVAL ERROR"
        return self.wrappedTool.determine_result(
            returncode, returnsignal, output, isTimeout
        )

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        verifierOption = options.index("--metaval")
        self.verifierName = options[verifierOption + 1].lower()
        del options[verifierOption : verifierOption + 2]
        witnessOption = options.index("--witness")
        self.witnessName = options[witnessOption + 1]
        del options[witnessOption : witnessOption + 2]
        if self.verifierName == "cpachecker":
            import benchexec.tools.cpachecker as cpachecker

            self.wrappedTool = cpachecker.Tool()
        elif self.verifierName == "esbmc":
            import benchexec.tools.esbmc as esbmc

            self.wrappedTool = esbmc.Tool()

        if hasattr(self, "wrappedTool"):
            os.environ["PATH"] += os.pathsep + os.path.join(
                os.curdir, *self.TOOL_TO_PATH_MAP[self.verifierName]
            )
            return (
                [executable]
                + ["--witness"]
                + [self.witnessName]
                + tasks
                + ["--"]
                + self.wrappedTool.cmdline(
                    self.wrappedTool.executable(),
                    options,
                    ["output/ARG.c",],
                    propertyfile,
                    rlimits,
                )
            )
        else:
            sys.exit("ERROR: Could not find wrapped tool")

    def version(self, executable):
        stdout = self._version_from_tool(executable, "--version")
        metavalVersion = next((l.strip() for l in stdout.splitlines())).split()[2]
        return metavalVersion
