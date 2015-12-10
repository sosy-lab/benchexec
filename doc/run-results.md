# BenchExec: Run Results

Both `benchexec` and `runexec` report result values for every executed run.
`benchexec` does so in the result file as
`<column title="<key>" value="<value>"/>` tags inside `<run>` tags
(cf. [document-type definition](result.dtd)),
whereas `runexec` prints them as `<key>=<value>` pairs to stdout
and `RunExecutor.execute_run()` returns these in a dictionary.

General rules:
- Any result value may be missing if the value is not present.
- We may add other possible result keys in the future.
- Seconds are used as unit for time values, and bytes are used for memory values.

The meanings of the current possible result values are as follows:

- **terminationreason**: String with reason for abnormal termination of run.
  If missing, the run terminated itself without intervention from BenchExec.
  Possible values are currently:
  - `cputime`: CPU-time limit was violated and run was killed.
  - `cputime-soft`: Soft CPU-time limit was violated and run stopped itself afterwards.
  - `walltime`: Wall-time limit was violated and run was killed.
  - `killed`: Run execution was interrupted with Ctrl+C or call to `RunExecutor.stop()`
     and run was killed.
  - `failed`: Run could not be started (e.g., because tool executable was not found).

  We may add other possible values in the future.
- **cputime**: CPU time of run in seconds, as decimal number with suffix "s"
- **cputime-cpu`<n>`**: CPU time of run which was used on CPU core *n* in seconds,
    as decimal number with suffix "s".
- **walltime**: Wall time of run in seconds, as decimal number with suffix "s"
- **memory** (from `runexec`) / **memUsage** (from `benchexec`):
    Peak memory consumption of run in bytes.
- **exitcode**: A number indicating how the process exited,
    as returned by the Python function [`os.wait`](https://docs.python.org/3/library/os.html#os.wait).
    It is recommended to use `returnvalue` and `exitsignal` instead (see below).

### Additional Results of runexec
`runexec` additionally uses the following result values:
- **returnvalue**: The return value of the process (between 0 and 255).
    Not present if process was killed.
- **exitsignal**: The signal with which the process was killed (if any).

### Additional Results of benchexec
`benchexec` additionally uses the following result values:
- **category**: One of the values of the `CATEGORY_*` constants of the
    [`result` module](https://github.com/sosy-lab/benchexec/blob/master/benchexec/result.py)
    that determines how the run result should be interpreted
    (cf. the documentation of these constants).
    Note that the distinction between `CATEGORY_UNKNOWN` and `CATEGORY_ERROR`
    is made by the tool-info module and thus may depend on the tool.
- **status**: The result of the run, as determined by BenchExec
    and interpreted by the tool-info module.
    This can be one of the `RESULT_*` constants of the
    [`result` module](https://github.com/sosy-lab/benchexec/blob/master/benchexec/result.py),
    or an arbitrary string.
    If the result is correct or wrong according to the `category` value,
    the `status` contains the answer of the tool.
    If the result is an error, the `status` is a human-readable string with more information
    about which kind of error occurred,
    e.g., whether the tool terminated with an error code, the time limit was hit etc.

Furthermore, `benchexec` allows the user to specify arbitrary additional result values
by defining them with a `<column>` tag in the benchmark-definition file.
The values of these will be extracted from the tool output by the tool-info module
and stored together with the result values that are determined by BenchExec.

If `benchexec` is interrupted during the execution,
result values may also be the empty string instead of missing completely
for runs that were not yet executed.

`benchexec` also reports the CPU time and wall time that was used for executing all runs
(as measured by the operating system, not as aggregation of the individual values).
These values are reported in the same way as for single runs,
but with `<column>` tags directly inside the `<rundefinition>` root tag.
Note that this CPU-time value is not measured with cgroups currently and may be incomplete.
The wall-time value can be used for example to calculate the speedup of executing runs in parallel
(this value is simply the time difference between the end and the start of executing all runs).
