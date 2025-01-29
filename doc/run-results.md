<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Run Results

Both `benchexec` and `runexec` report result values for every executed run.
`benchexec` does so in the result file as
`<column title="<key>" value="<value>"/>` tags inside `<run>` tags
(cf. [document-type definition](result.dtd)),
whereas `runexec` prints them as `<key>=<value>` pairs to stdout
and `RunExecutor.execute_run()` returns these in a dictionary.

General rules:
- Any result value may be missing if the value is not present.
- Other possible result keys may be added at any time in the future.
- Numeric values are reported with the standard [BenchExec units](INDEX.md#units).
- Values are reported as measured without rounding,
  thus the number of digits does not indicate significance.
  This is to prevent the proliferation of rounding errors when using the data in calculations.

The meanings of the current possible result values are as follows:

- **terminationreason**: String with reason for abnormal termination of run.
  If missing, the run terminated itself without intervention from BenchExec.
  Possible values are currently:
  - `cputime`: CPU-time limit was violated and run was killed.
     Note that if the tool terminates by itself after the time limit but before BenchExec had a chance to kill it,
     this value will not be set as `terminationreason` indicates only whether the run was forcefully killed,
     not whether a limit was exceeded.
  - `cputime-soft`: Soft CPU-time limit was violated and run stopped itself afterwards.
  - `walltime`: Wall-time limit was violated and run was killed.
  - `memory`: Memory limit was violated and run was killed.
  - `files-count`: Run created too many files inside container and was killed.
  - `files-size`: Run occupied too much disk space inside container and was killed.
  - `killed`: Run execution was interrupted with Ctrl+C or call to `RunExecutor.stop()`
     and run was killed.
  - `failed`: Run could not be started (e.g., because tool executable was not found).
     No other result values contain meaningful data in this case.

  Other possible values may be added in the future,
  but successful runs will never have this value set.
- **cputime**: CPU time of run in seconds, as decimal number with suffix "s".
- **cputime-cpu`<n>`**: CPU time of run which was used on CPU core *n* in seconds,
    as decimal number with suffix "s".
- **walltime**: Wall time of run in seconds, as decimal number with suffix "s" ([more information](resources.md#wall-time)).
- **starttime**: The time the run was started.
- **memory** / **memUsage** (before BenchExec 2.0):
    Peak memory consumption of run in bytes, as integer with suffix "B" ([more information](resources.md#memory)).
- **blkio-read**, **blkio-write**: Number of bytes read and written to block devices, as decimal number with suffix "B" ([more information](resources.md#disk-space-and-io)).
    This depends on the `blkio` cgroup and is still experimental.
    The value might not accurately represent disk I/O due to caches or if virtual block devices such as LVM, RAID, RAM disks etc. are used.
- **cpuenergy-pkg`<n>`**: Energy consumption of the CPU ([more information](resources.md#energy)).
    This is still experimental.
- **pressure-`*`-some**: Number of seconds (as decimal with suffix "s") that at least some process had to wait for the respective resource, e.g., the CPU becoming available ([more information](https://docs.kernel.org/accounting/psi.html)).
- **returnvalue**: The return value of the process (between 0 and 255).
    Not present if process was killed.
- **exitsignal**: The signal with which the process was killed (if any).


In the result dictionary of a call to `RunExecutor.execute_run()`,
integer values are stored as `int`,
decimal numbers as an instance of some arithmetic Python type,
the start time as an ["aware" `datetime.datetime`](https://docs.python.org/3/library/datetime.html#aware-and-naive-objects) instance in local time,
and other values as strings.
More complex values are represented as a `dict`.
Instead of `returnvalue` and `exitsignal`,
an instance of `benchexec.util.ProcessExitCode` is returned in a field named `exitcode`.

In the XML produced by `benchexec`,
the start time is stored as local time with time zone in ISO 8601 format.


### Additional Results of benchexec
`benchexec` additionally uses the following result values:
- **category**: One of the values of the `CATEGORY_*` constants of the
    [`result` module](https://github.com/sosy-lab/benchexec/blob/main/benchexec/result.py)
    that determines how the run result should be interpreted
    (cf. the documentation of these constants).
    Note that the distinction between `CATEGORY_UNKNOWN` and `CATEGORY_ERROR`
    also depends on the tool-info module (and thus may differ between tools).
    `CATEGORY_MISSING` is used in cases where was no expected result for the given task
    (e.g., because no property was specified, or the expected result is unknown).
    In cases where the tool returns only `done` instead of `true` or `false`
    the category is also `CATEGORY_MISSING`.
- **status**: The result of the run, as determined by BenchExec
    and interpreted by the tool-info module.
    This can be one of the `RESULT_*` constants of the
    [`result` module](https://github.com/sosy-lab/benchexec/blob/main/benchexec/result.py),
    or an arbitrary string.
    If the `category` is `CATEGORY_CORRECT`, `CATEGORY_WRONG`,
    `CATEGORY_UNKNOWN`, or `CATEGORY_MISSING`,
    the `status` contains the answer of the tool.
    If the `category` is `CATEGORY_ERROR`, the `status` is a human-readable string with more information
    about which kind of error occurred,
    e.g., whether the tool terminated with an error code, the time limit was hit, etc.

Furthermore, `benchexec` allows the user to specify arbitrary additional result values
by defining them with a `<column>` tag in the benchmark-definition file.
The values of these will be extracted from the tool output by the tool-info module
and stored together with the result values that are determined by BenchExec.
The content of these values can be arbitrary, but in most cases will be either a raw number,
a number with a unit suffix, or plain text.

The `<column>` tags may have an attribute `hidden` set to `true`.
This indicates values that are typically not primarily interesting for users,
and tools for displaying such results may choose to hide such columns by default.

`benchexec` also reports the CPU time and wall time that was used for executing all runs
(as measured by the operating system, not as aggregation of the individual values).
These values are reported in the same way as for single runs,
but with `<column>` tags directly inside the `<result>` root tag.
Note that this CPU-time value is not measured with cgroups currently and may be incomplete.
The wall-time value can be used for example to calculate the speedup of executing runs in parallel
(this value is simply the time difference between the end and the start of executing all runs).
