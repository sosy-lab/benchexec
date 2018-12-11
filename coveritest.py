# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2018  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import benchexec.result as result
import benchexec.tools.cpachecker as cpachecker


class Tool(cpachecker.Tool):
 
    def name(self):
        return "CoVeriTest-" +  super(Tool, self).name()



    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = super(Tool, self).determine_result(self, returncode, returnsignal, output, isTimeout)
        if not status or status == result.RESULT_UNKNOWN or status == result.RESULT_TRUE_PROP or status == 'TIMEOUT':
            return result.RESULT_DONE

        return status


