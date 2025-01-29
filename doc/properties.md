<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Property Files

`benchexec` uses so-called property files to determine which result is expected for some task.
This allows to have the same input file be used with different expected results
depending on the given property file.
A property file can be an arbitrary file that is listed in the
[task-definition file](benchexec.md#task-definition-files)
([example](task-definition-example.yml#L22)).
For benchmarking, one selects the property file to be used
in the `<propertyfile>` tag of the [benchmark definition](benchexec.md#input-for-benchexec).
Note that you can use variables in this tag,
for example `<propertyfile>${taskdef_path}/ALL.prp</propertyfile>`
refers to the file `ALL.prp` in the same directory as the respective task-definition file.

The [tool-info module](tool-integration.md) is given the name of the selected property file
and can pass it along to the tool, but it does not need to
(property files can be used without support of the tool).
`benchexec` then looks up the expected result for the selected property file in the task-definition file.
Note that if the tool does not need property files
and `benchexec` should not check the correctness of results,
then property files are not needed at all.

If the used property matches the format of the property files of [SV-COMP](http://sv-comp.sosy-lab.org/2019/rules.php),
`benchexec` will additionally compute scores according to the
[scoring scheme of SV-Comp](http://sv-comp.sosy-lab.org/2019/rules.php#scores).


## Usage without Task-Definition Files

If task-definition files are not used and instead the input files
are given directly in the benchmark definition,
property files can still be specified in the `<propertyfile>` tag,
but `benchexec` will pass them only as parameter to the tool.
It will not check the tool result whether it is as expected
and it will not compute scores.

For creating task-definition files for tasks where the expected result
is encoded in the file name (as it was previously supported by `benchexec`)
we provide a [helper script](../contrib/create_yaml_files.py).
