# BenchExec: runexec
## Benchmarking a Single Run

BenchExec provides a program called `runexec` that can be used to
easily execute a single command while measuring its resource consumption,
similarly to the tool `time` but with more reliable time measurements
and with measurement of memory usage.
To use it, simply pass as parameters the command that should be executed
(adding `--` before the command will ensure that the arguments to the command
will not be misinterpreted as arguments to `runexec`):

    runexec -- <cmd> <arg> ...

This will start the command, write its output to the file `output.log`,
and print resource measurements to stdout. Example:

    $ runexec echo Test
    2015-03-06 12:54:01,707 - INFO - Starting command echo Test
    2015-03-06 12:54:01,708 - INFO - Writing output to output.log
    exitcode=0
    returnvalue=0
    walltime=0.0024175643920898438s
    cputime=0.001671s
    memory=131072

For further details on the output, cf. [Run Results](run-results.md).

Resource limits can be enabled with additional arguments to `runexec`,
e.g. for CPU time (`--timelimit`), wall time (`--walltimelimit`),
or memory consumption (`--memlimit`). If any of the limits is exceeded,
the started command is killed forcefully (including any child processes it started).
Additionally, a "soft" limit can be given for CPU time (needs to be smaller than the real limit).
If given, the tool is sent the `TERM` signal after the soft limit is reached,
which will allow it to shutdown gracefully
(e.g., including writing output files and generating statistics)
before it is killed forcefully when the real time limit is reached.
For more information on how resources are measured and limited,
please refer to the general documentation on [resource handling](resources.md).

`runexec` can also restrict the executed command to a set of specific CPU cores
with the parameters `--cores`,
and (on NUMA systems) to specific memory regions with `--memoryNodes`.
The IDs used for CPU cores and memory regions are the same as used by the kernel
and can be seen in the directories `/sys/devices/system/cpu` and `/sys/devices/system/node`.

Additional parameters allow to change the name of the output file and the working directory.
The full set of available parameters can be seen with `runexec -h`.
For explanation of the parameters for containers, please see [container mode](container.md).
For executing benchmarks under a different user account with the parameter `--user`,
please check the [respective documentation](separate-user.md).
Command-line parameters can additionally be read from a file
as [described for benchexec](benchexec.md#starting-benchexec).

## Integration into other Benchmarking Frameworks

BenchExec can be used inside other benchmarking frameworks
for the actual command execution and handling of the resource limits and measurements.
To do so, simply use the `runexec` command in your benchmarking framework
as a wrapper around the actual command, and pass the appropriate command-line flags
for resource limits and read the resource measurements from the output.
If you want to bundle BenchExec with your framework,
you only need to use the `.egg` file for BenchExec,
no external dependencies are required.
You can also execute `runexec` directly from the `.egg` file with the following command
(no separate start script or installation is necessary):

    PYTHONPATH=path/to/BenchExec.egg python3 -m benchexec.runexecutor ...

From within Python, BenchExec can be used to execute a command as in the following example:

    from benchexec.runexecutor import RunExecutor
    executor = RunExecutor()
    result = executor.execute_run(args=[<TOOL_CMD>], ...)

Further parameters for `execute_run` can be used to specify resource limits
(c.f. [runexecutor.py](../benchexec/runexecutor.py)).
The result is a dictionary with the same information about the run
that is printed to stdout by the `runexec` command-line tool (cf. [Run Results](run-results.md)).

## Python 2 Compatibility

While BenchExec in general requires at least Python 3.2,
`runexec` should also work with Python 2.7,
both when run as a stand-alone tool and when used as a Python module.
This is also true for the `benchexc.check_cgroups` command
that can be used to verify the [cgroups setup](INSTALL.md#setting-up-cgroups).