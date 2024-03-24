<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: API

From within Python, BenchExec can be used to execute a command as in the following example:

```python
from benchexec.runexecutor import RunExecutor
executor = RunExecutor()
result = executor.execute_run(args=[<TOOL_CMD>], ...)
```

Further parameters for `execute_run` can be used to specify resource limits
(c.f. [runexecutor.py](../benchexec/runexecutor.py)).
The result is a dictionary with the same information about the run
that is printed to stdout by the `runexec` command-line tool (cf. [Run Results](run-results.md)).

If `RunExecutor` is used on the main thread,
caution must be taken to avoid `KeyboardInterrupt`, e.g., like this:

```python
import signal
from benchexec.runexecutor import RunExecutor
executor = RunExecutor()

def stop_run(signum, frame):
  executor.stop()

signal.signal(signal.SIGINT, stop_run)

result = executor.execute_run(args=[<TOOL_CMD>], ...)
```
