# BenchExec: benchexec
## Tool Integration

In order to know how to execute a tool and how to interpret its output,
`benchexec` needs a tool-specific Python module
with functions for creating the appropriate command-line arguments for a run etc.
(called "tool info").

BenchExec already provides such [ready-to-use modules for some common tools](../benchexec/tools/).
If your tool is in that list, you do not need to do anything special.
Simply use the name of the tool-info module (without `.py` suffix)
as the value of the `tool` attribute of the `<benchmark>` tag.

Note that BenchExec needs to be able to find the executable of the tool, of course.
By default, it searches in the directories of the `PATH` environment variable and in the current directory.
Thus the easiest way is to run BenchExec directly inside the directory of the tool,
or to adjust `PATH` accordingly:

    PATH=/path/to/tool/directory:$PATH benchexec ...

To debug problems if BenchExec cannot find your tool, use our test utility
described below.


### Writing a Tool-Info Module

For tools that are not supported out-of-the-box by BenchExec,
the tool info needs to be defined.
This is typically just a few lines of Python code.
If you write such a module, please consider sending us
a [pull request](https://github.com/sosy-lab/benchexec/pulls) with it
such that we can include it in BenchExec.

Tool-info modules need to define a class named `Tool`
that inherits from `benchexec.tools.template.BaseTool`.
This base class also contains the [documentation](../benchexec/tools/template.py)
on how to write such a tool-info module.
You can also look at the other files in this directory to see examples
of existing tool infos.

A minimal tool info needs to overwrite the functions `executable`, `name`,
and `determine_result`.
It is recommended to also overwrite the function `version` if the tool has a version
that can be automatically extracted.
Overwrite the functions `cmdline` and `working_directory`, and `environment`
to adjust the respective values, e.g., to add the name of a given property file
to the command-line options.

Overwriting the function `get_value_from_output` will allow you to add
`<column>` tags with custom values to your table-definition files,
and `table-generator` will extract the respective values from the output of
your tool using this function.

#### Specifying a Tool for BenchExec
The name of the tool-info module needs to be given to `benchexec` as the value
of the attribute `tool` of the tag `<benchmark>` of a benchmark-definition file
(note that `runexec` does not use tool infos).

Any of the [supplied tool infos](../benchexec/tools/) can be referenced
with its simple name (file name without `.py` suffix).

If you have checked out BenchExec from source and added your tool info
to the `benchexec/tools/` directory, also use the simple name.
If you have put your tool info as a module somewhere else on the Python search path,
you must specify the full name of the Python module including its package(s).
Note that tool-info modules that are not in a package are not supported.


### Testing the Tool Integration

In order to allow testing a tool info (either self-written or supplied with BenchExec)
and your installation (i.e., whether BenchExec can find your tool),
we provide a small utility that uses a given tool info just like it would be done
during benchmarking, and prints all the information provided by the tool info,
for example which executable is used and in which path it lies,
how the command line is constructed etc.

To execute this utility, run

    python3 -m benchexec.test_tool_info <TOOL> --tool-output <OUTPUT_FILE> ...

`<TOOL>` is the name of a tool-info module
as it would be given in the `tool` attribute of the `<benchmark>` tag.
If necessary, change to the appropriate directory or adjust `PATH` as described above.

The optional flag `--tool-output` activates testing of the function `determine_result`
that should analyze the tool output.
If specified, this option needs to be given at least one file with example output of the tool.

If the utility runs successfully and its output looks sane
(i.e., correct paths, command line, etc.),
then BenchExec should also be able to successfully run the tool.

#### Examples
If you have installed BenchExec successfully, the following command
should always work and print information about the fake tool `rand` supplied with BenchExec:

    python3 -m benchexec.test_tool_info rand

(Note that there are some warnings are expected in this case
because the simplistic tool info for `rand` ignores some irrelevant details.)

If you have written your own info for a tool `foobar` as a Python module named `tools.foobar`
(this means you have created a directory `tools` with an empty file `__init__.py`
and a file `foobar.py` with the tool info), the following command tests it:

    python3 -m benchexec.test_tool_info tools.foobar

This assumes that the package `tools` is already in your Python search path,
for example because it is inside the current directory.
If not, you can extend the search path by specifying the *parent* directory
of the package directory in the `PYTHONPATH` environment variable.
