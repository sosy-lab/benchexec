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

    table-generator results/benchmark-example-rand.*.results.xml.bz2

Further command-line arguments can be used to customized the table,
e.g. for ignoring all incorrect results (`--correct-only`),
or for specifying name and location of the table files (`--name`, `--outputpath`).
The full set of available parameters can be seen with `table-generator -h`.
Command-line parameters can additionally be read from a file
as [described for benchexec](benchexec.md#starting-benchexec).

The XML result files can be specified either by a local path or by a URL (e.g., HTTP or HTTPS).
Note that if you want to view log files from HTTP(S) URLs in generated tables,
you probably need to set the `Access-Control-Allow-Origin` HTTP header on the server
to avoid problems with the cross-origin policy of the browser.

You can give compressed (GZip and BZip2) as well as uncompressed XML result files to `table-generator`.
Similarly, the log files for the runs can be present in a ZIP archive
(which is the default for `benchexec`),
or in a regular directory with the same name except for the `.zip` suffix.
When clicking on a log-file link in the generated HTML table,
the log file is transparently searched in the directory as well as in the ZIP archive.
Showing log files from ZIP archives needs either JavaScript support in the browser,
or special setup of the web server, for example by using
[serveFileFromZIP.php](https://github.com/sosy-lab/benchexec/blob/master/contrib/serveFileFromZIP.php)
(cf. documentation in this file).
If you want to use direct links to log files, you also need to either unpack the archives
or use a solution like the PHP script.

Alternatively, `table-generator` also supports using a special table-definition file as input
that defines the layout of the generated tables
and allows even more customizations,
for example to have a different set of columns shown for each result file.
This mode also has several more features described below
that allow to customize the content of columns.
Such table-definition files are in XML format
and a complete definition can be found in the file
[doc/table-generator.xml](table-generator.xml),
and an example in [doc/table-generator-example.xml](table-generator-example.xml).
The document type of these files should be

    <!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec table 1.6//EN" "http://www.sosy-lab.org/benchexec/table-1.6.dtd">

A document-type definition with a formal specification of such files can be found in
[doc/table.dtd](table.dtd).
To use such files pass them with the parameter `-x` to `table-generator`
(no result files can be given as these are referenced within the table-definition file):

    table-generator -x doc/table-generator-example.xml

### Column Features

If a table-definition file is used, the `<column>` tags in it provide the following features.

If only the attribute `title` is given and no content of the tag,
the value is taken from the BenchExec result file if present
(this can be used for the default BenchExec columns like `status`, `cputime`, etc.,
but also for additional columns like `score`).
If some content is given for a `<column>` tag,
the respective value is extracted from the tool output of each run
(this needs specific support from the tool-info module that is responsible for this tool).
For example, the following line can be used to extract values for a column "analysis time"
by letting the tool info look for the given pattern in the output
(pattern format is tool specific):

    <column title="analysis time">Total time for analysis: </column>

If the attribute `href` is given, the column will contain a link to the respective target
(variables such as `${inputfile_name}` can be used to customize this link per task).
If `href` specifies a relative path, it is interpreted as relative to the directory
of the table-definition file and will be converted appropriately for the location of the output files.
An absolute URL can also be given.

The attributes `numberOfDigits`, `displayUnit`, and `scaleFactor`
change how numeric values are treated.
`numberOfDigits` specifies the number of significant digits to which a value should be rounded.
The other two attributes allow to convert the value into a different unit (given with `displayUnit`)
by applying the given `scaleFactor`. Currently this is only possible for values without a unit.
For example, this can be used to convert the memory column to MB
by using the following line in a table-definition file:

    <column title="memUsage" displayUnit="MB" scaleFactor="0.000001"/>


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
