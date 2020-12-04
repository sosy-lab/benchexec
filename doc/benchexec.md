<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: benchexec
## Benchmarking a Collection of Runs

The program `benchexec` provides the possibility to easily benchmark
multiple executions of a tool in one go.

### Input for benchexec
`benchexec` uses as input an XML file that defines the command(s) to execute,
the resource limits, and the tasks for which the command should be run.
A complete definition of the input format can be found in the file
[doc/benchmark.xml](benchmark.xml),
and examples in [doc/benchmark-example-rand.xml](benchmark-example-rand.xml),
[doc/benchmark-example-calculatepi.xml](benchmark-example-calculatepi.xml),
and [doc/benchmark-example-cbmc.xml](benchmark-example-cbmc.xml).
The document type of these files should be

```XML
<!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec benchmark 1.18//EN" "https://www.sosy-lab.org/benchexec/benchmark-1.18.dtd">
```

A document-type definition with a formal specification of input files can be found in
[doc/benchmark.dtd](benchmark.dtd).
The benchmark-definition files consist of a root tag `<benchmark>`
that has attributes for the tool to use and the resource limits.
Nested `<rundefinition>` tags allow to specify multiple different configurations of the tool,
each of which is executed with the tasks.
The tasks are defined in nested `<tasks>` tags,
which are explained in the next section.
Command-line arguments for the tool are given with `<option>` tags,
which can appear directly inside the root tag (always effective),
inside a `<rundefinition>` tag (effective for this configuration),
or inside a `<tasks>` tag (effective only for this subset of tasks for all configurations).
Note that you need to use a separate `<option>` tag for each argument,
putting multiple arguments separated by spaces into a single tag will not have the desired effect.

Which tool should be benchmarked by BenchExec is indicated by
the attribute `tool` of the tag `<benchmark>`.
It's value is the name of a so-called *tool-info module*
described in more detail under [Tool Integration](tool-integration.md).

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

If task-definition files are used, the following variables are defined:

    ${taskdef_name}       Name of current task-definition file (without path)
    ${taskdef_path}       Directory of current task-definition file
    ${taskdef_path_abs}   Directory of current task-definition file (absolute path)

Otherwise, these variables can be used:

    ${inputfile_name}       Name of current input file (without path)
    ${inputfile_path}       Directory of current input file
    ${inputfile_path_abs}   Directory of current input file (absolute path)

For example, to pass as additional tool parameter the name of a file
that is in the same directory as each input file, use

```XML
<option name="-f">${inputfile_path}/additional-file.txt</option>
```

The tag `<resultfiles>` inside the `<benchmark>` tag specifies
[which files should be copied to the output directory](container.md#retrieving-result-files)
(only supported if [container mode](container.md) is not turned off).

### Defining Tasks for BenchExec
Typically, tasks for `benchexec` correspond to an input file of the benchmarked tool.
The easiest way to specify tasks inside a `<tasks>` tag is with the `<include>` tag,
which contains a file-name pattern.
If the file-name patterns point to `.yml` files in the task-definition format of BenchExec,
these are parsed by `benchexec` as explained in the following section.
Otherwise, one task is created for each file matching the file-name pattern,
and the respective file is given to the tool as input file.

Inside a `<tasks>` tag there can also exist `<includesfile>` tags,
which contain a file-name pattern that points to so-called "set" files.
These set files are expected to contain a file-name pattern on each line,
and `benchexec` will treat these patterns as specified with `<include>`.

The tags `<exclude>` and `<excludesfile>` can be used to exclude tasks
that would otherwise be used by `benchexec`.
If the patterns given inside `<exclude>` or inside an exclude set file match a task,
the task will be ignored.

A task that does not directly correspond to an input file can be defined
with a `<withoutfile>` tag within a `<tasks>` tag,
giving the identifier of the task as tag content.

All of these tags can be freely combined inside a `<tasks>` tag.
Relative file names in these tags are interpreted as relative to the directory of the XML file,
and relative file names inside set files are interpreted as relative to the directory of the set file.

### Task-Definition Files
Such files can be used to specify more complex tasks,
such as tasks with several input files
or tasks where BenchExec should compare the produced tool output against an expected result.
The files need to be in [YAML format](http://yaml.org/) (which is a superset of JSON)
and their structure needs to adhere to the
[task-definition format](https://gitlab.com/sosy-lab/benchmarking/task-definition-format)
(cf. also our [example file doc/task-definition-example.yml](task-definition-example.yml)).
BenchExec supports versions 1.0 and 2.0 of the format.
For creating task-definition files for existing tasks
that use the legacy way of encoding expected verdicts in the file name
we provide a [helper script](../contrib/create_yaml_files.py).

If no property file is given in the benchmark XML definition,
one task is created for each task-definition file using the input files defined therein,
and any information on properties and expected results is ignored.

If a [property file](properties.md) is given in the benchmark XML definition with the `<propertyfile>` tag,
`benchexec` looks for an item in the `properties` entry of the task definition
that has the same property file listed as `property_file` (symlinks are allowed).
If none is found, the task defined by this task definition is ignored.
Otherwise a task is created using the set of input files from the task definition
and the given property, also using an expected verdict if given for that property.
All other properties defined in the task definition are ignored.
If the `<propertyfile>` tag has an attribute `expectedverdict`
with one of the values `true`, `false`, `unknown`,
or `false(subproperty)` for some `subproperty`,
`benchexec` will ignore tasks where the expected verdict
that is declared in the task-definition file does not match.

The `options` dictionary can optionally contain parameters or information about the task
in an application-specified format.
BenchExec passes the dictionary to tool-info modules as is, without further checks.

### Starting benchexec
To use `benchexec`, simply call it with an XML file with a benchmark definition:

    benchexec doc/benchmark-example-rand.xml

Command-line arguments to `benchexec` allow to override the defined resource limits.
If one wants to execute only a subset of the defined benchmark runs,
the name of the `<rundefinition>` and/or `<tasks>` tags
that should be executed can also be given on the command line.
To start multiple executions of the benchmarked tool in parallel
(if the local machine has enough resources),
use the parameter `--numOfThreads`.
Example:

    benchexec doc/benchmark-example-rand.xml --tasks "XML files" --limitCores 1 --timelimit 10s --numOfThreads 4

The full set of available parameters can be seen with `benchexec -h`.
For explanation of the parameters for containers, please see [container mode](container.md).

Command-line arguments can additionally be read from a file,
if the file name prefixed with `@` is given as argument.
The file needs to contain one argument per line.
If parameter name and value are on the same line,
they need to be separated with `=` (not with a space).
Alternatively, each of them can be put on a separate line.
For example, if the file `benchexec.cfg` has the content

    --tasks
    "XML files"
    --limitCores
    1
    --timelimit
    10s
    --numOfThreads
    4

the following command-line is equivalent to the one above:

    benchexec doc/benchmark-example-rand.xml @benchexec.cfg

### BenchExec Results
`benchexec` produces as output the results and resource measurements
of all the individual tool executions in (compressed) XML files
from which tables can be created using `table-generator`.
There is one file per run definition/tool configuration,
and additional files for each subset of tasks
(all by default in directory `./result/`).
A document-type definition with a formal specification of such result files can be found in
[doc/result.dtd](result.dtd), and a description under [Run Results](run-results.md).

The output of the tool executions is stored in separate log files
in a ZIP archive beside the XML files.
Storing the log files in an archive avoids producing large amounts of small individual files,
which can slow down some file systems significantly.
Furthermore, tool outputs can typically be compressed significantly.

If you prefer uncompressed results, you can pass `--no-compress-results` to `benchexec`,
this will let XML files be uncompressed and the log files be stored as regular files in a directory.
Alternatively, you can simply uncompress the results with `bzip2 -d ...results.xml.bz2`
and `unzip -x ...logfiles.zip`.
The post-processing of results with `table-generator` supports both compressed and uncompressed files.

If the target directory for the output files (specified with `--outputpath`)
is a git repository without uncommitted changes and the option `--commit`
is specified, `benchexec` will add and commit all created files to the git repository.
One can use this to create a reliable archive of experimental results.


### Resource Handling
`benchexec` automatically tries to allocate the available hardware resources
in the best possible way.
More information on what should be considered when allocating hardware resources such as CPU cores
can be found in our paper
[Reliable Benchmarking: Requirements and Solutions](https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf).
Some additional technical information is also present in the documentation on [resource handling](resources.md).


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
