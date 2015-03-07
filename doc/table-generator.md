# BenchExec: table-generator
## Generating Tables of Results

The program `table-generator` allows to generate HTML and CSV tables.
It takes one or more XML files with results from `benchexec`
and produces tables with columns for each of the files,
such that all results for a given input file appear on the same line.
To start it, simply pass all result files on the command line, e.g.

    table-generator results/benchmark-example-rand.*.results.xml

Further command-line arguments can be used to customized the table,
e.g. for ignoring all incorrect results (`--correct-only`),
or for specifying name and location of the table files (`--name`, `--outputpath`).
The full set of available parameters can be seen with `table-generator -h`.

`table-generator` also supports using a special file as input
that defines the layout of the generated tables
and allows even more customizations,
including the ability to extract arbitrary values
from the output of the tool of each run
and inserting them into the table.
Such table-definitition files are also in XML format
and a complete definition can be found in the file
[doc/table-generator.xml](table-generator.xml),
and an example in [doc/table-generator-example.xml](table-generator-example.xml).
A document-type definition with a formal specification of such files can be found in
[doc/table-generator.dtd](table-generator.dtd).
To use such files pass them with the parameter `-x` to `table-generator`:

    table-generator -x doc/table-generator-example.xml
