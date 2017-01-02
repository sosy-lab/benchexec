# BenchExec Changelog

## BenchExec 1.9

The main feature of this release is the addition of a [container mode](https://github.com/sosy-lab/benchexec/blob/master/doc/container.md)
that allows to isolate runs from each other and from the host,
for example preventing filesystem and network accesses.
It also allows to collect and store all files created by the tool in a run.
The container mode is still in beta and disabled by default for now,
it will be enabled by default in BenchExec 2.0.
Please try it out and tell us your experiences!

Further changes:
- `table-generator` now supports HTTP(S) URLs to be given for result XML files
  to allow generating tables for results without needing to download them first.
  The HTML tables will contain correct links to the log files.
- New SV-COMP property deadlock supported by `benchexec`.
- The parameters `--rundefinition` and `--tasks` of `benchexec` now support wildcards.
- Rounding of very small and very large values in `table-generator` has been fixed.
- The default font for HTML tables has changed,
  it is now a font that supports correctly aligned digits.

## BenchExec 1.8

- `benchexec` now compresses results by default: XML result files
  are compressed with BZip2, and log files are stored within a ZIP archive.
  This can reduce the necessary disk space significantly
  (typically these logs compress very well),
  and for large benchmark sets it reduces the number of necessary files,
  which can make dealing with the results much faster.
  The previous behavior can be restored with the parameter `--no-compress-results`.
- `table-generator` now supports benchmark results where the log files
  are stored in a ZIP file instead of a regular directory.
  All features continue to work with compressed results,
  including extraction of values from log files and viewing log files from HTML tables
  (cf. [table-generator documentation](https://github.com/sosy-lab/benchexec/blob/master/doc/table-generator.md) for more details).
  Compressed and uncompressed results are handled transparently and can be mixed,
  and using results that were manually compressed or decompressed
  is also supported.

## BenchExec 1.7

- Fix `table-generator` behavior for columns where different cells have different units:
  The release notes for 1.6 claimed that these columns are treated as text column,
  when instead they were rejected. Now they are treated as text.
  Note that BenchExec does not create such columns itself, so this should not affect most users.
- Fix computation of scores according to the SV-COMP scoring scheme:
  if the expected result is for example `false(valid-deref)` and the tool returns `false(valid-free)`,
  the resulting score is the one for a wrong false answer (-16 points),
  not the one for a wrong true answer (-32 points).
  The latter score is only given if the tool actually answers `true` incorrectly.
- Change result classification, if the returned answer does not belong to the property of the task,
  for example, if the tool returns `true` instead of `sat` for a task with category `satisfiability`,
  or if the tool returns `false(no-overflow)` when it should not even check for overflows.
  Now these results are classified as unknown (with score 0),
  previously these were treated as wrong answers.
- Fix escaping of links in HTML tables, e.g., to log files with special characters in their name.
  This was broken in 1.6.

## BenchExec 1.6

This release brings several improvements to `table-generator`:
- `table-generator` now rounds measurement values in a scientifically correct way,
  i.e., with a fixed number of significant digits, not with a fixed number of decimal places.
  The attribute `numberOfDigits` of `<column>` tags in table-definition files
  now also specifies significant digits, not decimal places.
  By default, in HTML tables all fractional values are now rounded (e.g., time measurements)
  and all integer values continue without rounding (e.g., memory measurements),
  previously only "time" columns were rounded.
  The remaining rounding-related behavior stays unchanged:
  In CSV tables, values are not rounded by default,
  and if `numberOfDigits` is explicitly given for a column,
  it's value will always be rounded in both HTML and CSV tables.
- `table-generator` now automatically extracts units from the cells in a column
  and puts them into the table header.
- In HTML tables, numeric values are now aligned at the decimal point,
  and text values are left aligned (previously both were right aligned).
- `table-generator` now allows to convert values from one unit into another.
  So far this is only implemented for values that do not have a unit attached to them,
  and both the target unit and the scale factor need to be specified explicitly
  in the `<column>` tag.
  This can be used for example to show memory measurements in MB instead of Bytes in tables.
- `table-generator` now allows columns with links to arbitrary files to be added to tables.
- `table-generator` does not handle columns where cells have differing units wrongly anymore.
  Previously, the unit was simply dropped, leading to wrong values for statistics.
  Now such columns are treated as text and no statistics are generated.
  (Note that BenchExec never creates such columns by itself,
  only if values are extracted from the tool output this could happen).

Other changes:
- The behavior of `benchexec --timelimit` was changed slightly,
  if a value for `hardtimelimit` was given in the benchmark-definition file.
  If a time limit is specified on the command line, this now overrides both soft and hard time limit.
- Implementation of tool-info modules got easier because the `test_tool_info` helper got improved
  (it now allows to test the function for extracting results from tool outputs).
- Several tool-info modules of tools participating in SV-COMP got improved.
- Simplified cgroups setup for systemd systems.
- Improved documentation.

## BenchExec 1.5

- Improved definition of time and memory limits:
  Both can now be specified including units such as "s", "min" / "MB", "GB".
  to make them easier to read and less ambiguous.
  The old input format without units is still valid.
- runexec now allows enabling other cgroup subsystems and setting arbitrary cgroup options.
- HTML tables gained the possibility for inverting row filters. 
- Improve detection of out-of-memory situations (were not always reported as OOM).
- External resources in HTML tables are loaded from HTTPS URLs
  such that browsers do not complain because of mixed content when viewing tables via HTTPS.
- Improved warnings for swapping and CPU throttling for benchexec.
- Various improvements to internal handling of memory values,
  they are not consistently stored as bytes
  (this only affects extensions of BenchExec, not regular input and output for users).

## BenchExec 1.4

- BenchExec moved to https://github.com/sosy-lab/benchexec
- Fix several bugs in table-generator introduced in version 1.3.
- BenchExec now creates fresh empty directories for $HOME and $TMPDIR
  of all runs, and removes them afterwards.
- table-generator now transparently supports result XML files as input
  that are compressed with GZip or BZip2.
- benchexec now reports some more information as status when a tool crashes,
  e.g. whether it segfaulted or aborted, and what the exit code was
  (previously this was only done for some tools).
- If a tool produces a result but still violates a resource limit,
  this is now shown in the status (but still counted as timeout / out of memory).
- Added dummy tool "calculatepi" that needs no input files and no installation,
  but can be used to create some CPU load and test benchmarking
  (it calculates Pi up some arbitrary number of digits using the tool "bc").
- Renaming "tool wrapper" to "tool info".
  This is mostly an internal and documentation change, but the utility
  `benchexec.test_tool_wrapper` is now named `benchexec.test_tool_info`.

## BenchExec 1.3

- Fix core assignment on AMD Bulldozer/Piledriver Opterons.
- Measure and report CPU time usage per core
  (hidden by default in tables, use `table-generator --all-columns` to show).
- Parameter `--user` allows executing benchmarks under a different user
  (cf. https://github.com/sosy-lab/benchexec/blob/master/doc/separate-user.md).
- Performance improvements for table-generator,
  including parallel processing of input and output files and statistics.
- HTML Tables support filtering rows by task name.
- Improved statistics in HTML tables: median is now the arithmetic median,
  unnecessary rounding removed, standard deviation added,
  and missing results are not counted as "0" but ignored in calculation.
- New utility for testing tool wrappers, making it easier to add support
  for new tools.
- Several new modules for integration of various software verifiers.

## BenchExec 1.2

- BenchExec now records whether TurboBoost was enabled during benchmarking.
- Updated SV-COMP scoring scheme to SV-COMP 2016.
- Support new property 'no-overflow' for SV-COMP 2016.
- Several new modules for integration of various software verifiers.
- Some improvements to CPU-core assignment.

## BenchExec 1.1

- HTML tables produced by table-generator now have a header that stays
  always visible, even when scrolling through the table.
- A Debian package is now created for releases and made available on GitHub.
- Small bug fixes.

## BenchExec 1.0

- Multiple runs for the same file can now be shown in the table in different rows
  if they have different properties or ids.
- Helper files for generating scatter and quantile plots with Gnuplot added.
- Doctype declarations are now used in all XML files.
- Statistics output at end of benchexec run was wrong.

## BenchExec 0.5

- Allow to redirect stdin of the benchmarked tool in runexec / RunExecutor
- Fix bug in measurement of CPU time
  (only occurred in special cases and produced a wrong value below 0.5s)
- Improve utility command for checking cgroups to work around a problem
  with cgrulesngd not handlings threads correctly.

## BenchExec 0.4

- Support for integrating SMTLib 2 compliant SMT solvers and checking the expected output.
- runexec now supports Python 2 again.
- table-generator allows to selected desired output formats and supports output to stdout.
- Added utility command for checking if cgroups have been set up correctly.
- Avoid "false posititive/negative" and use "incorrect false/true" instead.
- Command-line arguments to all tools can be read from a file given with prefix "@".
- Bug fixes and performance improvements.

## BenchExec 0.3

- HTML tables now have header with direct access to plots.
- Maximum score of table is generated again.
- table-generator can now extract statistic values for other tools, too (not only CPAchecker).
- More flexible time limit specifications.
- Warnings shown if system swaps or throttles during benchmarking.
- Improved reliability of benchmarking: forbid swapping, use freezer to kill processes atomically.
- Renamed `<sourcefiles>` tag to `<tasks>` in benchexec input.
- Bug fixes.
- Added documentation.
- Added more tests.


## BenchExec 0.2

- bug fixes
- switch to Python 3 completely


## BenchExec 0.1

Initial version of BenchExec as taken from the repository of CPAchecker.
