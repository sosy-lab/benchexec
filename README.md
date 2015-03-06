# BenchExec
## A Framework for Reliable Benchmarking and Resource Measurement

[![Build Status](https://travis-ci.org/dbeyer/benchexec.svg?branch=master)](https://travis-ci.org/dbeyer/benchexec)

BenchExec provides three major features:
- execution of arbitrary commands with precise and reliable measurement
  and limitation of resource usage (e.g., CPU time and memory)
- an easy way to define benchmarks with specific tool configurations
  and resource limits,
  and automatically executing them on large sets of input files
- generation of interactive tables and plots for the results

Contrary to other benchmarking frameworks,
it is able to reliably measure and limit resource usage
of the benchmarked tool even if it spawns subprocesses.
In order to achieve this,
it uses the [cgroups feature](https://www.kernel.org/doc/Documentation/cgroups/cgroups.txt)
of the Linux kernel to correctly handle groups of processes.
BenchExec allows to measure CPU time, wall time, and memory usage of a tool,
and to specify limits for these resources.
It also allows to limit the CPU cores and (on NUMA systems) memory regions.
In addition to measuring resource usage,
BenchExec can verify that the result of the tool was as expected,
and extract further statistical data from the output.
Results from multiple runs can be combined into CSV and interactive HTML tables,
of which the latter provide scatter and quantile plots.

BenchExec is intended for benchmarking non-interactive tools on Linux systems.
It was originally developed for use with the software verification framework
[CPAchecker](http://cpachecker.sosy-lab.org).

BenchExec was successfully used for benchmarking in all four instances
of the [International Competition on Software Verification](http://sv-comp.sosy-lab.org)
with a wide variety of benchmarked tools and hundreds of thousands benchmark runs.

BenchExec is developed at the [Software Systems Lab](http://www.sosy-lab.org) at the [University of Passau](http://www.uni-passau.de).


### Links
- [BenchExec GitHub Repository](https://github.com/dbeyer/benchexec),
  use this for reporting [issues](https://github.com/dbeyer/benchexec/issues)
- [BenchExec at PyPI](https://pypi.python.org/pypi/BenchExec)


## Documentation

### Download and Installation
BenchExec requires at least Python 3.2.

To install BenchExec we recommend to use the Python package installer pip
(installable for example with `sudo apt-get install pip3` on Debian/Ubuntu).

To automatically download and install the latest stable version and its dependencies
from the [Python Packaging Index](https://pypi.python.org/pypi/BenchExec),
run this command:

    sudo pip3 install benchexec

You can also install BenchExec only for your user with

    pip3 install --user benchexec

In this case you probably need to add the directory where pip installs the commands to the PATH environment by adding the following line to your `~/.profile` file:

    export PATH=~/.local/bin:$PATH

Of course you can also install BenchExec in a virtualenv if you are familiar with Python tools.

To install the latest development version from the [GitHub repository](https://github.com/dbeyer/benchexec), run this command:

    pip3 install --user git+https://github.com/dbeyer/benchexec.git


### Setting up Cgroups
To execute benchmarks and reliably measure and limit their resource consumption,
BenchExec requires that the user which executes the benchmarks
can create and modify cgroups.

Any Linux kernel version of the last years is
acceptable, though there have been performance improvements for the memory
controller in version 3.3, and cgroups in general are still getting improved, thus,
using a recent kernel is a good idea.

The cgroup virtual file system is typically mounted at `/sys/fs/cgroup`.
If it is not, you can mount it with

    sudo mount -t cgroup cgroup /sys/fs/cgroup

To give all users on the system the ability to create their own cgroups,
you can use

    sudo chmod o+wt,g+w /sys/fs/cgroup/

Of course permissions can also be assigned in a more fine-grained way if necessary.

Alternatively, software such as `cgrulesengd` from
the [cgroup-bin](http://libcg.sourceforge.net/) package
can be used to setup the cgroups hierarchy.

If your machine has swap, cgroups should be configured to also track swap memory.
If the file `memory.memsw.usage_in_bytes` does not exist in the directory
where the cgroup file system is mounted, this needs to be enabled by setting
`swapaccount=1` on the command line of the kernel.
To do so, you typically need to edit your bootloader configuration
(under Ubuntu for example in `/etc/default/grub`, line `GRUB_CMDLINE_LINUX`),
update the bootloader (`sudo update-grub`), and reboot.

It may be that your Linux distribution already mounts the cgroup file system
and creates a cgroup hierarchy for you.
In this case you need to adjust the above commands appropriately.
To optimally use BenchExec,
the cgroup controllers `cpuacct`, `cpuset`, `freezer`, and `memory`
should be mounted and usable,
i.e., they should be listed in `/proc/self/cgroups` and the current user
should have at least the permission to create sub-cgroups of the current cgroup(s)
listed in this file for these controllers.


### Using runexec to Benchmark a Single Run

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

Resource limits can be enabled with additional arguments to `runexec`,
e.g. for CPU time (`--timelimit`), wall time (`--walltimelimit`),
or memory consumption (`--memlimit`). If any of the limits is exceeded,
the started command is killed forcefully (including any child processes it started).

`runexec` can also restrict the executed command to a set of specific CPU cores
with the parameters `--cores`,
and (on NUMA systems) to specific memory regions with `--memoryNodes`.
The IDs used for CPU cores and memory regions are the same as used by the kernel
and can be seen in the directories `/sys/devices/system/cpu` and `/sys/devices/system/node`.

Additional parameters allow to change the name of the output file and the working directory.
The full set of available parameters can be seen with `runexec -h`.


### Using benchexec to Benchmark a Collection of Runs

The program `benchexec` provides the possibility to easily benchmark
multiple executions of a tool in one go.

#### Input for benchexec
`benchexec` uses as input an XML file that defines the command(s) to execute,
the resource limits, and the input files for which the command should be run.
A complete definition of the input format can be found in the example file
[doc/benchmark.xml](doc/benchmark.xml).
A document-type definition with a formal specification of such files can be found in
[doc/benchmark.dtd](doc/benchmark.dtd).
Such benchmark-definition files consist of a root tag `<benchmark>`
that has attributes for the tool to use and the resource limits.
Nested `<rundefinition>` tags allow to specify multiple different configurations of the tool,
each of which is executed with the input files.
The input files are defined in nested `<inputfiles>` tags,
either with `<include>` tags (which directly specify patterns of input files)
or with `<includesfile>` tags (which specify text files with file-name patterns on each line).
Relative file names in these tags are interpreted as relative to the directory of the XML file. 
Command-line arguments for the tool are given with `<option>` tags,
which can appear directly inside the root tag (always effective),
inside a `<rundefinition>` tag (affective for this configuration),
or inside a `<inputfiles>` tag (affective only for this subset of files for all configurations).
Note that you need to use a separate `<option>` tag for each argument,
putting multiple arguments separated by spaces into a single tag will not have the desired effect.

BenchExec allows to check whether the output of the tool matches the expected result
for a given input file, and to categorize the results accordingly.
This is currently only available for the domain of software verification,
where `benchexec` uses a
[property file as defined by the International Competition on Software Verification](http://sv-comp.sosy-lab.org/2015/rules.php).
Such files can be specified with the tag `<propertyfile>`.

Inside the `<option>` tag and other tags some variables can be used
that will be expanded by BenchExec. The following variables are supported:

    ${benchmark_name}       Name of benchmark execution
    ${benchmark_date}       Timestamp of benchmark execution
    ${benchmark_path}       Directory of benchmark XML file
    ${benchmark_path_abs}   Directory of benchmark XML file (absolute path)
    ${benchmark_file}       Name of benchmark XML file (without path)
    ${logfile_path}         Directory where tool-output files will be stored
    ${logfile_path_abs}     Directory where tool-output files will be stored (absolute path)
    ${rundefinition_name}   Name of current run definition
    ${inputfile_name}       Name of current input file (without path)
    ${inputfile_path}       Directory of current input file
    ${inputfile_path_abs}   Directory of current input file (absolute path)

For example, to pass as additional tool parameter the name of a file
that is in the same directory as each input files, use

    <option name="-f">${inputfile_path}/additional-file.txt</option>

#### Adopting benchexec for a specific tool
In order to know how to execute a tool and how to interpret its output,
`benchexec` needs a tool-specific Python module
with functions for creating the appropriate command-line arguments for a run etc.
Such modules need to define a class `Tool` that inherits from `benchexec.tools.template.BaseTool`.
This class also defines the [documentation](benchexec/tools/template.py)
on how to write such a module.
BenchExec already provides such [ready-to-use modules for some common tools](benchexec/tools/).

#### Running benchexec
Command-line arguments to `benchexec` allow to override the defined resource limits.
If one wants to execute only a subset of the defined benchmark runs,
the name of the `<rundefinition>` and/or `<inputfiles>` tags
that should be executed can also be given on the command line.

`benchexec` produces as output the results and resource measurements
of all the individual tool executions in an XML file from which tables
can be created using `table-generator` (by default in directory `./result/`).
A document-type definition with a formal specification of such files can be found in
[doc/benchmark-result.dtd](doc/benchmark-result.dtd).
The output of the tool executions is stored in additional files in a sub-directory.
If the target directory for the output files (specified with `--outputpath`)
is a git repository without uncommitted changes and the option `--commit`
is specified, `benchexec` will add and commit all created files to the git repository.
One can use this to create a reliable archive of experimental results.


### Using table-generator to Generate Tables of Results


### Integration into other Benchmarking Frameworks

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
(c.f. [runexecutor.py](benchexec/runexecutor.py)).
The result is a dictionary with the same information about the run
that is printed to stdout by the `runexec` command-line tool.


### Extending BenchExec

BenchExec executes all runs on the local machine.
In some cases, it might be desired to use for example some cloud service
to execute the commands, and BenchExec should only handle the benchmark definition
and aggregate the results.
This can be done by replacing the module `benchexec.localexecution`,
which is responsible for executing a collection of runs, by something else.
To do so, inherit from the BenchExec main class `benchexec.BenchExec`
and override the necessary methods such as `load_executor`
(which by default returns the `benchexec.localexecution` module),
`create_argument_parser` (to add your own command-line arguments) etc.
