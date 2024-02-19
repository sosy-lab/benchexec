<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2021 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

This directory contains additional tools, materials, and extensions
that are not part of BenchExec itself
but may be useful for users of BenchExec.

Content:
- `aws-benchmark.py`: BenchExec extension for executing benchmark runs on Amazon's AWS service
- `create_yaml_files.py`: Script for creating task-definition files from old input files that have expected verdicts encoded in the file name
- [`p4-benchmark.py`](p4): BenchExec extension for [P4](https://p4.org/) programs for programmable switches
- [`plots`](plots): Scripts and examples for generating plots from BenchExec results using Gnuplot or PGFPlots for LaTeX
- [`slurm-benchmark.py`](slurm): BenchExec extension for execution benchmark runs via [SLURM](https://slurm.schedmd.com/documentation.html)
- `serveFileFromZIP.php`: Script for letting a web server serve files from a ZIP archive as if the archive would have been expanded. This is useful for hosting HTML tables with results and links to log files in ZIP archives.
- `vcloud-benchmark.py`: BenchExec extension for executing benchmark runs on the VerifierCloud service

Further [contributions](https://github.com/sosy-lab/benchexec/pulls) are welcome!
