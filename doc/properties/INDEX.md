# BenchExec: Property Files

`benchexec` uses so-called property files to determine which result is expected for some task.
This allows to have the same input file be used with different expected results
depending on the given property file.
A property file can be an arbitrary file that is listed in the
[task-definition file](../benchexec.md#task-definition-files)
([example](../task-definition-example.yml#L22)).
For benchmarking, one selects the property file to be used
in the `<propertyfile>` tag of the [benchmark definition](../benchexec.md#input-for-benchexec).
Note that you can use variables in this tag,
for example `<propertyfile>${taskdef_path}/ALL.prp</propertyfile>`
refers to the file `ALL.prp` in the same directory as the respective task-definition file.

The [tool-info module](../tool-integration.md) is given the name of the selected property file
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

There exists a historical mode of operation for `benchexec`
without task-definition files.
[Starting with BenchExec 3.0](https://github.com/sosy-lab/benchexec/issues/439)
`benchexec` will no longer check for expected results in this mode.
Until then, expected results can be encoded in the name of the input file of each task
and only the specific property files in this directory are valid
if no task-definition files are used:

- [unreach-call](unreach-call.prp): Reachability of an error function in a program (defined by [SV-Comp](http://sv-comp.sosy-lab.org/2017/rules.php))
- [unreach-label](unreach-label.prp): Reachability of an error label in a program (defined by [previous SV-Comp](http://sv-comp.sosy-lab.org/2014/rules.php))
- [valid-memsafety](valid-memsafety.prp): Memory safety of a program ([defined by SV-Comp](http://sv-comp.sosy-lab.org/2017/rules.php))
- [no-overflow](no-overflow.prp): Absence of signed integer overflows in a program ([defined by SV-Comp](http://sv-comp.sosy-lab.org/2017/rules.php))
- [termination](termination.prp): Termination of a program (defined by [SV-Comp](http://sv-comp.sosy-lab.org/2017/rules.php))
- [no-deadlock](no-deadlock.prp): Absence of deadlocks in a program
- [observer-automaton](observer-automaton.prp): Specification given by an additional observer automaton for programs
- [sat](sat.prp): Satisfiability of a formula

The property `valid-memsafety` actually consists of the three properties
`valid-deref`, `valid-free`, and `valid-memtrack`,
which can also be used individually.

Some properties contain additional information,
such as the entry function or the name of the error function to check for reachability.
This information can be changed without affecting BenchExec,
but otherwise the property files cannot be changed in this mode
(use task-definition files if you need arbitrary properties).

The expected result is encoded in the file name of the input file
in the format `_(true|false)-prop` with `prop` as listed above.
An exception is checking for satisfiability, where `_sat` and `_unsat`
are used as markers in file names.
