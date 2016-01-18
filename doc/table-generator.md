# BenchExec: table-generator
## Generating Tables of Results

The program `table-generator` allows to generate HTML and CSV tables.
You can have a look at a
[demo table](https://sosy-lab.github.io/benchexec/example-table/svcomp-simple-cbmc-cpachecker.table.html)
to see how the result looks like.
`table-generator` takes one or more XML files with results from `benchexec`
and produces tables with columns for each of the files,
such that all results for a given input file appear on the same line.
To start it, simply pass all result files on the command line, e.g.

    table-generator results/benchmark-example-rand.*.results.xml

Further command-line arguments can be used to customized the table,
e.g. for ignoring all incorrect results (`--correct-only`),
or for specifying name and location of the table files (`--name`, `--outputpath`).
The full set of available parameters can be seen with `table-generator -h`.
Command-line parameters can additionally be read from a file
as [described for benchexec](benchexec.md#starting-benchexec).

You can also give compressed XML result files to `table-generator`,
just specify them in the regular way, they will be transparently decompressed.
Currently GZip and BZip2 are supported.

Alternatively, `table-generator` also supports using a special table-definition file as input
that defines the layout of the generated tables
and allows even more customizations,
for example to have a different set of columns shown for each result file.
This mode also includes the ability to extract arbitrary values
from the output of the tool of each run
and insert them into the table.
Such table-definition files are in XML format
and a complete definition can be found in the file
[doc/table-generator.xml](table-generator.xml),
and an example in [doc/table-generator-example.xml](table-generator-example.xml).
The document type of these files should be

    <!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec table 1.0//EN" "http://www.sosy-lab.org/benchexec/table-1.0.dtd">

A document-type definition with a formal specification of such files can be found in
[doc/table.dtd](table.dtd).
To use such files pass them with the parameter `-x` to `table-generator`
(no result files can be given as these are referenced within the table-definition file):

    table-generator -x doc/table-generator-example.xml


### Regression Checking

When given multiple result files, `table-generator` can automatically compute regression counts.
To use this, pass the parameter `--dump`. The console output will then contain lines like this:

    REGRESSIONS 4
    STATS
    338 8 136
    315 8 161
    321 8 155

The number after `REGRESSIONS` is the number of regressions
between the second-to-last and the last result set (in the order they are given as input).
A row in the result table is counted as regression,
if the column `status` is different and the later result is not strictly better than the previous one.
This means that a change from a wrong result to an error is counted as a regression,
as well as a change from an error to a wrong result.
Furthermore, changes between different kinds of errors are also counted as regressions.

It can be useful to additionally pass the parameter `--ignore-flapping-timeout-regressions`.
If it is given, a row with a `timeout` result is not counted as regression
if any previous result for the same task in the table is also `timeout`.

After the line `STATS` there are a few more statistics in the output,
one line for each given result file (in the same order).
Each line contains the counts for the correct, wrong, and other results.
Note that the regression count as output above does not necessarily correspond to a difference
between some of the statistics numbers, but they are useful for example for checking whether there
were any incorrect results.
