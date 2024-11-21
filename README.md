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

**News and Updates**:
- Successful [Google Summer of Code](https://summerofcode.withgoogle.com/) project by
  [Haoran Yang](https://summerofcode.withgoogle.com/programs/2024/projects/UzhlnEel)
  brings integration of [fuse-overlayfs](https://github.com/containers/fuse-overlayfs/) into BenchExec 3.25!  
  This makes BenchExec's default directory configuration for the container mode work out-of-the-box again
  without having to pass parameters such as `--read-only-dir /`.
- BenchExec 3.18 brings support for systems with cgroups v2!
- We now provide an [Ubuntu PPA](https://launchpad.net/~sosy-lab/+archive/ubuntu/benchmarking) that makes installing and upgrading BenchExec easier ([docs](https://github.com/sosy-lab/benchexec/blob/main/doc/INSTALL.md#debianubuntu)).
- An extended version of our paper on BenchExec and its background was published as open access in the journal STTT,
  you can read [Reliable Benchmarking: Requirements and Solutions](https://doi.org/10.1007/s10009-017-0469-y) online.
  We also provide a set of [overview slides](https://www.sosy-lab.org/research/prs/Latest_ReliableBenchmarking.pdf).

> To help new or inexperienced users get started with reliable benchmarking
> right away, we offer a [quickstart guide](doc/quickstart.md) that contains
> a brief explanation of the issues of common setups as well as the (few)
> steps necessary to setup and use BenchExec instead.

BenchExec is a framework for reliable benchmarking and resource measurement
and provides a standalone solution for benchmarking
that takes care of important low-level details for accurate, precise, and reproducible measurements
as well as result handling and analysis for large sets of benchmark runs.
However, even users of other benchmarking frameworks or scripts
can benefit from BenchExec
by letting it perform the resource measurements and limits
instead of less reliable tools and techniques like `time` or `ulimit`,
and results produced by BenchExec can easily be exported for use with other tools.

In particular, BenchExec provides three major features:

- execution of arbitrary commands with precise and reliable measurement
  and limitation of resource usage (e.g., CPU time and memory),
  and isolation against other running processes  
  (provided by [`runexec`](https://github.com/sosy-lab/benchexec/blob/main/doc/runexec.md),
  a replacement for `time` and similar tools)
- an easy way to define benchmarks with specific tool configurations
  and resource limits,
  and automatically executing them on large sets of input files  
  (provided by [`benchexec`](https://github.com/sosy-lab/benchexec/blob/main/doc/benchexec.md)
  on top of `runexec`)
- generation of interactive tables and plots for the results  
  (provided by [`table-generator`](https://github.com/sosy-lab/benchexec/blob/main/doc/table-generator.md)
  for results produced with `benchexec`)


Unlike other benchmarking frameworks,
BenchExec is able to reliably measure and limit resource usage
of the benchmarked tool even if the latter spawns subprocesses.
In order to achieve this,
it uses the [cgroups feature](https://docs.kernel.org/admin-guide/cgroup-v2.html)
of the Linux kernel to correctly handle groups of processes.
For proper isolation of the benchmarks, it uses (if available)
Linux [user namespaces](http://man7.org/linux/man-pages/man7/namespaces.7.html)
and an overlay filesystem
(either [kernel-based](https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt)
or [fuse-overlayfs](https://github.com/containers/fuse-overlayfs/))
to create a [container](https://github.com/sosy-lab/benchexec/blob/main/doc/container.md)
that restricts interference of the executed tool with the benchmarking host.
More information on why this is necessary and the problems with other tools
can be found in our paper
[Reliable Benchmarking: Requirements and Solutions](https://doi.org/10.1007/s10009-017-0469-y) (open access)
and our [slides](https://www.sosy-lab.org/research/prs/Latest_ReliableBenchmarking.pdf)
(starting with slide "Checklist").

BenchExec is intended for benchmarking non-interactive tools on Linux systems.
It measures CPU time, wall time, and memory usage of a tool,
and allows to specify limits for these resources.
It also allows to limit the CPU cores and (on NUMA systems) memory regions,
and the container mode allows to restrict filesystem and network access.
In addition to measuring resource usage,
BenchExec can optionally verify that the result of the tool was as expected
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
- [BenchExec at Zenodo](https://doi.org/10.5281/zenodo.1163552): Each release gets a DOI such that you can reference it from your publications and artifacts.

### Literature

- [Reliable Benchmarking: Requirements and Solutions](https://doi.org/10.1007/s10009-017-0469-y), by D. Beyer, S. Löwe, and P. Wendler.  International Journal on Software Tools for Technology Transfer (STTT), 21(1):1-29, 2019. [doi:10.1007/s10009-017-0469-y](https://doi.org/10.1007/s10009-017-0469-y). Journal paper about BenchExec (open access, also with a [supplementary webpage](https://www.sosy-lab.org/research/benchmarking/) and [overview slides](https://www.sosy-lab.org/research/prs/Latest_ReliableBenchmarking.pdf))
- [CPU Energy Meter: A Tool for Energy-Aware Algorithms Engineering](https://doi.org/10.1007/978-3-030-45237-7_8), by D. Beyer and P. Wendler. In Proc. TACAS 2020, part 2, LNCS 12079, pages 126-133, 2020. Springer. [doi:10.1007/978-3-030-45237-7_8](https://doi.org/10.1007/978-3-030-45237-7_8)
- [Benchmarking and Resource Measurement](https://doi.org/10.1007/978-3-319-23404-5_12), by D. Beyer, S. Löwe, and P. Wendler. In Proc. SPIN 2015, LNCS 9232, pages 160-178, 2015. Springer. [doi:10.1007/978-3-319-23404-5_12](https://doi.org/10.1007/978-3-319-23404-5_12)

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
- [Eshaan Aggarwal](https://github.com/EshaanAgg)
- [Aditya Arora](https://github.com/alohamora)
- [Levente Bajczi](https://github.com/leventeBajczi)
- [Dirk Beyer](https://www.sosy-lab.org/people/beyer/)
- [Laura Bschor](https://github.com/laurabschor)
- [Thomas Bunk](https://github.com/TBunk)
- [Montgomery Carter](https://github.com/MontyCarter)
- [Po-Chun Chien](https://github.com/Po-Chun-Chien)
- [Andreas Donig](https://github.com/adonig)
- [Florian Eder](https://github.com/schroeding)
- [Karlheinz Friedberger](https://www.sosy-lab.org/people/friedberger)
- [Robin Gloster](https://github.com/globin)
- [Sam Grayson](https://github.com/charmoniumQ)
- Peter Häring
- [Florian Heck](https://github.com/fheck)
- [Chinmay Joshi](https://github.com/JawHawk)
- [George Karpenkov](http://metaworld.me/)
- [Mike Kazantsev](http://fraggod.net/)
- [Hugo van Kemenade](https://github.com/hugovk)
- [Tobias Kleinert](https://github.com/Sowasvonbot)
- [Michael Lachner](https://github.com/lachnerm)
- [Thomas Lemberger](https://www.sosy-lab.org/people/lemberger/)
- [Lorenz Leutgeb](https://github.com/lorenzleutgeb)
- [Sebastian Ott](https://github.com/ottseb)
- Stefan Löwe
- [Stephan Lukasczyk](https://github.com/stephanlukasczyk)
- [Tobias Meggendorfer](https://github.com/incaseoftrouble)
- Alexander von Rhein
- [Alexander Schremmer](https://www.xing.com/profile/Alexander_Schremmer)
- [Dennis Simon](https://github.com/DennisSimon)
- [Andreas Stahlbauer](http://stahlbauer.net/)
- [Thomas Stieglmaier](https://stieglmaier.me/)
- [Martin Yankov](https://github.com/marto97)
- [Hojan Young](https://github.com/younghojan)
- [Ilja Zakharov](https://github.com/IljaZakharov)
- and [lots of more people who integrated tools into BenchExec](https://github.com/sosy-lab/benchexec/graphs/contributors)

### Users of BenchExec

Several well-known international competitions use BenchExec,
such as [SMT-COMP](https://smt-comp.github.io/),
[SV-COMP](https://sv-comp.sosy-lab.org) (software verification),
the [Termination Competition](https://termination-portal.org/wiki/Termination_Competition),
and
[Test-Comp](https://test-comp.sosy-lab.org).
In particular in SV-COMP
BenchExec was used successfully for benchmarking in all instances of the competition
and with a wide variety of benchmarked tools and millions of benchmark runs per year.
BenchExec is also integrated into the cluster-based logic-solving service
[StarExec](https://www.starexec.org/starexec/public/about.jsp) ([GitHub](https://github.com/StarExec/StarExec)).

The developers of the following tools use BenchExec:

- [CPAchecker](https://cpachecker.sosy-lab.org), also for regression testing
- [Dartagnan](https://github.com/hernanponcedeleon/Dat3M)
- [ESBMC](https://github.com/esbmc/esbmc), also for regression testing and even with a [GitHub action](https://github.com/esbmc/esbmc/blob/master/.github/workflows/benchexec.yml) for BenchExec
- [SMACK](https://github.com/smackers/smack)
- [SMTInterpol](https://github.com/ultimate-pa/smtinterpol)
- [TriCera](https://github.com/uuverifiers/tricera)
- [Ultimate](https://github.com/ultimate-pa/ultimate)

If you would like to be listed here, [contact us](https://github.com/sosy-lab/benchexec/issues/new).
