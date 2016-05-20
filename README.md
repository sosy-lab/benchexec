# BenchExec
## A Framework for Reliable Benchmarking and Resource Measurement

[![Build Status](https://travis-ci.org/sosy-lab/benchexec.svg?branch=master)](https://travis-ci.org/sosy-lab/benchexec)
[![Code Quality](https://api.codacy.com/project/badge/grade/d9926a7a5cb04bcaa8d43caae38a9c36)](https://www.codacy.com/app/PhilippWendler/benchexec)
[![Test Coverage](https://api.codacy.com/project/badge/coverage/d9926a7a5cb04bcaa8d43caae38a9c36)](https://www.codacy.com/app/PhilippWendler/benchexec)
[![PyPI version](https://badge.fury.io/py/benchexec.svg)](https://badge.fury.io/py/benchexec)
[![Apache 2.0 License](https://img.shields.io/badge/license-Apache--2-brightgreen.svg?style=flat)](http://www.apache.org/licenses/LICENSE-2.0)
    
**News**:
- BenchExec 1.9 adds a [container mode](https://github.com/sosy-lab/benchexec/blob/master/doc/container.md)
  that isolates each run from the host system and from other runs
  (disabled by now, will become default in BenchExec 2.0).
- We have published a paper titled
[Benchmarking and Resource Measurement](http://www.sosy-lab.org/~dbeyer/Publications/2015-SPIN.Benchmarking_and_Resource_Measurement.pdf)
on BenchExec and its background
at [SPIN 2015](http://www.spin2015.org/).
It also contains a list of rules that you should always follow when doing benchmarking
(and which BenchExec handles for you).

BenchExec provides three major features:

- execution of arbitrary commands with precise and reliable measurement
  and limitation of resource usage (e.g., CPU time and memory),
  and isolation against other running processes
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
For proper isolation of the benchmarks, it uses Linux [user namespaces](http://man7.org/linux/man-pages/man7/namespaces.7.html)
and an [overlay filesystem](https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt)
to create a [container](https://github.com/sosy-lab/benchexec/blob/master/doc/container.md)
that restricts interference of the executed tool with the benchmarking host.
BenchExec is intended for benchmarking non-interactive tools on Linux systems.
It measures CPU time, wall time, and memory usage of a tool,
and allows to specify limits for these resources.
It also allows to limit the CPU cores and (on NUMA systems) memory regions,
and the container mode allows to restrict filesystem and network access.
In addition to measuring resource usage,
BenchExec can verify that the result of the tool was as expected,
and extract further statistical data from the output.
Results from multiple runs can be combined into CSV and interactive HTML tables,
of which the latter provide scatter and quantile plots
(have a look at our [demo table](https://sosy-lab.github.io/benchexec/example-table/svcomp-simple-cbmc-cpachecker.table.html)).

BenchExec works only on Linux and needs a one-time setup of cgroups by the machine's administrator.
The actual benchmarking can be done by any user and does not need root access.

BenchExec was originally developed for use with the software verification framework
[CPAchecker](http://cpachecker.sosy-lab.org)
and is now developed as an independent project
at the [Software Systems Lab](http://www.sosy-lab.org) at the [University of Passau](http://www.uni-passau.de).

### Links

- [Documentation](https://github.com/sosy-lab/benchexec/tree/master/doc/INDEX.md)
- [Demo](https://sosy-lab.github.io/benchexec/example-table/svcomp-simple-cbmc-cpachecker.table.html) of a result table
- [Downloads](https://github.com/sosy-lab/benchexec/releases)
- [Changelog](https://github.com/sosy-lab/benchexec/tree/master/CHANGELOG.md)
- [BenchExec GitHub Repository](https://github.com/sosy-lab/benchexec),
  use this for [reporting issues and asking questions](https://github.com/sosy-lab/benchexec/issues)
- [BenchExec at PyPI](https://pypi.python.org/pypi/BenchExec)
- Paper [Benchmarking and Resource Measurement](http://www.sosy-lab.org/~dbeyer/Publications/2015-SPIN.Benchmarking_and_Resource_Measurement.pdf) about BenchExec ([supplementary webpage](http://www.sosy-lab.org/~dbeyer/benchmarking/))

### Users of BenchExec

BenchExec was successfully used for benchmarking in all four instances
of the [International Competition on Software Verification](http://sv-comp.sosy-lab.org)
with a wide variety of benchmarked tools and hundreds of thousands benchmark runs.

The developers of the following tools use BenchExec:

- [CPAchecker](http://cpachecker.sosy-lab.org), also for regression testing
- [SMACK](https://github.com/smackers/smack)

If you would like to be listed here, [contact us](https://github.com/sosy-lab/benchexec/issues/new).
