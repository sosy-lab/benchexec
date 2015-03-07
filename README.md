# BenchExec
## A Framework for Reliable Benchmarking and Resource Measurement

[![Build Status](https://travis-ci.org/dbeyer/benchexec.svg?branch=master)](https://travis-ci.org/dbeyer/benchexec)

BenchExec provides three major features:
- execution of arbitrary commands with precise and reliable measurement
  and limitation of resource usage (e.g., CPU time and memory)
- an easy way to define benchmarks with specific tool configurations
  and resource limits,
  and automatically executing them on large sets of input files
- generation of interactive tables and plots for the results

Contrary to other benchmarking frameworks,
it is able to reliably measure and limit resource usage
of the benchmarked tool even if it spawns subprocesses.
In order to achieve this,
it uses the [cgroups feature](https://www.kernel.org/doc/Documentation/cgroups/cgroups.txt)
of the Linux kernel to correctly handle groups of processes.
BenchExec allows to measure CPU time, wall time, and memory usage of a tool,
and to specify limits for these resources.
It also allows to limit the CPU cores and (on NUMA systems) memory regions.
In addition to measuring resource usage,
BenchExec can verify that the result of the tool was as expected,
and extract further statistical data from the output.
Results from multiple runs can be combined into CSV and interactive HTML tables,
of which the latter provide scatter and quantile plots.

BenchExec is intended for benchmarking non-interactive tools on Linux systems.
It was originally developed for use with the software verification framework
[CPAchecker](http://cpachecker.sosy-lab.org).

BenchExec was successfully used for benchmarking in all four instances
of the [International Competition on Software Verification](http://sv-comp.sosy-lab.org)
with a wide variety of benchmarked tools and hundreds of thousands benchmark runs.

BenchExec is developed at the [Software Systems Lab](http://www.sosy-lab.org) at the [University of Passau](http://www.uni-passau.de).

### Links
- [Documentation](https://github.com/dbeyer/benchexec/tree/master/doc/INDEX.md)
- [BenchExec GitHub Repository](https://github.com/dbeyer/benchexec),
  use this for reporting [issues](https://github.com/dbeyer/benchexec/issues)
- [BenchExec at PyPI](https://pypi.python.org/pypi/BenchExec)
