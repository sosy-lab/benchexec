<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Tool Integration

In order to know how to execute a tool and how to interpret its output,
`benchexec` needs a tool-specific Python module
with functions for creating the appropriate command-line arguments for a run etc.
(called "tool info").

BenchExec already provides such [ready-to-use modules for some common tools](../benchexec/tools/).
If your tool is in that list, you do not need to do anything special.
Simply use the name of the tool-info module (without `.py` suffix)
as the value of the `tool` attribute of the `<benchmark>` tag.

Note that BenchExec needs to be able to find the executable of the tool, of course.
The easiest way to achieve this is to specify the directory of the tool
with the parameter `--tool-directory` on the command line.
If this parameter is not given,
BenchExec searches in the directories of the `PATH` environment variable
and in the current directory.
Thus one can also execute BenchExec directly inside the directory of the tool,
or adjust `PATH` accordingly:

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
that inherits from one of the classes in the module `benchexec.tools.template`.
For compatibility with older tool-info modules, several such classes exist,
but new tool-info modules should inherit from the latest class,
`benchexec.tools.template.BaseTool2`
(for updating older tool-info modules, cf. our
[migration guide](#migrating-tool-info-modules-to-new-api)) at the end of this document.

The `template` module also contains the full [documentation](../benchexec/tools/template.py)
on how to write such a tool-info module.
In the following we provide a short summary.
You can also look at the other [existing tool-info modules](../benchexec/tools/) to see examples.

A minimal tool info needs to overwrite the functions `executable` and `name`.
If the tool gives `true` / `false` answers or customized errors should be shown,
the method `determine_result` needs to be overwritten.
It is recommended to also overwrite the function `version` if the tool has a version
that can be automatically extracted.
A Python doc string ([example](https://github.com/sosy-lab/benchexec/blob/92f10942b884e3ea85ffb66027d98672894796c6/benchexec/tools/template.py#L27-L36))
should be added to the `Tool` class with some short description of the tool.
In this doc string there should also be any additional information about the tool-info module,
such as its supported features
or whether it adds or requires certain command-line parameter of the tool.
It is also recommended to overwrite the function `project_url`
if the tool has a webpage.

Overwrite the functions `cmdline` and `working_directory`, and `environment`
to adjust the respective values, e.g., to add the name of a given property file
to the command-line options.

Overwriting the function `get_value_from_output` will allow you to add
`<column>` tags with custom values to your table-definition files,
and `table-generator` will extract the respective values from the output of
your tool using this function.

If a tool-info module encounters a request that it cannot handle
(e.g., because a tool does not support runs without property files,
but no property file was given),
the tool-info module should raise `benchexec.tools.template.UnsupportedFeatureException`
with an appropriate message for the user.

Note that the tool-info module itself and any commands it starts
will be executed in its own [container](container.md) similar to the actual runs
(except if `--no-container` is used).
This means that the tool-info module typically has no network access
and that any changes made to files will not be seen by the actual runs.


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

    python3 -m benchexec.test_tool_info <TOOL> [--debug] [--tool-output <OUTPUT_FILE>] ...

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
should work and print information about the fake tool `dummy` supplied with BenchExec:

    python3 -m benchexec.test_tool_info dummy

If [container mode](container.md) is not working on your system,
adjust the directory modes as necessary or add `--no-container`.

If you have written your own info for a tool `foobar` as a Python module named `tools.foobar`
(this means you have created a directory `tools` with an empty file `__init__.py`
and a file `foobar.py` with the tool info), the following command tests it:

    python3 -m benchexec.test_tool_info tools.foobar

This assumes that the package `tools` is already in your Python search path,
for example because it is inside the current directory.
If not, you can extend the search path by specifying the *parent* directory
of the package directory in the `PYTHONPATH` environment variable.


### Migrating Tool-Info Modules to new API
It is recommended to upgrade tool-info modules that do not yet inherit from `BaseTool2`
in order to be able to take advantage of new features like `--tool-directory`.
Upgrading should be straight forward in most cases
because the general structure of the APIs defined by `BaseTool` and `BaseTool2`
is the same.
The following assumes familiarity with the API of `BaseTool`
and explains the differences of `BaseTool2`,
it can serve as a step-by-step migration guide.
Everything not mentioned does not need to be changed.

- **General remarks**: Tool-info modules should not rely on any part of BenchExec
  except for what is defined within the `BaseTool2` class
  and the necessary `benchexec.result.RESULT_*` constants.
  Everything else is subject to change.
  In particular, `benchexec.util` should no longer be imported.
- **Class definition**: The tool-info module's class now needs to inherit from
  `benchexec.tools.template.BaseTool2`.
- **Method `executable`**:
  This method now has one parameter, `tool_locator`.
  Instead of calling `benchexec.util.find_executable()`,
  call `tool_locator.find_executable()`.
  If the executable is expected in a subdirectory like `bin`,
  pass the executable name on its own and use the parameter `subdir`
  (Example: `tool_locator.find_executable("foo", subdir="bin")`
  instead of `util.find_executable("foo", "bin/foo")`.)
  If the executable cannot be found,
  `executable` should raise `ToolNotFoundException` now
  (`tool_locator.find_executable()` does that automatically).
- **Method `cmdline`**:
  Previously it was common to have default values for some parameters,
  this is no longer recommended.
  - The parameters `tasks` and `propertyfile` have been replaced with
    one parameter `task` that contains an instance of `BaseTool2.Task`.
    An exact replacement of `tasks` is `list(task.input_files_or_identifier)`,
    though many tool-info modules can use `task.input_files` instead
    to automatically fail if the current task has no input files.
    The property file is available as `task.property_file`.
  - Task-definition files can now contain additional arbitrary information
    in a key named `options`.
    Whatever is contained in this key is passed to the method `cmdline`
    as `task.options`, whereas the parameter `options`
    continues to contain the parameters defined in the benchmark definition
    within `<option>` tags.
  - The parameter `rlimits` is now a proper object instead of a dict,
    cf. documentation of `BaseTool2.ResourceLimits`.
- **Method `determine_result`**:
  There is now only a single parameter `run` that contains
  an instance of `BaseTool2.Run`.
  - The command line of the run is now available as `run.cmdline`.
  - The parameter `returncode` was replaced by `run.exit_code.value`,
    which is `None` instead of `0` if the tool was terminated by a signal.
  - The parameter `returnsignal` was replaced by `run.exit_code.signal`,
    which is `None` instead of `0` if the tool terminated itself.
  - The parameter `output` was replaced by an instance of `BaseTool2.RunOutput`
    in `run.output`.
    This is still a sequence of strings, but without line separators,
    so calling `strip()` while iterating through it is often no longer necessary
    and code like `"result line" in run.output` works as expected.
    `RunOutput` also has additional utility methods.
  - The parameter `isTimeout` was replaced by `run.was_timeout`,
    but more information is now available
    as `run.was_terminated` and `run.termination_reason`.
- **Method `get_value_from_output`**:
  The parameter `lines` (list of strings with line separators) was replaced
  by the parameter `output` that contains an instance of `BaseTool2.RunOutput`
  (list of strings without line separators plus utility methods)
  like for `determine_result`.
