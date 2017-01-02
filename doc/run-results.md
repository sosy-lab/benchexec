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
  - `cputime-soft`: Soft CPU-time limit was violated and run stopped itself afterwards.
  - `walltime`: Wall-time limit was violated and run was killed.
  - `memory`: Memory limit was violated and run was killed.
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
- **memory** (from `runexec`) / **memUsage** (from `benchexec`):
    Peak memory consumption of run in bytes ([more information](resources.md#memory)).
- **returnvalue**: The return value of the process (between 0 and 255).
    Not present if process was killed.
- **exitsignal**: The signal with which the process was killed (if any).
- **exitcode**: A number indicating how the process exited,
    as returned by the Python function [`os.wait`](https://docs.python.org/3/library/os.html#os.wait).
    (**Deprecated**, use `returnvalue` and `exitsignal` instead.)


In the result dictionary of a call to `RunExecutor.execute_run()`,
integer values are stored as `int`,
decimal numbers as an instance of some arithmetic Python type,
and other values as strings.


### Additional Results of benchexec
`benchexec` additionally uses the following result values:
- **category**: One of the values of the `CATEGORY_*` constants of the
    [`result` module](https://github.com/sosy-lab/benchexec/blob/master/benchexec/result.py)
    that determines how the run result should be interpreted
    (cf. the documentation of these constants).
    Note that the distinction between `CATEGORY_UNKNOWN` and `CATEGORY_ERROR`
    also depends on the tool-info module (and thus may differ between tools).
    `CATEGORY_MISSING` is used in cases where BenchExec could not determine the expected result
    for the given task (e.g., because no property was specified, or because the expected result
    is not encoded in the input file's name.
- **status**: The result of the run, as determined by BenchExec
    and interpreted by the tool-info module.
    This can be one of the `RESULT_*` constants of the
    [`result` module](https://github.com/sosy-lab/benchexec/blob/master/benchexec/result.py),
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

Because the value for memory usage is named `memUsage` in `benchexec` result files
only for backwards compatibility, we may change its name to `memory`
in a future version (e.g., version 2.0) of BenchExec.
Tools that read such files and want to be future-proof may use both names for value lookup.

The `<column>` tags may have an attribute `hidden` set to `true`.
This indicates values that are typically not primarily interesting for users,
and tools for displaying such results may choose to hide such columns by default.

If `benchexec` is interrupted during the execution,
result values may also be the empty string instead of missing completely
for runs that were not yet executed.
However, this is not guaranteed and may change in the future
such that the values would not be present at all in this case.

`benchexec` also reports the CPU time and wall time that was used for executing all runs
(as measured by the operating system, not as aggregation of the individual values).
These values are reported in the same way as for single runs,
but with `<column>` tags directly inside the `<rundefinition>` root tag.
Note that this CPU-time value is not measured with cgroups currently and may be incomplete.
The wall-time value can be used for example to calculate the speedup of executing runs in parallel
(this value is simply the time difference between the end and the start of executing all runs).
