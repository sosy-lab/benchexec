<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: benchexec

## Benchmarking a Collection of Runs

The program `benchexec` provides the possibility to easily benchmark thousands of executions of a tool in one go.
This document lays out the three major components of this process

  1. Defining a set of runs that should be benchmarked
  2. Running `benchexec` to measure all these runs
  3. Gathering and displaying the results

### Input for benchexec

Effectively, a benchmark comprises a set of runs, where a run means to "execute tool `X` with configuration `Y` on task `Z`".
In order to concisely specify a benchmark comprising a large set of runs, BenchExec provides a custom specification language in the form of XML files, which are described below.

In a nutshell these files reference a particular tool and define one or more different configurations of the tool together with a set of inputs for which the tool (in each of the defined configurations) should be executed.
Every combination of tool configuration and task is then mapped to an actual invocation by a tool-specific module, called *tool-info module* (see [Tool Integration](tool-integration.md)).

In most of the following specifications, BenchExec allows the use of variables, which are replaced by their corresponding values.
All possible variables and their values are explained further below.

#### Benchmark Files

The top level definition of a benchmark is an XML file that defines the command(s) to execute, the resource limits, and the inputs for which the command should be run.
This benchmark-definition file consist of a root tag `<benchmark>`, that defines the tool to use and the resource limits of the benchmark.
For example
```
<benchmark tool="cpachecker" timelimit="4s">
...
</benchmark>
```
declares that this benchmark should execute the tool `cpachecker` with a timelimit of 4 seconds.
(To reference your own tool, you need to add a [tool-info module](tool-integration.md)), which is then associated with such a tool name.)

Within the benchmark tag, different configurations of the tool as well as different sets of inputs can be defined, described in the following.
A complete definition of the input format can be found in the file [doc/benchmark.xml](benchmark.xml), and examples in
  [doc/benchmark-example-rand.xml](benchmark-example-rand.xml),
  [doc/benchmark-example-calculatepi.xml](benchmark-example-calculatepi.xml), and
  [doc/benchmark-example-cbmc.xml](benchmark-example-cbmc.xml).
The document type of these files should be
```XML
<!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec benchmark 1.18//EN" "https://www.sosy-lab.org/benchexec/benchmark-1.18.dtd">
```
A document-type definition with a formal specification of input files can be found in [doc/benchmark.dtd](benchmark.dtd).

#### Tool Configuration

Fixed command-line options for the tool can be specified with `<option>` tags directly inside the root tag.
Repeated `<rundefinition>` tags allow to specify multiple different configurations of the tool, each of which is executed with the tasks.
In other words, a rundefinition effectively is a "template" to be filled with task-specific details.
As an example,
```
<benchmark tool="my_tool" ...>
  <option="--strict" />
  <rundefinition name="default"><option="--mode">default</option></rundefinition>
  <rundefinition name="precise"><option="--mode">precise</option></rundefinition>

  ...
</benchmark>
```
would define two variants of the tool `my_tool`, `default` and `precise`.
The former would execute the tool with `--strict --mode default`, the latter with `--strict --mode precise`.
Both of these will be executed on each of the defined inputs.
Note that you need to use a separate `<option>` tag for each argument, putting multiple arguments separated by spaces into a single tag will not have the desired effect.

#### Task Definition

The concrete tasks (each variant of) the tool should solve are defined in `<tasks>` tags.
One `<tasks>` tag defines a logical group of concrete tasks, e.g. all relevant tasks or all tasks of a particular kind, etc.
Typically (but not necessarily), tasks correspond to an input file for the benchmarked tool.
BenchExec allows for several ways to declare input files.

**Including**:
The easiest way to specify tasks inside a `<tasks>` tag is with the `<include>` tag, which contains a file-name pattern.
One task is created for each file matching the file-name pattern, and the respective file is given to the tool as input file.
As an example
```
<benchmark tool="my_tool" ...>
  <tasks><include>benchmarks/*.in</include></tasks>
</benchmark>
```
would run `my_tool` for each `.in` file in the folder `benchmarks/`.

**Set files**:
Instead of referring directly to input files, the `<tasks>` tag also supports `<includesfile>`, which contain a file-name pattern that points to *set files*.
These files are expected to contain a file-name pattern on each line, and `benchexec` will treat these patterns as specified with `<include>`.
This allows sharing a set of input files across different benchmark definitions.

**Excluding**:
The tags `<exclude>` and `<excludesfile>` can be used to exclude tasks that would otherwise be used by `benchexec`.
If the patterns given inside `<exclude>` or inside an exclude set file match a task, the task will be ignored.

**Tasks without files**:
A task that does not correspond to an input file can be defined with a `<withoutfile>` tag, giving the identifier of the task as tag content.
This might be applicable when the benchmark is completely defined by the tool's options.

**Task options**:
The `<option>` tag can also be specified inside `<tasks>`, which sets the specified command-line options for all runs derived from this set of tasks.

**`.yml` files**
If any file-name pattern points to a `.yml` file, these are instead interpreted in the *task-definition format* of BenchExec, described below.


All of the above tags can be freely combined inside a `<tasks>` tag.
Relative file names in these tags are interpreted as relative to the directory of the XML file, and relative file names inside set files are interpreted as relative to the directory of the set file.

#### Task-Definition Files

For more complex setups, more than a single input file might be required to fully define a task.
To simplify this case, BenchExec supports the [task-definition format](https://gitlab.com/sosy-lab/benchmarking/task-definition-format) version 1 and 2 (cf. also our [example file doc/task-definition-example.yml](task-definition-example.yml)).

A task-definition file may refer to one or more input files and define multiple *properties*.
Each property references a [property file](properties.md) which contains anything relevant to the property.
Combining the given input files together with any of the defined properties defines a concrete task.
The intention is that such task-definition files accompany the input files and compactly represent every interesting problem related or applicable to the input files.

As such, when referencing a task-definition file within `<tasks>`, BenchExec does *not* create one task for each property definition.
Instead, a `<tasks>` definition must specify which property files should be selected.
To this end, specify the tag `<propertyfile>` with a file path (see the referenced examples).
This instructs BenchExec to select all tasks defined by referenced task-definition files which point to this property file (listed as `property_file` in the task-definition files), following symlinks.
<!-- If the `<propertyfile>` tag has an attribute `expectedverdict` with one of the values `true`, `false`, `unknown`, or `false(subproperty)` for some `subproperty`, `benchexec` will ignore tasks where the expected verdict that is declared in the task-definition file does not match. -->
If instead no `<propertyfile>` tag is given in the `<tasks>` definition, one task is created for each task-definition file using the input files defined therein, and any information on properties and expected results is ignored.

The task-definition file can also define `options`, which are also passed to the tool-info modules as is, without further checks.

For creating task-definition files for existing tasks that use the legacy way of encoding expected verdicts in the file name we provide a [helper script](../contrib/create_yaml_files.py).

#### Result Files

The tag `<resultfiles>` inside the `<benchmark>` tag specifies [which files should be copied to the output directory](container.md#retrieving-result-files) (only supported if [container mode](container.md) is not turned off).

#### Variable Replacement

Inside most tags, some variables can be used that will be expanded by BenchExec.
The following variables are supported:

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

### Running benchexec

To use `benchexec`, simply call it with an XML file with a benchmark definition:

    benchexec doc/benchmark-example-rand.xml

Command-line arguments to `benchexec` allow to override the defined resource limits.
If one wants to execute only a subset of the defined benchmark runs, the name of the `<rundefinition>` and/or `<tasks>` tags that should be executed can also be given on the command line.
To start multiple executions of the benchmarked tool in parallel (if the local machine has enough resources), use the parameter `--numOfThreads`.
Example:

    benchexec doc/benchmark-example-rand.xml --tasks "XML files" --limitCores 1 --timelimit 10s --numOfThreads 4

The full set of available parameters can be seen with `benchexec -h`.
For explanation of the parameters for containers, please see [container mode](container.md).

Command-line arguments can additionally be read from a file, if the file name prefixed with `@` is given as argument.
The file needs to contain one argument per line.
If parameter name and value are on the same line, they need to be separated with `=` (not with a space).
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

### Viewing Results

`benchexec` produces as output the results and resource measurements of all the individual tool executions in (compressed) XML files from which tables can be created using `table-generator`.
There is one file per run definition/tool configuration, and additional files for each subset of tasks (all by default in directory `./result/`).
A document-type definition with a formal specification of such result files can be found in [doc/result.dtd](result.dtd), and a description under [Run Results](run-results.md).

The output of the tool executions is stored in separate log files in a ZIP archive beside the XML files.
Storing the log files in an archive avoids producing large amounts of small individual files, which can slow down some file systems significantly.
Furthermore, tool outputs can typically be compressed significantly.

If you prefer uncompressed results, you can pass `--no-compress-results` to `benchexec`, this will let XML files be uncompressed and the log files be stored as regular files in a directory.
Alternatively, you can simply uncompress the results with `bzip2 -d ...results.xml.bz2` and `unzip -x ...logfiles.zip`.
The post-processing of results with `table-generator` supports both compressed and uncompressed files.

If the target directory for the output files (specified with `--outputpath`) is a git repository without uncommitted changes and the option `--commit` is specified, `benchexec` will add and commit all created files to the git repository.
This can be used to create a reliable archive of experimental results.


### Resource Handling

`benchexec` automatically tries to allocate the available hardware resources in the best possible way.
More information on what should be considered when allocating hardware resources such as CPU cores can be found in our paper [Reliable Benchmarking: Requirements and Solutions](https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf).
Some additional technical information is also present in the documentation on [resource handling](resources.md).


### Extending BenchExec

<!-- TODO Should this go into API? -->

BenchExec executes all runs on the local machine.
In some cases, it might be desired to use for example some cloud service to execute the commands, and BenchExec should only handle the benchmark definition and aggregate the results.
This can be done by replacing the module `benchexec.localexecution`, which is responsible for executing a collection of runs, by something else.
To do so, inherit from the BenchExec main class `benchexec.BenchExec` and override the necessary methods such as `load_executor` (which by default returns the `benchexec.localexecution` module), `create_argument_parser` (to add your own command-line arguments) etc.
