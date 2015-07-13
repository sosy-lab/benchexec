# BenchExec Changelog

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
