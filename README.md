<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec
## A Framework for Reliable Benchmarking and Resource Measurement

[![Build Status](https://gitlab.com/sosy-lab/software/benchexec/badges/main/pipeline.svg)](https://gitlab.com/sosy-lab/software/benchexec/pipelines)
[![Apache 2.0 License](https://img.shields.io/badge/license-Apache--2-brightgreen.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![PyPI version](https://img.shields.io/pypi/v/BenchExec.svg)](https://pypi.python.org/pypi/BenchExec)
[![DOI](https://zenodo.org/badge/30758422.svg)](https://zenodo.org/badge/latestdoi/30758422)


**News**:
- Linux kernel 5.11 finally [makes it possible](https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#kernel-requirements) to use all BenchExec features on other distributions than Ubuntu!
- We now provide an [Ubuntu PPA](https://launchpad.net/~sosy-lab/+archive/ubuntu/benchmarking) that makes installing and upgrading BenchExec easier ([docs](https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#debianubuntu)).
- An extended version of our paper on BenchExec and its background was published in [STTT](https://link.springer.com/article/10.1007/s10009-017-0469-y),
  you can read the preprint of [Reliable Benchmarking: Requirements and Solutions](https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf) online.
  We also provide a set of [overview slides](https://www.sosy-lab.org/research/prs/Current_ReliableBenchmarking.pdf).

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
it uses the [cgroups feature](https://www.kernel.org/doc/Documentation/cgroup-v1/cgroups.txt)
of the Linux kernel to correctly handle groups of processes.
For proper isolation of the benchmarks, it uses (if available)
Linux [user namespaces](http://man7.org/linux/man-pages/man7/namespaces.7.html)
and an [overlay filesystem](https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt)
to create a [container](https://github.com/sosy-lab/benchexec/blob/main/doc/container.md)
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
[CPAchecker](https://cpachecker.sosy-lab.org)
and is now developed as an independent project
at the [Software Systems Lab](https://www.sosy-lab.org)
of the [Ludwig-Maximilians-Universität München (LMU Munich)](https://www.uni-muenchen.de).

### Links

- [Documentation](https://github.com/sosy-lab/benchexec/tree/main/doc/INDEX.md)
- [Demo](https://sosy-lab.github.io/benchexec/example-table/svcomp-simple-cbmc-cpachecker.table.html) of a result table
- [Downloads](https://github.com/sosy-lab/benchexec/releases)
- [Changelog](https://github.com/sosy-lab/benchexec/tree/main/CHANGELOG.md)
- [BenchExec GitHub Repository](https://github.com/sosy-lab/benchexec),
  use this for [reporting issues and asking questions](https://github.com/sosy-lab/benchexec/issues)
- [BenchExec at PyPI](https://pypi.python.org/pypi/BenchExec)
- Paper [Reliable Benchmarking: Requirements and Solutions](https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf) about BenchExec ([supplementary webpage](https://www.sosy-lab.org/research/benchmarking/), [slides](https://www.sosy-lab.org/research/prs/Current_ReliableBenchmarking.pdf))

### License and Copyright

BenchExec is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0),
copyright [Dirk Beyer](https://www.sosy-lab.org/people/beyer/).
Exceptions are some tool-info modules
and third-party code that is bundled in the HTML tables,
which are available under several other free licenses
(cf. [folder `LICENSES`](https://github.com/sosy-lab/benchexec/tree/main/LICENSES)).

### Authors
Maintainer: [Philipp Wendler](https://www.philippwendler.de)

Contributors:
- [Aditya Arora](https://github.com/alohamora)
- [Dirk Beyer](https://www.sosy-lab.org/people/beyer/)
- [Laura Bschor](https://github.com/laurabschor)
- [Thomas Bunk](https://github.com/TBunk)
- [Montgomery Carter](https://github.com/MontyCarter)
- [Andreas Donig](https://github.com/adonig)
- [Karlheinz Friedberger](https://www.sosy-lab.org/people/friedberger)
- Peter Häring
- [Florian Heck](https://github.com/fheck)
- [Hugo](https://github.com/hugovk)
- [George Karpenkov](http://metaworld.me/)
- [Mike Kazantsev](http://fraggod.net/)
- [Michael Lachner](https://github.com/lachnerm)
- [Thomas Lemberger](https://www.sosy-lab.org/people/lemberger/)
- [Sebastian Ott](https://github.com/ottseb)
- Stefan Löwe
- [Stephan Lukasczyk](https://github.com/stephanlukasczyk)
- [Alexander von Rhein](http://www.infosun.fim.uni-passau.de/se/people-rhein.php)
- [Alexander Schremmer](https://www.xing.com/profile/Alexander_Schremmer)
- [Dennis Simon](https://github.com/DennisSimon)
- [Andreas Stahlbauer](http://stahlbauer.net/)
- [Thomas Stieglmaier](https://stieglmaier.me/)
- [Martin Yankov](https://github.com/marto97)
- [Ilja Zakharov](https://github.com/IljaZakharov)
- and [lots of more people who integrated tools into BenchExec](https://github.com/sosy-lab/benchexec/graphs/contributors)

### Users of BenchExec

BenchExec was successfully used for benchmarking in all instances
of the international competitions on [Software Verification](https://sv-comp.sosy-lab.org)
and [Software Testing](https://test-comp.sosy-lab.org)
with a wide variety of benchmarked tools and hundreds of thousands benchmark runs.
It is integrated into the cluster-based logic-solving service
[StarExec](https://www.starexec.org/starexec/public/about.jsp) ([GitHub](https://github.com/StarExec/StarExec)).

The developers of the following tools use BenchExec:

- [CPAchecker](https://cpachecker.sosy-lab.org), also for regression testing
- [Dartagnan](https://github.com/hernanponcedeleon/Dat3M)
- [SMACK](https://github.com/smackers/smack)
- [SMTInterpol](https://github.com/ultimate-pa/smtinterpol)
- [Ultimate](https://github.com/ultimate-pa/ultimate)

If you would like to be listed here, [contact us](https://github.com/sosy-lab/benchexec/issues/new).
