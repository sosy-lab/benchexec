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

    <!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec benchmark 1.9//EN" "http://www.sosy-lab.org/benchexec/benchmark-1.9.dtd">

A document-type definition with a formal specification of input files can be found in
[doc/benchmark.dtd](benchmark.dtd).
The benchmark-definition files consist of a root tag `<benchmark>`
that has attributes for the tool to use and the resource limits.
Nested `<rundefinition>` tags allow to specify multiple different configurations of the tool,
each of which is executed with the tasks.
The tasks are defined in nested `<tasks>` tags,
either with `<include>` tags (which directly specify patterns of input files)
or with `<includesfile>` tags (which specify text files with file-name patterns on each line).
Relative file names in these tags are interpreted as relative to the directory of the XML file. 
A task that does not directly correspond to an input file can be defined
with a `<withoutfile>` tag within a `<tasks>` tag,
giving the identifier of the task as tag content.
This can be used for example to declare multiple tasks for the same input file
but with different entry points.
Command-line arguments for the tool are given with `<option>` tags,
which can appear directly inside the root tag (always effective),
inside a `<rundefinition>` tag (affective for this configuration),
or inside a `<tasks>` tag (affective only for this subset of tasks for all configurations).
Note that you need to use a separate `<option>` tag for each argument,
putting multiple arguments separated by spaces into a single tag will not have the desired effect.

Which tool should be benchmarked by BenchExec is indicated by
the attribute `tool` of the tag `<benchmark>`.
It's value is the name of a so-called *tool-info module*
described in more detail under [Tool Integration](tool-integration.md).

BenchExec allows to check whether the output of the tool matches the expected result
for a given task, and to categorize the results accordingly.
To do so, it needs to be given a [property file](properties/INDEX.md)
with the tag `<propertyfile>`
and the name of the input file needs to encode the expected result
for the given property.

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
that is in the same directory as each input file, use

    <option name="-f">${inputfile_path}/additional-file.txt</option>

The tag `<resultfiles>` inside the `<benchmark>` tag specifies
[which files should be copied to the output directory](container.md#retrieving-result-files)
(only supported in [container mode](container.md)).


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
For executing benchmarks under a different user account with the parameter `--user`,
please check the [respective documentation](separate-user.md).

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
[Benchmarking and Resource Measurement](http://www.sosy-lab.org/~dbeyer/Publications/2015-SPIN.Benchmarking_and_Resource_Measurement.pdf).
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
