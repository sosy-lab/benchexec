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
