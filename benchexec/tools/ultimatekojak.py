"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2015  Daniel Dietsch
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

from . import ultimate

class Tool(ultimate.UltimateTool):

    REQUIRED_PATHS = [
                  "artifacts.xml",
                  "configuration",
                  "features",
                  "Kojak.xml",
                  "p2",
                  "plugins",
                  "svcomp-DerefFreeMemtrack-32bit-Kojak_Bitvector.epf",
                  "svcomp-DerefFreeMemtrack-32bit-Kojak_Default.epf",
                  "svcomp-Overflow-64bit-Kojak_Default.epf",
                  "svcomp-Reach-32bit-Kojak_Bitvector.epf",
                  "svcomp-Reach-32bit-Kojak_Default.epf",
                  "svcomp-Reach-64bit-Kojak_Bitvector.epf",
                  "svcomp-Reach-64bit-Kojak_Default.epf",
                  "Ultimate",
                  "Ultimate.ini",
                  "Ultimate.py",
                  "z3"
                  ]

    def name(self):
        return 'ULTIMATE Kojak'
