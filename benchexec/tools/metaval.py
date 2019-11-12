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

import argparse
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result
import os


class Tool(benchexec.tools.template.BaseTool):

    TOOL_TO_PATH_MAP = {"cpachecker": "CPAchecker", "esbmc": "esbmc"}
    REQUIRED_PATHS = list(TOOL_TO_PATH_MAP.values())

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
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--witness")
        parser.add_argument("--metaval")
        (knownargs, options) = parser.parse_known_args(options)
        self.verifierName = knownargs.metaval.lower()
        self.witnessName = knownargs.witness
        self.wrappedTool = __import__("benchexec.tools." + self.verifierName, fromlist=["Tool"]).Tool()

        if hasattr(self, "wrappedTool"):
            oldcwd = os.getcwd()
            os.chdir(os.path.join(oldcwd, self.TOOL_TO_PATH_MAP[self.verifierName]))
            wrappedOptions = self.wrappedTool.cmdline(
                self.wrappedTool.executable(),
                options,
                [os.path.relpath(os.path.join(oldcwd, "output/ARG.c"))],
                os.path.relpath(os.path.join(oldcwd, propertyfile)),
                rlimits,
            )
            os.chdir(oldcwd)
            return [
                executable,
                "--verifier",
                self.TOOL_TO_PATH_MAP[self.verifierName],
                "--witness",
                self.witnessName,
                *tasks,
                "--",
                *wrappedOptions,
            ]
        else:
            sys.exit("ERROR: Could not find wrapped tool")

    def version(self, executable):
        stdout = self._version_from_tool(executable, "--version")
        metavalVersion = stdout.splitlines()[0].strip()
        return metavalVersion
