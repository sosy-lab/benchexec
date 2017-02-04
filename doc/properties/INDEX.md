# BenchExec: Property Files

`benchexec` uses so-called property files to determine which result is expected for some task.
This allows to have the same input file be used with different expected results
depending on the given property file.

The following property files are currently supported:

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
This information can be changed without affecting BenchExec.

For properties defined by SV-Comp, BenchExec will automatically use the
[scoring scheme of SV-Comp](http://sv-comp.sosy-lab.org/2017/rules.php#scores)
to compute a score.

The property file that should be used is given with the `<propertyfile>` tag
in the [benchmark definition](../benchexec.md#input-for-benchexec).
Note that you can use variables in this tag,
for example `<propertyfile>${inputfile_path}/ALL.prp</propertyfile>`
refers to the file `ALL.prp` in the same directory as each input file.

The expected result is encoded in the file name of the input file
in the format `_(true|false)-prop` with `prop` as listed above.
Examples can be seen in the [benchmarks of SV-Comp](https://github.com/sosy-lab/sv-benchmarks/tree/master/c).
An exception is checking for satisfiability, where `_sat` and `_unsat`
are used as markers in file names.
